#! /usr/bin/env python
"""
Arast Daemon

The Arast daemon runs on the control node.

"""
import os
import argparse
import sys
import daemon
import logging
import json
import pymongo
import multiprocessing
import pika
import re
import requests

from ConfigParser import SafeConfigParser
from multiprocessing import current_process as proc

import consume
import shock
import utils


logger = logging.getLogger(__name__)

#context = daemon.DaemonContext(stdout=sys.stdout) #temp print to stdout
#TODO change to log file

#with context:
mgr = multiprocessing.Manager()
job_list = mgr.list()
job_list_lock = multiprocessing.Lock()
kill_list = mgr.list()
kill_list_lock = multiprocessing.Lock()

def start(arasturl, config, num_threads, queue, datapath, binpath, modulebin):

    logger.info("==========================================")
    logger.info("  Starting Assembly Service Compute Node")
    logger.info("==========================================")

    #### Get default configuration from ar_compute.conf
    cparser = SafeConfigParser()
    cparser.read(config)
    logging.getLogger('yapsy').setLevel(logging.WARNING)
    logging.getLogger('yapsy').propagate = True
    logging.getLogger('pika').propagate = True
    logging.getLogger('pika').setLevel(logging.WARNING)

    arastport = cparser.get('assembly','arast_port')
    full_arasturl = utils.verify_url(arasturl, arastport)
    if not num_threads:
        num_threads =  cparser.get('compute','threads')

    #### Retrieve system configuration from AssemblyRAST server
    logger.info("[.] AssemblyRAST host: {}".format(arasturl))
    try:
        ctrl_conf = json.loads(requests.get('{}/admin/system/config'.format(full_arasturl)).content)
        logger.info("[.] Retrieved system config from host")
    except:
        raise Exception('Could not communicate with server for system config')

    shockurl = ctrl_conf['shock']['host']
    mongo_port = int(ctrl_conf['assembly']['mongo_port'])
    mongo_host = ctrl_conf['assembly']['mongo_host']
    rmq_port = int(ctrl_conf['assembly']['rabbitmq_port'])
    rmq_host = ctrl_conf['assembly']['rabbitmq_host']
    if not queue:
        queue = [ctrl_conf['rabbitmq']['default_routing_key']]
    if mongo_host == 'localhost':
        mongo_host = arasturl
    if rmq_host == 'localhost':
        rmq_host = arasturl

    logger.info('[.] Shock URL: {}'.format(shockurl))
    logger.info("[.] MongoDB host: {}".format(mongo_host))
    logger.info("[.] MongoDB port: {}".format(mongo_port))
    logger.info("[.] RabbitMQ host: {}".format(rmq_host))
    logger.info("[.] RabbitMQ port: {}".format(rmq_port))

    # Check shock status
    logger.info("[.] Connecting to Shock server...")
    shockurl = utils.verify_url(shockurl, 7445)
    try:
        res = requests.get(shockurl)
    except Exception as e:
        logger.error("Shock connection error: {}".format(e))
        sys.exit(1)
    logger.info("[.] Shock connection successful")

    # Check MongoDB status
    logger.info("[.] Connecting to MongoDB server...")
    try:
        connection = pymongo.mongo_client.MongoClient(mongo_host, mongo_port)
        connection.close()
        logger.debug("MongoDB Info: %s" % connection.server_info())
    except pymongo.errors.PyMongoError as e:
        logger.error("MongoDB connection error: {}".format(e))
        sys.exit(1)
    logger.info("[.] MongoDB connection successful.")

    # Check RabbitMQ status
    logger.info("[.] Connecting to RabbitMQ server...")
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=rmq_host, port=rmq_port))
        connection.close()
    except Exception as e:
        logger.error("RabbitMQ connection error: {}".format(e))
        sys.exit(1)
    logger.info("[.] RabbitMQ connection successful")


    #### Check data write permissions
    rootpath = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', '..'))
    datapath = datapath or cparser.get('compute', 'datapath')
    binpath = binpath or cparser.get('compute', 'binpath')
    modulebin = modulebin or cparser.get('compute', 'modulebin')
    if not os.path.isabs(datapath): datapath = os.path.join(rootpath, datapath)
    if not os.path.isabs(binpath): binpath = os.path.join(rootpath, binpath)
    if not os.path.isabs(modulebin): modulebin = os.path.join(rootpath, modulebin)

    if os.path.isdir(datapath) and os.access(datapath, os.W_OK):
        logger.info('[.] Storage path writeable: {}'.format(datapath))
    else:
        raise Exception('ERROR: Storage path not writeable: {}'.format(datapath))

    if os.path.isdir(binpath) and os.access(binpath, os.R_OK):
        logger.info("[.] Third-party binary path readable: {}".format(binpath))
    else:
        raise Exception('ERROR: Third-party binary path not readable: {}'.format(binpath))

    if os.path.isdir(modulebin) and os.access(modulebin, os.R_OK):
        logger.info("[.] Module binary path readable: {}".format(modulebin))
    else:
        raise Exception('ERROR: Module binary path not readable: {}'.format(modulebin))

    ## Start Monitor Thread
    kill_process = multiprocessing.Process(name='killd', target=start_kill_monitor,
                                           args=(rmq_host, rmq_port))
    kill_process.start()

    workers = []
    for i in range(int(num_threads)):
        worker_name = "worker #%s" % i
        compute = consume.ArastConsumer(shockurl, rmq_host, rmq_port, mongo_host, mongo_port, config, num_threads,
                                        queue, kill_list, kill_list_lock, job_list, job_list_lock, ctrl_conf,
                                        datapath, binpath, modulebin)
        logger.info("Master: starting %s" % worker_name)
        p = multiprocessing.Process(name=worker_name, target=compute.start)
        workers.append(p)
        p.start()
    workers[0].join()

