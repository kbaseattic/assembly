"""
Job router.  Recieves job requests.  Manages data transfer, job queuing.
"""
# Import python libs
import cherrypy
import datetime
import json
import logging
import pika
import pprint
import os
import re
import sys
from bson import json_util
from ConfigParser import SafeConfigParser
from distutils.version import StrictVersion
from prettytable import PrettyTable
from traceback import format_exc

# Import A-RAST libs
import metadata as meta
import shock
from nexus import client as nexusclient

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
    #if params['version'].find('beta'):
     #   print 'Sent to testing queue'
      #  return 'jobs.test'
    try:
        routing_key = params['queue']
    except:
        pass
    if routing_key:
        return routing_key
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
        if StrictVersion(params['version']) < StrictVersion('0.2.1') and params['command'] == 'run':
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


def authenticate_request():
    print 'authorization'
    print cherrypy.request.headers
    try:
        token = cherrypy.request.headers['Authorization']
    except:
        raise cherrypy.HTTPError(403)
    
    #parse out username
    r = re.compile('un=(.*?)\|')
    m = r.search(token)
    if m:
        user = m.group(1)
    else:
        raise cherrypyHTTPError(403, 'Bad Token')
    print user
    auth_info = metadata.get_auth_info(user)
    if auth_info:
        # Check exp date
        auth_time_str = auth_info['token_time']
        atime = datetime.datetime.strptime(auth_time_str, '%Y-%m-%d %H:%M:%S.%f')
        ctime = datetime.datetime.today()
        print 'found auth'
        globus_user = user
        print auth_info
        if (ctime - atime).seconds > 15*60: # 15 min auth token
            print 'expired, reauth'
            nexus = nexusclient.NexusClient(config_file = 'nexus/nexus.yml')
            globus_user = nexus.authenticate_user(token)
            metadata.update_auth_info(globus_user, token, str(ctime))
            
    else:
        print 'auth first time'
        nexus = nexusclient.NexusClient(config_file = 'nexus/nexus.yml')
        globus_user = nexus.authenticate_user(token)
        if globus_user:
            metadata.insert_auth_info(globus_user, token,
                                      str(datetime.datetime.today()))
        else:
            raise Exception ('problem authorizing with nexus')
        
    try:
        #cherrypy.request.params['globus_user'] = globus_user
        print globus_user
    except:
        raise cherrypy.HTTPError(403, 'Failed Authorization')
    

def start(config_file, mongo_host=None, mongo_port=None,
          rabbit_host=None, rabbit_port=None):
    global parser, metadata
    logging.basicConfig(level=logging.DEBUG)

    parser = SafeConfigParser()
    parser.read(config_file)
    metadata = meta.MetadataConnection(config_file, mongo_host)

    ##### CherryPy ######
    root = Root()
    root.user = UserResource()
    root.module = ModuleResource()
    root.shock = ShockResource({"shockurl": get_upload_url()})
    
    conf = {
        'global': {
            'server.socket_host': '0.0.0.0',
            'server.socket_port': 8000,
            'log.screen': True,
        },
    }

    #cherrypy.request.hooks.attach('before_request_body', authenticate_request)
    cherrypy.quickstart(root, '/', conf)
    ###### DOES IT AUTH EVERY REQUEST??? ########
    

class JobResource:

    @cherrypy.expose
    def new(self, userid=None):
        authenticate_request()
        params = json.loads(cherrypy.request.body.read())
        params['ARASTUSER'] = userid
        params['oauth_token'] = cherrypy.request.headers['Authorization']
        return route_job(json.dumps(params))

    @cherrypy.expose
    def kill(self, userid=None, job_id=None):
        print 'kill'
        return 'KILL not implemented'

    @cherrypy.expose
    def default(self, job_id, *args, **kwargs):
        if len(args) == 0: # /user/USER/job/JOBID/
            pass
        else:
            resource = args[0]
        try:
            userid = kwargs['userid']
        except:
            raise cherrypyHTTPError(403)

        if resource == 'shock_node':
            return self.get_shock_node(userid, job_id)
        elif resource == 'status':
            return self.status(job_id=job_id, userid=userid)
        elif resource == 'kill':
            return self.kill(job_id=job_id)
        else:
            return resource
    @cherrypy.expose
    def status(self, **kwargs):
        try:
            job_id = kwargs['job_id']
        except:
            job_id = None
        if job_id:
            doc = metadata.get_job(kwargs['userid'], job_id)
            if doc:
                return doc['status']
            else:
                return "Could not get job status"
            
        else:
            try: 
                records = int(kwargs['records'])
            except:
                records = 15

            docs = metadata.list_jobs(kwargs['userid'])
            pt = PrettyTable(["Job ID", "Data ID", "Status", "Run time", "Description"])
            if docs:
                for doc in docs[-records:]:
                    row = [doc['job_id'], str(doc['data_id']), doc['status'],]
                    try:
                        row.append(str(doc['computation_time']))
                        row.append(str(doc['message']))
                    except:
                        row += ['','']
                    pt.add_row(row)
                return pt.get_string() + "\n"



    def get_shock_node(self, userid=None, job_id=None):
        """ GET /user/USER/job/JOB/node """
        if not job_id:
            raise cherrypy.HTTPError(403)
        doc = metadata.get_job(userid, job_id)
        try:
            result_data = doc['result_data']
        except:
            raise cherrypy.HTTPError(500)
        return json.dumps(result_data)

        
class UserResource(object):

    @cherrypy.expose
    def new():
        pass

    @cherrypy.expose
    def default(self):
        print 'user default'
        pass

    default.job = JobResource()

    def __getattr__(self, name):
        if name is not ('_cp_config'): #assume username
            cherrypy.request.params['userid'] = name
            return self.default
        raise AttributeError("%r object has no attribute %r" % (self.__class__.__name__, name))

        
class StatusResource:
    def current(self):
        json_request = cherrypy.request.body.read()
        return route_job(json_request)

class ModuleResource:
    @cherrypy.expose
    def default(self, module_name, *args, **kwargs):
        print module_name
        if len(args) == 0: # /module/
            pass
        else:
            resource = args[0]
        if resource == 'avail':
            return 'Available Modules'
        return module_name
        
class ShockResource(object):

    def __init__(self, content):
        self.content = content

    @cherrypy.expose
    def index(self):
        print 'shock'
        return json.dumps(self.content)


class Root(object):
    @cherrypy.expose
    def default(self):
        print 'root'

