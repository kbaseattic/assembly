"""
Job router.  Recieves job requests.  Manages data transfer, job queuing.
"""
# Import python libs
import ast
import cherrypy
import datetime
import errno
import json
import logging
import pika
import pprint
import os
import re
import requests
import sys
import threading
import tarfile
import time
import uuid
from bson import json_util
from ConfigParser import SafeConfigParser
from distutils.version import StrictVersion
from prettytable import PrettyTable
from traceback import format_exc

# Import A-RAST libs
import asmtypes
import recipes
import metadata as meta
import shock
from nexus import client as nexusclient
import client as ar_client
from assembly import ignored

# Global variables
parser = None
metadata = None
rjobmon = None

logger = logging.getLogger(__name__)


def send_message(body, routingKey):
    """ Place the job request on the correct job queue """

    rmq_host = parser.get('assembly', 'rabbitmq_host')
    rmq_port = parser.get('assembly', 'rabbitmq_port')

    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=rmq_host, port=int(rmq_port)))
    channel = connection.channel()
    channel.queue_declare(queue=routingKey, durable=True)
    #channel.basic_qos(prefetch_count=1)
    channel.basic_publish(exchange = '',
                          routing_key=routingKey,
                          body=body,
                          properties=pika.BasicProperties(
                          delivery_mode=2)) #persistant message
    logger.info("Sent to queue: %r: %r" % (routingKey, body))
    connection.close()


def send_kill_message(user, job_id=None):
    """ Place the kill request on the correct job queue """
    ## Try to kill all
    if job_id == 'all':
        rjobmon.user_jobs(user)
        uids = rjobmon.user_jobs(user).keys()
        jobs = [metadata.get_job_by_uid(u) for u in uids]
    elif job_id:
        jobs = [metadata.get_job(user, job_id)]

    kill_status = ''
    for job_doc in jobs:
        try:
            jid = job_doc['job_id']
            uid = job_doc['_id']
            status = job_doc['status']
        except TypeError:
            kill_status += 'Invalid job ID\n'
            break

        if status == 'Queued':
            metadata.update_job(uid, 'status', 'Terminated by user')
            metadata.rjob_remove(uid)
            kill_status += 'Job {}: Removed From Queue\n'.format(jid)
            publish_kill_request(user, jid)

        elif re.search(r"(Running|Stage|Data)", status):
            publish_kill_request(user, jid)
            kill_status += 'Job {}: Kill Request Sent\n'.format(jid)

        elif re.search(r"(Complete|Terminate)", status):
            kill_status += 'Job {}: No longer running.\n'.format(jid)

        else:
            kill_status += 'Job {}: Unexpected error.\n'.format(jid)

    return kill_status.rstrip() or 'No jobs to be killed'


def publish_kill_request(user, job_id):
    msg = json.dumps({'user':user, 'job_id':str(job_id)})

    rmq_host = parser.get('assembly', 'rabbitmq_host')
    rmq_port = parser.get('assembly', 'rabbitmq_port')

    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=rmq_host, port=int(rmq_port)))
    channel = connection.channel()
    channel.exchange_declare(exchange='kill',
                             type='fanout')
    channel.basic_publish(exchange='kill',
                          routing_key='',
                          body=msg,)
    logger.info("Sent to kill exchange: {}".format(job_id))
    connection.close()


def determine_routing_key(size, params):
    """Depending on job submission, decide which queue to route to."""
    routing_key = params.get('queue')
    return routing_key or parser.get('rabbitmq','default_routing_key')


def get_upload_url():
    global parser
    return parser.get('shock', 'host')


def check_valid_client(body):
    client_params = json.loads(body) #dict of params
    min_version = parser.get('assembly', 'min_cli_version')
    try: return StrictVersion(client_params['version']) >= StrictVersion(min_version)
    except: return True


