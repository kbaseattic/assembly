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
import traceback

my_version = '0.3.8.1'
# setup option/arg parser
parser = argparse.ArgumentParser(prog='arast', epilog='Use "arast command -h" for more information about a command.')
parser.add_argument('-s', dest='ARASTURL', help='arast server url')
parser.add_argument('-c', '--config', action="store", help='Specify config file')
parser.add_argument("-v", "--verbose", action="store_true", help="Verbose")
parser.add_argument('--version', action='version', version='AssemblyRAST Client ' + my_version)

subparsers = parser.add_subparsers(dest='command', title='The commands are')

# run -h
p_run = subparsers.add_parser('run', description='Run an Assembly RAST job', help='run job')
data_group = p_run.add_mutually_exclusive_group()
p_run.add_argument("-f", action="append", dest="single", nargs='*', help="specify sequence file(s)")
#p_run.add_argument("-u", "--urls",  action="append",  nargs='*', help="specify url(s) of sequence file")
data_group.add_argument("-r", "--reference", action="append", dest="reference", nargs='*', help="specify sequence file(s)")
p_run.add_argument("-a", "--assemblers", action="store", dest="assemblers", nargs='*', help="specify assemblers to use. None will invoke automatic mode")
p_run.add_argument("-p", "--pipeline", action="append", dest="pipeline", nargs='*', help="invoke a pipeline. None will invoke automatic mode")
p_run.add_argument("-m", "--message", action="store", dest="message", help="Attach a description to job")
p_run.add_argument("-q", "--queue", action="store", dest="queue", help=argparse.SUPPRESS)
data_group.add_argument("--data", action="store", dest="data_id", help="Reuse uploaded data")
p_run.add_argument("--pair", action="append", dest="pair", nargs='*', help="Specify a paired-end library and parameters")
p_run.add_argument("--single", action="append", dest="single", nargs='*', help="Specify a single end file and parameters")
#p_run.add_argument("--all-data", action="store_true", help="save all data for return")
p_run.add_argument("--curl", action="store_true", help="Use curl for http requests")

# stat -h
p_stat = subparsers.add_parser('stat', description='Query status of running jobs', help='list jobs status')
p_stat.add_argument("-j", "--job", action="store", help="get status of specific job")
p_stat.add_argument("-w", "--watch", action="store_true", help="monitor in realtime")
p_stat.add_argument("-n", dest="stat_n", action="store", default=15, type=int, help="specify number of records to show")

p_avail = subparsers.add_parser('avail', description='List available AssemblyRAST modules', help='list available modules')
p_avail.add_argument("-v", "--verbose", action="store_true", help="show module details")

p_upload = subparsers.add_parser('upload', description='Upload a read set', help='Upload a read library or set of libraries, returns a data ID for future use')
p_upload.add_argument("-f", action="append", dest="single", nargs='*', help="specify sequence file(s)")
p_upload.add_argument("--pair", action="append", dest="pair", nargs='*', help="Specify a paired-end library and parameters")
p_upload.add_argument("--single", action="append", dest="single", nargs='*', help="Specify a single end file and parameters")
p_upload.add_argument("-r", "--reference", action="append", dest="reference", nargs='*', help="specify sequence file(s)")
p_upload.add_argument("-m", "--message", action="store", dest="message", help="Attach a description to job")


p_kill = subparsers.add_parser('kill', description='Send a kill signal to jobs', help='kill jobs')
p_kill.add_argument("-j", "--job", action="store", help="kill specific job")
p_kill.add_argument("-a", "--all", action="store_true", help="kill all user jobs")

# get
p_get = subparsers.add_parser('get', description='Download result data', help='download data')
p_get.add_argument("-j", "--job", action="store", dest="job_id", nargs=1, required=True, help="specify which job data to get")
p_get.add_argument("-a", "--assembly", action="store", nargs='?', default=False, const=True, help="Get assemblies only")
p_get.add_argument("--stdout", action="store_true", help="Print assembly to stdout")
p_get.add_argument("-o", "--outdir", action="store", help="Download to specified dir")

p_logout = subparsers.add_parser('logout', description='Log out', help='log out')
p_login = subparsers.add_parser('login', description='Force log in', help='log in')

