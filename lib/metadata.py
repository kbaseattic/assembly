"""
Handles metadata and MongoDB
"""

import config
import logging
import pymongo
import uuid
from ConfigParser import SafeConfigParser

def get_jobs():
    """Fetch approriate database and collection for jobs."""
    global db, collection
    connection = pymongo.Connection(host,port)
    database = connection[db]
    jobs = database[collection]
    return jobs

def insert_job(data):
    jobs = get_jobs()
    my_id = str(uuid.uuid4())
    data['_id'] = my_id
    job_id = jobs.insert(data)
    return job_id

def get_next_id(user):
    connection = pymongo.Connection(host,port)
    database = connection[db]
    ids = database['ids']
    # TODO finish this

def update_job(job_id, field, value):
    logging.info("Updating metadata job %s" % job_id)
    jobs = get_jobs()
    jobs.update({'_id' : job_id},
                {'$set' : {field : value}})
    if jobs.find_one({'_id' : job_id}) is not None:
        logging.info("Job updated: %s:%s:%s" % (job_id, field, value))
    else:
        logging.warning("Job %s not updated!" % job_id)

def list_jobs(user):
    r = []
    jobs = get_jobs()
    for j in jobs.find({'ARASTUSER':user}):
        r.append(j)
    return r

global host, port, db, collection        
parser = SafeConfigParser()
parser.read('arast.conf')    
host = parser.get('meta', 'mongo.host')
port = int(parser.get('meta', 'mongo.port'))
db = parser.get('meta', 'mongo.db')
collection = parser.get('meta', 'mongo.collection')