def route_job(body):
    if not check_valid_client(body):
        return "Client too old, please upgrade"
    client_params = json.loads(body) #dict of params
    routing_key = determine_routing_key (1, client_params)
    job_id = metadata.get_next_job_id(client_params['ARASTUSER'])
    if not client_params['data_id']:
        data_id, _ = register_data(body)
        client_params['data_id'] = data_id
    client_params['job_id'] = job_id

    ## Check that user queue limit is not reached
    uid = metadata.insert_job(client_params)
    metadata.rjob_insert(uid, client_params)
    logger.debug("Inserting job record: {}".format(client_params))
    metadata.update_job(uid, 'status', 'Queued')
    p = dict(client_params)
    metadata.update_job(uid, 'message', p['message'])

    msg = json.dumps(p)
    send_message(msg, routing_key)
    response = str(job_id)
    return response


def route_data(body):
    data_id, _ = register_data(body)
    return json.dumps({"data_id": data_id})


def register_data(body):
    """ User is only submitting libraries, return data ID """
    if not check_valid_client(body):
        return "Client too old, please upgrade"
    client_params = json.loads(body) #dict of params
    keep = ['assembly_data', 'client', 'ARASTUSER', 'message', 'version', 'kbase_assembly_input']
    data_info = {k:client_params.get(k) for k in keep if client_params.get(k)}
    logger.info('Register data: {}'.format(data_info))
    return metadata.insert_data(data_info['ARASTUSER'], data_info)


def analyze_data(body): #run fastqc
    """Send data to compute node for analysis, wait for result"""
    # analysis_pipes = ['fastqc']
    # client_params = json.loads(body) #dict of params
    # job_id = metadata.get_next_job_id(client_params['ARASTUSER'])
    # client_params['pipeline'] = analysis_pipes
    # client_params['job_id'] = job_id
    # routing_key = determine_routing_key (1, client_params)
    # uid = metadata.insert_job(client_params)
    # msg = json.dumps(dict(client_params))
    # metadata.update_job(uid, 'status', 'Analysis')
    # send_message(msg, routing_key)

    client_params = json.loads(body) #dict of params
    routing_key = 'qc'
    job_id = metadata.get_next_job_id(client_params['ARASTUSER'])
    client_params['job_id'] = job_id
    if not client_params['data_id']:
        data_id = metadata.get_next_data_id(client_params['ARASTUSER'])
        client_params['data_id'] = data_id

    analysis_pipes = ['fastqc']
    client_params['pipeline'] = analysis_pipes
    client_params['compute_type'] = 'qc'

    ## Check that user queue limit is not reached
    uid = metadata.insert_job(client_params)
    logger.debug("Inserting job record: {}".format(client_params))
    metadata.update_job(uid, 'status', 'Queued')
    p = dict(client_params)
    metadata.update_job(uid, 'message', p['message'])
    msg = json.dumps(p)

    send_message(msg, routing_key)
    response = str(job_id)
    return response


def sanitize_doc(doc):
    """ Removes unwanted information in response data """
    to_remove = ['oauth_token', '_id', 'data']
    for k in to_remove:
        try: del doc[k]
        except KeyError: pass
    return doc


