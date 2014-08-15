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
import requests

from ConfigParser import SafeConfigParser
import consume
import shock
import client

#context = daemon.DaemonContext(stdout=sys.stdout) #temp print to stdout
#TODO change to log file

#with context:
mgr = multiprocessing.Manager()
job_list = mgr.list()
job_list_lock = multiprocessing.Lock()
kill_list = mgr.list()

def start(arast_server, config, num_threads, queue, datapath, binpath):

    #### Get default configuration from ar_compute.conf
    print " [.] Starting Assembly Service Compute Node"    
    cparser = SafeConfigParser()
    cparser.read(config)
    logging.getLogger('yapsy').setLevel(logging.WARNING)
    logging.getLogger('yapsy').propagate = True
    logging.getLogger('pika').propagate = True
    logging.getLogger('pika').setLevel(logging.WARNING)

    arasturl =  cparser.get('assembly','arast_url')
    arastport = cparser.get('assembly','arast_port')
    if arast_server and arast_server != '':
        arasturl = arast_server
    if not num_threads:
        num_threads =  cparser.get('compute','threads')


    #### Retrieve system configuration from AssemblyRAST server
    ctrl_conf = json.loads(requests.get('http://{}:{}/admin/system/config'.format(arasturl, arastport)).content)
    mongo_port = int(ctrl_conf['assembly']['mongo_port'])
    mongo_host = ctrl_conf['assembly']['mongo_host']
    rmq_port = int(ctrl_conf['assembly']['rabbitmq_port'])
    rmq_host = ctrl_conf['assembly']['rabbitmq_host']
    if mongo_host == 'localhost':
        mongo_host = arasturl
    if rmq_host == 'localhost':
        rmq_host = arasturl
    try:
        shockurl = ctrl_conf['shock']['host']
        print ' [.] Retrieved Shock URL: {}'.format(shockurl)
    except:
        raise Exception('Could not communicate with server')


    print " [.] AssemblyRAST host: %s" % arasturl
    print " [.] MongoDB port: %s" % mongo_port
    print " [.] RabbitMQ port: %s" % rmq_port
    # Check MongoDB status
    try:
        connection = pymongo.Connection(mongo_host, mongo_port)
        logging.info("MongoDB Info: %s" % connection.server_info())
    except pymongo.errors.PyMongoError as e:
        logging.error("MongoDB connection error: {}".format(e))
        sys.exit(1)
    print " [.] MongoDB connection successful."

    # Check RabbitMQ status
        #TODO
        
    print " [.] Connecting to Shock server..."
    url = "http://{}".format(shockurl)
    res = shock.get(url)
    
    if res is not None:
        print " [.] Shock connection successful"
    else:
        raise Exception("Shock connection error: {}".format(shockurl))

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
        worker_name = "[Worker %s]:" % i
        compute = consume.ArastConsumer(shockurl, rmq_host, rmq_port, arasturl, config, num_threads, 
                                        queue, kill_list, job_list, job_list_lock, ctrl_conf, datapath, binpath)
        logging.info("[Master]: Starting %s" % worker_name)
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
        print " [x] %r" % (body,)
        kill_request = json.loads(body)
        print 'job_list:', job_list
        job_list_lock.acquire()
        for job_data in job_list:
            if kill_request['user'] == job_data['user'] and kill_request['job_id'] == str(job_data['job_id']):
                print 'on this node'
                kill_list.append(kill_request)
        job_list_lock.release()




parser = argparse.ArgumentParser(prog='ar_computed', epilog='Use "arast command -h" for more information about a command.')

parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")
parser.add_argument("-s", "--server", help="specify AssemblyRAST server",
                    action="store")
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
    logging.basicConfig(level=logging.DEBUG)

arasturl = args.server or None
queue = args.queue or None
num_threads = args.threads or None
datapath = args.datapath or None
binpath = args.binpath or None

start(arasturl, args.config, num_threads, queue, datapath, binpath)
