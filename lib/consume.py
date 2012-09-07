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
        self.metadata = meta.MetadataConnection(arasturl, config)

    def get_data(self, body):
        """Get data from cache or Shock server."""
        params = json.loads(body)

        # Download data

        #TODO data caching
        filename = self.datapath
        filename += str(params['data_id'])
        datapath = filename
        if os.path.isdir(datapath):
            logging.info("Requested data exists on node")
        else:
            data_doc = self.metadata.get_doc_by_data_id(params['data_id'])
            files = data_doc['filename']

            ids = data_doc['ids']
            job_id = params['job_id']
            uid = params['_id']

            filename += "/raw/"
            os.makedirs(filename)

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
        return datapath


    def compute(self, body):
        params = json.loads(body)

        # Download files (if necessary)
        datapath = self.get_data(body)
        job_id = params['job_id']
        uid = params['_id']

        # Run assemblies
        download_ids = {}
        for a in params['assemblers']:
            if asm.is_available(a):
                self.metadata.update_job(uid, 'status', "running: %s" % a)
                result_tar = asm.run(a, datapath, uid)
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
##        shutil.rmtree(datapath, ignore_errors=True)
        # TODO garbage collection on data
        self.metadata.update_job(uid, 'result_data', download_ids)
        self.metadata.update_job(uid, 'status', 'complete')

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

    def fetch_job(self, queue):
        connection = pika.BlockingConnection(pika.ConnectionParameters(
                host = self.arasturl))
        channel = connection.channel()

        result = channel.queue_declare(queue=queue,
                                       exclusive=False,
                                       auto_delete=False,
                                       durable=True)

        print ' [*] Fetching job...'

        channel.basic_consume(self.callback,
                              queue=queue,
                              no_ack=True) #change?

        channel.start_consuming()

    def callback(self, ch, method, properties, body):
        print " [*] %r:%r" % (method.routing_key, body)
        self.compute(body)


    # For now, use this instead of daemon
    def start(self):
        self.fetch_job(self.parser.get('rabbitmq','job.medium'))


