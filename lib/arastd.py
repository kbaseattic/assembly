#! /usr/bin/env python
"""
Arast Daemon

The Arast daemon runs on the control node.

"""

#! /usr/bin/python
import sys
import daemon
import pymongo
import pika
import router
from ConfigParser import SafeConfigParser

context = daemon.DaemonContext(stdout=sys.stdout) #temp print to stdout
#TODO change to log file

with context:
    # Read config file
    cparser = SafeConfigParser()
    cparser.read('arast.conf')
    print "Starting arastd"
    

    # Check MongoDB status
    try:
        connection = pymongo.Connection(cparser.get('meta','mongodb.host'),
                                    cparser.get('meta','mongodb.port'))
        logging.info("MongoDB Info: %s" % connection.serverinfo())
    except:
        logging.error("MongoDB connection error!")
    
    # Check RabbitMQ status
        #TODO
        
    # Start RPC server
    router.start()
