"""
Job router.  Recieves job requests.  Manages data transfer, job queuing.
"""

import pika
import sys
import json
import pymongo
from bson import json_util
import config



def send_message(body, routingKey):
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host = config.RABBITMQ_HOST))
    channel = connection.channel()

    channel.basic_publish(exchange = '',
                          routing_key=routingKey,
                          body=body,
                          properties=pika.BasicProperties(
                          delivery_mode=2)) #persistant message

    print " [x] Sent to queue: %r: %r" % (routingKey, body)
    connection.close()

def get_data_size(files):
    return 2

def transfer_data(files):
    """
    Return file path on NFS server
    """
    return 2

def determine_routing_key(size, params):
    return config.DEFAULT_ROUTING_KEY

def get_upload_url(body):
    return config.DEFAULT_UPLOAD

def route_job(body):
    client_params = json.loads(body) #dict of params
    routing_key = determine_routing_key (1, body)
    write_metadata(client_params)
    send_message(body, routing_key)

def write_metadata(data):
    """
    Insert Job metadata into database.  Returns Job id

    """
    connection = pymongo.Connection(config.MONGO_HOST, config.MONGO_PORT)
    db = connection[config.DB_NAME]
    jobs = db[config.COLLECTION]
    return jobs.insert(document)




