"""
Consumes a job from the queue
"""

import logging
import pika
import sys
import json
import requests
import os

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

    def compute(self, body):
        params = json.loads(body)

        # Download data
#        files = params['filename']
 #       ids = params['ids']
        data_doc = metadata.get_doc_by_data_id(params['data_id'])
        files = data_doc['filename']

        ids = data_doc['ids']
        job_id = params['_id']

        filename = self.datapath
        filename += job_id
        datapath = filename
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
        # Run assemblies
        download_ids = {}
        for a in params['assemblers']:
            if asm.is_available(a):
                self.metadata.update_job(job_id, 'status', "running: %s" % a)
                result_tar = asm.run(a, datapath, job_id)
                # send to shock
                url += '/node'
                res = self.upload(url, result_tar, job_id, a)
                # Get location
                download_ids[a] = res['D']['id']
            else:
                logging.info("%s failed to finish" % a)
        self.metadata.update_job(job_id, 'result_data', download_ids)
        self.metadata.update_job(job_id, 'status', 'complete')

    def upload(self, url, file, job_id, assembler):
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


