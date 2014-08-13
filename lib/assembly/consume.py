"""
Consumes a job from the queue
"""

import copy
import errno
import logging
import pika
import sys
import json
import requests
import os
import shutil
import time
import datetime 
import socket
import multiprocessing
import re
import threading
import subprocess
from plugins import ModuleManager
from job import ArastJob
from multiprocessing import current_process as proc
from traceback import format_tb, format_exc

import assembly as asm
from assembly import ignored
import metadata as meta
import asmtypes
import shock 
import wasp
import recipes
from kbase import typespec_to_assembly_data as kb_to_asm

from ConfigParser import SafeConfigParser

class ArastConsumer:
    def __init__(self, shockurl, rmq_host, rmq_port, arasturl, config, threads, queue, 
                 kill_queue, job_list, ctrl_conf, datapath, binpath):
        self.parser = SafeConfigParser()
        self.parser.read(config)
        self.job_list = job_list
        # Load plugins
        self.pmanager = ModuleManager(threads, kill_queue, job_list, binpath)

    # Set up environment
        self.shockurl = shockurl
        self.arasturl = arasturl
        self.datapath = datapath
        self.rmq_host = rmq_host
        self.rmq_port = rmq_port
        if queue:
            self.queue = queue
            logging.info('Using queue:{}'.format(self.queue))
        else:
            self.queue = self.parser.get('rabbitmq','default_routing_key')
        self.min_free_space = float(self.parser.get('compute','min_free_space'))
        m = ctrl_conf['meta']        
        a = ctrl_conf['assembly']
        
        collections = {'jobs': m.get('mongo.collection'),
                       'auth': m.get('mongo.collection.auth'),
                       'data': m.get('mongo.collection.data'),
                       'running': m.get('mongo.collection.running')}

        ###### TODO Use REST API
        self.metadata = meta.MetadataConnection(arasturl, int(a['mongo_port']), m['mongo.db'],
                                                collections)
        self.gc_lock = multiprocessing.Lock()

    def garbage_collect(self, datapath, user, required_space):
        """ Monitor space of disk containing DATAPATH and delete files if necessary."""
        self.gc_lock.acquire()
        s = os.statvfs(datapath)
        free_space = float(s.f_bsize * s.f_bavail)
        logging.debug("Free space in bytes: %s" % free_space)
        logging.debug("Required space in bytes: %s" % required_space)
        while ((free_space - self.min_free_space) < required_space):
            #Delete old data
            dirs = os.listdir(os.path.join(datapath, user))
            times = []
            for dir in dirs:
                times.append(os.path.getmtime(os.path.join(datapath, user, dir)))
            if len(dirs) > 0:
                old_dir = os.path.join(datapath, user, dirs[times.index(min(times))])
                shutil.rmtree(old_dir, ignore_errors=True)
            else:
                logging.error("No more directories to remove")
                break
            logging.info("Space required.  %s removed." % old_dir)
            s = os.statvfs(datapath)
            free_space = float(s.f_bsize * s.f_bavail)
            logging.debug("Free space in bytes: %s" % free_space)
        self.gc_lock.release()

    def get_data(self, body):
        """Get data from cache or Shock server."""
        params = json.loads(body)
        logging.info('New Data Format')
        return self._get_data(body)

    def _get_data(self, body):
        params = json.loads(body)
        filepath = os.path.join(self.datapath, params['ARASTUSER'],
                                str(params['data_id']))
        datapath = filepath
        filepath += "/raw/"
        all_files = []
        user = params['ARASTUSER']
        token = params['oauth_token']
        uid = params['_id']

        ##### Get data from ID #####
        data_doc = self.metadata.get_data_docs(params['ARASTUSER'], params['data_id'])
        if not data_doc:
            raise Exception('Invalid Data ID: {}'.format(params['data_id']))
        logging.debug('data_doc')
        logging.debug(data_doc)
        if 'kbase_assembly_input' in data_doc:
            params['assembly_data'] = kb_to_asm(data_doc['kbase_assembly_input'])
        elif 'assembly_data' in data_doc:
            params['assembly_data'] = data_doc['assembly_data']

        ##### Get data from assembly_data #####
        self.metadata.update_job(uid, 'status', 'Data transfer')
        with ignored(OSError):
            os.makedirs(filepath)

          ### TODO Garbage collect ###
        download_url = 'http://{}'.format(self.shockurl)
        file_sets = params['assembly_data']['file_sets']
        for file_set in file_sets:
            if file_set['type'] == 'paired_url':
                file_set['type'] = 'paired'
            elif file_set['type'] == 'single_url':
                file_set['type'] = 'single'
            elif file_set['type'] == 'reference_url':
                file_set['type'] = 'reference'
            file_set['files'] = [] #legacy
            for file_info in file_set['file_infos']:
                #### File is stored on Shock
                if file_info['filename']:
                    local_file = os.path.join(filepath, file_info['filename'])
                    if os.path.exists(local_file):
                        local_file = extract_file(local_file)
                        logging.info("Requested data exists on node: {}".format(local_file))
                    else:
                        local_file = self.download_shock(download_url, user, token, 
                                                   file_info['shock_id'], filepath)
                elif file_info['direct_url']:
                    local_file = os.path.join(filepath, os.path.basename(file_info['direct_url']))
                    if os.path.exists(local_file):
                        local_file = extract_file(local_file)
                        logging.info("Requested data exists on node: {}".format(local_file))
                    else:
                        local_file = self.download_url(file_info['direct_url'], filepath)
                file_info['local_file'] = local_file
                file_set['files'].append(local_file) #legacy
            all_files.append(file_set)
        return datapath, all_files                    

    def compute(self, body):
        error = False
        params = json.loads(body)
        job_id = params['job_id']
        uid = params['_id']
        user = params['ARASTUSER']
        token = params['oauth_token']
        pipelines = params['pipeline']
        recipe = params.get('recipe')
        wasp_in = params.get('wasp')

        #support legacy arast client
        if len(pipelines) > 0:
            if type(pipelines[0]) is not list:
                pipelines = [pipelines]
                
        ### Download files (if necessary)
        datapath, all_files = self.get_data(body)
        rawpath = datapath + '/raw/'
        jobpath = os.path.join(datapath, str(job_id))
        
        try:
            os.makedirs(jobpath)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        ### Create job log
        self.out_report_name = '{}/{}_report.txt'.format(jobpath, str(job_id))
        self.out_report = open(self.out_report_name, 'w')

        ### Create data to pass to pipeline
        reads = []
        reference = []
        for fileset in all_files:
            if len(fileset['files']) != 0:
                if (fileset['type'] == 'single' or 
                    fileset['type'] == 'paired'):
                    reads.append(fileset)
                elif fileset['type'] == 'reference':
                    reference.append(fileset)
                else:
                    raise Exception('fileset error')

        job_data = ArastJob({'job_id' : params['job_id'], 
                    'uid' : params['_id'],
                    'user' : params['ARASTUSER'],
                    'reads': reads,
                    'logfiles': [],
                    'reference': reference,
                    'initial_reads': list(reads),
                    'raw_reads': copy.deepcopy(reads),
                    'params': [],
                    'exceptions': [],
                    'pipeline_data': {},
                    'datapath': datapath,
                    'out_report' : self.out_report})
                    
        self.out_report.write("Arast Pipeline: Job {}\n".format(job_id))
        self.job_list.append(job_data)
        self.start_time = time.time()

        timer_thread = UpdateTimer(self.metadata, 29, time.time(), uid, self.done_flag)
        timer_thread.start()
        
        url = "http://%s" % (self.shockurl)
        status = ''
        logging.debug('Job Data') 
        logging.debug(job_data) 

        #### Parse pipeline to wasp exp
        reload(recipes)
        if recipe:
            try: wasp_exp = recipes.get(recipe[0], job_id)
            except AttributeError: raise Exception('"{}" recipe not found.'.format(recipe[0]))
        elif wasp_in:
            wasp_exp = wasp_in[0]
        elif pipelines[0] == 'auto':
            wasp_exp = recipes.get('auto', job_id)
        else:
            all_pipes = []
            for p in pipelines:
                all_pipes += self.pmanager.parse_input(p)
            print all_pipes
            wasp_exp = wasp.pipelines_to_exp(all_pipes, params['job_id'])
            logging.info('Wasp Expression: {}'.format(wasp_exp))
        print('Wasp Expression: {}'.format(wasp_exp))
        w_engine = wasp.WaspEngine(self.pmanager, job_data, self.metadata)


        ###### Run Job
        try: 
            w_engine.run_expression(wasp_exp, job_data)
            ###### Upload all result files and place them into appropriate tags
            uploaded_fsets = job_data.upload_results(url, token)

            for i, job in enumerate(self.job_list):
                if job['user'] == job_data['user'] and job['job_id'] == job_data['job_id']:
                    self.job_list.pop(i)

            # Format report
            new_report = open('{}.tmp'.format(self.out_report_name), 'w')

            ### Log errors
            if len(job_data['errors']) > 0:
                new_report.write('PIPELINE ERRORS\n')
                for i,e in enumerate(job_data['errors']):
                    new_report.write('{}: {}\n'.format(i, e))
            try: ## Get Quast output
                quast_report = job_data['wasp_chain'].find_module('quast')['data'].find_type('report')[0].files[0]
                with open(quast_report) as q:
                    new_report.write(q.read())
            except:
                new_report.write('No Summary File Generated!\n\n\n')
            self.out_report.close()
            with open(self.out_report_name) as old:
                new_report.write(old.read())

            for log in job_data['logfiles']:
                new_report.write('\n{1} {0} {1}\n'.format(os.path.basename(log), '='*20))
                with open(log) as l:
                    new_report.write(l.read())

            ### Log tracebacks
            if len(job_data['tracebacks']) > 0:
                new_report.write('EXCEPTION TRACEBACKS\n')
                for i,e in enumerate(job_data['tracebacks']):
                    new_report.write('{}: {}\n'.format(i, e))

            new_report.close()
            os.remove(self.out_report_name)
            shutil.move(new_report.name, self.out_report_name)
            res = self.upload(url, user, token, self.out_report_name)
            report_info = asmtypes.FileInfo(self.out_report_name, shock_url=url, shock_id=res['data']['id'])

            self.metadata.update_job(uid, 'report', [asmtypes.set_factory('report', [report_info])])
            status = 'Complete with errors' if job_data.get('errors') else 'Complete'

            ## Make compatible with JSON dumps()
            del job_data['out_report']
            del job_data['initial_reads']
            del job_data['raw_reads']
            self.metadata.update_job(uid, 'data', job_data)
            self.metadata.update_job(uid, 'result_data', uploaded_fsets)

            ###### Legacy Support #######
            filesets = uploaded_fsets.append(asmtypes.set_factory('report', [report_info]))
            contigsets = [fset for fset in uploaded_fsets if fset.type == 'contigs' or fset.type == 'scaffolds']
            download_ids = {fi['filename']: fi['shock_id'] for fset in uploaded_fsets for fi in fset['file_infos']}
            contig_ids = {fi['filename']: fi['shock_id'] for fset in contigsets for fi in fset['file_infos']}
            self.metadata.update_job(uid, 'result_data_legacy', [download_ids])
            self.metadata.update_job(uid, 'contig_ids', [contig_ids])
            ###################

            print '============== JOB COMPLETE ==============='
        except asmtypes.ArastUserInterrupt:
            status = 'Terminated by user'
            print '============== JOB KILLED ==============='
        self.metadata.update_job(uid, 'status', status)

    def upload(self, url, user, token, file, filetype='default'):
        files = {}
        files["file"] = (os.path.basename(file), open(file, 'rb'))
        logging.debug("Message sent to shock on upload: %s" % files)
        sclient = shock.Shock(url, user, token)
        if filetype == 'contigs' or filetype == 'scaffolds':
            res = sclient.upload_contigs(file)
        else:
            res = sclient.upload_misc(file, filetype)
        return res

    def download_shock(self, url, user, token, node_id, outdir):
        sclient = shock.Shock(url, user, token)
        downloaded = sclient.curl_download_file(node_id, outdir=outdir)
        return extract_file(downloaded)

    def download_url(self, url, outdir):
        downloaded = asm.curl_download_url(url, outdir=outdir)
        return extract_file(downloaded)

    def fetch_job(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=self.rmq_host, port=self.rmq_port))
        channel = connection.channel()
        channel.basic_qos(prefetch_count=1)
        result = channel.queue_declare(queue=self.queue,
                                       exclusive=False,
                                       auto_delete=False,
                                       durable=True)
        logging.basicConfig(format=("%(asctime)s %s %(levelname)-8s %(message)s",proc().name))
        print proc().name, ' [*] Fetching job...'

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(self.callback,
                              queue=self.queue)

        channel.start_consuming()

    def callback(self, ch, method, properties, body):
        params = json.loads(body)
        display = ['ARASTUSER', 'job_id', 'message']
        print ' [+] Incoming:', ', '.join(['{}: {}'.format(k, params[k]) for k in display])
        logging.info(params)
        job_doc = self.metadata.get_job(params['ARASTUSER'], params['job_id'])
        uid = job_doc['_id']
        ## Check if job was not killed
        if job_doc['status'] == 'Terminated':
            print 'Job {} was killed, skipping'.format(params['job_id'])
        else:
            self.done_flag = threading.Event()
            try:
                self.compute(body)
            except Exception as e:
                tb = format_exc()
                status = "[FAIL] {}".format(e)
                print e
                print logging.error(tb) 
                self.metadata.update_job(uid, 'status', status)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        self.done_flag.set()

    def start(self):
        self.fetch_job()


