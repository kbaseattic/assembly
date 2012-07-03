import config
import pymongo

def get_jobs():
    connection = pymongo.Connection(config.MONGO_HOST, config.MONGO_PORT)
    db = connection[config.DB_NAME]
    jobs = db[config.COLLECTION]
    return jobs

def insert_job(data):
    jobs = get_jobs()
    job_id = jobs.insert(data)

    return job_id

def update_job(job_id, field, value):
    jobs = get_jobs()
    jobs.update({'_id' : job_id},
                {'$set' : {field : value}})
    print jobs.find_one({'_id' : job_id})