def authenticate_request():
    if cherrypy.request.method == 'OPTIONS':
        return 'OPTIONS'
    token = cherrypy.request.headers.get('Authorization')
    if not token:
        logger.warning("Auth error")
        raise cherrypy.HTTPError(403)

    #parse out username
    r = re.compile('un=(.*?)\|')
    m = r.search(token)
    if m:
        user = m.group(1)
    else:
        logger.warning("Auth error")
        raise cherrypy.HTTPError(403, 'Bad Token')
    auth_info = metadata.get_auth_info(user)

    self_path = os.path.join(os.path.dirname( __file__ ))
    nexus_config_file = os.path.join(self_path, "nexus", "nexus.yml")

    #### Previous Authorization found
    if auth_info:
        # Check exp date
        auth_time_str = auth_info['token_time']
        atime = datetime.datetime.strptime(auth_time_str, '%Y-%m-%d %H:%M:%S.%f')
        ctime = datetime.datetime.today()
        globus_user = user
        if (ctime - atime).seconds > 15*60: # 15 min auth token
            logger.warning('Token expired, reauthenticating with Globus')
            nexus = nexusclient.NexusClient(config_file = nexus_config_file)
            globus_user = nexus.authenticate_user(token)
            metadata.update_auth_info(globus_user, token, str(ctime))

    #### Validate Token
    else:
        nexus = nexusclient.NexusClient(config_file = nexus_config_file)
        globus_user = nexus.authenticate_user(token)
        if globus_user:
            metadata.insert_auth_info(globus_user, token,
                                      str(datetime.datetime.today()))
        else:
            raise Exception ('problem authorizing with nexus')
    try:
        if globus_user is None:
            return user
        return globus_user
    except:
        raise cherrypy.HTTPError(403, 'Failed Authorization')


def CORS():
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
    cherrypy.response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    cherrypy.response.headers["Access-Control-Allow-Headers"] = "Authorization, origin, content-type, accept"

def start(config_file, shock_url=None,
          mongo_host=None, mongo_port=None,
          rabbit_host=None, rabbit_port=None):

    global parser, metadata, rjobmon
    # logging.basicConfig(level=logging.DEBUG)

    parser = SafeConfigParser()
    parser.read(config_file)
    collections = {'jobs': parser.get('meta', 'mongo.collection'),
                   'auth': parser.get('meta', 'mongo.collection.auth'),
                   'data': parser.get('meta', 'mongo.collection.data'),
                   'running': parser.get('meta', 'mongo.collection.running')}

    # Config precedence: args > config file

    if shock_url:
        parser.set('shock', 'host', shock.verify_shock_url(shock_url))
    if mongo_host:
        parser.set('assembly', 'mongo_host', mongo_host)
    if mongo_port:
        parser.set('assembly', 'mongo_port', str(mongo_port))
    if rabbit_host:
        parser.set('assembly', 'rabbitmq_host', rabbit_host)
    if rabbit_port:
        parser.set('assembly', 'rabbitmq_port', str(rabbit_port))

    metadata = meta.MetadataConnection(parser.get('assembly', 'mongo_host'),
                                       int(parser.get('assembly', 'mongo_port')),
                                       parser.get('meta', 'mongo.db'),
                                       collections)

    ##### Running Job Monitor #####
    rjobmon = RunningJobsMonitor(metadata)
    cherrypy.process.plugins.Monitor(cherrypy.engine, rjobmon.purge,
                                     frequency=int(parser.get('monitor', 'running_job_freq'))).subscribe()

    ##### CherryPy ######
    conf = {
        'global': {
            'server.socket_host': '0.0.0.0',
            'server.socket_port': int(parser.get('assembly', 'cherrypy_port')),
            'log.screen': True,
            'ar_shock_url': parser.get('shock', 'host'),
            'environment': 'production'
            },
    }

    static_root = parser.get('web_serve', 'root')

    root = Root()
    root.user = UserResource()
    root.module = ModuleResource()
    root.recipe = RecipeResource()
    root.shock = ShockResource({"shockurl": get_upload_url()})
    root.static = StaticResource(static_root)

    #### Admin Routes ####
    rmq_host = parser.get('assembly', 'rabbitmq_host')
    rmq_mp = parser.get('rabbitmq', 'management_port')
    rmq_user = parser.get('rabbitmq', 'management_user')
    rmq_pass = parser.get('rabbitmq', 'management_pass')
    root.admin = SystemResource(rmq_host, rmq_mp, rmq_user, rmq_pass)

    cherrypy.request.hooks.attach('before_finalize', CORS)
    cherrypy.quickstart(root, '/', conf)


