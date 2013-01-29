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
import os
import pymongo
import pika
import router
#import router2 as router
from ConfigParser import SafeConfigParser

import shock
import cloud 

def start(config_file):
    # Read config file
    cparser = SafeConfigParser()
    cparser.read(config_file)
    print " [.] Starting Assembly Service Control Server"
    print " [.] MongoDB port: %s" % cparser.get('meta','mongo.port')
    print " [.] RabbitMQ port: %s" % cparser.get('rabbitmq','port')
    
    # Check MongoDB status
    try:
        connection = pymongo.Connection(cparser.get('meta','mongo.host'))
                      
        logging.info("MongoDB Info: %s" % connection.server_info())
    except:
        logging.error("MongoDB connection error!")
        sys.exit()
    print " [x] MongoDB connection successful."
    # Check RabbitMQ status
        #TODO
        
    # print " [.] Connecting to Shock server..."
    # url = "http://%s" % cparser.get('shock', 'host')
    # res = shock.get(url, cparser.get('shock','admin_user'),
    #           cparser.get('shock','admin_pass'))
    
    # if res is not None:
    #     print " [x] Shock connection successful"
    # Start RPC server

    router.start(config_file)

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
parser.add_argument("-c", "--config", help="specify the config file",
                    action="store", required=True)

args = parser.parse_args()
if args.verbose:
    logging.basicConfig(level=logging.DEBUG)

try:
    os_user = os.environ.get('OS_AUTH_USER')
    os_password = os.environ.get('OS_AUTH_KEY')
    os_tenant = os.environ.get('OS_AUTH_TENANT')
    os_auth_url = os.environ.get('OS_AUTH_URL')
    cloud_control = True
except:
    print " [!] WARNING: Openstack environmental variables not set!  Disabling cloud monitor."
    cloud_control = False

if not os_user:
    print " [!] WARNING: Openstack environmental variables not set!  Disabling cloud monitor."
    cloud_control = False

logging.info("OS_USER: %s" % os_user)
logging.info("OS_TENANT: %s" % os_tenant)

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

if cloud_control:    
    monitor = cloud.CloudMonitor(os_user, os_password, os_tenant, 
                                 os_auth_url, args.config)
    #monitor.list_ids()
    #monitor.terminate_all_nodes()
    #monitor.launch_node()
    if monitor.list_nodes() is None:
        #print ("No compute instances running. Launching...")
        #monitor.launch_node()
        pass

start(args.config)