### Helper functions ###
def touch(path):
    now = time.time()
    try:
        # assume it's there
        os.utime(path, (now, now))
    except os.error:
        # if it isn't, try creating the directory,
        # a file with that name
        os.makedirs(os.path.dirname(path))
        open(path, "w").close()
        os.utime(path, (now, now))
    
def extract_file(filename):
    """ Decompress files if necessary """
    root_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', '..'))
    module_bin_path = os.path.join(root_path, "module_bin")
    unp_bin = os.path.join(module_bin_path, 'unp')

    filepath = os.path.dirname(filename)
    supported = ['tar.gz', 'tar.bz2', 'bz2', 'gz', 'lz', 
                 'rar', 'tar', 'tgz','zip']
    for ext in supported:
        if filename.endswith(ext):
            extracted_file = filename[:filename.index(ext)-1]
            if os.path.exists(extracted_file): # Check extracted already
                return extracted_file
            logging.debug("Extracting %s" % filename)
            p = subprocess.Popen([unp_bin, filename], 
                                 cwd=filepath, stderr=subprocess.STDOUT)
            p.wait()
            if os.path.exists(extracted_file):
                return extracted_file
            else:
                print "{} does not exist!".format(extracted_file)
                raise Exception('Archive structure error')
    logging.debug("Could not extract %s" % filename)
    return filename            

def is_filename(word):
    return word.find('.') != -1 and word.find('=') == -1

class UpdateTimer(threading.Thread):
    """ Thread for updating time in the mongodb record (for arast stat). """
    def __init__(self, meta_obj, update_interval, start_time, uid, done_flag):
        self.meta = meta_obj
        self.interval = update_interval
        self.uid = uid
        self.start_time = start_time
        self.done_flag = done_flag
        threading.Thread.__init__(self)

    def run(self):
        while True:
            if self.done_flag.is_set():
                logging.info('Stopping Timer Thread')
                elapsed_time = time.time() - self.start_time
                ftime = str(datetime.timedelta(seconds=int(elapsed_time)))
                self.meta.update_job(self.uid, 'computation_time', ftime)
                self.meta.rjob_remove(self.uid)
                return
            elapsed_time = time.time() - self.start_time
            ftime = str(datetime.timedelta(seconds=int(elapsed_time)))
            self.meta.update_job(self.uid, 'computation_time', ftime)
            self.meta.rjob_update_timestamp(self.uid)
            if int(elapsed_time) < self.interval:
                time.sleep(3)
            else:
                time.sleep(self.interval)
