"""
Consumes a job from the queue
"""

import copy
import errno
import glob
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
from multiprocessing import current_process as proc
from traceback import format_tb, format_exc

import assembly as asm
import metadata as meta
import asmtypes
import shock
import wasp
import recipes
import utils
from assembly import ignored
from job import ArastJob
from kbase import typespec_to_assembly_data as kb_to_asm
from plugins import ModuleManager

from ConfigParser import SafeConfigParser


logger = logging.getLogger(__name__)


class ArastConsumer:
    def __init__(self, shockurl, rmq_host, rmq_port, mongo_host, mongo_port, config, threads, queues,
                 kill_list, kill_list_lock, job_list, job_list_lock, ctrl_conf, datapath, binpath, modulebin):
        self.parser = SafeConfigParser()
        self.parser.read(config)
        self.kill_list = kill_list
        self.kill_list_lock = kill_list_lock
        self.job_list = job_list
        self.job_list_lock = job_list_lock
        # Load plugins
        self.threads = threads
        self.binpath = binpath
        self.modulebin = modulebin
        self.pmanager = ModuleManager(threads, kill_list, kill_list_lock, job_list, binpath, modulebin)

        # Set up environment
        self.shockurl = shockurl
        self.datapath = datapath
        self.rmq_host = rmq_host
        self.rmq_port = rmq_port
        self.mongo_host = mongo_host
        self.mongo_port = mongo_port
        self.queues = queues
        self.min_free_space = float(self.parser.get('compute','min_free_space'))
        self.data_expiration_days = float(self.parser.get('compute','data_expiration_days'))
        m = ctrl_conf['meta']
        a = ctrl_conf['assembly']

        collections = {'jobs': m.get('mongo.collection', 'jobs'),
                       'auth': m.get('mongo.collection.auth', 'auth'),
                       'data': m.get('mongo.collection.data', 'data'),
                       'running': m.get('mongo.collection.running', 'running_jobs')}

        ###### TODO Use REST API
        self.metadata = meta.MetadataConnection(self.mongo_host, self.mongo_port, m['mongo.db'],
                                                collections)
        self.gc_lock = multiprocessing.Lock()

    def garbage_collect(self, datapath, required_space, user, job_id, data_id):
        """ Monitor space of disk containing DATAPATH and delete files if necessary."""
        datapath = self.datapath
        required_space = self.min_free_space
        expiration = self.data_expiration_days

        ### Remove expired directories
        def can_remove(d, user, job_id, data_id):
            u, data, j = d.split('/')[-4:-1]
            if u == user and j == str(job_id):
                return False
            if data == str(data_id) and j == 'raw':
                return False
            if os.path.isdir(d):
                return True
            return False

        dir_depth = 3
        dirs = filter(lambda f: can_remove(f, user, job_id, data_id), glob.glob(datapath + '/' + '*/' * dir_depth))
        removed = []
        logger.info('Searching for directories older than {} days'.format(expiration))
        for d in dirs:
            file_modified = None
            try:
                file_modified = datetime.datetime.fromtimestamp(os.path.getmtime(d))
            except os.error as e:
                logger.warning('GC ignored "{}": could not get timestamp: {}'.format(d, e))
                continue
            tdiff = datetime.datetime.now() - file_modified
            if tdiff > datetime.timedelta(days=expiration):
                logger.info('GC: removing expired directory: {} (modified {} ago)'.format(d, tdiff))
                removed.append(d)
                shutil.rmtree(d, ignore_errors=True)
            else:
                logger.debug('GC: not removing: {} (modified {} ago)'.format(d, tdiff))
        for r in removed:
            dirs.remove(r)

        ### Check free space and remove old directories
        free_space = free_space_in_path(datapath)
        logger.info("Required space in GB: {} (free = {})".format(required_space, free_space))

        times = []
        for d in dirs:
            try:
                t = os.path.getmtime(d)
                times.append([t, d])
            except:
                pass
        times.sort()
        logger.debug("Directories sorted by time: {}".format(times))
        dirs = [x[1] for x in times]

        busy_dirs = []
        while free_space < self.min_free_space and len(dirs) > 0:
            d = dirs.pop(0)
            if is_dir_busy(d):
                busy_dirs.append(d)
            else:
                free_space = self.remove_dir(d)

        while free_space < self.min_free_space:
            if len(busy_dirs) == 0:
                logger.error("GC: free space {} < {} GB; waiting for system space to be available...".format(free_space, self.min_free_space))
                time.sleep(60)
            else:
                logger.warning("GC: free space {} < {} GB; waiting for jobs to complete to reclaim space: {} busy directories..."
                               .format(free_space, self.min_free_space, len(busy_dirs)))
                checked_dirs = []
                while free_space < self.min_free_space and len(busy_dirs) > 0:
                    bd = busy_dirs.pop(0)
                    if is_dir_busy(bd):
                        checked_dirs.append(bd)
                        continue
                    free_space = self.remove_dir(bd)
                    # self.remove_empty_dirs()
                if free_space < self.min_free_space:
                    busy_dirs = checked_dirs
                    time.sleep(20)
            free_space = free_space_in_path(self.datapath)

        self.remove_empty_dirs()


    def remove_dir(self, d):
        shutil.rmtree(d, ignore_errors=True)
        logger.info("GC: space required; %s removed." % d)
        return free_space_in_path(self.datapath)

    def remove_empty_dirs(self):
        data_dirs = filter(lambda f: os.path.isdir(f), glob.glob(self.datapath + '/' + '*/' * 2))
        for dd in data_dirs:
            if not os.listdir(dd):
                logger.info('GC: removing empty directory: {}'.format(dd))
                try:
                    os.rmdir(dd)
                except os.error as e:
                    logger.warning('GC: could not remove empty dir "{}": {}'.format(dd, e))

    def get_data(self, body):
        """Get data from cache or Shock server."""
        params = json.loads(body)
        logger.debug('New Data Format')
        return self._get_data(body)

    def _get_data(self, body):
        params = json.loads(body)
        filepath = os.path.join(self.datapath, params['ARASTUSER'],
                                str(params['data_id']))
        datapath = filepath
        filepath += "/raw/"
        all_files = []
        user = params['ARASTUSER']
        job_id = params['job_id']
        data_id = params['data_id']
        token = params['oauth_token']
        uid = params['_id']

        self.gc_lock.acquire()
        try:
            self.garbage_collect(self.datapath, self.min_free_space, user, job_id, data_id)
        except:
            logger.error('Unexpected error in GC.')
            raise
        finally:
            self.gc_lock.release()

        ##### Get data from ID #####
        data_doc = self.metadata.get_data_docs(params['ARASTUSER'], params['data_id'])
        if not data_doc:
            raise Exception('Invalid Data ID: {}'.format(params['data_id']))
        logger.debug('data_doc = {}'.format(data_doc))
        if 'kbase_assembly_input' in data_doc:
            params['assembly_data'] = kb_to_asm(data_doc['kbase_assembly_input'])
        elif 'assembly_data' in data_doc:
            params['assembly_data'] = data_doc['assembly_data']

        ##### Get data from assembly_data #####
        self.metadata.update_job(uid, 'status', 'Data transfer')
        with ignored(OSError):
            os.makedirs(filepath)
            touch(filepath)

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
                        local_file = self.extract_file(local_file)
                        logger.info("Requested data exists on node: {}".format(local_file))
                    else:
                        local_file = self.download_shock(file_info['shock_url'], user, token,
                                                   file_info['shock_id'], filepath)

                elif file_info['direct_url']:
                    local_file = os.path.join(filepath, os.path.basename(file_info['direct_url']))
                    if os.path.exists(local_file):
                        local_file = self.extract_file(local_file)
                        logger.info("Requested data exists on node: {}".format(local_file))
                    else:
                        local_file = self.download_url(file_info['direct_url'], filepath, token=token)
                file_info['local_file'] = local_file
                if file_set['type'] == 'single' and asm.is_long_read_file(local_file):
                    if not 'tags' in file_set:
                        file_set['tags'] = []
                    if not 'long_read' in file_set['tags']:
                        file_set['tags'].append('long_read') # pacbio or nanopore reads
                file_set['files'].append(local_file) #legacy
            all_files.append(file_set)
        return datapath, all_files


    def prepare_job_data(self, body):
        params = json.loads(body)
        job_id = params['job_id']

        ### Download files (if necessary)
        datapath, all_files = self.get_data(body)
        rawpath = datapath + '/raw/'
        jobpath = os.path.join(datapath, str(job_id))

        try:
            os.makedirs(jobpath)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        ### Protect data directory from GC before any job starts
        touch(os.path.join(rawpath, "_READY_"))

        ### Create job log
        self.out_report_name = '{}/{}_report.txt'.format(jobpath, str(job_id))
        self.out_report = open(self.out_report_name, 'w')

        ### Create data to pass to pipeline
        reads = []
        reference = []
        contigs = []
        for fileset in all_files:
            if len(fileset['files']) != 0:
                if (fileset['type'] == 'single' or
                    fileset['type'] == 'paired'):
                    reads.append(fileset)
                elif fileset['type'] == 'reference':
                    reference.append(fileset)
                elif fileset['type'] == 'contigs':
                    contigs.append(fileset)
                else:
                    raise Exception('fileset error')

        job_data = ArastJob({'job_id' : params['job_id'],
                    'uid' : params['_id'],
                    'user' : params['ARASTUSER'],
                    'reads': reads,
                    'logfiles': [],
                    'reference': reference,
                    'contigs': contigs,
                    'initial_reads': list(reads),
                    'raw_reads': copy.deepcopy(reads),
                    'params': [],
                    'exceptions': [],
                    'pipeline_data': {},
                    'datapath': datapath,
                    'out_report' : self.out_report})

        self.out_report.write("Arast Pipeline: Job {}\n".format(job_id))

        return job_data


    def compute(self, body):
        self.job_list_lock.acquire()
        try:
            job_data = self.prepare_job_data(body)
            self.job_list.append(job_data)
        except:
            logger.error("Error in adding new job to job_list")
            raise
        finally:
            self.job_list_lock.release()

        status = ''
        logger.debug('job_data = {}'.format(job_data))

        params = json.loads(body)
        job_id = params['job_id']
        data_id = params['data_id']
        uid = params['_id']
        user = params['ARASTUSER']
        token = params['oauth_token']
        pipelines = params.get('pipeline')
        recipe = params.get('recipe')
        wasp_in = params.get('wasp')
        jobpath = os.path.join(self.datapath, user, str(data_id), str(job_id))

        url = shock.verify_shock_url(self.shockurl)

        self.start_time = time.time()

        timer_thread = UpdateTimer(self.metadata, 29, time.time(), uid, self.done_flag)
        timer_thread.start()

        #### Parse pipeline to wasp exp
        reload(recipes)
        if recipe:
            try: wasp_exp = recipes.get(recipe[0], job_id)
            except AttributeError: raise Exception('"{}" recipe not found.'.format(recipe[0]))
        elif wasp_in:
            wasp_exp = wasp_in[0]
        elif not pipelines:
            wasp_exp = recipes.get('auto', job_id)
        elif pipelines:
            ## Legacy client
            if pipelines[0] == 'auto':
                wasp_exp = recipes.get('auto', job_id)
            ##########
            else:
                if type(pipelines[0]) is not list: # --assemblers
                    pipelines = [pipelines]
                all_pipes = []
                for p in pipelines:
                    all_pipes += self.pmanager.parse_input(p)
                logger.debug("pipelines = {}".format(all_pipes))
                wasp_exp = wasp.pipelines_to_exp(all_pipes, params['job_id'])
        else:
            raise asmtypes.ArastClientRequestError('Malformed job request.')
        logger.debug('Wasp Expression: {}'.format(wasp_exp))
        w_engine = wasp.WaspEngine(self.pmanager, job_data, self.metadata)

        ###### Run Job
        try:
            w_engine.run_expression(wasp_exp, job_data)
            ###### Upload all result files and place them into appropriate tags
            uploaded_fsets = job_data.upload_results(url, token)

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

            sys.stdout.flush()
            touch(os.path.join(jobpath, "_DONE_"))
            logger.info('============== JOB COMPLETE ===============')

        except asmtypes.ArastUserInterrupt:
            status = 'Terminated by user'
            sys.stdout.flush()
            touch(os.path.join(jobpath, "_CANCELLED__"))
            logger.info('============== JOB KILLED ===============')

        finally:
            self.remove_job_from_lists(job_data)
            logger.debug('Reinitialize plugin manager...') # Reinitialize to get live changes
            self.pmanager = ModuleManager(self.threads, self.kill_list, self.kill_list_lock, self.job_list, self.binpath, self.modulebin)

        self.metadata.update_job(uid, 'status', status)


    def remove_job_from_lists(self, job_data):
        self.job_list_lock.acquire()
        try:
            for i, job in enumerate(self.job_list):
                if job['user'] == job_data['user'] and job['job_id'] == job_data['job_id']:
                    self.job_list.pop(i)
        except:
            logger.error("Unexpected error in removing executed jobs from job_list")
            raise
        finally:
            self.job_list_lock.release()

        # kill_list cleanup for cases where a kill request is enqueued right before the corresponding job gets popped
        self.kill_list_lock.acquire()
        try:
            for i, kill_request in enumerate(self.kill_list):
                if kill_request['user'] == job_data['user'] and kill_request['job_id'] == job_data['job_id']:
                    self.kill_list.pop(i)
        except:
            logger.error("Unexpected error in removing executed jobs from kill_list")
            raise
        finally:
            self.kill_list_lock.release()


    def upload(self, url, user, token, file, filetype='default'):
        files = {}
        files["file"] = (os.path.basename(file), open(file, 'rb'))
        logger.debug("Message sent to shock on upload: %s" % files)
        sclient = shock.Shock(url, user, token)
        if filetype == 'contigs' or filetype == 'scaffolds':
            res = sclient.upload_contigs(file)
        else:
            res = sclient.upload_file(file, filetype, curl=True)
        return res

    def download_shock(self, url, user, token, node_id, outdir):
        sclient = shock.Shock(url, user, token)
        downloaded = sclient.curl_download_file(node_id, outdir=outdir)
        return self.extract_file(downloaded)

    def download_url(self, url, outdir, token=None):
        downloaded = shock.curl_download_url(url, outdir=outdir, token=token)
        return self.extract_file(downloaded)

    def fetch_job(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=self.rmq_host, port=self.rmq_port))
        channel = connection.channel()
        channel.basic_qos(prefetch_count=1)
        result = channel.queue_declare(exclusive=False,
                                       auto_delete=False,
                                       durable=True)
        logger.info('Fetching job...')

        channel.basic_qos(prefetch_count=1)
        for queue in self.queues:
            print 'Using queue: {}'.format(queue)
            channel.basic_consume(self.callback,
                              queue=queue)

        channel.start_consuming()

    def callback(self, ch, method, properties, body):
        params = json.loads(body)
        display = ['ARASTUSER', 'job_id', 'message', 'recipe', 'pipeline', 'wasp']
        logger.info('Incoming job: ' + ', '.join(['{}: {}'.format(k, params[k]) for k in display if params[k]]))
        logger.debug(params)
        job_doc = self.metadata.get_job(params['ARASTUSER'], params['job_id'])

        ## Check if job was not killed
        if job_doc is None:
            logger.error('Error: no job_doc found for {}'.format(params.get('job_id')))
            return

        if job_doc.get('status') == 'Terminated by user':
            logger.warn('Job {} was killed, skipping'.format(params.get('job_id')))
        else:
            self.done_flag = threading.Event()
            uid = None
            try:
                uid = job_doc['_id']
                self.compute(body)
            except Exception as e:
                tb = format_exc()
                status = "[FAIL] {}".format(e)
                logger.error("{}\n{}".format(status, tb))
                self.metadata.update_job(uid, 'status', status)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        self.done_flag.set()

    def start(self):
        self.fetch_job()

    def extract_file(self, filename):
        """ Decompress files if necessary """
        unp_bin = os.path.join(self.modulebin, 'unp')

        filepath = os.path.dirname(filename)
        uncompressed = ['fasta', 'fa', 'fastq', 'fq', 'fna', 'h5' ]
        supported = ['tar.gz', 'tar.bz2', 'bz2', 'gz', 'lz',
                     'rar', 'tar', 'tgz','zip']
        for ext in uncompressed:
            if filename.endswith('.'+ext):
                return filename
        for ext in supported:
            if filename.endswith('.'+ext):
                extracted_file = filename[:filename.index(ext)-1]
                if os.path.exists(extracted_file): # Check extracted already
                    return extracted_file
                logger.info("Extracting {}...".format(filename))
                # p = subprocess.Popen([unp_bin, filename],
                #                      cwd=filepath, stderr=subprocess.STDOUT)
                # p.wait()
                # Hide the "broken pipe" message from unp
                out = subprocess.Popen([unp_bin, filename],
                                       cwd=filepath,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT).communicate()[0]
                if os.path.exists(extracted_file):
                    return extracted_file
                else:
                    logger.error("Extraction of {} failed: {}".format(filename, out))
                    raise Exception('Archive structure error')
        logger.error("Could not extract {}".format(filename))
        return filename

