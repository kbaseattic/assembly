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
from kbase import typespec_to_assembly_data as kb_to_asm
from shock import Shock
from shock import get as shock_get

""" Assembly Service client library. """


class Client:
    def __init__(self, url, user, token):
        self.port = 8000 ## change
        if url.find(':') == -1: # Port not included
            self.url = url + ':{}'.format(self.port)
        else:
            self.url = url
        self.user = user
        self.token = token
        self.headers = {'Authorization': '{}'.format(self.token),
                        'Content-type': 'application/json', 
                        'Accept': 'text/plain'}
        shockres = requests.get('http://{}/shock'.format(self.url), headers=self.headers).text
        self.shockurl = 'http://{}/'.format(json.loads(shockres)['shockurl'])
        self.shock = Shock(self.shockurl, self.user, self.token)

    def upload_data_shock(self, filename, curl=False):
        res = self.shock.upload_reads(filename, curl=curl)
        shock_info = {'filename': os.path.basename(filename),
                                  'filesize': os.path.getsize(filename),
                                  'shock_url': self.shockurl,
                                  'shock_id': res['data']['id'],
                                  'upload_time': str(datetime.datetime.utcnow())}
        return res, shock_info

    def upload_data_file_info(self, filename, curl=False):
        """ Returns FileInfo Object """
        res = self.shock.upload_reads(filename, curl=curl)
        return asmtypes.FileInfo(filename, shock_url=self.shockurl, shock_id=res['data']['id'],
                                 create_time=str(datetime.datetime.utcnow()))
        # return FileInfo(self.shockurl, res['data']['id'], os.path.getsize(filename),
        #                     os.path.basename(filename), str(datetime.datetime.utcnow()))

    def submit_job(self, data):
        url = 'http://{}/user/{}/job/new'.format(self.url, self.user)
        r = requests.post(url, data=data, headers=self.headers)
        return r.content

    def submit_data(self, data):
        url = 'http://{}/user/{}/data/new'.format(self.url, self.user)
        r = requests.post(url, data=data, headers=self.headers)
        return r.content

    def get_job_status(self, stat_n, job_id=None, detail=False):
        if job_id:
            url = 'http://{}/user/{}/job/{}/status'.format(self.url, self.user, job_id)
        else:
            if detail:
                url = 'http://{}/user/{}/job/status?records={}&detail=True'.format(
                    self.url, self.user, stat_n)
            else:
                url = 'http://{}/user/{}/job/status?records={}'.format(
                    self.url, self.user, stat_n)
        status = self.req_get(url)
        return status

    def get_data_list(self):
        url = 'http://{}/user/{}/data'.format(self.url, self.user)
        r = requests.get(url, headers=self.headers)
        li = json.loads(r.content)
        li.sort(key=lambda e: e["data_id"])
        return li

    def get_data_list_table(self, stat_n=10):
        li = self.get_data_list()
        li = li[-stat_n:]
        rows = []
        for data in li:
            data_id = data.get("data_id", "")
            message = data.get("message", "")
            data_rows = assembly_data_to_rows(data)
            data_rows = [ [''] * 2 + r for r in data_rows]
            rows += [[data_id, message] + [''] * 2]
            rows += data_rows
        pt = PrettyTable(["Data ID", "Description", "Type", "Files"]);
        for r in rows: pt.add_row(r)
        return pt.get_string()

    def get_data_json(self, data_id):
        url = 'http://{}/user/{}/data/{}'.format(self.url, self.user, data_id)
        r = requests.get(url, headers=self.headers)
        return r.content

    def is_job_valid(self, job_id):
        stat = self.get_job_status(1, job_id)
        return False if stat.startswith("Could not get job status") else True

    def is_job_done(self, job_id):
        stat = self.get_job_status(1, job_id)
        match = re.search('(complete|fail)', stat, re.IGNORECASE)
        return True if match else False

    def validate_job(self, job_id):
        if not self.is_job_valid(job_id):
            sys.exit("Invalid job ID: {}".format(job_id))
        return

    def wait_for_job(self, job_id):
        self.validate_job(job_id)
        while not self.is_job_done(job_id):
            time.sleep(5)
        return self.get_job_status(1, job_id)

    def check_job(self, job_id):
        if not self.is_job_done(job_id): 
            sys.stderr.write("Job in progress. Use -w to wait for the job.\n")
            sys.exit()

    def get_job_report(self, job_id):
        """Get the stats section of job report"""
        url = 'http://{}/user/{}/job/{}/report'.format(self.url, self.user, job_id)
        return self.req_get(url)

    def get_job_log(self, job_id):
        """Get the log section of job report"""
        url = 'http://{}/user/{}/job/{}/log'.format(self.url, self.user, job_id)
        return self.req_get(url)

    def get_job_report_full(self, job_id, stdout=False, outdir=None):
        url = 'http://{}/user/{}/job/{}/report_handle'.format(self.url, self.user, job_id)
        handle = json.loads(self.req_get(url))
        self.download_shock_handle(handle, stdout=stdout, outdir=outdir)

    def get_assemblies(self, job_id, asm=None, stdout=False, outdir=None):
        """ Assembly ID cases: None => all, 'auto' => best, numerical/string => label"""
        if not asm: asm = ''
        url = 'http://{}/user/{}/job/{}/assemblies/{}'.format(self.url, self.user, job_id, asm)
        handles = json.loads(self.req_get(url))
        if len(asm) and not handles:
            # result-not-found exception handled by router
            raise ValueError('Invalid assembly ID: ' + asm)
        for h in handles:
            self.download_shock_handle(h, stdout, outdir, prefix=job_id+'_')
        return

    def get_job_analysis_tarball(self, job_id, outdir=None, remove=True):
        """Download and extract quast tarball"""
        url = 'http://{}/user/{}/job/{}/analysis'.format(self.url, self.user, job_id)
        handle = json.loads(self.req_get(url))
        filename = self.download_shock_handle(handle, outdir=outdir)
        dirname = filename.split('/')[-1].split('.')[0]
        destpath = os.path.join(outdir, dirname) if outdir else dirname
        tar = tarfile.open(filename)
        tar.extractall(path=destpath)
        tar.close()
        sys.stderr.write("HTML extracted:  {}/report.html\n".format(destpath))
        if remove: os.remove(filename)

    def get_job_data(self, job_id, outdir=None):
        self.get_assemblies(job_id, outdir=outdir)
        self.get_job_report_full(job_id, outdir=outdir)
        self.get_job_analysis_tarball(job_id, outdir=outdir)

    def get_available_modules(self):
        url = 'http://{}/module/all/avail/'.format(self.url)
        return self.req_get(url)

    def get_available_recipes(self):
        url = 'http://{}/recipe/all/avail/'.format(self.url)
        return self.req_get(url)

    def kill_jobs(self, job_id=None):
        if job_id:
            url = 'http://{}/user/{}/job/{}/kill'.format(self.url, self.user, job_id)
        else:
            url = 'http://{}/user/{}/job/all/kill'.format(
                self.url, self.user)
        r = requests.get(url, headers=self.headers)
        return r.content

    def get_config(self):
        return requests.get('http://{}/admin/system/config'.format(self.url)).content

    def req_get(self, url, ret=None):
        r = requests.get(url, headers=self.headers)

        if r.status_code != requests.codes.ok:
            cherry = re.compile("^HTTPError: \(\d+, '(.*?)'", re.MULTILINE)
            match = cherry.search(r.content)
            msg = match.group(1) if match else r.reason
            raise requests.exceptions.HTTPError("HTTPError {}: {}".format(r.status_code, msg))

        if   ret == 'text': return r.text
        elif ret == 'json': return r.json
        else:               return r.content
    
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
            raise Exception("Invalid shock handle: {}".format(handle))        
        url = "{}/node/{}?download".format(shock_url, shock_id)
        if stdout:
            filename = None
        else:
            outdir = self.verify_dir(outdir) if outdir else None 
            filename = handle.get('filename') or handle.get('local_file') or shock_id
            filename = prefix + filename.split('/')[-1]
            filename = os.path.join(outdir, filename) if outdir else filename

        r = requests.get(url, stream=True)
        with self.smart_open(filename) as f:
            for chunk in r.iter_content(chunk_size=1024): 
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
        if filename:
            if not os.path.exists(filename):
                raise Exception('Data exists but file not properly saved')
            else:
                sys.stderr.write("File downloaded: {}\n".format(filename))
                return filename

    def verify_dir(self, path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise
        return path


##### ARAST JSON SPEC CLASSES #####

class AssemblyData(dict):
    def __init__(self, *args):
        dict.__init__(self, *args)
        self['file_sets'] = []

    def add_set(self, file_set):
        self['file_sets'].append(file_set)


##### Helper methods #####

def assembly_data_to_rows(data):
    rows = []
    data_key  = "assembly_data"
    kbase_key = "kbase_assembly_input"
    lib_key   = "file_sets"
    info_key  = "file_infos"
    
    if data_key in data: data = data[data_key]
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

def sizeof_fmt(num):
    for x in ['bytes','KB','MB','GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')    

def dump(var):
    from pprint import pprint
    pprint (vars(var))
