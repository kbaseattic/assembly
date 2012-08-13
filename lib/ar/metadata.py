import pymongo
import uuid
from ConfigParser import SafeConfigParser

def get_jobs():
    connection = pymongo.Connection(host,port)
    db = connection[db]
    jobs = db[collection]
    return jobs

def insert_job(data):
    jobs = get_jobs()
    my_id = str(uuid.uuid4())
    data['_id'] = my_id
    job_id = jobs.insert(data)
    return job_id

def update_job(job_id, field, value):
    print type(job_id)
    print job_id
    jobs = get_jobs()
    jobs.update({'_id' : job_id},
                {'$set' : {field : value}})
    print jobs.find_one({'_id' : job_id})

def list_jobs(user):
    r = []
    jobs = get_jobs()
    for j in jobs.find({'ARASTUSER':user}):
        r.append(j)
    return r
        
parser = SafeConfigParser()
parser.read('arast.conf')    
host = parser.get('meta', 'mongo.host')
port = int(parser.get('meta', 'mongo.port'))
db = parser.get('meta', 'mongo.db')
collection = parser.get('meta', 'mongo.collection')
