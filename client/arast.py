#! /usr/bin/env python
"""
arast-client -- commandline client for Assembly RAST

"""

import os, sys, json, shutil
import argparse
import datetime
import getpass
import logging
import requests
import uuid
import subprocess
import time
import traceback
from ConfigParser import SafeConfigParser
# from pkg_resources import resource_filename

# arast libs
from assembly import asmtypes
from assembly import client
from assembly import config as conf
from assembly import auth


my_version = '0.4.0.1'

# Config precedence: command-line args > environment variables > config file

ARAST_URL = os.getenv('ARAST_URL') or conf.URL
ARAST_QUEUE = os.getenv('ARAST_URL')
ARAST_AUTH_USER = os.getenv('ARAST_AUTH_USER') or os.getenv('KB_AUTH_USER_ID')
ARAST_AUTH_TOKEN = os.getenv('ARAST_AUTH_TOKEN') or os.getenv('KB_AUTH_TOKEN')

ARAST_ENVIRON = None
if os.getenv('KB_RUNNING_IN_IRIS'):
    ARAST_ENVIRON = 'IRIS'


def get_parser():
    parser = argparse.ArgumentParser(prog='arast', epilog='Use "arast command -h" for more information about a command.')

    parser.add_argument('-s', dest='arast_url', help='arast server url')
    parser.add_argument('-c', '--config', action="store", help='Specify config file')
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose")
    parser.add_argument('--version', action='version', version='AssemblyRAST Client ' + my_version)

    subparsers = parser.add_subparsers(dest='command', title='The commands are')

    p_upload = subparsers.add_parser('upload', description='Upload a read set', help='Upload a read library or set of libraries, returns a data ID for future use')
    p_run = subparsers.add_parser('run', description='Run an Assembly RAST job', help='run job')
    p_stat = subparsers.add_parser('stat', description='Query status of running jobs', help='list jobs status')
    p_avail = subparsers.add_parser('avail', description='List available AssemblyRAST modules', help='list available modules')
    p_kill = subparsers.add_parser('kill', description='Send a kill signal to jobs', help='kill jobs')
    p_get = subparsers.add_parser('get', description='Get result data', help='Get data')
    p_login = subparsers.add_parser('login', description='Force log in', help='log in')
    p_logout = subparsers.add_parser('logout', description='Log out', help='log out')

    # run options
    p_run.add_argument("-f", action="append", dest="single", nargs='*', help="specify sequence file(s)")
    p_run.add_argument("-m", "--message", action="store", dest="message", help="Attach a description to job")
    p_run.add_argument("-q", "--queue", action="store", dest="queue", help=argparse.SUPPRESS)
    p_run.add_argument("--pair", action="append", dest="pair", nargs='*', help="Specify a paired-end library and parameters")
    p_run.add_argument("--pair_url", action="append", dest="pair_url", nargs='*', help="Specify URLs for a paired-end library and parameters")
    p_run.add_argument("--single", action="append", dest="single", nargs='*', help="Specify a single end file and parameters")
    p_run.add_argument("--single_url", action="append", dest="single_url", nargs='*', help="Specify a URL for a single end file and parameters")
    p_run.add_argument("--reference", action="append", dest="reference", nargs='*', help="specify sequence file(s)")
    p_run.add_argument("--reference_url", action="append", dest="reference_url", nargs='*', help="Specify a URL for a reference contig file and parameters")
    p_run.add_argument("--curl", action="store_true", help="Use curl for http requests")

    data_group = p_run.add_mutually_exclusive_group()
    data_group.add_argument("--data", action="store", dest="data_id", help="Reuse uploaded data")

    cmd_group = p_run.add_mutually_exclusive_group()
    cmd_group.add_argument("-a", "--assemblers", action="store", dest="assemblers", nargs='*', help="specify assemblers to use. None will invoke automatic mode")
    cmd_group.add_argument("-p", "--pipeline", action="append", dest="pipeline", nargs='*', help="invoke a pipeline. None will invoke automatic mode")
    cmd_group.add_argument("-r", "--recipe", action="store", dest="recipe", nargs='*', help="invoke a recipe")
    cmd_group.add_argument("-w", "--wasp", action="store", dest="wasp", nargs='*', help="invoke a wasp expression")

    # stat options
    p_stat.add_argument("-j", "--job", action="store", help="get status of specific job")
    p_stat.add_argument("-w", "--watch", action="store_true", help="monitor in realtime")
    p_stat.add_argument("-n", dest="stat_n", action="store", default=10, type=int, help="specify number of records to show")
    p_stat.add_argument("-d", "--detail", action="store_true", help="show pipeline/recipe/wasp details in status table")
    p_stat.add_argument("-l", "--list-data", action="store_true", dest="list_data", help="list data objects")
    p_stat.add_argument("--data-json", action="store", dest="data_id", help="print json string for data object")

    # avail options
    p_avail.add_argument("-r", "--recipe", action="store_true", help="list recipes")
    p_avail.add_argument("-d", "--detail", action="store_true", help="show module details")

    # upload options
    p_upload.add_argument("-f", action="append", dest="single", nargs='*', help="specify sequence file(s)")
    p_upload.add_argument("--pair", action="append", dest="pair", nargs='*', help="Specify a paired-end library and parameters")
    p_upload.add_argument("--pair_url", action="append", dest="pair_url", nargs='*', help="Specify URLs for a paired-end library and parameters")
    p_upload.add_argument("--single", action="append", dest="single", nargs='*', help="Specify a single end file and parameters")
    p_upload.add_argument("--single_url", action="append", dest="single_url", nargs='*', help="Specify a URL for a single end file and parameters")
    p_upload.add_argument("--reference", action="append", dest="reference", nargs='*', help="specify a reference contig file")
    p_upload.add_argument("--reference_url", action="append", dest="reference_url", nargs='*', help="Specify a URL for a reference contig file and parameters")
    p_upload.add_argument("-m", "--message", action="store", dest="message", help="Attach a description to job")
    p_upload.add_argument("--json", action="store_true", help="Print data info json object")

    # kill options
    p_kill.add_argument("-j", "--job", action="store", help="kill specific job")
    p_kill.add_argument("-a", "--all", action="store_true", help="kill all user jobs")

    # get options
    p_get.add_argument("-j", "--job", action="store", required=True, help="Specify which job data to get")
    p_get.add_argument("-a", "--assembly", action="store", nargs='?', default=None, const=True, help="Download an assembly or assemblies")
    p_get.add_argument("-p", "--pick", action="store", nargs='?', default=None, const=True, help="Print an assembly")
    p_get.add_argument("-r", "--report", action="store_true", help="Print assembly stats report")
    p_get.add_argument("-l", "--log", action="store_true", help="Print assembly job log")
    p_get.add_argument("-o", "--outdir", action="store", help="Download to specified dir")
    p_get.add_argument("-w", "--wait", action="store_true", help="Wait until job is done")

    # login options
    p_login.add_argument("--rast", action="store_true", help="Log in using RAST account")

    return parser