def parser_as_dict(parser):
    """Return configparser as a dict"""
    d = dict(parser._sections)
    for k in d:
        d[k] = dict(parser._defaults, **d[k])
        d[k].pop('__name__', None)
    return d


def start_qc_monitor(rabbit_host, rabbit_port):
    """
    Listens on QC queue for finished QC jobs
    """
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=rabbit_host, port=int(rabbit_port)))
    channel = connection.channel()
    channel.exchange_declare(exchange='qc-complete',
                             type='fanout')
    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange='qc',
                       queue=queue_name)
    logger.info('Waiting for QC completion')
    channel.basic_consume(qc_callback,
                          queue=queue_name,
                          no_ack=True)

    channel.start_consuming()


def qc_callback():
    pass

###########
###########
#CherryPy Resources
###########

class JobResource:
    @cherrypy.expose
    def new(self, userid=None):
        token_user = authenticate_request()
        if token_user == 'OPTIONS':
            return ('New Job Request') # To handle initial html OPTIONS requess
        # user IDs can be in the email address format; somehow cherrypy converts @ and . to _
        sanitized_token_user = token_user.replace('@', '_').replace('.', '_')
        if not (userid == sanitized_token_user or userid.split('_rast')[0] == sanitized_token_user):
            raise cherrypy.HTTPError(403)

        path = parser.get('monitor', 'running_job_user_list')
        if not os.path.isabs(path):
            libpath = os.path.abspath(os.path.dirname( __file__ ))
            path = os.path.join(libpath, path)
        with open(path) as j:
            user_list = json.load(j)
        user = next((u for u in user_list if u["user"] == userid), None)
        if user:
            if user["job_limit"] == -1:
                pass
            elif len(rjobmon.user_jobs(userid)) >= user["job_limit"]:
                raise cherrypy.HTTPError(403, "User Job limit reached")
        elif len(rjobmon.user_jobs(userid)) >= int(parser.get('monitor', 'running_job_limit')):
            raise cherrypy.HTTPError(403, "User Job limit reached")
        params = json.loads(cherrypy.request.body.read())
        params['ARASTUSER'] = userid
        params['oauth_token'] = cherrypy.request.headers['Authorization']
        return route_job(json.dumps(params))

    @cherrypy.expose
    def kill(self, userid=None, job_id=None):
        if userid == 'OPTIONS':
            return ('New kill Request') # To handle initial html OPTIONS requess
        k = send_kill_message(userid, job_id=job_id)
        if k:
            return k
        return 'Kill request sent for job {}'.format(job_id)

    @cherrypy.expose
    def default(self, job_id=None, *args, **kwargs):
        resource = None
        if len(args) == 0: # /user/USER/job/JOBID/
            pass
        else:
            resource = args[0]
        try:
            userid = kwargs['userid']
            del kwargs['userid']
        except:
            raise cherrypy.HTTPError(403)

        token = cherrypy.request.headers.get('Authorization')

        ### No job_id, return all
        if not job_id:
            return self.status(job_id=job_id, format='json', **kwargs)

        ### job_id
        if resource == 'shock_node':
            return self.get_shock_node(userid, job_id)
        elif resource == 'assembly':
            try: asm = args[1]
            except IndexError: asm = None
            return self.get_assembly_nodes(userid, job_id, asm)
        elif resource == 'assemblies':
            try: asm = args[1]
            except IndexError: asm = None
            return self.get_assembly_handles(userid, job_id, asm)
        elif resource == 'results':
            try: args = args[1:]
            except IndexError: args = ()
            return self.get_results(userid, job_id, *args, **kwargs)
        elif resource == 'data':
            return self.get_job_data(userid, job_id)
        elif resource == 'report_handle':
            return self.get_report_handle(userid, job_id)
        elif resource == 'report':
            return self.get_report_stats(userid, job_id, token)
        elif resource == 'log':
            return self.get_report_log(userid, job_id, token)
        elif resource == 'analysis':
            return self.get_analysis_handle(userid, job_id)
        elif resource == 'status':
            return self.status(userid, job_id=job_id, **kwargs)
        elif resource == 'kill':
            authenticate_request()
            return self.kill(job_id=job_id, userid=userid)
        else:
            raise cherrypy.HTTPError(403, 'Resource not found: {}'.format(resource))

    def get_job_data(self, userid, job_id=None):
        if userid == 'OPTIONS':
            return ('New Data Request') # To handle initial html OPTIONS requess
        try:
            doc = metadata.get_job(userid, job_id)
            del doc['oauth_token']
            return json.dumps(doc)
        except:
            raise cherrypy.HTTPError(403, 'Could not get data')

    @cherrypy.expose
    def status(self, userid, **kwargs):
        ### Single Job ID
        job_id = kwargs.get('job_id')
        if job_id:
            doc = metadata.get_job(userid, job_id)
            if doc:
                if kwargs.get('format') == 'json':
                    return json.dumps(doc)
                return doc['status']
            else:
                return "Could not get job status"

        ### List of Recent Jobs
        else:
            records = int(kwargs.get('records', 100))
            detail = kwargs.get('detail')
            docs = [sanitize_doc(d) for d in metadata.list_jobs(userid)]
            columns = ["Job ID", "Data ID", "Status", "Run time", "Description"]
            if detail:
                columns.append("Parameters")
            pt = PrettyTable(columns)
            if detail:
                pt.align["Parameters"] = "l"
            if docs:
                if kwargs.get('format') == 'json':
                    return json.dumps(list(reversed(docs[-records:])));
                for doc in docs[-records:]:
                    try:
                        stat_msg = doc.get('status')[:40]
                    except TypeError:
                        stat_msg = ''
                    row = [doc.get('job_id'), str(doc.get('data_id')), stat_msg]
                    row.append(str(doc.get('computation_time', '')))
                    row.append(str(doc.get('message', '')))
                    if detail:
                        try:
                            row.append(self.parse_job_doc_to_parameter(doc))
                        except:
                            row += ['']
                    pt.add_row(row)
                return pt.get_string() + "\n"


    def get_validated_job(self, user=None, job=None):
        if not job:  raise cherrypy.HTTPError(403, 'Undefined Job ID')
        if not user: raise cherrypy.HTTPError(403, 'Undefined user ID')
        doc = metadata.get_job(user, job)
        if not doc:  raise cherrypy.HTTPError(403, 'Invalid user or job ID')
        return doc

    def get_shock_node(self, userid=None, job_id=None):
        """ GET /user/USER/job/JOB/node """
        doc = self.get_validated_job(userid, job_id)
        try:
            result_data = doc['result_data_legacy'][0]
        except Exception as e:
            raise cherrypy.HTTPError(403)
        return json.dumps(result_data)

    def get_assembly_nodes(self, userid=None, job_id=None, asm=None):
        doc = self.get_validated_job(userid, job_id)
        try:
            if asm:
                if asm.isdigit() and asm != '0':
                    result_data = doc['contig_ids'][0].items()[int(asm)-1]
                elif asm == 'auto':
                    result_data = doc['contig_ids'][0].items()[0]
            else:
                result_data = doc['contig_ids'][0]
        except Exception as e:
            logger.warn("Could not get assembly nodes")
            raise cherrypy.HTTPError(500)
        return json.dumps(result_data)

    def get_assembly_handles(self, userid=None, job_id=None, asm=None):
        """ Get assembly file handles"""

        if not asm:         tag = None
        elif asm.isdigit(): tag = 'quast-{}'.format(asm)
        elif asm == 'auto': tag = 'rank-1'
        else:               tag = asm

        results = self.get_results(userid, job_id, tags=tag, type='contigs,scaffolds')
        handles = self.filesets_to_first_handles(json.loads(results))

        return json.dumps(handles)

    def get_results(self, userid=None, job_id=None, *args, **kwargs):
        """ Get results file handles with filtering based on type and tags """
        doc = self.get_validated_job(userid, job_id)
        filesets = []
        try:
            keep = kwargs.get('types') or kwargs.get('type')
            tags = kwargs.get('tags')  or kwargs.get('tag')
            if keep: keep = set(keep.split(','))
            if tags: tags = set(tags.split(','))
            for fileset in doc['result_data']:
                pass_tags = not tags or set(fileset['tags']) & tags
                pass_type = not keep or fileset['type'] in keep
                if pass_tags and pass_type:
                    filesets.append(fileset)
        except Exception as e:
            raise cherrypy.HTTPError(403, "No results found for job {}".format(job_id))
        return json.dumps(filesets)

    def get_analysis_handle(self, userid=None, job_id=None):
        """Get quast tarball handle"""
        results = self.get_results(userid, job_id, type='tar')
        try:
            handle = json.loads(results)[0]['file_infos'][0]
        except Exception as e:
            raise cherrypy.HTTPError(403, 'No analysis tarball found for job {}'.format(job_id))
        return json.dumps(handle)

    def get_report_handle(self, userid=None, job_id=None):
        """ Get job report file handles """
        doc = self.get_validated_job(userid, job_id)
        handle = None
        try:
            handle = doc['report'][0]['file_infos'][0]
        except:
            raise cherrypy.HTTPError(403, "Report not found for job {}".format(job_id))
        return json.dumps(handle)

    def get_report(self, userid=None, job_id=None, token=None):
        """ Get job report in text """
        handle = json.loads(self.get_report_handle(userid, job_id))
        if not handle:
            raise cherrypy.HTTPError(403, 'Report not found for job {}'.format(job_id))
        try:
            report = shock.get_handle(handle, token)
        except Exception as e:
            raise cherrypy.HTTPError(403, 'Could not get report using shock: {}'.format(e))
        return report

    def get_report_log(self, userid=None, job_id=None, token=None):
        log = self.get_report(userid, job_id, token)
        if not log: return
        pat = self.get_quast_pattern()
        log = pat.sub('', log)
        return log

    def get_report_stats(self, userid=None, job_id=None, token=None):
        report = self.get_report(userid, job_id, token)
        if not report: return
        pat = self.get_quast_pattern()
        match = pat.search(report)
        if match:
            stats = "QUAST: " + match.group()
            return stats

    def get_quast_pattern(self):
        return re.compile(r"(^All statistics are based on contigs(.|\n)*)(?=^Arast Pipeline: Job)",
                          re.MULTILINE)

    def filesets_to_first_handles(self, filesets):
        try: handles = [fs['file_infos'][0] for fs in filesets]
        except: raise cherrypy.HTTPError(403, "Handles not found in filesets")
        return handles

    def parse_job_doc_to_parameter(self, doc):
        pipeline = doc.get('pipeline')
        recipe = doc.get('recipe')
        wasp = doc.get('wasp')
        if pipeline == 'auto': pipeline = None
        if pipeline:
            pipeline = ast.literal_eval(str(pipeline))
            pipeline = self.parse_pipeline_to_str(pipeline)
        if recipe:
            recipe = ast.literal_eval(str(recipe))
            recipe = ' '.join(["-r "+r for r in recipe])
        if wasp:
            wasp = ast.literal_eval(str(wasp))
            wasp = ' '.join(["-w "+w for w in wasp])
        param = pipeline or recipe or wasp or '-p auto'
        return param

    def parse_pipeline_to_str(self, pipeline):
        """Convert pipeline structure back to a command line parameter string
        Input examples:
            [u'velvet kiki']
            [[u'none tagdust', u'kiki velvet']]
            [[u'none tagdust', u'kiki velvet'], [u'spades']]
            [[u'none tagdust', u'velvet', u'?hash_length=29-77:4'], [u'kiki']]
        Output:
            -p 'velvet kiki'
            -p 'none tagdust' 'kiki velvet'
            -p 'none tagdust' 'kiki velvet' -p spades
            -p 'none tagdust' velvet ?hash_length=29-77:4 -p kiki
        Converts legacy run parameters:
            command line:   ... -a velvet kiki
            internal structure: [u'velvet kiki']
            output:            -p 'velvet kiki'

        """
        pipes = []
        if type(pipeline[0]) is not list:
            pipeline = [pipeline]
        for pipe in pipeline:
            params = ['-p']
            for stage in pipe:
                if ' ' in stage: stage = "'{}'".format(stage)
                params.append(stage)
            pipes.append(' '.join(params))
        return ' '.join(pipes)


