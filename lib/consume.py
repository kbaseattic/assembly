"""
Consumes a job from the queue
"""

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
import tarfile
import subprocess
#from yapsy.PluginManager import PluginManager
from plugins import ModuleManager
from multiprocessing import current_process as proc

import config
import assembly as asm
import metadata as meta

from ConfigParser import SafeConfigParser

class ArastConsumer:
    def __init__(self, shockurl, arasturl, config):
        self.parser = SafeConfigParser()
        self.parser.read(config)
        # Load plugins
        self.pmanager = ModuleManager()


    # Set up environment
        self.shockurl = shockurl
        self.arasturl = arasturl
        self.shockuser = self.parser.get('shock','admin_user')
        self.shockpass = self.parser.get('shock','admin_pass')
        self.datapath = self.parser.get('compute','datapath')
        self.queue = self.parser.get('rabbitmq','default_routing_key')
        self.min_free_space = float(self.parser.get('compute','min_free_space'))
        self.metadata = meta.MetadataConnection(config, arasturl)
        self.gc_lock = multiprocessing.Lock()
        
        #self.metadata.update_doc('active_nodes', 'server_name', socket.gethostname(),
         #                        'status', 'running')

    def garbage_collect(self, datapath, required_space):
        """ Monitor space of disk containing DATAPATH and delete files if necessary."""
        self.gc_lock.acquire()
        s = os.statvfs(datapath)
        free_space = float(s.f_bsize * s.f_bavail)
        logging.debug("Free space in bytes: %s" % free_space)
        logging.debug("Required space in bytes: %s" % required_space)
        while ((free_space - self.min_free_space) < required_space):
            #Delete old data
            dirs = os.listdir(datapath)
            times = []
            for dir in dirs:
                times.append(os.path.getmtime(datapath + dir))
            if len(dirs) > 0:
                old_dir = datapath + dirs[times.index(min(times))]
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

        filename = self.datapath
        filename += str(params['data_id'])
        datapath = filename
        all_files = []
        if os.path.isdir(datapath):
            logging.info("Requested data exists on node")
            touch(datapath)
        else:
            uid = params['_id']
            self.metadata.update_job(uid, 'status', 'Data transfer')
            data_doc = self.metadata.get_doc_by_data_id(params['data_id'])
            if data_doc:
                files = data_doc['filename']
                ids = data_doc['ids']
                job_id = params['job_id']
                uid = params['_id']
                filename += "/raw/"
                os.makedirs(filename)

                # Get required space and garbage collect
                try:
                    req_space = 0
                    for file_size in data_doc['file_sizes']:
                        req_space += file_size
                    self.garbage_collect(self.datapath, req_space)
                except:
                    pass 

                url = "http://%s" % (self.shockurl)
                for i in range(len(files)):
                    file = files[i]
                    id = ids[i]
                    temp_url = url
                    temp_url += "/node/%s" % (id)
                    temp_url += "?download" 
                    r = self.get(temp_url)
                    cur_file = filename
                    cur_file += file
                    with open(cur_file, "wb") as code:
                        code.write(r.content)
                    all_files.append(cur_file)
            else:
                datapath = None
        return datapath, all_files


    def compute(self, body):
        error = False
        params = json.loads(body)

        # Download files (if necessary)
        datapath, all_files = self.get_data(body)
        rawpath = datapath + '/raw/'
        #extract_files(rawpath)
        if not datapath:
            error = True
            logging.error("Data does not exist!")
        
        job_id = params['job_id']
        uid = params['_id']

        ### Build job_data
        ### {'reads' : [(file1,), (paired1,paired2)]}
        reads = [(f,) for f in all_files]
        job_data = {'job_id' : params['job_id'], 
                    'uid' : params['_id'],
                    'reads': reads,
                    'datapath': datapath}


        try:
            bwa = params['bwa']
        except:
            bwa = False

        try:
            pipeline = params['pipeline']
        except:
            pipeline = False

        start_time = time.time()
        download_ids = {}
        #ex pipeline = ['sga', 'kiki', 'sspace']
        

        if error:
            self.metadata.update_job(uid, 'status', 'Datapath error')

        url = "http://%s" % (self.shockurl)
        url += '/node'


        # Run individual assemblies
        status = 'complete:'
        if params['assemblers']:
            for a in params['assemblers']:
                #if asm.is_available(a):
                if self.pmanager.has_plugin(a):
                    self.garbage_collect(self.datapath, 0)
                    self.metadata.update_job(uid, 'status', "running: %s" % a)
                    try:
                        result_tar = self.pmanager.run_module(a, job_data, tar=True)
                        res = self.upload(url, result_tar)
                         # Get location
                        download_ids[a] = res['D']['id']
                        status += "{} [success] ".format(a)
                    except Exception as e:
                        status += "%s [failed:%s] " % (a, e)
                    except:
                        status += "%s [failed:%s] " % (a, str(sys.exc_info()[0]))
                        logging.info("%s failed to finish" % a)
                else:
                    status += "%s [failed:Module unavail] " % (a)

        if pipeline:
            try:
                result_tar = self.run_pipeline(pipeline, job_data)
                res = self.upload(url, result_tar)
                # Get location
                download_ids['pipeline'] = res['D']['id']
                status += "pipeline [success] "
            except:
                status += "%s [failed:%s] " % ("pipeline", str(sys.exc_info()))

        elapsed_time = time.time() - start_time
        ftime = str(datetime.timedelta(seconds=int(elapsed_time)))
        self.metadata.update_job(uid, 'result_data', download_ids)
        self.metadata.update_job(uid, 'status', status)
        self.metadata.update_job(uid, 'computation_time', ftime)

    def run_pipeline(self, pipe, job_data):
        # Parse param overrides
        overrides = []
        pipeline = []
        for word in pipe:
            module_num = -1
            if not word.startswith('?'): # is module
                pipeline.append(word)
                module_num += 1
                overrides.append({})

            elif word[1:-1].find('=') != -1: # is param
                kv = word[1:].split('=')
                overrides[module_num] = dict(overrides[module_num].items() +
                                             dict([kv]).items())

        pipeline_stage = 1
        pipeline_results = []
        for module_name in pipeline:
            print pipeline_stage
            job_data['params'] = overrides[pipeline_stage-1].items()
            output = self.pmanager.run_module(module_name, job_data)
             # Prefix outfiles with pipe stage
            newfiles = [asm.prefix_file(file, pipeline_stage) 
                        for file in output]
            job_data['reads'] = asm.tupled(newfiles)
            pipeline_results += newfiles
            pipeline_stage += 1
        pipeline_datapath = job_data['datapath'] + '/pipeline/'
        os.makedirs(pipeline_datapath)
        return asm.tar_list(pipeline_datapath, pipeline_results, 
                            'pipeline' + str(job_data['job_id']) +
                            '.tar.gz')

    def upload(self, url, file):
        files = {}
        files["file"] = (os.path.basename(file), open(file, 'rb'))
        logging.debug("Message sent to shock on upload: %s" % files)
        res = self.post(url, files)
        return res

    # TODO move this to shock.py
    def post(self, url, files):
            r = None
            r = requests.post(url, auth=(self.shockuser, self.shockpass), files=files)

            res = json.loads(r.text)
            return res

    def get(self, url):     
        r = None
        r = requests.get(url, auth=(self.shockuser, self.shockpass))       
            #res = json.loads(r.text)
        return r

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

        channel.basic_consume(self.callback,
                              queue=self.queue,
                              no_ack=True) #change?

        channel.start_consuming()

    def callback(self, ch, method, properties, body):
        print " [*] %r:%r" % (method.routing_key, body)
        self.compute(body)


    # For now, use this instead of daemon
    def start(self):
            # workers = []
            # for i in range(int(threads)):
            #     worker_name = "[Worker %s]:" % i
            #     logging.info("[Master]: Starting %s" % worker_name)
            #     p = multiprocessing.Process(name=worker_name, target=self.fetch_job)
            #     workers.append(p)
            #     p.start()
            #     #self.fetch_job(self.parser.get('rabbitmq','job.medium'))
            # workers[0].join()
        self.fetch_job()

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
    
def extract_files(datapath):
    """ Decompress files if necessary """
    files = os.listdir(datapath)
    logging.debug("Looking for files to extract in %s" % files)
    for tfile in [datapath + f for f in files]:
        if tarfile.is_tarfile(tfile):
            logging.debug("Extracting %s" % tfile)
            tarfile.open(tfile, 'r').extractall(datapath)
            os.remove(tfile)
        elif tfile.endswith('.bz2'):
            logging.debug("Extracting %s" % tfile)
            p = subprocess.Popen(['bunzip2', tfile])
            p.wait()

            

