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


logging.basicConfig(format="[%(asctime)s %(levelname)s %(process)d %(name)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO)
logger = logging.getLogger(__name__)

#context = daemon.DaemonContext(stdout=sys.stdout) #temp print to stdout
#TODO change to log file

#with context:
mgr = multiprocessing.Manager()
job_list = mgr.list()
job_list_lock = multiprocessing.Lock()
kill_list = mgr.list()
kill_list_lock = multiprocessing.Lock()

def start(arasturl, config, num_threads, queue, datapath, binpath):

    #### Get default configuration from ar_compute.conf
    print " [.] Starting Assembly Service Compute Node"
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
    print " [.] AssemblyRAST host: %s" % arasturl
    try:
        ctrl_conf = json.loads(requests.get('{}/admin/system/config'.format(full_arasturl)).content)
        print " [.] Retrieved system config from host"
    except:
        raise Exception('Could not communicate with server for system config')

    shockurl = ctrl_conf['shock']['host']
    mongo_port = int(ctrl_conf['assembly']['mongo_port'])
    mongo_host = ctrl_conf['assembly']['mongo_host']
    rmq_port = int(ctrl_conf['assembly']['rabbitmq_port'])
    rmq_host = ctrl_conf['assembly']['rabbitmq_host']
    if not queue:
        queue = ctrl_conf['rabbitmq']['default_routing_key']
    if mongo_host == 'localhost':
        mongo_host = arasturl
    if rmq_host == 'localhost':
        rmq_host = arasturl

    print ' [.] Shock URL: %s' % shockurl
    print " [.] MongoDB host: %s" % mongo_host
    print " [.] MongoDB port: %s" % mongo_port
    print " [.] RabbitMQ host: %s" % rmq_host
    print " [.] RabbitMQ port: %s" % rmq_port

    # Check shock status
    print " [.] Connecting to Shock server..."
    shockurl = utils.verify_url(shockurl, 7445)
    try:
        res = requests.get(shockurl)
    except Exception as e:
        logger.error("Shock connection error: {}".format(e))
        sys.exit(1)
    print " [.] Shock connection successful"

    # Check MongoDB status
    print " [.] Connecting to MongoDB server..."
    try:
        connection = pymongo.Connection(mongo_host, mongo_port)
        connection.close()
        logger.info("MongoDB Info: %s" % connection.server_info())
    except pymongo.errors.PyMongoError as e:
        logger.error("MongoDB connection error: {}".format(e))
        sys.exit(1)
    print " [.] MongoDB connection successful."

    # Check RabbitMQ status
    print " [.] Connecting to RabbitMQ server..."
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=rmq_host, port=rmq_port))
        connection.close()
    except Exception as e:
        logger.error("RabbitMQ connection error: {}".format(e))
        sys.exit(1)
    print " [.] RabbitMQ connection successful"


    #### Check data write permissions
    rootpath = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', '..'))
    datapath = datapath or cparser.get('compute', 'datapath')
    binpath = binpath or cparser.get('compute','binpath')
    if not os.path.isabs(datapath): datapath = os.path.join(rootpath, datapath)
    if not os.path.isabs(binpath): binpath = os.path.join(rootpath, binpath)

    if os.path.isdir(datapath) and os.access(datapath, os.W_OK):
        print ' [.] Storage path -- {} : OKAY'.format(datapath)
    else:
        raise Exception(' [.] Storage path -- {} : ERROR'.format(datapath))

    if os.path.isdir(binpath) and os.access(datapath, os.R_OK):
        print " [.] Binary path -- {} : OKAY".format(binpath)
    else:
        raise Exception(' [.] Binary directory does not exist -- {} : ERROR'.format(binpath))

    ## Start Monitor Thread
    kill_process = multiprocessing.Process(name='killd', target=start_kill_monitor,
                                           args=(rmq_host, rmq_port))
    kill_process.start()

    workers = []
    for i in range(int(num_threads)):
        worker_name = "worker #%s" % i
        compute = consume.ArastConsumer(shockurl, rmq_host, rmq_port, mongo_host, mongo_port, config, num_threads,
                                        queue, kill_list, kill_list_lock, job_list, job_list_lock, ctrl_conf, datapath, binpath)
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
    print ' [*] Waiting for kill commands'
    channel.start_consuming()

def kill_callback(ch, method, properties, body):
    kill_request = json.loads(body)
    job_list_lock.acquire()
    print >> sys.stderr, 'job_list (len={}): '.format(len(job_list)),
    print >> sys.stderr, [(j.get('job_id'), j.get('user')) for j in job_list]
    kill_list_lock.acquire()
    for job_data in job_list:
        if kill_request['user'] == job_data['user'] and kill_request['job_id'] == str(job_data['job_id']):
            print >> sys.stderr, 'Job to be deleted is on this node: {}'.format(body)
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
parser.add_argument("-d", "--compute-data", dest='datapath', help="specify a directory for computation data",
                    action="store", required=False)
parser.add_argument("-b", "--compute-bin", dest='binpath', help="specify a directory for computation binaries",
                    action="store", required=False)

args = parser.parse_args()

if args.verbose:
    logging.root.setLevel(logging.DEBUG)

arasturl = args.server or None
queue = args.queue or None
num_threads = args.threads or None
datapath = args.datapath or None
binpath = args.binpath or None

start(arasturl, args.config, num_threads, queue, datapath, binpath)
