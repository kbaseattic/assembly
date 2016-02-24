"""
Handles metadata and MongoDB
"""

import config
import logging
import pymongo
import uuid
import time
import json
import re
from ConfigParser import SafeConfigParser

logger = logging.getLogger(__name__)

class MetadataConnection:
    def __init__(self, host, port, db, collections):
        self.host = host
        self.port = port
        self.db = db
        self.collection = collections.get('jobs')
        self.auth_collection = collections.get('auth')
        self.data_collection = collections.get('data')
        self.rjobs_collection = collections.get('running')

        # Connect
        self.connection = pymongo.mongo_client.MongoClient(self.host, self.port)
        self.database = self.connection[self.db]

        # Get local data
        self.jobs = self.get_jobs()

        # Ensure compound index
        self.jobs.ensure_index([("ARASTUSER", pymongo.ASCENDING), ("job_id", pymongo.ASCENDING)])

        self.data_collection = self.get_data()

    def get_jobs(self):
        """Fetch approriate database and collection for jobs."""
        return self.database[self.collection]

    def get_data(self):
        """Fetch approriate database and collection for jobs."""
        return self.database[self.data_collection]

    def insert_job(self, data):
        jobs = self.get_jobs()
        my_id = str(uuid.uuid4())
        data['_id'] = my_id
        job_id = jobs.insert(data)
        return job_id

    def insert_doc(self, collection, data):
        connection = self.connection
        database = connection[self.db]
        col = database[collection]
        col.insert(data)

    def list (self, collection):
        connection = self.connection
        database = connection[self.db]
        col = database[collection]
        for r in col.find({}):
            print r
        return col.find({})

    def remove_doc(self, collection, key, value):
        connection = self.connection
        database = connection[self.db]
        col = database[collection]
        col.remove({key:value})

    def update_doc(self, collection, query_key, query_value, key, value):
        connection = self.connection
        database = connection[self.db]
        col = database[collection]

        col.update({query_key : query_value},
                    {'$set' : {key : value}})
        if col.find_one({query_key : query_value}) is not None:
            logger.info("Doc updated: %s - %s - %s" % (query_value, key, value))
        else:
            logger.warning("Doc %s not updated!" % query_value)


    def get_next_id(self, user, category):
        connection = self.connection
        database = connection[self.db]
        ids = database[category]
        next_id = 1
        if ids.find_one({'user' : user}) is None:
            ids.insert({'user' : user, 'c' : 1})
        else:
            doc = ids.find_and_modify(query={'user' : user}, update={'$inc': {'c' : 1}})
            next_id = doc['c'] + 1
        return next_id

    def get_next_job_id(self, user):
        return self.get_next_id(user, 'ids')

    def update_job(self, job_id, field, value):
        jobs = self.get_jobs()
        jobs.update({'_id' : job_id},
                    {'$set' : {field : value}})

        if jobs.find_one({'_id' : job_id}) is not None:
            if re.search(r'(status|contig_ids)', field):
                logger.info("Job updated: %s - %s - %s" % (job_id, field, value))
            else:
                logger.debug("Job updated: %s - %s - %s" % (job_id, field, value))
        else:
            logger.warning("Job %s not updated!" % job_id)

    def list_jobs(self, user):
        r = []
        jobs = self.get_jobs()
        for j in jobs.find({'ARASTUSER':user}).sort('job_id', 1):
            r.append(j)
        return r

    def get_job(self, user, job_id):
        try:
            job = self.get_jobs().find({'ARASTUSER':user, 'job_id':int(job_id)})[0]
        except:
            job = None
            logger.error("Job %s does not exist" % job_id)
        return job

    def get_job_by_uid(self, uid):
        try:
            job = self.get_jobs().find({'_id': uid})[0]
        except:
            job = None
        return job

    def job_is_complete(self, user, job_id):
        job = self.get_job(user, job_id)
        return job['status'].find('success') != -1

    def get_auth_info(self, user):
        connection = self.connection
        database = connection[self.db]
        col = database[self.auth_collection]
        try:
            auth_info = col.find_one({'globus_user': user})
        except:
            return None
        return auth_info

    def insert_auth_info(self, globus_user, token, token_time):
        data = {'globus_user': globus_user,
                'token': token,
                'token_time': token_time}
        return self.insert_doc(self.auth_collection, data)

    def update_auth_info(self, globus_user, token, token_time):
        self.update_doc(self.auth_collection, 'globus_user', globus_user,
                   'token', token)
        self.update_doc(self.auth_collection, 'globus_user', globus_user,
                   'token_time', token_time)


######## DATA COLLECTION ############
    def insert_data(self, user, data):
        if not 'data_id' in data:
            data['data_id'] = self.get_next_data_id(user)
        uid = self.data_collection.insert(data)
        return data['data_id'], uid

    def get_next_data_id(self, user):
        return self.get_next_id(user, 'data')


    def get_data_docs(self, user, data_id=None):
        if data_id:
            doc = self.data_collection.find_one({'ARASTUSER': user,'data_id':int(data_id)})
        else:
            doc = self.data_collection.find({'ARASTUSER': user})
        return doc


####### Running jobs ########
    def rjob_insert(self, uid, data):
        fields = ['job_id', 'ARASTUSER', 'pipeline']
        jdata = {k:data[k] for k in fields}
        jdata['job_uid'] = uid
        jdata['timestamp'] = str(time.time())
        jdata['status'] = 'queued'
        self.database[self.rjobs_collection].insert(jdata)

    def rjob_update_timestamp(self, job_uid):
        ## If accidentally purged, reinsert

        if self.database[self.rjobs_collection].find({'job_uid': job_uid}).count() == 0:
            self.rjob_insert(job_uid, self.get_jobs().find({'_id': job_uid})[0])
        self.database[self.rjobs_collection].update({'job_uid': job_uid},
                                                    {'$set' : {'timestamp': str(time.time()),
                                                               'status': 'running'}})

    def rjob_all(self):
        return {d['job_uid']: d for d in self.database[self.rjobs_collection].find()}

    def rjob_user_jobs(self, user):
        return {d['job_uid']: d for d in self.database[self.rjobs_collection].find({'ARASTUSER': user})}

    def rjob_remove(self, job_uid):
        self.database[self.rjobs_collection].remove({'job_uid': job_uid})

    def rjob_admin_stats(self):
        from collections import defaultdict

        class NestedDD(defaultdict):
            def __add__(self, other):
                return other

        ndefaultdict = lambda: NestedDD(ndefaultdict)
        d = ndefaultdict()

        for rjob in self.database[self.rjobs_collection].find():
            if rjob['status'] == 'running':
                d[rjob['ARASTUSER']]['running'] += 1
            elif rjob['status'] == 'queued':
                d[rjob['ARASTUSER']]['queued'] += 1
        return json.dumps(d)