# upload all files in list, return list of ids
def upload(files, curl=False):
    ids = [] # legacy
    shock_handles = []
    for f in files:
        # check if file exists
        if not os.path.exists(f):
            logging.error("File does not exist: '%s'" % (f))
            continue
        else:
            sys.stderr.write( "Uploading: %s...\n" % os.path.basename(f))
            res, shock_info = aclient.upload_data_shock(f, curl=curl)
            ids.append(res['data']['id'])
            shock_handles.append(shock_info)
            if res["error"] is not None:
                sys.exit("Shock: err from server: %s" % res["error"][0])
            else:
                sys.stderr.write( "Uploaded: %s...\n" % os.path.basename(f))

    return ids, shock_handles

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

    if "KB_RUNNING_IN_IRIS" in os.environ:
        if args.command == 'logout' or args.command == 'login':
            print "Please use the IRIS controls to log in/out"
            sys.exit()
        if "KB_AUTH_TOKEN" in os.environ and "KB_AUTH_USER_ID" in os.environ and \
                len(os.environ["KB_AUTH_USER_ID"]) > 0 and \
                len(os.environ["KB_AUTH_TOKEN"]) > 0 :
            a_user = os.environ["KB_AUTH_USER_ID"]
            a_token = os.environ["KB_AUTH_TOKEN"]
        else:
            print "Please authenticate with KBase credentials"
            sys.exit()

    else:
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


    curl = False
    try:
        curl = args.curl
    except:
        pass


    # Format into separate pipelines
    if args.command == "run" or args.command == "upload":
        if args.command == "run":
            if args.assemblers:
                args.pipeline = [(" ".join(args.assemblers))]

            if not args.pipeline: # auto
                args.pipeline = 'auto'

            if not args.pipeline:
                parser.print_usage()
                sys.exit()

            if not (args.data_id or args.pair or args.single):
                parser.print_usage()
                sys.exit()

        if args.command == "upload" and not (args.pair or args.single):
            parser.print_usage()
            sys.exit()

        files = []
        adata = client.AssemblyData()
        
        ##### Parse args and create AssemblyData dict #####
        try:
            has_data_id = args.data_id
        except:
            has_data_id = False
        if not has_data_id:
            all_lists = [args.pair, args.single, args.reference]
            file_lists = []
            for l in all_lists:
                if l is None:
                    file_lists.append([])
                else:
                    file_lists.append(l)
                    
            all_types = ['paired', 'single', 'reference']
            for f_list, f_type in zip(file_lists, all_types):
                f_infos = []
                f_set_args = {}
                for ls in f_list:
                    for word in ls:
                        if is_filename(word) and os.path.isfile(word):
                            f_info = aclient.upload_data_file_info(word, curl=curl)
                            f_infos.append(f_info)
                        elif '=' in word:
                            kv = word.split('=')
                            f_set_args[kv[0]] = kv[1]
                f_set = client.FileSet(f_type, f_infos, **f_set_args)
                adata.add_set(f_set)

        arast_msg = {k:options[k] for k in ['pipeline', 'data_id', 'message', 'queue', 'version']
                     if k in options}
        arast_msg['assembly_data'] = adata
        arast_msg['client'] = 'CLI'

        ##### Send message to Arast Server #####
        payload = json.dumps(arast_msg, sort_keys=True)
        clientlog.debug(" [x] Sending message: %r" % (payload))

        if args.command == "run":
            response = aclient.submit_job(payload)
        if args.command == "upload":
            response = aclient.submit_data(payload)
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
        if args.assembly:
            try:
                if type(args.assembly) is int:
                    aclient.get_assemblies(job_id=args.job_id[0], asm_id=args.assembly, stdout=args.stdout, outdir=args.outdir)
                else:
                    aclient.get_assemblies(job_id=args.job_id[0], stdout=args.stdout, outdir=args.outdir)
            except:
                print traceback.format_tb(sys.exc_info()[2])
                print sys.exc_info()
        else:
            try:
                aclient.get_job_data(job_id=args.job_id[0], outdir=args.outdir)
            except:
                print 'Invalid job id'

    elif args.command == 'avail':
        try:
            mods = json.loads(aclient.get_available_modules())
            mods = sorted(mods, key=lambda mod: mod['module'])
            # print json.dumps(mods, indent=4)
            
            if args.verbose:
                for mod in mods:
                    keys = ('description', 'version', 'stages', 'modules', 'limitations', 'references')
                    if mod['version'] >= '1.0':
                        print '[Module] ' + mod['module']
                        for key in keys:
                            if key in mod.keys():
                                print '  '+key.title()+': '+mod[key]

                        if 'parameters' in mod.keys() :
                            parms = mod['parameters']
                            if len(parms) > 0:
                                print '  Customizable parameters: default (available values)'
                                for parm in sorted(parms, key=lambda p: p[0]):
                                    print '%25s  =  %s' % (parm[0], parm[1])
                        print
            else:
                print '{0:16} {1:35} {2:10}'.format('Module', 'Stages', 'Description')
                print '----------------------------------------------------------------'
                for mod in mods:
                    if mod['version'] >= '1.0':
                        print '{module:16} {stages:35} {description}'.format(**mod)

        except:
            print 'Error getting available modules'

    elif args.command == 'kill':
        print aclient.kill_jobs(args.job)

def is_filename(word):
    return word.find('.') != -1 and word.find('=') == -1

if __name__ == '__main__':
    main()
