"""
Handles metadata and MongoDB
"""

import config
import logging
import pymongo
import uuid
from ConfigParser import SafeConfigParser

class MetadataConnection:
    def __init__(self, host):
        self.parser = SafeConfigParser()
        self.parser.read('arast.conf')    
        self.host = host
        self.port = int(self.parser.get('meta', 'mongo.port'))
        self.db = self.parser.get('meta', 'mongo.db')
        self.collection = self.parser.get('meta', 'mongo.collection')

    def get_jobs(self):
        """Fetch approriate database and collection for jobs."""
        connection = pymongo.Connection(self.host, self.port)
        database = connection[self.db]
        jobs = database[self.collection]
        return jobs

    def insert_job(self, data):
        jobs = self.get_jobs()
        my_id = str(uuid.uuid4())
        data['_id'] = my_id
        job_id = jobs.insert(data)
        return job_id

    def get_next_id(self, user):
        connection = pymongo.Connection(self.host, self.port)
        database = connection[self.db]
        ids = database['ids']
        # TODO finish this

    def update_job(self, job_id, field, value):
        logging.info("Updating metadata job %s" % job_id)
        jobs = self.get_jobs()
        jobs.update({'_id' : job_id},
                    {'$set' : {field : value}})
        if jobs.find_one({'_id' : job_id}) is not None:
            logging.info("Job updated: %s:%s:%s" % (job_id, field, value))
        else:
            logging.warning("Job %s not updated!" % job_id)

    def list_jobs(self, user):
        r = []
        jobs = self.get_jobs()
        for j in jobs.find({'ARASTUSER':user}):
            r.append(j)
        return r

