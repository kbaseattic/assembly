#! /usr/bin/env python
"""
Arast Daemon

The Arast daemon runs on the control node.

"""
import argparse
import sys
import signal
import daemon
import logging
import lockfile
import pymongo
import pika
import router
from ConfigParser import SafeConfigParser

import shock

def start():
    # Read config file
    cparser = SafeConfigParser()
    cparser.read('arast.conf')
    print " [.] Starting Assembly Service Control Server"
    print " [.] Starting Assembly Service Control Server"
    print " [.] Starting Assembly Service Control Server"
    print " [.] MongoDB port: %s" % cparser.get('meta','mongo.port')
    print " [.] RabbitMQ port: %s" % cparser.get('rabbitmq','port')
    
    # Check MongoDB status
    try:
        connection = pymongo.Connection(cparser.get('meta','mongo.control.host'))
                      
        logging.info("MongoDB Info: %s" % connection.server_info())
    except:
        logging.error("MongoDB connection error!")
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
    router.start()

def tear_down():
    print "Tear down"
    sys.exit()

parser = argparse.ArgumentParser(prog='arast', epilog='Use "arast command -h" for more information about a command.')

parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")
parser.add_argument("-p", "--pidfile", help="Process ID file",
                    action="store")
parser.add_argument("-s", "--shock", help="specify the shock server url",
                    action="store_true")

args = parser.parse_args()
if args.verbose:
    logging.basicConfig(level=logging.DEBUG)

########### DAEMON STUFF
#if args.shock:
#    shockurl = args.shock
#if args.pidfile:
#    print args.pidfile
#    context = daemon.DaemonContext(stdout=sys.stdout, 
#                                   pidfile=lockfile.FileLock(args.pidfile))
#else:
#    context = daemon.DaemonContext(stdout=sys.stdout)
#context.signal_map = {
#    signal.SIGTERM: tear_down,
#    signal.SIGHUP: 'terminate'}
#with context:
#    start()
##############


start()
