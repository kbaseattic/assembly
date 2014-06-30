"""
Consumes a job from the queue
"""

import copy
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
import metadata as meta
import asmtypes
import shock 
import wasp
import recipes
from kbase import typespec_to_assembly_data as kb_to_asm

from ConfigParser import SafeConfigParser

class ArastConsumer:
    def __init__(self, shockurl, arasturl, config, threads, queue, kill_queue, job_list, ctrl_conf, datapath):
        self.parser = SafeConfigParser()
        self.parser.read(config)
        self.job_list = job_list
        # Load plugins
        binpath = self.parser.get('compute','binpath')
        self.pmanager = ModuleManager(threads, kill_queue, job_list, binpath)

    # Set up environment
        self.shockurl = shockurl
        self.arasturl = arasturl
        self.datapath = datapath
        if queue:
            self.queue = queue
            logging.info('Using queue:{}'.format(self.queue))
        else:
            self.queue = self.parser.get('rabbitmq','default_routing_key')
        self.min_free_space = float(self.parser.get('compute','min_free_space'))
        m = ctrl_conf['meta']        
        a = ctrl_conf['assembly']
        

        ###### TODO Use REST API
        self.metadata = meta.MetadataConnection(arasturl, int(a['mongo_port']), m['mongo.db'],
                                                m['mongo.collection'], m['mongo.collection.auth'], m['mongo.collection.data'] )
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
        if ('assembly_data' in params or
            params['version'] == 'widget'):
            logging.info('New Data Format')
            return self._get_data(body)

        else:
            return self._get_data_old(body)

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

        if 'kbase_assembly_input' in data_doc:
            params['assembly_data'] = kb_to_asm(data_doc['kbase_assembly_input'])
        elif 'assembly_data' in data_doc:
            params['assembly_data'] = data_doc['assembly_data']

        ##### Get data from assembly_data #####
        self.metadata.update_job(uid, 'status', 'Data transfer')
        try:os.makedirs(filepath)
        except:pass
            
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
                        logging.info("Requested data exists on node: {}".format(local_file))
                    else:
                        local_file = self.download_shock(download_url, user, token, 
                                                   file_info['shock_id'], filepath)
                elif file_info['direct_url']:
                    local_file = os.path.join(filepath, os.path.basename(file_info['direct_url']))
                    if os.path.exists(local_file):
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
        recipe = None
        wasp_in = None
        try: ## In case legacy
            recipe = params['recipe']
            wasp_in = params['wasp']
        except:pass

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
        except Exception as e:
            print e
            raise Exception ('Data Error')

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

        #### Parse pipeline to wasp exp
        wasp_exp = pipelines[0][0]
        if recipe:
            try: wasp_exp = recipes.get(recipe[0])
            except AttributeError: raise Exception('"{}" recipe not found.'.format(recipe[0]))
        elif wasp_in:
            wasp_exp = wasp_in[0]
        elif pipelines[0] == 'auto':
            wasp_exp = recipes.get('auto')
        else:
            all_pipes = []
            for p in pipelines:
                all_pipes += self.pmanager.parse_input(p)
            print all_pipes
            wasp_exp = wasp.pipelines_to_exp(all_pipes, params['job_id'])
            logging.info('Wasp Expression: {}'.format(wasp_exp))
        print('Wasp Expression: {}'.format(wasp_exp))
        w_engine = wasp.WaspEngine(self.pmanager, job_data, self.metadata)
        w_engine.run_expression(wasp_exp, job_data)

        ###### Upload all result files and place them into appropriate tags
        uploaded_fsets = job_data.upload_results(url, token)
        
        for i, job in enumerate(self.job_list):
            if job['user'] == job_data['user'] and job['job_id'] == job_data['job_id']:
                self.job_list.pop(i)


        # Format report
        new_report = open('{}.tmp'.format(self.out_report_name), 'w')

        ### Log exceptions
        if len(job_data['exceptions']) > 0:
            new_report.write('PIPELINE ERRORS\n')
            for i,e in enumerate(job_data['exceptions']):
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
        new_report.close()
        os.remove(self.out_report_name)
        shutil.move(new_report.name, self.out_report_name)
        res = self.upload(url, user, token, self.out_report_name)
        report_info = asmtypes.FileInfo(self.out_report_name, shock_url=url, shock_id=res['data']['id'])

        self.metadata.update_job(uid, 'report', [asmtypes.set_factory('report', [report_info])])
        status = 'Complete with errors' if job_data['exceptions'] else 'Complete'

        ## Make compatible with JSON dumps()
        del job_data['out_report']
        del job_data['initial_reads']
        del job_data['raw_reads']
        self.metadata.update_job(uid, 'data', job_data)
        self.metadata.update_job(uid, 'result_data', uploaded_fsets)
        self.metadata.update_job(uid, 'status', status)

        ###### Legacy Support #######
        filesets = uploaded_fsets.append(asmtypes.set_factory('report', [report_info]))
        contigsets = [fset for fset in uploaded_fsets if fset.type == 'contigs' or fset.type == 'scaffolds']
        download_ids = {fi['filename']: fi['shock_id'] for fset in uploaded_fsets for fi in fset['file_infos']}
        contig_ids = {fi['filename']: fi['shock_id'] for fset in contigsets for fi in fset['file_infos']}
        self.metadata.update_job(uid, 'result_data_legacy', [download_ids])
        self.metadata.update_job(uid, 'contig_ids', [contig_ids])
        ###################

        print '============== JOB COMPLETE ==============='

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
                host = self.arasturl))
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

