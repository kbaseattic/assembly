import config
import pymongo
import uuid

def get_jobs():
    connection = pymongo.Connection(config.MONGO_HOST, config.MONGO_PORT)
    db = connection[config.DB_NAME]
    jobs = db[config.COLLECTION]
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
        
    
