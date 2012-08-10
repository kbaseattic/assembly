"""
Job router.  Recieves job requests.  Manages data transfer, job queuing.
"""

import pika
import pprint
import sys
import json
from bson import json_util
import config
import metadata


def send_message(body, routingKey):
    """ Place the job request on the correct job queue """

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
    #TODO
    """ Return the size in MB of the total data """
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
    job_id =  metadata.insert_job(client_params)
    metadata.update_job(job_id, 'status', 'queued')
    print client_params
    p = dict(client_params)
    msg = json.dumps(p)

    send_message(msg, routing_key)
    return job_id

#    send_message(body, routing_key)


# One RPC receive 
def on_request(ch, method, props, body):
    print " [.] Incoming request:  %r" % (body)
    params = json.loads(body)
    ack = ''

    # if 'stat'
    if params['command'] == 'stat':
        print params['ARASTUSER']
        docs = metadata.list_jobs(params['ARASTUSER'])
        msg = []
        for doc in docs:
            msg.append([str(doc['_id']),str(doc['status'])])
        ack = pprint.pformat(msg)

    elif params['command'] == 'run':
        ack = str(route_job(body))

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(
            correlation_id=props.correlation_id),
                     body=ack)
    ch.basic_ack(delivery_tag=method.delivery_tag)

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=config.RABBITMQ_HOST))

channel = connection.channel()
channel.queue_declare(queue='rpc_queue')
channel.basic_qos(prefetch_count=1)
channel.basic_consume(on_request, queue='rpc_queue')
print " [x] Awaiting RPC requests"
channel.start_consuming()

