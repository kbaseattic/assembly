"""
Job router.  Recieves job requests.  Manages data transfer, job queuing.
"""

import logging
import pika
import pprint
import sys
import json
import os
from bson import json_util
from ConfigParser import SafeConfigParser
from prettytable import PrettyTable

import shock
import metadata as meta

def send_message(body, routingKey):
    """ Place the job request on the correct job queue """

    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost'))
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
    job_id = metadata.get_next_job_id(client_params['ARASTUSER'])
#    try:
#        data_id = client_params['data_id']
#    except:
#        print "none"
#        data_id = metadata.get_next_data_id(client_params['ARASTUSER'])
#        client_params['data_id'] = data_id

    if not client_params['data_id']:
        data_id = metadata.get_next_data_id(client_params['ARASTUSER'])
        client_params['data_id'] = data_id
        
    client_params['job_id'] = job_id
    uid = metadata.insert_job(client_params)
    metadata.update_job(uid, 'status', 'queued')
    p = dict(client_params)
    msg = json.dumps(p)
    send_message(msg, routing_key)
    return job_id


# One RPC receive 
def on_request(ch, method, props, body):
    global parser
    logging.info(" [.] Incoming request:  %r" % (body))
    params = json.loads(body)
    ack = ''
    pt = PrettyTable(["Error"])
    # if 'stat'
    if params['command'] == 'stat':

        if params['files']:
            if params['files'] == -1:
                ack = 'list all data not implemented'
                pass
            else:
                pt = PrettyTable(['#', "File", "Size"])
                data_id = params['files']
                try:
                    doc = metadata.get_doc_by_data_id(data_id)
                    files = doc['filename']
                    fsizes = doc['file_sizes']
                    for i in range(len(files)):
                        row = [i+1, os.path.basename(files[i]), fsizes[i]]
                        pt.add_row(row)
                except:
                    pass
    
        ######  Stat Jobs #######
        else:
            pt = PrettyTable(["Job ID", "Data ID", "Status", "Run time", "Description"])
            docs = metadata.list_jobs(params['ARASTUSER'])
            for doc in docs[-15:]:
                try:
                    row = [doc['job_id']]
                except:
                    row = [doc['_id']]
                try:
                    row.append(str(doc['data_id']))
                except:
                    row.append('')
                try:
                    row.append(str(doc['status']))
                except:
                    row.append('')
                try:
                    row.append(str(doc['computation_time']))
                except:
                    row.append('')
                try:
                    row.append(str(doc['message']))
                except:
                    row.append('')
                try:
                    pt.add_row(row)
                except:
                    pt.add_row(doc['job_id'], "error")

        
        ack = pt.get_string()

    # if 'run'
    elif params['command'] == 'run':
        if params['config']:
            logging.info("Config file submitted")
            #Download config file
            shock.download("http://" + parser.get('shock','host'),
                           params['config_id'][0],
                           'temp/',
                           parser.get('shock','admin_user'),
                           parser.get('shock','admin_pass'))
        ack = str(route_job(body))
    
    # if 'get_url'
    elif params['command'] == 'get_url':
        ack = get_upload_url()

    elif params['command'] == 'get':
        if params['job_id'] == -1:
            docs = metadata.list_jobs(params['ARASTUSER'])
            doc = docs[-1]
        else:
            # NEXT get specific job
            doc = metadata.get_job(params['ARASTUSER'], params['job_id'])
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



def start(config_file):
    global parser, metadata
    logging.basicConfig(level=logging.DEBUG)

    parser = SafeConfigParser()
    parser.read(config_file)

    metadata = meta.MetadataConnection(parser.get('meta','mongo.control.host'), config_file)

    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='rpc_queue')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(on_request, queue='rpc_queue')
    print " [x] Awaiting RPC requests..."
    channel.start_consuming()

#start()
