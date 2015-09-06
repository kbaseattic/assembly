import collections
import contextlib
import datetime
import errno
import json
import os
import re
import requests
import subprocess
import sys
import tarfile
import time
import traceback
from prettytable import PrettyTable

import asmtypes
import utils
from kbase import typespec_to_assembly_data as kb_to_asm
from shock import Shock

""" Assembly Service client library. """


class Client:
    def __init__(self, url, user, token):
        self.url = utils.verify_url(url)
        self.user = user
        self.token = token
        self.headers = {'Authorization': '{}'.format(self.token),
                        'Content-type': 'application/json',
                        'Accept': 'text/plain'}
        self.shock = None

    def init_shock(self):
        if self.shock is None:
            shockres = self.req_get('{}/shock'.format(self.url))
            self.shockurl = utils.verify_url(json.loads(shockres)['shockurl'])
            self.shock = Shock(self.shockurl, self.user, self.token)

    def upload_data_shock(self, filename, curl=False):
        self.init_shock()
        res = self.shock.upload_reads(filename, curl=curl)
        shock_info = {'filename': os.path.basename(filename),
                                  'filesize': os.path.getsize(filename),
                                  'shock_url': self.shockurl,
                                  'shock_id': res['data']['id'],
                                  'upload_time': str(datetime.datetime.utcnow())}
        return res, shock_info

    def upload_data_file_info(self, filename, curl=False):
        """ Returns FileInfo Object """
        self.init_shock()
        res = self.shock.upload_reads(filename, curl=curl)
        return asmtypes.FileInfo(filename, shock_url=self.shockurl, shock_id=res['data']['id'],
                                 create_time=str(datetime.datetime.utcnow()))

    def submit_job(self, data):
        url = '{}/user/{}/job/new'.format(self.url, self.user)
        return self.req_post(url, data=data)

    def submit_data(self, data):
        url = '{}/user/{}/data/new'.format(self.url, self.user)
        return self.req_post(url, data=data)

    def get_job_status(self, stat_n, job_id=None, detail=False):
        if job_id:
            url = '{}/user/{}/job/{}/status'.format(self.url, self.user, job_id)
        else:
            if detail:
                url = '{}/user/{}/job/status?records={}&detail=True'.format(
                    self.url, self.user, stat_n)
            else:
                url = '{}/user/{}/job/status?records={}'.format(
                    self.url, self.user, stat_n)
        return self.req_get(url)

    def get_data_list(self):
        url = '{}/user/{}/data'.format(self.url, self.user)
        li = json.loads(self.req_get(url))
        li.sort(key=lambda e: e["data_id"])
        return li

    def get_data_list_table(self, stat_n=10):
        li = self.get_data_list()
        li = li[-stat_n:]
        rows = []
        for data in li:
            data_id = data.get("data_id", "")
            message = data.get("message")
            if 'kbase_assembly_input' in data:
                message = data['kbase_assembly_input'].get(
                    'dataset_description')
            data_rows = assembly_data_to_rows(data)
            data_rows = [ [''] * 2 + r for r in data_rows]
            rows += [[data_id, message] + [''] * 2]
            rows += data_rows
        pt = PrettyTable(["Data ID", "Description", "Type", "Files"]);
        for r in rows: pt.add_row(r)
        return pt.get_string()

    def get_data_json(self, data_id):
        url = '{}/user/{}/data/{}'.format(self.url, self.user, data_id)
        return self.req_get(url)

    def is_job_valid(self, job_id):
        stat = self.get_job_status(1, job_id)
        return False if stat.startswith("Could not get job status") else True

    def is_job_done(self, job_id):
        stat = self.get_job_status(1, job_id)
        match = re.search('(complete|fail|terminated)', stat, re.IGNORECASE)
        return True if match else False

    def validate_job(self, job_id):
        if not self.is_job_valid(job_id):
            sys.exit("Invalid job ID: {}".format(job_id))
        return

    def wait_for_job(self, job_id, interval=30):
        self.validate_job(job_id)
        try:
            interval = int(interval)
        except ValueError:
            interval = 30
        if interval < 2:
            interval = 2
        while not self.is_job_done(job_id):
            time.sleep(interval)
        return self.get_job_status(1, job_id)

    def check_job(self, job_id):
        if not self.is_job_done(job_id):
            sys.stderr.write("Job in progress. Use -w to wait for the job.\n")
            sys.exit()

    def get_job_report(self, job_id):
        """Get the stats section of job report"""
        url = '{}/user/{}/job/{}/report'.format(self.url, self.user, job_id)
        return self.req_get(url)

    def get_job_log(self, job_id):
        """Get the log section of job report"""
        url = '{}/user/{}/job/{}/log'.format(self.url, self.user, job_id)
        return self.req_get(url)

    def get_job_report_full(self, job_id, stdout=False, outdir=None):
        url = '{}/user/{}/job/{}/report_handle'.format(self.url, self.user, job_id)
        handle = json.loads(self.req_get(url))
        self.download_shock_handle(handle, stdout=stdout, outdir=outdir)

    def get_assemblies(self, job_id, asm=None, stdout=False, outdir=None):
        """ Assembly ID cases: None => all, 'auto' => best, numerical/string => label"""
        if not asm: asm = ''
        url = '{}/user/{}/job/{}/assemblies/{}'.format(self.url, self.user, job_id, asm)
        handles = json.loads(self.req_get(url))
        if asm and not handles:
            # result-not-found exception handled by router
            raise Error('Invalid assembly ID: ' + asm)
        for h in handles:
            self.download_shock_handle(h, stdout, outdir, prefix=job_id+'_')
        return

    def get_job_analysis_tarball(self, job_id, outdir=None, remove=True):
        """Download and extract quast tarball"""
        url = '{}/user/{}/job/{}/analysis'.format(self.url, self.user, job_id)
        handle = json.loads(self.req_get(url))
        filename = self.download_shock_handle(handle, outdir=outdir)
        dirname = filename.split('/')[-1].split('.')[0]
        destpath = os.path.join(outdir, dirname) if outdir else dirname
        tar = tarfile.open(filename)
        tar.extractall(path=destpath)
        tar.close()
        sys.stderr.write("HTML extracted:  {}/report.html\n".format(destpath))
        if remove: os.remove(filename)
        return '{}/report.html\n'.format(destpath)

    def get_job_data(self, job_id, outdir=None):
        self.get_assemblies(job_id, outdir=outdir)
        self.get_job_report_full(job_id, outdir=outdir)
        self.get_job_analysis_tarball(job_id, outdir=outdir)

    def get_available_modules(self):
        url = '{}/module/all/avail/'.format(self.url)
        return self.req_get(url)

    def get_available_recipes(self):
        url = '{}/recipe/all/avail/'.format(self.url)
        return self.req_get(url)

    def kill_jobs(self, job_id=None):
        if job_id:
            url = '{}/user/{}/job/{}/kill'.format(self.url, self.user, job_id)
        else:
            url = '{}/user/{}/job/all/kill'.format(self.url, self.user)
        return self.req_get(url)

    def get_config(self):
        return self.req_get('{}/admin/system/config'.format(self.url))

    def req(self, url, req_type='get', data=None, ret=None):
        """Authenticated request. Parses CherryPy message and raises HTTPError"""
        try:
            if req_type == 'get':
                r = requests.get(url, headers=self.headers)
            elif req_type == 'post':
                r = requests.post(url, data=data, headers=self.headers)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(e)
        if r.status_code != requests.codes.ok:
            cherry = re.compile("^HTTPError: \(\d+, '(.*?)'", re.MULTILINE)
            match = cherry.search(r.content)
            msg = match.group(1) if match else r.reason
            raise HTTPError("{} (HTTP status code {})".format(msg, r.status_code))
        return {'text': r.text, 'json': r.json}.get(ret, r.content)

    def req_get(self, url, ret=None):
        return self.req(url, req_type='get', ret=ret)

    def req_post(self, url, data=None, ret=None):
        return self.req(url, req_type='post', data=data, ret=ret)

    @contextlib.contextmanager
    def smart_open(self, filename=None):
        if filename and filename != '-':
            fh = open(filename, 'w')
        else:
            fh = sys.stdout
        try:
            yield fh
        finally:
            if fh is not sys.stdout:
                fh.close()

    def download_shock_handle(self, handle, stdout=False, outdir=None, prefix=''):
        shock_url = handle.get('shock_url') or handle.get('url')
        shock_id  = handle.get('shock_id')  or handle.get('id')
        if not shock_url or not shock_id:
            raise Error("Invalid shock handle: {}".format(handle))
        url = "{}/node/{}?download".format(shock_url, shock_id)
        if stdout:
            filename = None
        else:
            outdir = utils.verify_dir(outdir) if outdir else None
            filename = handle.get('filename') or handle.get('local_file') or shock_id
            filename = prefix + filename.split('/')[-1]
            filename = os.path.join(outdir, filename) if outdir else filename
        headers = {'Authorization': 'OAuth {}'.format(self.token)}
        r = requests.get(url, stream=True, headers=headers)
        with self.smart_open(filename) as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
        if filename:
            if not os.path.exists(filename):
                raise Error('Data exists but file not properly saved')
            else:
                sys.stderr.write("File downloaded: {}\n".format(filename))
                return filename


