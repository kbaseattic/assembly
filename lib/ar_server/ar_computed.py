#! /usr/bin/env python
"""
Arast Daemon

The Arast daemon runs on the control node.

"""
import argparse
import sys
import daemon
import logging
import pymongo
import multiprocessing
import pika
from ConfigParser import SafeConfigParser

import consume
import shock

#context = daemon.DaemonContext(stdout=sys.stdout) #temp print to stdout
#TODO change to log file

#with context:

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

    workers = []
    for i in range(int(num_threads)):
        worker_name = "[Worker %s]:" % i
        compute = consume.ArastConsumer(shockurl, arasturl, config, num_threads, queue)
        logging.info("[Master]: Starting %s" % worker_name)
        p = multiprocessing.Process(name=worker_name, target=compute.start)
        workers.append(p)
        p.start()
        #self.fetch_job(self.parser.get('rabbitmq','job.medium'))
    workers[0].join()


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