###### Legacy Support ######

    def _get_data_old(self, body):
        params = json.loads(body)
        #filepath = self.datapath + str(params['data_id'])
        filepath = os.path.join(self.datapath, params['ARASTUSER'],
                                str(params['data_id']))
        datapath = filepath
        filepath += "/raw/"
        all_files = []

        uid = params['_id']
        job_id = params['job_id']
        user = params['ARASTUSER']

        data_doc = self.metadata.get_doc_by_data_id(params['data_id'], params['ARASTUSER'])
        if data_doc:
            paired = data_doc['pair']
            single = data_doc['single']
            files = data_doc['filename']
            ids = data_doc['ids']
            token = params['oauth_token']
            try:
                ref = data_doc['reference']
            except:
                pass
        else:
            self.metadata.update_job(uid, 'status', 'Invalid Data ID')
            raise Exception('Data {} does not exist on Shock Server'.format(
                    params['data_id']))

        all_files = []
        if os.path.isdir(filepath):
            logging.info("Requested data exists on node")
            try:
                for l in paired:
                    filedict = {'type':'paired', 'files':[]}
                    for word in l:
                        if is_filename(word):
                            baseword = os.path.basename(word)
                            filedict['files'].append(
                                extract_file(os.path.join(filepath,  baseword)))
                        else:
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                    all_files.append(filedict)
            except:
                logging.info('No paired files submitted')

            try:
                for seqfiles in single:
                    for wordpath in seqfiles:
                        filedict = {'type':'single', 'files':[]}    
                        if is_filename(wordpath):
                            baseword = os.path.basename(wordpath)
                            filedict['files'].append(
                                extract_file(os.path.join(filepath, baseword)))
                        else:
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                        all_files.append(filedict)
            except:
                logging.info(format_tb(sys.exc_info()[2]))
                logging.info('No single files submitted!')
            
            try:
                for r in ref:
                    for wordpath in r:
                        filedict = {'type':'reference', 'files':[]}    
                        if is_filename(wordpath):
                            baseword = os.path.basename(wordpath)
                            filedict['files'].append(
                                extract_file(os.path.join(filepath, baseword)))
                        else:
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                        all_files.append(filedict)
            except:
                logging.info(format_tb(sys.exc_info()[2]))
                logging.info('No reference files submitted!')
            
    
            touch(datapath)

        ## Data does not exist on current compute node
        else:
            self.metadata.update_job(uid, 'status', 'Data transfer')
            os.makedirs(filepath)

            # Get required space and garbage collect
            try:
                req_space = 0
                for file_size in data_doc['file_sizes']:
                    req_space += file_size
                self.garbage_collect(self.datapath, user, req_space)
            except:
                pass 
            url = "http://%s" % (self.shockurl)

            try:
                for l in paired:
                    #FILEDICT contains a single read library's info
                    filedict = {'type':'paired', 'files':[]}
                    for word in l:
                        if is_filename(word):
                            baseword = os.path.basename(word)
                            dl = self.download_shock(url, user, token, 
                                               ids[files.index(baseword)], filepath)
                            if shock.parse_handle(dl): #Shock handle, get real data
                                logging.info('Found shock handle, getting real data...')
                                s_addr, s_id = shock.parse_handle(dl)
                                s_url = 'http://{}'.format(s_addr)
                                real_file = self.download_shock(s_url, user, token, 
                                                          s_id, filepath)
                                filedict['files'].append(real_file)
                            else:
                                filedict['files'].append(dl)
                        elif re.search('=', word):
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                    all_files.append(filedict)
            except:
                logging.info(format_exc(sys.exc_info()))
                logging.info('No paired files submitted')

            try:
                for seqfiles in single:
                    for wordpath in seqfiles:
                        filedict = {'type':'single', 'files':[]}
                        # Parse user directories
                        try:
                            path, word = wordpath.rsplit('/', 1)
                            path += '/'
                        except:
                            word = wordpath
                            path = ''

                        if is_filename(word):
                            baseword = os.path.basename(word)
                            dl = self.download_shock(url, user, token, 
                                               ids[files.index(baseword)], filepath)
                            if shock.parse_handle(dl): #Shock handle, get real data
                                logging.info('Found shock handle, getting real data...')
                                s_addr, s_id = shock.parse_handle(dl)
                                s_url = 'http://{}'.format(s_addr)
                                real_file = self.download_shock(s_url, user, token, 
                                                          s_id, filepath)
                                filedict['files'].append(real_file)
                            else:
                                filedict['files'].append(dl)
                        elif re.search('=', word):
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                        all_files.append(filedict)
            except:
                logging.info(format_exc(sys.exc_info()))
                logging.info('No single end files submitted')

            try:
                for r in ref:
                    for wordpath in r:
                        filedict = {'type':'reference', 'files':[]}
                        # Parse user directories
                        try:
                            path, word = wordpath.rsplit('/', 1)
                            path += '/'
                        except:
                            word = wordpath
                            path = ''

                        if is_filename(word):
                            baseword = os.path.basename(word)
                            dl = self.download_shock(url, user, token, 
                                               ids[files.index(baseword)], filepath)
                            if shock.parse_handle(dl): #Shock handle, get real data
                                logging.info('Found shock handle, getting real data...')
                                s_addr, s_id = shock.parse_handle(dl)
                                s_url = 'http://{}'.format(s_addr)
                                real_file = self.download_shock(s_url, user, token, 
                                                          s_id, filepath)
                                filedict['files'].append(real_file)
                            else:
                                filedict['files'].append(dl)
                        elif re.search('=', word):
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                        all_files.append(filedict)
            except:
                #logging.info(format_exc(sys.exc_info()))
                logging.info('No single end files submitted')

        return datapath, all_files



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
    filepath = os.path.dirname(filename)
    supported = ['tar.gz', 'tar.bz2', 'bz2', 'gz', 'lz', 
                 'rar', 'tar', 'tgz','zip']
    for ext in supported:
        if filename.endswith(ext):
            extracted_file = filename[:filename.index(ext)-1]
            if os.path.exists(extracted_file): # Check extracted already
                return extracted_file
            logging.debug("Extracting %s" % filename)
            p = subprocess.Popen(['unp', filename], 
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
                return
            elapsed_time = time.time() - self.start_time
            ftime = str(datetime.timedelta(seconds=int(elapsed_time)))
            self.meta.update_job(self.uid, 'computation_time', ftime)
            if int(elapsed_time) < self.interval:
                time.sleep(3)
            else:
                time.sleep(self.interval)
