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
import uuid
import time
from ConfigParser import SafeConfigParser
from pkg_resources import resource_filename

import shock


my_version = '0.0.6'
# setup option/arg parser
parser = argparse.ArgumentParser(prog='arast', epilog='Use "arast command -h" for more information about a command.')
parser.add_argument('--ARASTURL', help='Overrules env ARASTURL')
parser.add_argument('--ARASTUSER', help='Overrules env ARASTUSER')
parser.add_argument('--ARASTPASSWORD', help='Overrules env ARASTPASSWORD')
parser.add_argument("-c", "--config", action="store",
                  dest="config", help="specify parameter configuration file")
parser.add_argument("-v", "--verbose", action="store_true",
                   help="Verbose")
parser.add_argument('--version', action='version', version='%(prog)s ' + my_version)

subparsers = parser.add_subparsers(dest='command', title='The commands are')

# run -h
p_run = subparsers.add_parser('run', description='Run an Assembly RAST job', help='run job')
p_run.add_argument("-f", "--file", action="store", dest="filename",
                   nargs='*', help="specify sequence file(s)")
p_run.add_argument("-a", "--assemblers", action="store",
                  dest="assemblers", nargs='*')
p_run.add_argument("-d", "--directory", action="store",
                  dest="directory",
                  help="specify input directory")
p_run.add_argument("-p", "--params", action="store",
                  dest="params", nargs='*',
                  help="specify global assembly parameters")
p_run.add_argument("-m", "--message", action="store",
                  dest="message",
                  help="Attach a description to job")
p_run.add_argument("--data", action="store",
                  dest="data_id",
                  help="Reuse uploaded data")
p_run.add_argument("--bwa", action="store_true", dest="bwa",
                   help="enable bwa alignment")

## Assembler flags ##

# Velvet
v = p_run.add_argument_group('Velvet parameters')
v.add_argument('--velvet-lib1', nargs = '+', help= "paired ends")
v.add_argument('--velvet-lib2', nargs = '+', help= "paired ends")




# filetype, special flags, config file
# global, -k=31, -cov
# velvet

# stat -h
p_stat = subparsers.add_parser('stat', description='Query status of running jobs', help='list jobs status')
p_stat.add_argument("-w", "--watch", action="store_true", help="monitor in realtime")
#p_stat.add_argument("-a", "--all", action="store_true", dest="stat_all", help="show all statistics")


p_stat.add_argument("--data", dest="files", action="store", nargs='?', const=-1, help="list latest or data-id specific files")

p_stat.add_argument("--job", dest="stat_job", action="store", nargs=1, default=-1, help="list latest or id specific job status")
p_stat.add_argument("-n", dest="stat_n", action="store", nargs=1, default=15, type=int, help="specify number ofrecords to show")



# get
p_get = subparsers.add_parser('get', description='Download result data', help='download data')
p_get.add_argument("-j", "--job", action="store",
                  dest="job_id", nargs=1,
                  help="specify which job data to get")

p_get.add_argument("-a", "--assemblers", action="store",
                  dest="assemblers", nargs='*',
                  help="specify which assembly data to get")

p_prep = subparsers.add_parser('prep', description='Prepare a parameter file', help='prepare job submission')

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

	options['version'] = my_version
	cparser = SafeConfigParser()
	if args.verbose:
		logging.basicConfig(level=logging.DEBUG)
	if args.config:
		config_file = args.config
	else:
		#config_file = "settings.conf"
		config_file = resource_filename(__name__, 'settings.conf')
		logging.info("Reading config file: %s" % config_file)
	cparser.read(config_file)

	try:
		ARASTUSER = cparser.get('arast', 'user')
		ARASTPASSWORD = cparser.get('arast', 'password')
		ARASTURL = cparser.get('arast', 'url')
	except:
		logging.error("Invalid config file")

	# overwrite env vars in args
	if args.ARASTUSER:
		ARASTUSER = args.ARASTUSER				
	if args.ARASTPASSWORD:
		ARASTPASSWORD = args.ARASTPASSWORD				
	if args.ARASTURL:
		ARASTURL = args.ARASTURL
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
	file_sizes = []
	file_list = []
	if args.command == "run":
            if not (args.assemblers and (args.filename or args.directory or args.data_id)):
		    parser.print_usage()
		    sys.exit()
			    

            if args.directory or args.filename:
                url += "/node"
		files = args.filename
		file_list = args.filename
		if args.config:
			options['config_id'] = upload(url, [args.config])
	    if args.filename:
		    res_ids = upload(url, files)
		    base_files = [os.path.basename(f) for f in files]
		    del options['filename']
		    options['filename'] = base_files
	    elif args.directory:
		    ls_files = os.listdir(args.directory)
		    #Remove config from upload list
		    if args.config:
			    cfile = os.path.basename(args.config)
			    if cfile in ls_files:
				    ls_files.remove(cfile)
		    fullpaths = [str(args.directory + file) for file in ls_files]
		    file_list = fullpaths
		    res_ids = upload(url, fullpaths)
		    options['filename'] = ls_files
	    if args.directory or args.filename:
		    for f in file_list:
			    file_sizes.append(os.path.getsize(f))
			    

           # Send message to RPC Server
            options['ARASTUSER'] = ARASTUSER
            options['ids'] = res_ids
	    options['file_sizes'] = file_sizes
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
			if args.watch:
				os.system('clear')
			options['ARASTUSER'] = ARASTUSER
			rpc_body = json.dumps(options, sort_keys=True)
			arast_rpc = RpcClient()
			logging.debug(" [x] Sending message: %r" % (rpc_body))
			response = arast_rpc.call(rpc_body)
			logging.debug(" [.] Response: %s" % (response))
			print response
			if not args.watch:
				break
			time.sleep(2)			

	elif args.command == 'get':
		if not args.job_id:
			job = -1
		else:
			job = args.job_id[0]
		if args.assemblers:
			pass
		logging.info("get %s" % (job))
		options['ARASTUSER'] = ARASTUSER
		options['job_id'] = job
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
                host=ARASTURL))

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