class StaticResource:

    def __init__(self, static_root):
        self.static_root = static_root
        self._cp_config = {'tools.staticdir.on' : True,
                           'tools.staticdir.dir': self.static_root}

    def _makedirs(self, dir):
        with ignored(OSError):
            os.makedirs(dir)

    def format_static_url(self, datadir=None, userid=None, job_id=None):
        common = os.path.commonprefix([self.static_root, datadir])
        return '/static/{}'.format(datadir.replace(common, ''))

    @cherrypy.expose
    def serve(self, userid=None, resource=None, resource_id=None, type='analysis', **kwargs):
        token = cherrypy.request.headers.get('Authorization')
        aclient = ar_client.Client('localhost', userid, token)
        outdir = os.path.join(self.static_root, userid, resource, resource_id)
        self._makedirs(outdir)

        ## Get all data
        if resource == 'job':
            job_id = resource_id
            doc = metadata.get_job(userid, job_id)
            # Download data
            if type == 'analysis':
                adir = os.path.join(outdir, 'analysis')
                self._makedirs(adir)
                report = aclient.get_job_analysis_tarball(job_id=job_id, outdir=adir)
                return self.format_static_url(report, userid, job_id)

    serve._cp_config = {'tools.staticdir.on' : False}


class FilesResource:
    def default(self, userid=None):
        testResponse = {}
        return '{}s files!'.format(userid)