### Helper functions ###
def touch(path):
    logger.debug("touch {}".format(path))
    now = time.time()
    try:
        os.utime(path, (now, now))
    except os.error:
        pdir = os.path.dirname(path)
        if len(pdir) > 0 and not os.path.exists(pdir):
            os.makedirs(pdir)
        open(path, "a").close()
        os.utime(path, (now, now))

def is_filename(word):
    return word.find('.') != -1 and word.find('=') == -1

def is_dir_busy(d):
    busy = False
    if not os.path.exists(d):
        logger.info("GC: directory not longer exists: {}".format(d))
        return False
    if re.search(r'raw/*$', d): # data path: check if no job directories exist
        fname = os.path.join(d, "_READY_")
        dirs = glob.glob(d + '/../*/')
        logger.debug("GC: data directory {} contains {} jobs".format(d, len(dirs)-1))
        busy = len(dirs) > 1 or not os.path.exists(fname)
    else:                       # job path
        fname1 = os.path.join(d, '_DONE_')
        fname2 = os.path.join(d, '_CANCELLED_')
        busy = not (os.path.exists(fname1) or os.path.exists(fname2))
    if busy:
        logger.debug("GC: directory is busy: {}".format(d))
    return busy

def free_space_in_path(path):
    s = os.statvfs(path)
    free_space = float(s.f_bsize * s.f_bavail / (10**9))
    logger.debug("Free space in {}: {} GB".format(path, free_space))
    return free_space

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
                logger.info('Stopping timer thread')
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
