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
import client
import shock
from auth_token import *

my_version = '0.2.2'
# setup option/arg parser
parser = argparse.ArgumentParser(prog='arast', epilog='Use "arast command -h" for more information about a command.')
parser.add_argument('-s', dest='ARASTURL', help='arast server url')
parser.add_argument('-c', '--config', action="store", help='Specify config file')
parser.add_argument('-u', '--ARASTUSER', help='Overrules env ARASTUSER')
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
p_stat.add_argument("-n", dest="stat_n", action="store", default=15, type=int, help="specify number of records to show")


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
        config_file = resource_filename(__name__, 'settings.conf')
        clientlog.debug("Reading config file: %s" % config_file)

    cparser.read(config_file)

    try:
        ARASTURL = cparser.get('arast', 'url')
    except:
        clientlog.error("Invalid config file")

    # Check Authorization
    user_dir = appdirs.user_data_dir(cparser.get('arast','appname'),
                                       cparser.get('arast','appauthor'))
    oauth_file = os.path.join(user_dir, cparser.get('arast','oauth_filename'))
    expiration = int(cparser.get('arast', 'oauth_exp_days'))


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
        print >> sys.stderr, "Logged in as: {}".format(a_user)
    else:
        print("Please authenticate with Globus Online")
        a_user = raw_input("Globus Login: ")
        a_pass = getpass.getpass(prompt="Globus Password: ")
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
                response = aclient.get_job_status(args.stat_n)
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
