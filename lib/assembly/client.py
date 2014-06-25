import collections
import datetime
import json
import requests
import subprocess
import os
import time
import re
from kbase import typespec_to_assembly_data as kb_to_asm
from prettytable import PrettyTable

from shock import Shock

#Debug
import sys
import traceback
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

    def get_job_data(self, job_id=None, outdir=None):
        if not job_id:
            raise NotImplementedError('Job id required')
        # Get node id
        res = requests.get('http://{}/user/{}/job/{}/shock_node'.format(
                self.url, self.user, job_id), headers=self.headers)
        if res.status_code == 403:
            raise ValueError('Invalid Job Id')
        # Download files
        try:
            nodes_map = json.loads(res.text)
            for node_id in nodes_map.values():
                self.shock.download_file(node_id, outdir=outdir)
        except Exception as e:
            print e
            raise Exception("Error retrieving results")
        return 

    def get_assemblies(self, job_id=None, asm_id=None, stdout=False, outdir=None):
        if not job_id:
            raise NotImplementedError('Job id required')
        # Get node id
        res = requests.get('http://{}/user/{}/job/{}/assembly'.format(
                self.url, self.user, job_id), headers=self.headers)

        # Download files
        try:
            nodes_map = json.loads(res.text)
            if stdout: # Get first one and print
                asm_file = self.shock.download_file(nodes_map.values()[0], outdir=outdir)
                with open(asm_file) as f:
                    for line in f:
                        print line
            elif asm_id:
                ordered = collections.OrderedDict(sorted(nodes_map.items()))
                id = ordered.values()[int(asm_id)-1]
                self.shock.download_file(id , outdir=outdir)
            else:
                for node_id in nodes_map.values():
                    self.shock.download_file(node_id, outdir=outdir)
        except:
            print traceback.format_tb(sys.exc_info()[2])
            print sys.exc_info()
            raise Exception("Error retrieving results")
        return 
        
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
        return FileInfo(self.shockurl, res['data']['id'], os.path.getsize(filename),
                            os.path.basename(filename), str(datetime.datetime.utcnow()))

    def submit_job(self, data):
        url = 'http://{}/user/{}/job/new'.format(self.url, self.user)
        r = requests.post(url, data=data, headers=self.headers)
        return r.content

    def submit_data(self, data):
        url = 'http://{}/user/{}/data/new'.format(self.url, self.user)
        r = requests.post(url, data=data, headers=self.headers)
        return r.content

    def get_job_status(self, stat_n, job_id=None):
        if job_id:
            url = 'http://{}/user/{}/job/{}/status'.format(self.url, self.user, job_id)
        else:
            url = 'http://{}/user/{}/job/status?records={}'.format(
                self.url, self.user, stat_n)
        r = requests.get(url, headers=self.headers)
        return r.content

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

    def wait_for_job(self, job_id):
        stat = self.get_job_status(1, job_id)
        while not re.search('(complete|fail)', stat, re.IGNORECASE):
            time.sleep(5)
            stat = self.get_job_status(1, job_id)
        return stat

    def get_job_report(self, job_id):
        url = 'http://{}/user/{}/job/{}/report'.format(self.url, self.user, job_id)
        r = requests.get(url, headers=self.headers)
        try:
            
        return r.content

    def get_available_modules(self):
        url = 'http://{}/module/all/avail/'.format(self.url, self.user)
        r = requests.get(url, headers=self.headers)
        return r.content

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


##### ARAST JSON SPEC METHODS #####

class FileInfo(dict):
    def __init__(self, shock_url, shock_id, filesize, filename, create_time, metadata=None, *args):
        dict.__init__(self, *args)
        self.update({'shock_url': shock_url,
                     'shock_id' : shock_id,
                     'filesize': filesize,
                     'filename': filename,
                     'create_time': create_time,
                     'metadata': metadata})

class FileSet(dict):
    def __init__(self, set_type, file_infos, 
                 **kwargs):
        dict.__init__(self, **kwargs)
        self.update({'type': set_type,
                     'file_infos': []})
        if type(file_infos) is list:
            for f in file_infos:
                self['file_infos'].append(f)
        else:
            self['file_infos'] = [file_infos]

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
            filename = info.get("filename", "")
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