def main():
    
    parser = get_parser()
    args = parser.parse_args()

    # TODO:only used by run
    options = vars(args)
    options['version'] = my_version

    frmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(frmt)

    clientlog = logging.getLogger('client')
    clientlog.setLevel(logging.INFO)
    clientlog.addHandler(sh)
    if args.verbose:
        clientlog.setLevel(logging.DEBUG)
        clientlog.debug("Logger Debugging mode")

    if args.command == 'login':
        cmd_login(args)
        sys.exit()

    if args.command == 'logout':
        cmd_login(args)
        sys.exit()
    
    a_user, a_token = auth.verify_token(ARAST_AUTH_USER,ARAST_AUTH_TOKEN)
    if not a_user or not a_token:
        if ARAST_ENVIRON:
            sys.exit('Please use the {} controls to authenticate'.format(ARAST_ENVIRON))
        else:
            sys.stderr.write('You can use the login/logout commands to authenticate\n')
            a_user, a_token = auth.authenticate()

    # main command options
    a_url = args.arast_url or ARAST_URL
    a_url = client.verify_url(a_url)
    logging.info('ARAST_URL: {}'.format(a_url))
    try:
        aclient = client.Client(a_url, a_user, a_token)
    except Exception as e:
        sys.exit("Error creating client: {}".format(e))
        
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

            if not (args.data_id or 
                    args.pair or args.pair_url or
                    args.single or args.single_url):
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
            all_lists = [args.pair, args.pair_url, args.single, args.single_url, args.reference, args.reference_url]
            file_lists = []
            for l in all_lists:
                if l is None:
                    file_lists.append([])
                else:
                    file_lists.append(l)
                   
            all_types = ['paired', 'paired_url', 'single', 'single_url', 'reference', 'reference_url']
            for f_list, f_type in zip(file_lists, all_types):
                for ls in f_list:
                    f_infos = []
                    f_set_args = {}
                    for word in ls:
                        if not (os.path.isfile(word) or '=' in word or is_valid_url(word)):
                            raise Exception('{} is not valid input!'.format(word))
                    for word in ls:
                        if os.path.isfile(word):
                            f_info = aclient.upload_data_file_info(word, curl=curl)
                            f_infos.append(f_info)
                        elif '=' in word:
                            kv = word.split('=')
                            f_set_args[kv[0]] = kv[1]
                        elif is_valid_url(word):
                            f_info = asmtypes.FileInfo(direct_url=word)
                            f_infos.append(f_info)
                    f_set = asmtypes.FileSet(f_type, f_infos, **f_set_args)
                    adata.add_set(f_set)

        arast_msg = dict((k, options[k]) for k in ['pipeline', 'data_id', 'message', 'queue', 'version', 'recipe', 'wasp'] if k in options)

        arast_msg['assembly_data'] = adata
        arast_msg['client'] = 'CLI'

        ##### Send message to Arast Server #####
        payload = json.dumps(arast_msg, sort_keys=True)
        clientlog.debug(" [.] Sending message: %r" % (payload))

        if args.command == "run":
            response = aclient.submit_job(payload)
            print 'Job ID: {}'.format(response)
        if args.command == "upload":
            response = aclient.submit_data(payload)
            arast_msg.update(json.loads(response))
            if args.json:
                # print arast_msg
                print payload
            print 'Data ID: {}'.format(arast_msg['data_id'])

    elif args.command == 'stat':
        if args.list_data:
            table = aclient.get_data_list_table(args.stat_n)
            print table
            sys.exit()

        if args.data_id:
            data_json = aclient.get_data_json(args.data_id)
            print data_json
            sys.exit()
        
        # default: print job information
        while True:
            try:
                response = aclient.get_job_status(args.stat_n, args.job, detail=args.detail)
                if args.watch:
                        os.system('clear')
                print response
                if not args.watch:
                        break
                else:
                    print 'Press CTRL-C to quit.'
                ### Spinner loop
                spinners = ['-', '\\', '|', '/'] 
                sleep_seconds = 25
                spins_per_sec = 4
                for i in range(sleep_seconds * spins_per_sec):
                    os.system('clear')
                    print('[{}] Assembly Service Status').format(spinners[i%4])
                    print response
                    print 'Press CTRL-C to quit.'
                    time.sleep(1.0/spins_per_sec)			
            except KeyboardInterrupt:
                break
                

    elif args.command == 'get':
        aclient.validate_job(args.job)

        if args.wait:
            try:
                stat = aclient.wait_for_job(args.job)
            except KeyboardInterrupt:
                print
                sys.exit()
            if 'FAIL' in stat:
                print 'Job failed: ', stat
                sys.exit()
        else:
            aclient.check_job(args.job)


        if args.report:
            try:
                report = aclient.get_job_report(args.job)
            except Exception as e:
                sys.exit("Error retrieving job report: {}".format(e))
            if report: print report

        elif args.log:
            try:
                joblog = aclient.get_job_log(args.job)
            except Exception as e:
                sys.exit("Error retrieving job log: {}".format(e))
            if joblog: print joblog

        elif args.pick:
            try:
                # the assembly ID can be supplied by either argument
                asm1 = args.pick if type(args.pick) is str else None
                asm2 = args.assembly if type(args.assembly) is str else None
                # pick the best assembly by default
                asm = asm1 or asm2 or 'auto'
                aclient.get_assemblies(args.job, asm, stdout=True)
            except Exception as e:
                sys.exit("Error getting assembly: {}".format(e))

        elif args.assembly:
            try:
                # download all assemblies by default
                asm = args.assembly if type(args.assembly) is str else None
                aclient.get_assemblies(args.job, asm, outdir=args.outdir)
            except Exception as e:
                sys.exit("Error downloading assembly: {}".format(e))

        else:
            try:
                aclient.get_job_data(job_id=args.job, outdir=args.outdir)
            except Exception as e:
                sys.exit("Error downloading job results: {}".format(e))

    elif args.command == 'avail':
        if args.recipe:
            try:
                recipes = json.loads(aclient.get_available_recipes())
                for r in recipes:
                    if not recipes[r]['description']: continue
                    print '[Recipe]', r
                    print ''.join(["  "+l for l in recipes[r]['description'].splitlines(True)]),
                    if args.detail:
                        print "\n  Wasp expression = "
                        print recipes[r]['recipe'],
                    print
            except Exception as e:
                sys.exit('Error getting available recipes: {}'.format(e))
            sys.exit()

        try:
            mods = json.loads(aclient.get_available_modules())
            mods = sorted(mods, key=lambda mod: mod['module'])
            
            if args.detail:
                for mod in mods:
                    keys = ('description', 'version', 'base version', 'stages', 'modules', 'limitations', 'references')
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

        except Exception as e:
            sys.exit('Error getting available modules: {}'.format(e))

    elif args.command == 'kill':
        print aclient.kill_jobs(args.job)



def cmd_login(args):
    auth_service = 'RAST' if args.rast else 'KBase'
    auth.authenticate(service=auth_service, save=True)
    sys.stderr.write('[.] Logged in\n')


def cmd_logout(args):
    auth.remove_stored_token()
    sys.stderr.write('[.] Logged out\n')


def is_valid_url(url):
    import re
    regex = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url is not None and regex.search(url)


def user_data_dir(appname, appauthor):
     return os.path.expanduser('/'.join(['~', '.config', appname]))


if __name__ == '__main__':
    main()