class DataResource:
    @cherrypy.expose
    def new(self, userid=None):
        token_user = authenticate_request()
        if token_user == 'OPTIONS':
            return ('New Job Request') # To handle initial html OPTIONS requess
        if not (userid == token_user or userid.split('_rast')[0] == token_user):
            raise cherrypy.HTTPError(403)

        params = json.loads(cherrypy.request.body.read())
        params['ARASTUSER'] = userid
        params['oauth_token'] = cherrypy.request.headers['Authorization']
        #Return data id
        return route_data(json.dumps(params))

    @cherrypy.expose
    def default(self, data_id=None, userid=None):
        if not data_id: ## /user/USERID/data/
            return json_util.dumps(list(metadata.get_data_docs(userid)))
        else: ## /user/USERID/data/<data.id>
            return json_util.dumps(metadata.get_data_docs(userid, data_id))


class UserResource(object):
    @cherrypy.expose
    def new():
        pass

    @cherrypy.expose
    def default(self):
        return 'user default ok'

    default.job = JobResource()
    default.files = FilesResource()
    default.data = DataResource()

    # Pull user id from URL
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
    def default(self, module_name="avail", *args, **kwargs):
        if module_name == 'avail' or module_name == 'all':
            path = parser.get('web', 'ar_modules')
            if not os.path.isabs(path):
                libpath = os.path.abspath(os.path.dirname( __file__ ))
                path = os.path.join(libpath, path)
            with open(path) as outfile:
                return outfile.read()
        else: raise cherrypy.HTTPError(403)


