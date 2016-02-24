#! /usr/bin/env python
"""
arast-client -- commandline client for Assembly RAST

"""

import argparse
import errno
import json
import logging
import os
import sys
import time
from ConfigParser import SafeConfigParser

from assembly import asmtypes
from assembly import auth
from assembly import client
from assembly import config as conf
from assembly import shock
from assembly import utils
from assembly import __version__


CLIENT_VERSION = __version__
CLIENT_NAME = 'CLI'

# Config precedence: command-line args > environment variables > config file

ARAST_URL = os.getenv('ARAST_URL') or conf.URL
ARAST_QUEUE = os.getenv('ARAST_QUEUE')
ARAST_AUTH_TOKEN = os.getenv('ARAST_AUTH_TOKEN') or os.getenv('KB_AUTH_TOKEN')
ARAST_AUTH_USER = os.getenv('ARAST_AUTH_USER') or os.getenv('KB_AUTH_USER_ID') or utils.parse_user_from_token(ARAST_AUTH_TOKEN)
ARAST_AUTH_SERVICE = os.getenv('ARAST_AUTH_SERVICE')

ARAST_ENVIRON = None
if os.getenv('KB_RUNNING_IN_IRIS'):
    ARAST_ENVIRON = 'IRIS'

def get_parser():
    parser = argparse.ArgumentParser(prog='arast', epilog='Use "arast command -h" for more information about a command.')

    parser.add_argument('-s', dest='arast_url', help='arast server url')
    parser.add_argument('-c', '--config', action="store", help='Specify config file')
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose")
    parser.add_argument('--version', action='version', version='AssemblyRAST Client ' + CLIENT_VERSION)

    subparsers = parser.add_subparsers(dest='command', title='The commands are')

    p_upload = subparsers.add_parser('upload', description='Upload a read set', help='Upload a read library or set of libraries, returns a data ID for future use')
    p_run = subparsers.add_parser('run', description='Run an Assembly RAST job', help='run job')
    p_stat = subparsers.add_parser('stat', description='Query status of running jobs', help='list jobs status')
    p_avail = subparsers.add_parser('avail', description='List available AssemblyRAST modules', help='list available modules or recipes')
    p_kill = subparsers.add_parser('kill', description='Send a kill signal to jobs', help='kill jobs')
    p_get = subparsers.add_parser('get', description='Get result data', help='Get data')
    p_login = subparsers.add_parser('login', description='Force log in', help='log in')
    p_logout = subparsers.add_parser('logout', description='Log out', help='log out')

    # upload options
    p_upload.add_argument("-f", action="append", dest="single", nargs='*', help="specify sequence file(s)")
    p_upload.add_argument("--pair", action="append", dest="pair", nargs='*', help="Specify a paired-end library and parameters")
    p_upload.add_argument("--pair_url", action="append", dest="pair_url", nargs='*', help="Specify URLs for a paired-end library and parameters")
    p_upload.add_argument("--single", action="append", dest="single", nargs='*', help="Specify a single end file and parameters")
    p_upload.add_argument("--single_url", action="append", dest="single_url", nargs='*', help="Specify a URL for a single end file and parameters")
    p_upload.add_argument("--reference", action="append", dest="reference", nargs='*', help="specify a reference contig file")
    p_upload.add_argument("--reference_url", action="append", dest="reference_url", nargs='*', help="Specify a URL for a reference contig file and parameters")
    p_upload.add_argument("--contigs", action="append", dest="contigs", nargs='*', help="specify a contig file")
    p_upload.add_argument("-m", "--message", action="store", dest="message", help="Attach a description to job")
    p_upload.add_argument("--curl", action="store_true", help="Use curl for http requests")
    p_upload.add_argument("--json", action="store_true", help="Print data info json object")

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
    p_run.add_argument("--contigs", action="append", dest="contigs", nargs='*', help="specify a contig file")
    p_run.add_argument("--curl", action="store_true", help="Use curl for http requests")

    data_group = p_run.add_mutually_exclusive_group()
    data_group.add_argument("--data", action="store", dest="data_id", help="Reuse uploaded data")
    data_group.add_argument("--data-json", action="store", dest="data_json", help="Reuse uploaded data from a json object")

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
    p_avail.add_argument("-d", "--detail", action="store_true", help="show module or recipe details")

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
    p_get.add_argument("-w", "--wait", action="store", nargs='?', const=True, help="Wait until job is done")

    # login options
    p_login.add_argument("--rast", action="store_true", help="Log in using RAST account")

    return parser


