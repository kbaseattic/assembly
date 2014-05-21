"""
Handles metadata and MongoDB
"""

import config
import logging
import pymongo
import uuid
from ConfigParser import SafeConfigParser

class MetadataConnection:
    def __init__(self, host, port, db, collection, auth_collection):
        self.host = host
        self.port = port
        self.db = db
        self.collection = collection
        self.auth_collection = auth_collection
        
        # Connect
        self.connection = pymongo.Connection(self.host, self.port)
        self.database = self.connection[self.db]
        
        # Get local data
        self.jobs = self.get_jobs()

    def get_jobs(self):
        """Fetch approriate database and collection for jobs."""
        return self.database[self.collection]

    def insert_job(self, data):
        jobs = self.get_jobs()
        my_id = str(uuid.uuid4())
        data['_id'] = my_id
        job_id = jobs.insert(data)
        return job_id

    def insert_doc(self, collection, data):
        connection = pymongo.Connection(self.host, self.port)
        database = connection[self.db]
        col = database[collection]
        col.insert(data)

    def list (self, collection):
        connection = pymongo.Connection(self.host, self.port)
        database = connection[self.db]
        col = database[collection]
        for r in col.find({}):
            print r
        return col.find({})
        
    def remove_doc(self, collection, key, value):
        connection = pymongo.Connection(self.host, self.port)
        database = connection[self.db]
        col = database[collection]
        col.remove({key:value})

    def update_doc(self, collection, query_key, query_value, key, value):
        connection = pymongo.Connection(self.host, self.port)
        database = connection[self.db]
        col = database[collection]

        col.update({query_key : query_value},
                    {'$set' : {key : value}})
        if col.find_one({query_key : query_value}) is not None:
            logging.info("Doc updated: %s:%s:%s" % (query_value, key, value))
        else:
            logging.warning("Doc %s not updated!" % query_value)

        
    def get_next_id(self, user, category):
        connection = pymongo.Connection(self.host, self.port)
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

    def get_next_data_id(self, user):
        return self.get_next_id(user, 'data')

    def get_doc_by_data_id(self, data_id, user):
        try:
            job = self.get_jobs().find_one({'ARASTUSER': user,'data_id':int(data_id)})
        except:
            job = None
            logging.error("Data %s does not exist" % data_id)
        return job

    def get_docs_distinct_data_id(self, user):
        docs = []
        distinct_ids = [int(id) for id in self.jobs.find(
                {'ARASTUSER': user}).distinct('data_id')]
        ## remove dupes due to str/int variability
        dset = set()
        for d in distinct_ids:
            dset.add(d)
        for d in sorted(dset):
            doc = self.get_jobs().find_one({'ARASTUSER': user,'data_id':int(d)})
            if doc:
                docs.append(doc)
        return docs

    def update_job(self, job_id, field, value):
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
        for j in jobs.find({'ARASTUSER':user}).sort('job_id', 1):
            r.append(j)
        return r

    def get_job(self, user, job_id):
        try:
            job = self.get_jobs().find({'ARASTUSER':user, 'job_id':int(job_id)})[0]
        except:
            job = None
            logging.error("Job %s does not exist" % job_id)
        return job

    def job_is_complete(self, user, job_id):
        job = self.get_job(user, job_id)
        return job['status'].find('success') != -1

    def get_auth_info(self, user):
        connection = pymongo.Connection(self.host, self.port)
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
        
        
