"""
Job router.  Recieves job requests.  Manages data transfer, job queuing.
"""

import logging
import pika
import pprint
import sys
import json
from bson import json_util
from ConfigParser import SafeConfigParser
from prettytable import PrettyTable

import metadata

def send_message(body, routingKey):
    """ Place the job request on the correct job queue """

    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=parser.get('rabbitmq','host')))
    channel = connection.channel()
    channel.basic_publish(exchange = '',
                          routing_key=routingKey,
                          body=body,
                          properties=pika.BasicProperties(
                          delivery_mode=2)) #persistant message
    logging.debug(" [x] Sent to queue: %r: %r" % (routingKey, body))
    connection.close()


def determine_routing_key(size, params):
    """Depending on job submission, decide which queue to route to."""
    return parser.get('rabbitmq','default_routing_key')

def get_upload_url():
    global parser
    return parser.get('shock', 'host')


def route_job(body):
    client_params = json.loads(body) #dict of params
    
    routing_key = determine_routing_key (1, body)
    job_id =  metadata.insert_job(client_params)
    metadata.update_job(job_id, 'status', 'queued')
    p = dict(client_params)
    msg = json.dumps(p)
    send_message(msg, routing_key)
    return job_id


# One RPC receive 
def on_request(ch, method, props, body):
    logging.info(" [.] Incoming request:  %r" % (body))
    params = json.loads(body)
    ack = ''

    # if 'stat'
    if params['command'] == 'stat':
        pt = PrettyTable(["Job ID", "Status"])
        docs = metadata.list_jobs(params['ARASTUSER'])
        msg = []
        for doc in docs[-15:-1]:
            print doc
            try:
                msg.append([str(doc['_id']), str(doc['status'])])
                pt.add_row([str(doc['_id']), str(doc['status'])])
                if doc['status'] == 'complete':
                    msg.append(doc['result_data'])
            except:
                msg.append("MALFORMED JOB RECORD")
        #ack = pprint.pformat(msg)
        ack = pt.get_string()

    # if 'run'
    elif params['command'] == 'run':
        ack = str(route_job(body))
    
    # if 'get_url'
    elif params['command'] == 'get_url':
        ack = get_upload_url()

    elif params['command'] == 'get':
        docs = metadata.list_jobs(params['ARASTUSER'])
        
        # Get latest
        doc = docs[-1]
        try:
            result_data = doc['result_data']
            ack = json.dumps(result_data)
        except:
            ack = "Error getting results"

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(
            correlation_id=props.correlation_id),
                     body=ack)
    ch.basic_ack(delivery_tag=method.delivery_tag)



def start():
    global parser
    logging.basicConfig(level=logging.DEBUG)

    parser = SafeConfigParser()
    parser.read('arast.conf')

    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=parser.get('rabbitmq','host')))
    channel = connection.channel()
    channel.queue_declare(queue='rpc_queue')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(on_request, queue='rpc_queue')
    print " [x] Awaiting RPC requests..."
    channel.start_consuming()

start()