def cmd_login(args):
    auth_service = 'KBase'
    try:
        auth_service = conf.AUTH_SERVICE if conf.AUTH_SERVICE else auth_service
    except AttributeError:
        pass
    if ARAST_AUTH_SERVICE:
        auth_service = ARAST_AUTH_SERVICE
    auth_service = 'RAST' if args.rast else auth_service
    auth.authenticate(service=auth_service, save=True)
    sys.stderr.write('[.] Logged in\n')


def cmd_logout(args):
    auth.remove_stored_token()
    sys.stderr.write('[.] Logged out\n')


def cmd_upload(args, aclient, usage, log=None):
    data = prepare_assembly_data(args, aclient, usage)

    arast_msg = {'assembly_data': data,
                 'client': CLIENT_NAME,
                 'version': CLIENT_VERSION}

    payload = json.dumps(arast_msg, sort_keys=True)
    if log:
        log.debug(" [.] Sending upload message: %r" % (payload))

    response = aclient.submit_data(payload)
    arast_msg.update(json.loads(response))
    if args.json:
        print payload
    else:
        print 'Data ID: {}'.format(arast_msg['data_id'])


def cmd_run(args, aclient, usage, log=None):
    if args.data_id:
        data = None
    elif args.data_json:
        data = utils.load_json_from_file(args.data_json)
    else:
        data = prepare_assembly_data(args, aclient, usage)

    if args.assemblers:
        args.pipeline = [(" ".join(args.assemblers))]

    options = vars(args)
    options['client'] = CLIENT_NAME
    options['version'] = CLIENT_VERSION

    queue = args.queue or ARAST_QUEUE
    if queue: options['queue'] = queue

    keys = ['pipeline', 'recipe', 'wasp', 'message',
            'data_id', 'queue', 'version', 'client']
    arast_msg = dict((k, options[k]) for k in keys if k in options)

    if data:
        if 'file_sets' in data:        #
            arast_msg['assembly_data'] = data
        elif 'assembly_data' in data:  # from: --json data.json
            arast_msg['assembly_data'] = data['assembly_data']
        else:
            arast_msg['kbase_assembly_input'] = data

    payload = json.dumps(arast_msg, sort_keys=True)
    if log:
        log.debug(" [.] Sending run message: %r" % (payload))

    response = aclient.submit_job(payload)
    print 'Job ID: {}'.format(response)


def cmd_stat(args, aclient):
    if args.list_data:
        table = aclient.get_data_list_table(args.stat_n)
        print table
        sys.exit()

    if args.data_id:
        data_json = aclient.get_data_json(args.data_id)
        print data_json
        sys.exit()

    while True:
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


def cmd_get(args, aclient):
    aclient.validate_job(args.job)

    if args.wait:
        if type(args.wait) is str:
            stat = aclient.wait_for_job(args.job, args.wait)
        else:
            stat = aclient.wait_for_job(args.job)
        if 'FAIL' in stat:
            print 'Job failed: ', stat
            sys.exit()
    else:
        aclient.check_job(args.job)

    if args.report:
        report = aclient.get_job_report(args.job)
        if report: print report
    elif args.log:
        joblog = aclient.get_job_log(args.job)
        if joblog: print joblog
    elif args.pick:
        # the assembly ID can be supplied by either argument
        asm1 = args.pick if type(args.pick) is str else None
        asm2 = args.assembly if type(args.assembly) is str else None
        # pick the best assembly by default
        asm = asm1 or asm2 or 'auto'
        aclient.get_assemblies(args.job, asm, stdout=True)
    elif args.assembly:
        # download all assemblies by default
        asm = args.assembly if type(args.assembly) is str else None
        aclient.get_assemblies(args.job, asm, outdir=args.outdir)
    else:
        aclient.get_job_data(job_id=args.job, outdir=args.outdir)


