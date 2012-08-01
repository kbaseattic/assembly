"""
arast-client -- commandline client for Assembly RAST

A lot of code taken from Jared Wilkening / ShockClient

"""

#!/usr/bin/python
import os, sys, json, shutil
import pika
import argparse
import requests
import prettytable as pt
import uuid
from progressbar import Counter, ProgressBar, Timer

import client_config

# get env vars
#ARASTURL = os.getenv("ARASTURL")
#ARASTUSER = os.getenv("ARASTUSER")
#ARASTPASSWORD = os.getenv("ARASTPASSWORD")
ARASTURL = client_config.ARASTURL
print ARASTURL
ARASTUSER = client_config.ARASTUSER
print ARASTUSER
ARASTPASSWORD = client_config.ARASTPASSWORD


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


# stat -h
p_stat = subparsers.add_parser('stat', description='Query status of running jobs', help='list jobs status')


def post(url, files):
	global ARASTUSER, ARASTPASSWORD
	r = None
	if ARASTUSER and ARASTPASSWORD:
            print "Uploading"
            r = requests.post(url, auth=(ARASTUSER, ARASTPASSWORD), files=files)
	else:
            r = requests.post(url, files=files)

        res = json.loads(r.text)
        print r.text
	return res


def printNodeTable(n):
	t = pt.PrettyTable(["name", "key/value", "value"])
	t.set_field_align("name", "l")
	t.set_field_align("key/value", "l")
	t.set_field_align("value", "l")		
	t.add_row(["id",n["id"],""])
	t.add_row(["file","",""])
	for k,v in n["file"].iteritems():
		t.add_row(["",k,json.dumps(v)])
	t.add_row(["indexes",json.dumps(n["indexes"]),""])		
	if n["attributes"] != None:
		t.add_row(["attributes","",""])
		for k,v in n["attributes"].iteritems():
			value = json.dumps(v, sort_keys=True, indent=4)
			split = value.split('\n')
			if len(split) > 1:
				t.add_row(["",k,split[0]])
				for attr in value.split('\n')[1:]:
					for r in fmtText(attr):
						t.add_row(["","",r])
			else:
				t.add_row(["",k,split[0]])
	else:
		t.add_row(["attributes","{}",""])
	t.add_row(["acls","",""])
	for k,v in n["acl"].iteritems():
		val = json.dumps(v) if v != None else "[]"
		t.add_row(["",k,val])		
	print t


def main():
	global ARASTURL, ARASTUSER, ARASTPASSWORD
	
	args = parser.parse_args()
	opt = parser.parse_args()
        options = vars(args)

	# overwrite env vars in args
	if args.ARASTURL:
		ARASTURL = args.ARASTURL
	if args.ARASTUSER:
		ARASTUSER = args.ARASTUSER				
	if args.ARASTPASSWORD:
		ARASTPASSWORD = args.ARASTPASSWORD				
	if not ARASTURL:
		print parser.print_usage()
		print "arast: err: ARASTURL not set"
		sys.exit()
	url = "http://%s" % (ARASTURL)

        # Upload file to Shock
        res = {}
	if args.command == "run":
            url += "/node"
            files = {}
            if args.filename:
                print args.filename
                files["file"] = (os.path.basename(args.filename[0]), open(args.filename[0], 'rb'))
		res = post(url, files)
		if res["E"] is None:
                    # Prettytable 0.6 breaks this
                    #printNodeTable(res["D"])
                    print "File(s) uploaded"
		else:
                    print "shock: err from server: %s" % res["E"][0]

        # Send message to RPC Server
        options['ARASTUSER'] = ARASTUSER
        options['id'] = res["D"]["id"]
        del options['ARASTPASSWORD']
        del options['ARASTURL']
        print options
        rpc_body = json.dumps(options, sort_keys=True)
        arast_rpc = RpcClient()
        print " [x] Sending message: %r" % (rpc_body)
        #response = arast_rpc.call(rpc_body)
        #print " [.] Response: %r" % (response)

## Send RPC call ##
class RpcClient:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=client_config.ARASTCONTROLHOST))

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

main()
