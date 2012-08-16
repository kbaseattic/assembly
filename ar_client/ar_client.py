#! /usr/bin/env python
"""
arast-client -- commandline client for Assembly RAST

A lot of code taken from Jared Wilkening / ShockClient

"""


import os, sys, json, shutil
import pika
import argparse
import logging
import requests
import prettytable as pt
import uuid
import time
from ConfigParser import SafeConfigParser

import shock


# arg type checking
def file_type(f):
	if not os.path.isfile(f):
		msg = "%s is not a file" % f
		raise argparse.ArgumentTypeError(msg)
	else:
		return f

def dir_type(d):
	if not os.path.isdir(d):
		msg = "%s is not a directory" % d
		raise argparse.ArgumentTypeError(msg)
	else:
		return d


# setup option/arg parser
parser = argparse.ArgumentParser(prog='arast', epilog='Use "arast command -h" for more information about a command.')
parser.add_argument('--ARASTURL', help='Overrules env ARASTURL')
parser.add_argument('--ARASTUSER', help='Overrules env ARASTUSER')
parser.add_argument('--ARASTPASSWORD', help='Overrules env ARASTPASSWORD')
subparsers = parser.add_subparsers(dest='command', title='The commands are')

# run -h
p_run = subparsers.add_parser('run', description='Run an Assembly RAST job', help='run job')
p_run.add_argument("-f", "--file", action="store", dest="filename",
                   nargs='*', help="specify sequence file(s)")
p_run.add_argument("-a", "--assemblers", action="store",
                  dest="assemblers", nargs='*')
p_run.add_argument("-s", "--size", action="store", dest="size",
                  help="size of data in GB")
p_run.add_argument("-d", "--directory", action="store",
                  dest="directory",
                  help="specify input directory")
p_run.add_argument("-c", "--config", action="store",
                  dest="config",
                  help="specify parameter configuration file")
p_run.add_argument("-p", "--params", action="store",
                  dest="params", nargs='*',
                  help="specify global assembly parameters")
p_run.add_argument("-m", "--message", action="store",
                  dest="message",
                  help="Attach a description to job")


# filetype, special flags, config file
# global, -k=31, -cov
# velvet

# stat -h
p_stat = subparsers.add_parser('stat', description='Query status of running jobs', help='list jobs status')

# get
p_get = subparsers.add_parser('get', description='Download result data', help='download data')
p_get.add_argument("-a", "--assemblers", action="store",
                  dest="assemblers", nargs='*',
                  help="specify which assembly data to get")


def post(url, files):
	global ARASTUSER, ARASTPASSWORD
	r = None
	if ARASTUSER and ARASTPASSWORD:
            r = requests.post(url, auth=(ARASTUSER, ARASTPASSWORD), files=files)
	else:
            r = requests.post(url, files=files)

        res = json.loads(r.text)
	return res


# upload all files in list, return list of ids
def upload(url, files):
    ids = []
    for f in files:
        files = {}
        print "Uploading: %s" % os.path.basename(f)
        files["file"] = (os.path.basename(f), open(f, 'rb'))
        res = post(url, files)
        ids.append(res['D']['id'])
        
        #Error check
        if res["E"] is None:
        # Prettytable 0.6 breaks this
                    #printNodeTable(res["D"])
		pass
        else:
            print "shock: err from server: %s" % res["E"][0]
    return ids


def main():
	global ARASTURL, ARASTUSER, ARASTPASSWORD
	
	args = parser.parse_args()
	opt = parser.parse_args()
        options = vars(args)

	

	# overwrite env vars in args
	if args.ARASTUSER:
		ARASTUSER = args.ARASTUSER				
	if args.ARASTPASSWORD:
		ARASTPASSWORD = args.ARASTPASSWORD				
	if not ARASTURL:
		print parser.print_usage()
		print "arast: err: ARASTURL not set"
		sys.exit()

        # Request Shock URL
        url_req = {}
        url_req['command'] = 'get_url'
        url_rpc = RpcClient()
	url = "http://%s" % url_rpc.call(json.dumps(url_req))

        # Upload file(s) to Shock
        res_ids = []
	if args.command == "run":
            if args.directory or args.filename:
                url += "/node"
		files = args.filename
            if args.filename:
		    if args.config:
			    files.append(args.config)
		    res_ids = upload(url, files)
		    base_files = [os.path.basename(f) for f in files]
		    del options['filename']
		    options['filename'] = base_files
            elif args.directory:
		    ls_files = os.listdir(args.directory)
		    fullpaths = [str(args.directory + file) for file in ls_files]
		    if args.config:
			    ls_files.append(os.path.basename(args.config))
			    fullpaths.append(args.config)
		    res_ids = upload(url, fullpaths)
		    options['filename'] = ls_files

           # Send message to RPC Server
            options['ARASTUSER'] = ARASTUSER
            options['ids'] = res_ids
            del options['ARASTPASSWORD']
            del options['ARASTURL']
            rpc_body = json.dumps(options, sort_keys=True)
            arast_rpc = RpcClient()
            logging.debug(" [x] Sending message: %r" % (rpc_body))
            response = arast_rpc.call(rpc_body)
            logging.debug(" [.] Response: %r" % (response))

        # Stat
        elif args.command == 'stat':
		while True:
			os.system('clear')
			options['ARASTUSER'] = ARASTUSER
			rpc_body = json.dumps(options, sort_keys=True)
			arast_rpc = RpcClient()
			logging.debug(" [x] Sending message: %r" % (rpc_body))
			response = arast_rpc.call(rpc_body)
			logging.debug(" [.] Response: %s" % (response))
			print response
			time.sleep(2)
			

	elif args.command == 'get':
		job = ''
		if args.assemblers:
			pass
#		if args.job_id:
#			pass
		options['ARASTUSER'] = ARASTUSER
		rpc_body = json.dumps(options, sort_keys=True)
		arast_rpc = RpcClient()
	        logging.debug(" [x] Sending message: %r" % (rpc_body))
		response = arast_rpc.call(rpc_body)
		logging.debug(" [.] Response: %s" % (response))
		try:
			params = json.loads(response)
			for id in params.values():
				shock.download(url, id, '', ARASTUSER, ARASTPASSWORD)
		except:
			print "Error getting results"
			



## Send RPC call ##
class RpcClient:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=ARASTURL), timeout=10)

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, msg):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(exchange='',
                                   routing_key='rpc_queue',
                                   properties=pika.BasicProperties(
                reply_to = self.callback_queue,
                correlation_id = self.corr_id,
                ),
                                   body=msg)
        while self.response is None:
            self.connection.process_data_events()
        return self.response


global ARASTUSER, ARASTPASSWORD
cparser = SafeConfigParser()
cparser.read('settings.conf')
ARASTUSER = cparser.get('arast', 'user')
ARASTPASSWORD = cparser.get('arast', 'password')
ARASTURL = cparser.get('arast', 'url')
main()