def start_kill_monitor(rmq_host, rmq_port):
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=rmq_host, port=rmq_port))
    channel = connection.channel()
    channel.exchange_declare(exchange='kill',
                             type='fanout')
    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange='kill',
                       queue=queue_name)
    channel.basic_consume(kill_callback,
                          queue=queue_name,
                          no_ack=True)
    logger.info('Waiting for kill commands')
    channel.start_consuming()

def kill_callback(ch, method, properties, body):
    kill_request = json.loads(body)
    job_list_lock.acquire()
    logger.info('Job list (len={}): '.format(len(job_list),
                                             [(j.get('job_id'), j.get('user')) for j in job_list]))
    kill_list_lock.acquire()
    for job_data in job_list:
        if kill_request['user'] == job_data['user'] and kill_request['job_id'] == str(job_data['job_id']):
            logger.warning('Job to be deleted is on this node: {}'.format(body))
            kill_list.append(kill_request)
    kill_list_lock.release()
    job_list_lock.release()


parser = argparse.ArgumentParser(prog='ar_computed', epilog='Use "arast command -h" for more information about a command.')

parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")
parser.add_argument("-s", "--server", help="specify AssemblyRAST server",
                    action="store", required=True)
parser.add_argument("-c", "--config", help="specify configuration file",
                    action="store", required=True)
parser.add_argument("-t", "--threads", help="specify number of worker threads",
                    action="store", required=False)
parser.add_argument("-q", "--queue", help="specify a queue to pull from",
                    action="store", required=False)
parser.add_argument("-l", "--logfile", help="specify the logfile",
                    action="store", required=False)
parser.add_argument("-d", "--compute-data", dest='datapath', help="specify a directory for computation data",
                    action="store", required=False)
parser.add_argument("-b", "--compute-bin", dest='binpath', help="specify a directory for third-party computation binaries",
                    action="store", required=False)
parser.add_argument("-m", "--module-bin", dest='modulebin', help="specify a directory for module computation binaries",
                    action="store", required=False)

args = parser.parse_args()

arasturl = args.server or None
queues = []
if args.queue:
    queues = args.queue.split(',')
num_threads = args.threads or None
datapath = args.datapath or None
binpath = args.binpath or None
modulebin = args.modulebin or None
logfile = args.logfile or 'ar_compute.log'

if os.path.dirname(logfile):
    utils.verify_dir(os.path.dirname(logfile))

logging.basicConfig(format="[%(asctime)s %(levelname)s %(process)d %(name)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO, filename=logfile)

if args.verbose:
    logging.root.setLevel(logging.DEBUG)

start(arasturl, args.config, num_threads, queues, datapath, binpath, modulebin)
