import json
import requests
import subprocess
import os

from shock import Shock

#Debug
import sys
import traceback
""" Assembly Service client library.

REST interface:

Resources:
* http://assembly.kbase.us/api/

** user/current
** user/USER_ID/

*** jobs/current
*** jobs/JOB_ID
**** status
**** download
**** runtime
**** data_id
**** ... other metadata

*** data/current
*** data/DATA_ID
**** files
**** files/FILE_ID(?)
***** filename
***** filesize


Admin
-----
Create user                       POST URL/users
Run job                           POST URL/user/USER_ID/job/new --data JSON_MSG
Get status of recent jobs         GET  URL/user/USER_ID/job/status?records=<>

# TODO
Get status of one job             GET  URL/user/USER_ID/job/JOB_ID/status
Get list of user's data           GET  URL/user/USER_ID/data/current/status
Get list of files for data_id     GET  URL/user/USER_ID/data/DATA_ID/status


#TODO
format from html??

"""


class Client:
    def __init__(self, url, user, token):
        self.port = 8000 ## change
        if url.find(':') == -1: # Port not included
            self.url = url + ':{}'.format(self.port)
        else:
            self.url = url
        print self.url
        self.user = user
        self.token = token
        self.headers = {'Authorization': '{}'.format(self.token),
                        'Content-type': 'application/json', 
                        'Accept': 'text/plain'}
        shockres = requests.get('http://{}/shock'.format(self.url), headers=self.headers).text
        shockurl = 'http://{}/'.format(json.loads(shockres)['shockurl'])
        self.shock = Shock(shockurl, self.user, self.token)

    def get_job_data(self, job_id=None, outdir=None):
        if not job_id:
            raise NotImplementedError('Job id required')
        # Get node id
        res = requests.get('http://{}/user/{}/job/{}/shock_node'.format(
                self.url, self.user, job_id), headers=self.headers)
        # Download files
        try:
            nodes_map = json.loads(res.text)
            for node_id in nodes_map.values():
                self.shock.download_file(node_id, outdir=outdir)
        except:
            print traceback.format_tb(sys.exc_info()[2])
            print sys.exc_info()
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
            else:
                for node_id in nodes_map.values():
                    self.shock.download_file(node_id, outdir=outdir)
        except:
            print traceback.format_tb(sys.exc_info()[2])
            print sys.exc_info()
            raise Exception("Error retrieving results")
        return 
        
    def upload_data_shock(self, filename, curl=False):
        return self.shock.upload_reads(filename, curl=curl)

    def submit_job(self, data):
        url = 'http://{}/user/{}/job/new'.format(self.url, self.user)
        r = requests.post(url, data=data, headers=self.headers)
        return r.content

    def submit_data(self, data):
        print("Registering data upload")
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
