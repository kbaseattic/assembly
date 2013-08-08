#! /usr/bin/env python
"""
arast-client -- commandline client for Assembly RAST

"""

import os, sys, json, shutil
import appdirs
import argparse
import datetime
import getpass
import logging
import requests
import uuid
import subprocess
import time
from ConfigParser import SafeConfigParser
from pkg_resources import resource_filename

#arast libs

import ar_client.client as client
import ar_client.config as conf
from ar_client.auth_token import *



my_version = '0.2.7'
# setup option/arg parser
parser = argparse.ArgumentParser(prog='arast', epilog='Use "arast command -h" for more information about a command.')
parser.add_argument('-s', dest='ARASTURL', help='arast server url')
parser.add_argument('-c', '--config', action="store", help='Specify config file')
parser.add_argument("-v", "--verbose", action="store_true", help="Verbose")
parser.add_argument('--version', action='version', version='%(prog)s ' + my_version)

subparsers = parser.add_subparsers(dest='command', title='The commands are')

# run -h
p_run = subparsers.add_parser('run', description='Run an Assembly RAST job', help='run job')
data_group = p_run.add_mutually_exclusive_group()
p_run.add_argument("-f", action="append", dest="single", nargs='*', help="specify sequence file(s)")
data_group.add_argument("-r", "--reference", action="append", dest="reference", nargs='*', help="specify sequence file(s)")
p_run.add_argument("-a", "--assemblers", action="store", dest="assemblers", nargs='*', help="specify assemblers to use")
p_run.add_argument("-p", "--pipeline", action="append", dest="pipeline", nargs='*', help="invoke a pipeline")
p_run.add_argument("-m", "--message", action="store", dest="message", help="Attach a description to job")
p_run.add_argument("-q", "--queue", action="store", dest="queue", help=argparse.SUPPRESS)
data_group.add_argument("--data", action="store", dest="data_id", help="Reuse uploaded data")
p_run.add_argument("--pair", action="append", dest="pair", nargs='*', help="Specify a paired-end library and parameters")
p_run.add_argument("--single", action="append", dest="single", nargs='*', help="Specify a single end file and parameters")
p_run.add_argument("--all-data", action="store_true", help="save all data for return")

# stat -h
p_stat = subparsers.add_parser('stat', description='Query status of running jobs', help='list jobs status')
p_stat.add_argument("-j", "--job", action="store", help="get status of specific job")
p_stat.add_argument("-w", "--watch", action="store_true", help="monitor in realtime")
p_stat.add_argument("-n", dest="stat_n", action="store", default=15, type=int, help="specify number of records to show")

p_avail = subparsers.add_parser('avail', description='List available AssemblyRAST modules', help='list available modules')

p_kill = subparsers.add_parser('kill', description='Send a kill signal to jobs', help='kill jobs')
p_kill.add_argument("-j", "--job", action="store", help="kill specific job")
p_kill.add_argument("-a", "--all", action="store_true", help="kill all user jobs")

# get
p_get = subparsers.add_parser('get', description='Download result data', help='download data')
p_get.add_argument("-j", "--job", action="store", dest="job_id", nargs=1, required=True, help="specify which job data to get")

p_logout = subparsers.add_parser('logout', description='Log out', help='log out')
p_login = subparsers.add_parser('login', description='Force log in', help='log in')

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
    global aclient
    
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

    if args.verbose:
        clientlog.setLevel(logging.DEBUG)
        clientlog.debug("Logger Debugging mode")

    ARASTURL = conf.URL
    user_dir = appdirs.user_data_dir(conf.APPNAME, conf.APPAUTHOR)
    oauth_file = os.path.join(user_dir, conf.OAUTH_FILENAME)
    expiration = conf.OAUTH_EXP_DAYS

    oauth_parser = SafeConfigParser()
    oauth_parser.read(oauth_file)
    reauthorize = True

    if args.command == 'logout' or args.command == 'login':
        try:
            os.remove(oauth_file)
        except:
            pass
        if args.command == 'logout':
            print >> sys.stderr, '[x] Logged out'
            sys.exit()

    # Check if user file exists
    if os.path.exists(oauth_file):
        token_date_str = oauth_parser.get('auth', 'token_date')
        tdate = datetime.datetime.strptime(token_date_str, '%Y-%m-%d').date()
        cdate = datetime.date.today()
        if (cdate - tdate).days > expiration:
            reauthorize = True
        else:
            reauthorize = False
    if not reauthorize:
        a_user = oauth_parser.get('auth', 'user')
        a_token = oauth_parser.get('auth', 'token')
        # print >> sys.stderr, "Logged in as: {}".format(a_user)
    else:
        print("Please authenticate with KBase credentials")
        a_user = raw_input("KBase Login: ")
        a_pass = getpass.getpass(prompt="KBase Password: ")
        globus_map = get_token(a_user, a_pass)
        a_token = globus_map['access_token']
        try:
            os.makedirs(user_dir)
        except:
            pass
        uparse = SafeConfigParser()
        uparse.add_section('auth')
        uparse.set('auth', 'user', a_user)
        uparse.set('auth', 'token', a_token)
        uparse.set('auth', 'token_date', str(datetime.date.today()))
        uparse.write(open(oauth_file, 'wb'))

    if args.command == 'login':
        print "Logged in"
        sys.exit()
    
    if args.ARASTURL:
        ARASTURL = args.ARASTURL

    aclient = client.Client(ARASTURL, a_user, a_token)
        
    res_ids = []
    file_sizes = []
    file_list = []
    # Format into separate pipelines
    if args.command == "run":
        if args.assemblers:
            args.pipeline = [(" ".join(args.assemblers))]

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
        if args.reference:
            for ls in args.reference:
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
            else:
                print('File does not exist:{}'.format(f))
                sys.exit(1)

        options['filename'] = base_files

        # # Send message to RPC Server
        options['ids'] = res_ids
        options['file_sizes'] = file_sizes
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
                response = aclient.get_job_status(args.stat_n, args.job)
                print response
                if not args.watch:
                        break
                time.sleep(2)			

    elif args.command == 'get':
        try:
            aclient.get_job_data(args.job_id[0])
        except:
            print 'Invalid job id'

    elif args.command == 'avail':
        try:
            print aclient.get_available_modules()
        except:
            print 'Error getting available modules'

    elif args.command == 'kill':
        print aclient.kill_jobs(args.job)

def is_filename(word):
    return word.find('.') != -1 and word.find('=') == -1

if __name__ == '__main__':
    main()
