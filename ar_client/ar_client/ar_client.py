#! /usr/bin/env python
"""
arast-client -- commandline client for Assembly RAST

"""


import os, sys, json, shutil
import argparse
import logging
import requests
import uuid
import subprocess
import time
from ConfigParser import SafeConfigParser
from pkg_resources import resource_filename

import client
import shock


my_version = '0.2.1'
# setup option/arg parser
parser = argparse.ArgumentParser(prog='assembly', epilog='Use "arast command -h" for more information about a command.')
parser.add_argument('-s', dest='ARASTURL', help='arast server url')
parser.add_argument('-c', '--config', action="store", help='Specify config file')
parser.add_argument('-u', '--ARASTUSER', help='Overrules env ARASTUSER')
parser.add_argument('-p', '--ARASTPASSWORD', help='Overrules env ARASTPASSWORD')
parser.add_argument("-v", "--verbose", action="store_true", help="Verbose")
parser.add_argument('--version', action='version', version='%(prog)s ' + my_version)

subparsers = parser.add_subparsers(dest='command', title='The commands are')

# run -h
p_run = subparsers.add_parser('run', description='Run an Assembly RAST job', help='run job')
p_run.add_argument("-f", action="append", dest="single", nargs='*', help="specify sequence file(s)")
p_run.add_argument("-a", "--assemblers", action="store", dest="pipeline", nargs='*')
p_run.add_argument("-p", "--pipeline", action="store", dest="pipeline", nargs='*', help="Pipeline")
p_run.add_argument("-m", "--message", action="store", dest="message", help="Attach a description to job")
p_run.add_argument("--data", action="store", dest="data_id", help="Reuse uploaded data")
p_run.add_argument("--pair", action="append", dest="pair", nargs='*', help="Specify a paired-end library and parameters")
p_run.add_argument("--single", action="append", dest="single", nargs='*', help="Specify a single end file and parameters")

# stat -h
p_stat = subparsers.add_parser('stat', description='Query status of running jobs', help='list jobs status')
p_stat.add_argument("-w", "--watch", action="store_true", help="monitor in realtime")
p_stat.add_argument("-n", dest="stat_n", action="store", nargs=1, default=15, type=int, help="specify number ofrecords to show")


# get
p_get = subparsers.add_parser('get', description='Download result data', help='download data')
p_get.add_argument("-j", "--job", action="store", dest="job_id", nargs=1, required=True, help="specify which job data to get")


# upload all files in list, return list of ids
def upload(files):
    ids = []
    for f in files:
        # check if file exists
        if not os.path.exists(f):
            logging.error("File does not exist: '%s'" % (f))
            continue
        else:
            sys.stderr.write( "Uploading: %s...\n" % os.path.basename(f))
             #res = curl_post_file(url, f)
            res = aclient.upload_data_shock(f)
            ids.append(res['D']['id'])
            if res["E"] is not None:
                sys.exit("Shock: err from server: %s" % res["E"][0])
    return ids

def main():
    global ARASTURL, ARASTUSER, ARASTPASSWORD, aclient
    
    clientlog = logging.getLogger('client')
    clientlog.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    frmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    sh.setFormatter(frmt)
    clientlog.addHandler(sh)


    args = parser.parse_args()
    opt = parser.parse_args()
    options = vars(args)
    
    options['version'] = my_version
    cparser = SafeConfigParser()

    if args.verbose:
        clientlog.setLevel(logging.DEBUG)
        clientlog.debug("Logger Debugging mode")

    if args.config:
        config_file = args.config
    else:
        #config_file = "settings.conf"
        config_file = resource_filename(__name__, 'settings.conf')
        clientlog.debug("Reading config file: %s" % config_file)

    cparser.read(config_file)

    try:
        ARASTUSER = cparser.get('arast', 'user')
        ARASTPASSWORD = cparser.get('arast', 'password')
        ARASTURL = cparser.get('arast', 'url')
    except:
        clientlog.error("Invalid config file")

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


    aclient = client.Client(ARASTURL, ARASTUSER, ARASTPASSWORD)
        
    res_ids = []
    file_sizes = []
    file_list = []
    if args.command == "run":
        if not ((args.pipeline) and (args.data_id or args.pair or args.single)):
            parser.print_usage()
            sys.exit()

        files = []
        if args.pair:
            for ls in args.pair:
                for word in ls:
                    if is_filename(word):
                        files.append(word)
        if args.single:
            for ls in args.single:
                for word in ls:
                    if is_filename(word):
                        files.append(word)

        base_files = []
        file_sizes = []
        res_ids = []
        for f in files:
            #Check file or dir
            if os.path.isfile(f):
                res_ids += upload([f,])
                file_sizes.append(os.path.getsize(f))
                base_files.append(os.path.basename(f))
            elif os.path.isdir(f):
                ls_files = os.listdir(f)

                fullpaths = [str(f + "/"+ file) for file in ls_files 
                             if not os.path.isdir(str(f + "/" +file))]
                print fullpaths
                file_list = fullpaths # ???

                res_ids += upload(url, fullpaths)
                for path in fullpaths:
                    file_sizes.append(os.path.getsize(path))
                base_files += [os.path.basename(file) for file in fullpaths]

        options['filename'] = base_files
        # # Send message to RPC Server
        #options['ARASTUSER'] = ARASTUSER
        options['ids'] = res_ids
        options['file_sizes'] = file_sizes
        del options['ARASTPASSWORD']
        del options['ARASTURL']
        rpc_body = json.dumps(options, sort_keys=True)
        clientlog.debug(" [x] Sending message: %r" % (rpc_body))
        response = aclient.submit_job(rpc_body)
        print response
        clientlog.debug(" [.] Response: %r" % (response))


    elif args.command == 'stat':
        while True:
                if args.watch:
                        os.system('clear')
                response = aclient.get_job_status(args.stat_n[0])
                print response
                if not args.watch:
                        break
                time.sleep(2)			

    elif args.command == 'get':
        aclient.get_job_data(args.job_id[0])


global ARASTUSER, ARASTPASSWORD

def is_filename(word):
    return word.find('.') != -1 and word.find('=') == -1

if __name__ == '__main__':
    main()
