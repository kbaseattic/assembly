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
import router
from ConfigParser import SafeConfigParser

import shock

#context = daemon.DaemonContext(stdout=sys.stdout) #temp print to stdout
#TODO change to log file

#with context:

def start():
    # Read config file
    cparser = SafeConfigParser()
    cparser.read('arast.conf')
    print " [.] Starting Assembly Service Control Server"
    print " [.] MongoDB port: %s" % cparser.get('meta','mongo.port')
    print " [.] RabbitMQ port: %s" % cparser.get('rabbitmq','port')
    
    # Check MongoDB status
    try:
        connection = pymongo.Connection('localhost')
                      
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

start()