class RecipeResource:
    @cherrypy.expose
    def default(self, module_name="avail", *args, **kwargs):
        reload(recipes)
        all = recipes.get_all()
        if module_name == 'avail' or module_name == 'all':
            return json.dumps(all)
        else:
            try:
                if args[0] == 'raw':
                    return json.dumps(all[module_name]['recipe'])
                elif args[0] == 'description':
                    return json.dumps(all[module_name]['description'])
            except IndexError: return json.dumps(all[module_name])
            except: raise cherrypy.HTTPError(403)


class SystemResource:

    def __init__(self, rmq_host, rmq_admin_port, rmq_admin_user, rmq_admin_pass):
        self.rmq_host = rmq_host
        self.rmq_admin_port = rmq_admin_port
        self.rmq_admin_user = rmq_admin_user
        self.rmq_admin_pass = rmq_admin_pass

    @cherrypy.expose
    def system(self, resource=None, *args):
        if resource == 'node':
            if len(args) == 0: # List nodes
                return self.get_connections()
            if len(args) == 2:
                node_ip = args[0]
                command = args[1]
                if command == 'close':
                    logger.warning("Closing connection: {}".format(node_ip))
                    sys.stdout.flush()
                    return self.close_connection(node_ip)
        elif resource == 'config':
            return json.dumps(parser_as_dict(parser))
        elif resource == 'jobs':
            return rjobmon.stats()

    def get_connections(self):
        """Returns a list of deduped connection IPs"""
        conns = json.loads(requests.get('http://{}:{}/api/connections'.format(
                    self.rmq_host, self.rmq_admin_port),
                                        auth=(self.rmq_admin_user, self.rmq_admin_pass)).text)
        ## Dedupe
        unique = set()
        for c in conns:
            unique.add(c['peer_host'])
        con_json = []
        for u in unique:
            con_json.append({'host': u})
        return json.dumps(con_json)

    def close_connection(self, host):
        conns = json.loads(requests.get('http://{}:{}/api/connections'.format(
                    self.rmq_host, self.rmq_admin_port),
                                        auth=(self.rmq_admin_user, self.rmq_admin_pass)).text)
        shutdown_success = False
        for c in conns:
            if c['peer_host'] == host:
                res = requests.delete('http://{}:{}/api/connections/{}'.format(
                    self.rmq_host, self.rmq_admin_port, c['name']),
                                      auth=(self.rmq_admin_user, self.rmq_admin_pass)).text
                shutdown_success = True
        if shutdown_success:
            return '{} will shutdown after completing running job(s)\n'.format(host)
        else:
            return 'Could not shutdown node: {}'.format(host)


