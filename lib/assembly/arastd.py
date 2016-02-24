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
import multiprocessing
import os
import pymongo
import pika
import router
from ConfigParser import SafeConfigParser

import shock
import utils


logger = logging.getLogger(__name__)

# Config precedence: command-line args > config file

def start(config_file, shock_url=None, mongo_host=None, mongo_port=None,
          rabbit_host=None, rabbit_port=None, deploy_config=None):

    logger.info("============================================")
    logger.info("  Starting Assembly Service Control Server")
    logger.info("============================================")

    # Read config file
    cparser = SafeConfigParser()
    if deploy_config:
        cparser.read(deploy_config)
        logger.info("[.] Found Deployment Config: {}".format(deploy_config))
    else:
        cparser.read(config_file)

    if not shock_url:
        shock_host = cparser.get('shock', 'host')
        shock_url = shock.verify_shock_url(shock_host)
    if not mongo_host:
        mongo_host = cparser.get('assembly', 'mongo_host')
    if not mongo_port:
        mongo_port = int(cparser.get('assembly', 'mongo_port'))
    if not rabbit_host:
        rabbit_host = cparser.get('assembly', 'rabbitmq_host')
    if not rabbit_port:
        rabbit_port = int(cparser.get('assembly', 'rabbitmq_port'))

    logger.info("[.] Shock URL: {}".format(shock_url))
    logger.info("[.] MongoDB host: {}".format(mongo_host))
    logger.info("[.] MongoDB port: {}".format(mongo_port))
    logger.info("[.] RabbitMQ host: {}".format(rabbit_host))
    logger.info("[.] RabbitMQ port: {}".format(rabbit_port))

    # Check MongoDB status
    try:
        connection = pymongo.mongo_client.MongoClient(mongo_host, mongo_port)
        logging.debug("MongoDB Info: %s" % connection.server_info())
    except pymongo.errors.PyMongoError as e:
        logger.error("MongoDB connection error: {}".format(e))
        sys.exit('MongoDB error: {}'.format(e))
    logger.info("[.] MongoDB connection successful.")

    router_kwargs = {'shock_url': shock_url,
                     'mongo_host': mongo_host, 'mongo_port': mongo_port,
                     'rabbit_host' :rabbit_host, 'rabbit_port' : rabbit_port}

    router_process = multiprocessing.Process(name='router', target=start_router,
                                             args=(config_file,), kwargs=router_kwargs)
    router_process.start()

    # qc_process = multiprocessing.Process(name='qcmon', target=start_qc_monitor,
    #                                          args=(rabbit_host,))
    # qc_process.start()

    # router.start(config_file, mongo_host=mongo_host, mongo_port=mongo_port,
    #              rabbit_host=rabbit_host, rabbit_port=rabbit_port)

def start_router(config_file, **kwargs):
    router.start(config_file, **kwargs)

def start_qc_monitor(rabbit_host, rabbit_port):
    router.start_qc_monitor(rabbit_host, rabbit_port)

def tear_down():
    logger.warning("Tearing down...")
    sys.exit()

parser = argparse.ArgumentParser(prog='arastd')

parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")
parser.add_argument("-p", "--pidfile", help="Process ID file",
                    action="store")
parser.add_argument("--shock-url", help="specify the shock server url",
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

logfile = args.logfile or 'ar_server.log'
utils.verify_dir(os.path.dirname(logfile))

logging.basicConfig(format="[%(asctime)s %(levelname)s %(name)s] %(message)s",
                    level=logging.INFO, filename=logfile)

if args.verbose:
    logging.root.setLevel(logging.DEBUG)

start(args.config, shock_url=args.shock_url, mongo_host=args.mongo_host, mongo_port=args.mongo_port,
      rabbit_host=args.rabbit_host, rabbit_port=args.rabbit_port,
      deploy_config=args.deploy_config)
