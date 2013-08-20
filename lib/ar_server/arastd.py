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
from ConfigParser import SafeConfigParser

import shock 
import cloud 

def start(config_file, mongo_host=None, mongo_port=None,
          rabbit_host=None, rabbit_port=None, deploy_config=None):
    # Read config file
    cparser = SafeConfigParser()
    if deploy_config:
        cparser.read(deploy_config)
        print " [.] Found Deployment Config: {}".format(deploy_config)
    else:
        cparser.read(config_file)

    if not mongo_host:
        mongo_host = cparser.get('assembly', 'mongo_host')
    if not mongo_port:
        mongo_port = cparser.get('assembly', 'mongo_port')
    if not rabbit_host:
        rabbit_host = cparser.get('assembly', 'rabbitmq_host')
    if not rabbit_port:
        rabbit_port = cparser.get('assembly', 'rabbitmq_port')

    print " [.] Starting Assembly Service Control Server"
    print " [.] MongoDB port: " + mongo_port
    print " [.] RabbitMQ port: " + rabbit_port
    
    # Check MongoDB status
    try:
        connection = pymongo.Connection(mongo_host)
        logging.info("MongoDB Info: %s" % connection.server_info())
    except:
        logging.error("MongoDB connection error!")
        sys.exit()
    print " [x] MongoDB connection successful."

    router.start(config_file, mongo_host=mongo_host, mongo_port=mongo_port,
                 rabbit_host=rabbit_host, rabbit_port=rabbit_port)

def tear_down():
    print "Tear down"
    sys.exit()

parser = argparse.ArgumentParser(prog='arastd')

parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")
parser.add_argument("-p", "--pidfile", help="Process ID file",
                    action="store")
parser.add_argument("--shock-host", help="specify the shock server url",
                    action="store")
parser.add_argument("--mongo-host", help="specify the mongodb url",
                    action="store")
parser.add_argument("--mongo-port", help="specify the mongodb port",
                    action="store")
parser.add_argument("--rabbit-host", help="specify the rabbitmq url",
                    action="store")
parser.add_argument("--rabbit-port", help="specify the rabbitmq port",
                    action="store")
parser.add_argument("--logfile", help="specify the logfile",
                    action="store")
parser.add_argument("--deploy-config", help="specify the deployment-specific config",
                    action="store")
parser.add_argument("-c", "--config", help="specify the config file",
                    action="store", required=True)

args = parser.parse_args()
if args.logfile:
    logfile = args.logfile
    try:
        os.makedirs(os.path.dirname(logfile))
    except:
        pass

else:
    logfile = 'ar_server.log'

if args.verbose:
    logging.basicConfig(level=logging.DEBUG, filename=logfile, stream=sys.stdout)
else:
    logging.basicConfig(level=logging.DEBUG, filename=logfile)

# try:
#     os_user = os.environ.get('OS_AUTH_USER')
#     os_password = os.environ.get('OS_AUTH_KEY')
#     os_tenant = os.environ.get('OS_AUTH_TENANT')
#     os_auth_url = os.environ.get('OS_AUTH_URL')
#     cloud_control = True
# except:
#     print " [!] WARNING: Openstack environmental variables not set!  Disabling cloud monitor."
#     cloud_control = False

# if not os_user:
#     print " [!] WARNING: Openstack environmental variables not set!  Disabling cloud monitor."
#     cloud_control = False

# logging.info("OS_USER: %s" % os_user)
# logging.info("OS_TENANT: %s" % os_tenant)

########### DAEMON STUFF
# if args.pidfile:
#     print args.pidfile
#     context = daemon.DaemonContext(working_directory=os.getcwd(),
#                                    stdout=sys.stdout, 
#                                    pidfile=lockfile.FileLock(args.pidfile))
# else:
#     context = daemon.DaemonContext(stdout=sys.stdout)
#     context.signal_map = {
#     signal.SIGTERM: tear_down,
#     signal.SIGHUP: 'terminate'}
# with context:
#     start(args.config, mongo_host=args.mongo_host, mongo_port=args.mongo_port,
#           rabbit_host=args.rabbit_host, rabbit_port=args.rabbit_port, 
#           deploy_config=args.deploy_config)

# if cloud_control:    
#     monitor = cloud.CloudMonitor(os_user, os_password, os_tenant, 
#                                  os_auth_url, args.config)
#     #monitor.list_ids()
#     #monitor.terminate_all_nodes()
#     #monitor.launch_node()
#     if monitor.list_nodes() is None:
#         #print ("No compute instances running. Launching...")
#         #monitor.launch_node()
#         pass

start(args.config, mongo_host=args.mongo_host, mongo_port=args.mongo_port,
      rabbit_host=args.rabbit_host, rabbit_port=args.rabbit_port, 
      deploy_config=args.deploy_config)