class ShockResource(object):

    def __init__(self, content):
        self.content = content

    @cherrypy.expose
    def default(self):
        return json.dumps(self.content)


class Root(object):
    @cherrypy.expose
    def default(self):
        logger.info('Accessing root')


########### Running Jobs Service
class RunningJobsMonitor():
    def __init__(self, meta_obj):
        self.meta = meta_obj
        self.past_jobs = {}

    def purge(self, user=None):
        jobs = self.meta.rjob_all()
        set_past = set(self.past_jobs.keys())
        set_current = set(jobs.keys())
        set_intersect = set_current.intersection(set_past)

        ### Remove Stale Jobs
        for same in set_intersect:
            job = self.meta.get_job_by_uid(same)
            if (self.past_jobs[same]['timestamp'] == jobs[same]['timestamp'] and
                jobs[same]['status'] == 'running'):
                logger.info('Removing stale job: {}'.format(same))
                self.meta.rjob_remove(same)
            elif jobs[same]['status'] == 'running':
                logger.info('Running: {}'.format(same))
            elif job['status'] == 'queued':
                logger.info('Queued: {}'.format(same))
            else:
                self.meta.rjob_remove(same)
                logger.warning('Removing rogue job: {}'.format(same))
        self.past_jobs = jobs

    def user_jobs(self, user):
        """ Returns all current jobs of USER. """
        user_jobs = self.meta.rjob_user_jobs(user)
        return user_jobs

    def stats(self):
        return self.meta.rjob_admin_stats()
