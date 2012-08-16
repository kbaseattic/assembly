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
import pika
from ConfigParser import SafeConfigParser

import consume
import shock

#context = daemon.DaemonContext(stdout=sys.stdout) #temp print to stdout
#TODO change to log file

#with context:

def start(arast_server):
    # Read config file
    
    print "Reading from config file"
    cparser = SafeConfigParser()
    cparser.read('arast.conf')
    shockurl = cparser.get('shock', 'host')
    shockuser = cparser.get('shock','admin_user')
    shockpass = cparser.get('shock','admin_pass')
    arasturl =  cparser.get('meta','mongo.remote.host')
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
    # Start RPC server
    compute = consume.ArastConsumer(shockurl, arasturl)
    compute.start()


parser = argparse.ArgumentParser(prog='ar_computed', epilog='Use "arast command -h" for more information about a command.')

parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")

parser.add_argument("-s", "--server", help="specify AssemblyRAST server",
                    action="store")

args = parser.parse_args()
if args.verbose:
    logging.basicConfig(level=logging.DEBUG)
arasturl = ''
if args.server:
    arasturl = args.server
start(arasturl)
