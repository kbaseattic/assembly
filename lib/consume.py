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
from multiprocessing import current_process as proc

import config
import assembly as asm
import metadata as meta

from ConfigParser import SafeConfigParser

class ArastConsumer:
    def __init__(self, shockurl, arasturl, config):
        self.parser = SafeConfigParser()
        self.parser.read(config)

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
        filename += '_tmp/'

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
                #os.makedirs(tmp)
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
                    temp_url = url + "node/{}?download".format(id)
                    #temp_url = url
                    #temp_url += "/node/%s" % (id)
                    #temp_url += "?download" 

                    # TODO make sure this chunks downloading
                    r = self.get(temp_url)
                    #cur_file = tmp
                    cur_file = filename
                    cur_file += file
                    with open(cur_file, "wb") as code:
                        code.write(r.content)
                # Done downloading, move file to correct dir
                os.renames(datapath + '_tmp/', datapath)
            else:
                datapath = None
        return datapath


    def compute(self, body):
        error = False
        params = json.loads(body)

        # Download files (if necessary)
        datapath = self.get_data(body)
        if not datapath:
            error = True
            logging.error("Data does not exist!")
        
        job_id = params['job_id']
        uid = params['_id']

        try:
            bwa = params['bwa']
        except:
            bwa = False

        # Run assemblies
        if not error:
            start_time = time.time()
            download_ids = {}
            for a in params['assemblers']:
                if asm.is_available(a):
                    self.garbage_collect(self.datapath, 0)
                    self.metadata.update_job(uid, 'status', "running: %s" % a)
                    result_tar = asm.run(a, datapath, uid, bwa)
                    renamed = os.path.split(result_tar)[0] + '/'
                    renamed += asm.get_tar_name(job_id, a)
                    os.rename(result_tar, renamed)
                    # send to shock
                    url = "http://%s" % (self.shockurl)
                    url += '/node'
                    res = self.upload(url, renamed, a)
                    # Get location
                    download_ids[a] = res['D']['id']
                else:
                    logging.info("%s failed to finish" % a)
            elapsed_time = time.time() - start_time
            ftime = str(datetime.timedelta(seconds=int(elapsed_time)))
            self.metadata.update_job(uid, 'result_data', download_ids)
            self.metadata.update_job(uid, 'status', 'complete')
            self.metadata.update_job(uid, 'computation_time', ftime)
        else:
            self.metadata.update_job(uid, 'status', 'Data error')

    def upload(self, url, file, assembler):
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
    