class AssemblyData(dict):
    """Class for handling ARAST json specs"""
    def __init__(self, *args):
        self['file_sets'] = []
        dict.__init__(self, *args)

    def add_set(self, file_set):
        self['file_sets'].append(file_set)


class Error(Exception):
    """Base class for exceptions in this module"""
    pass


class URLError(Error, ValueError):
    pass


class HTTPError(Error):
    pass


class ConnectionError(Error):
    pass


def assembly_data_to_rows(data):
    """Converts assembly data dictionary to text rows"""
    rows = []
    data_key  = "assembly_data"
    kbase_key = "kbase_assembly_input"
    lib_key   = "file_sets"
    info_key  = "file_infos"

    if data_key in data:
        data = data[data_key]
    else:
        if kbase_key in data: data = kb_to_asm(data[kbase_key])

    for lib in data.get(lib_key, []):
        libtype = lib.get("type", "unknown")
        files = []
        for info in lib.get(info_key, []):
            filename = info.get("filename", None)
            if not filename:
                filename = info.get("direct_url", "")
                filename = re.sub(r'.*/', '', filename)
            filesize = info.get("filesize", None)
            filesize = " (%s)" % sizeof_fmt(filesize) if filesize else ""
            files.append("%s%s" % (filename, filesize))
        rows.append([libtype, " ".join(files)])

    return rows


def print_recipes(recipes, detail=False):
    for name, rec in recipes.items():
        desc = rec['description']
        if not desc: continue
        print '[Recipe]', name
        print ''.join(["  "+line for line in desc.splitlines(True)]),
        if detail:
            print "\n  Wasp expression = "
            print rec['recipe'],
        print


def print_modules(modules, detail=False):
    if detail:
        for mod in modules:
            keys = ('description', 'version', 'base version', 'stages',
                    'modules', 'limitations', 'references')
            version = mod.get('version', 0)
            if version >= '1.0':
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
        for mod in modules:
            version = mod.get('version', 0)
            if version >= '1.0':
                print '{module:16} {stages:35} {description}'.format(**mod)


def sizeof_fmt(num):
    """Human-readable file size"""
    for x in ['bytes','KB','MB','GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')


def dump(var):
    from pprint import pprint
    pprint (vars(var))