def cmd_avail(args, aclient):
    if args.recipe:
        recipes = json.loads(aclient.get_available_recipes())
        client.print_recipes(recipes, args.detail)
    else:
        mods = json.loads(aclient.get_available_modules())
        mods = sorted(mods, key=lambda mod: mod['module'])
        client.print_modules(mods, args.detail)


def prepare_assembly_data(args, aclient, usage):
    """Parses args and uploads files
    returns data spec for submission in run/upload commands"""
    if not (args.pair or args.single or args.pair_url or args.single_url or args.contigs):
        sys.exit(usage)

    adata = client.AssemblyData()
    curl = args.curl

    res_ids = []
    files = []
    file_sizes = []
    file_list = []
    file_lists = []

    all_lists = [args.pair, args.pair_url, args.single, args.single_url,
                 args.reference, args.reference_url, args.contigs]
    all_types = ['paired', 'paired_url', 'single', 'single_url',
                 'reference', 'reference_url', 'contigs']

    for li in all_lists:
        if li is None:
            file_lists.append([])
        else:
            file_lists.append(li)

    seen = {}
    for f_list in file_lists:
        for ls in f_list:
            for word in ls:
                if '=' not in word:
                    if word in seen:
                        sys.exit('Input error: duplicated file: {}'.format(word))
                    else:
                        seen[word] = True

    for f_list, f_type in zip(file_lists, all_types):
        for ls in f_list:
            f_infos = []
            f_set_args = {}
            for word in ls:
                if '=' in word:
                    key, val = word.split('=')
                    f_set_args[key] = val
                elif os.path.isfile(word):
                    f_info = aclient.upload_data_file_info(word, curl=curl)
                    f_infos.append(f_info)
                elif f_type.endswith('_url'):
                    file_url = utils.verify_url(word)
                    f_info = asmtypes.FileInfo(direct_url=file_url)
                    f_infos.append(f_info)
                else:
                    sys.exit('Invalid input: {}: {}'.format(f_type, word))
            f_set = asmtypes.FileSet(f_type, f_infos, **f_set_args)
            adata.add_set(f_set)

    return adata


def run_command():
    parser = get_parser()
    args = parser.parse_args()
    usage = parser.format_usage()

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
        cmd_logout(args)
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
    a_url = utils.verify_url(a_url)
    logging.info('ARAST_URL: {}'.format(a_url))

    aclient = client.Client(a_url, a_user, a_token)

    if args.command == 'upload':
        cmd_upload(args, aclient, usage, clientlog)
    elif args.command == 'run':
        cmd_run(args, aclient, usage, clientlog)
    elif args.command == 'stat':
        cmd_stat(args, aclient)
    elif args.command == 'get':
        cmd_get(args, aclient)
    elif args.command == 'avail':
        cmd_avail(args, aclient)
    elif args.command == 'kill':
        print aclient.kill_jobs(args.job)


def main():
    try:
        run_command()
    except KeyboardInterrupt:
        sys.exit()
    except IOError as e:
        if e.errno != errno.EPIPE:
            raise
    except auth.Error as e:
        sys.exit('Authentication error: {}'.format(e))
    except shock.Error as e:
        sys.exit('Shock error: {}'.format(e))
    except client.URLError as e:
        sys.exit('Invalid URL: {}'.format(e))
    except client.ConnectionError as e:
        sys.exit('Connection error: {}'.format(e))
    except client.HTTPError as e:
        sys.exit('HTTP error: {}'.format(e))
    except client.Error as e:
        sys.exit('Error: {}'.format(e))
    # print stack for unexpected errors


if __name__ == '__main__':
    main()
