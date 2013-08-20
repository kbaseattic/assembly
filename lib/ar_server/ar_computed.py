#! /usr/bin/env python
"""
Arast Daemon

The Arast daemon runs on the control node.

"""
import argparse
import sys
import daemon
import logging
import json
import pymongo
import multiprocessing
import pika
from ConfigParser import SafeConfigParser

import consume
import shock

#context = daemon.DaemonContext(stdout=sys.stdout) #temp print to stdout
#TODO change to log file

#with context:
mgr = multiprocessing.Manager()
job_list = mgr.list()
kill_list = mgr.list()

def start(arast_server, config, num_threads, queue):
    # Read config file
    print config
    print "Reading from config file"
    cparser = SafeConfigParser()
    cparser.read(config)
    shockurl = cparser.get('shock', 'host')
    shockuser = cparser.get('shock','admin_user')
    shockpass = cparser.get('shock','admin_pass')
    arasturl =  cparser.get('meta','mongo.host')
    if not num_threads:
        num_threads =  cparser.get('compute','threads')

    mongo_port = int(cparser.get('meta','mongo.port'))
    if arast_server != '':
        arasturl = arast_server
    print " [.] Starting Assembly Service Compute Node"
    print " [.] AssemblyRAST host: %s" % arasturl
    print " [.] MongoDB port: %s" % cparser.get('meta','mongo.port')
    print " [.] RabbitMQ port: %s" % cparser.get('rabbitmq','port')
    
    # Check MongoDB status
    try:
        connection = pymongo.Connection(arasturl, mongo_port)
                      
        logging.info("MongoDB Info: %s" % connection.server_info())
    except:
        logging.error("MongoDB connection error: %s" % sys.exc_info()[0])
        sys.exit()
    print " [x] MongoDB connection successful."
    # Check RabbitMQ status
        #TODO
        
    print " [.] Connecting to Shock server..."
    url = "http://%s" % cparser.get('shock', 'host')
    res = shock.get(url, cparser.get('shock','admin_user'),
              cparser.get('shock','admin_pass'))
    
    if res is not None:
        print " [x] Shock connection successful"


    ## Start Monitor Thread
    kill_process = multiprocessing.Process(name='killd', target=start_kill_monitor,
                                           args=(arasturl,))
    kill_process.start()

    workers = []
    for i in range(int(num_threads)):
        worker_name = "[Worker %s]:" % i
        compute = consume.ArastConsumer(shockurl, arasturl, config, num_threads, 
                                        queue, kill_list, job_list)
        logging.info("[Master]: Starting %s" % worker_name)
        p = multiprocessing.Process(name=worker_name, target=compute.start)
        workers.append(p)
        p.start()
    workers[0].join()

def start_kill_monitor(arasturl):
    connection = pika.BlockingConnection(pika.ConnectionParameters(
            host = arasturl))
    channel = connection.channel()
    channel.exchange_declare(exchange='kill',
                             type='fanout')
    result = channel.queue_declare(exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange='kill',
                       queue=queue_name)
    print ' [*] Waiting for kill commands'
    channel.basic_consume(kill_callback,
                          queue=queue_name,
                          no_ack=True)

    channel.start_consuming()

def kill_callback(ch, method, properties, body):
        print " [x] %r" % (body,)
        kill_request = json.loads(body)
        print 'job_list:', job_list
        for job_data in job_list:
            if kill_request['user'] == job_data['user'] and kill_request['job_id'] == str(job_data['job_id']):
                print 'on this node'
                kill_list.append(kill_request)




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

args = parser.parse_args()
if args.verbose:
    logging.basicConfig(level=logging.DEBUG)
arasturl = ''
if args.server:
    arasturl = args.server
if args.queue:
    queue = args.queue
else:
    queue = None
if args.threads:
    num_threads = args.threads
else:
    num_threads = None
start(arasturl, args.config, num_threads, queue)
