"""
Job router.  Recieves job requests.  Manages data transfer, job queuing.
"""

import logging
import cherrypy
import pika
import pprint
import sys
import json
import os
from distutils.version import StrictVersion
from bson import json_util
from ConfigParser import SafeConfigParser
from prettytable import PrettyTable
from traceback import format_exc

import shock
import metadata as meta


def send_message(body, routingKey):
    """ Place the job request on the correct job queue """

    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=routingKey, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_publish(exchange = '',
                          routing_key=routingKey,
                          body=body,
                          properties=pika.BasicProperties(
                          delivery_mode=2)) #persistant message
    logging.debug(" [x] Sent to queue: %r: %r" % (routingKey, body))
    connection.close()


def determine_routing_key(size, params):
    """Depending on job submission, decide which queue to route to."""
    if params['version'].find('beta'):
        print 'Sent to testing queue'
        return 'jobs.test'
    return parser.get('rabbitmq','default_routing_key')


def get_upload_url():
    global parser
    return parser.get('shock', 'host')


def route_job(body):
    client_params = json.loads(body) #dict of params
    routing_key = determine_routing_key (1, client_params)
    job_id = metadata.get_next_job_id(client_params['ARASTUSER'])

    if not client_params['data_id']:
        data_id = metadata.get_next_data_id(client_params['ARASTUSER'])
        client_params['data_id'] = data_id
        
    client_params['job_id'] = job_id
    uid = metadata.insert_job(client_params)
    logging.info("Inserting job record: %s" % client_params)
    metadata.update_job(uid, 'status', 'queued')
    p = dict(client_params)
    msg = json.dumps(p)
    send_message(msg, routing_key)
    response = str(job_id)
    return response

def on_request(ch, method, props, body):
    global parser
    logging.info(" [.] Incoming request:  %r" % (body))
    params = json.loads(body)
    ack = ''
    pt = PrettyTable(["Error"])

    # if 'stat'
    try:
        if params['command'] == 'stat':

            #####  Stat Data #####
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
                        ack = pt.get_string()
                    except:
                        ack = "Error: problem fetching DATA %s" % data_id

            ######  Stat Jobs #######
            else:
                try:
                    job_stat = params['stat_job'][0]
                except:
                    job_stat = None
                
                pt = PrettyTable(["Job ID", "Data ID", "Status", "Run time", "Description"])
                if job_stat:
                    doc = metadata.get_job(params['ARASTUSER'], job_stat)

                    if doc:
                        docs = [doc]
                    else:
                        docs = None
                    n = -1
                else:
                    try:
                        record_count = params['stat_n'][0]
                        if not record_count:
                            record_count = 15
                    except:
                        record_count = 15

                    n = record_count * -1
                    docs = metadata.list_jobs(params['ARASTUSER'])

                if docs:
                    for doc in docs[n:]:
                        row = [doc['job_id'], str(doc['data_id']), doc['status'],]

                        try:
                            row.append(str(doc['computation_time']))
                        except:
                            row.append('')
                        row.append(str(doc['message']))

                        try:
                            pt.add_row(row)
                        except:
                            pt.add_row(doc['job_id'], "error")

                    ack = pt.get_string()
                else:
                    ack = "Error: Job %s does not exist" % job_stat

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
                
    except:
        logging.error("Unexpected error: {}".format(sys.exc_info()[0]))
        traceback = format_exc(sys.exc_info())
        print traceback
        ack = "Error: Malformed message. Using latest version?"

    # Check client version TODO:handle all cases
    try:
        if StrictVersion(params['version']) < StrictVersion('0.0.7') and params['command'] == 'run':
            ack += "\nNew version of client available.  Please update"
    except:
        if params['command'] == 'run':
            ack += "\nNew version of client available.  Please update."

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
    mongo_host = parser.get('meta', 'mongo.host')
    metadata = meta.MetadataConnection(config_file, mongo_host)

    ##### CherryPy ######
    root = Root()
    root.job = JobResource({})
    root.shock = ShockResource({"shockurl": get_upload_url()})
    root.status = StatusResource()
    
    conf = {
        'global': {
            'server.socket_host': '0.0.0.0',
            'server.socket_port': 8080,
            'log.screen': True,
        },
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        }
    }

    cherrypy.quickstart(root, '/', conf)

    # TODO remove this ######
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='rpc_queue')
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(on_request, queue='rpc_queue')
    print " [x] Awaiting RPC requests..."
    channel.start_consuming()
    ##### REMOVE #######



class Root(object):
    pass

class JobResource(object):

    def __init__(self, content):
        self.content = content

    exposed = True

    def GET(self):
        pass

    def PUT(self):
        pass

    def POST(self):
        json_request = cherrypy.request.body.read()
        return route_job(json_request)

class StatusResource:
    def GET(self):
        json_request = cherrypy.request.body.read()
        return route_job(json_request)

class ShockResource(object):

    def __init__(self, content):
        self.content = content

    exposed = True

    def GET(self):
        return json.dumps(self.content)
