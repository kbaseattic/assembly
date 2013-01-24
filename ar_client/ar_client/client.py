import json
import requests
import subprocess
import os

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
    def __init__(self, url, user, password):
        self.port = 8000 ## change
        self.url = url + ':{}'.format(self.port)
        self.user = user
        self.password = password
        self.headers = {'Content-type': 'application/json', 
                        'Accept': 'text/plain'}
        shockres = requests.get('http://{}/shock'.format(self.url)).text
        shockurl = 'http://{}/'.format(json.loads(shockres)['shockurl'])
        self.shock = Shock(shockurl, self.user, self.password)

    def get_job_data(self, job_id=None, outdir=None):
        if not job_id:
            raise NotImplementedError('Job id required')
        # Get node id
        res = requests.get('http://{}/user/{}/job/{}/shock_node'.format(
                self.url, self.user, job_id))

        # Download files
        try:
            nodes_map = json.loads(res.text)
            for node_id in nodes_map.values():
                self.shock.curl_download_file(node_id)
        except:
            print traceback.format_tb(sys.exc_info()[2])
            print sys.exc_info()
            raise Exception("Error retrieving results")
        return 
        
    def upload_data_shock(self, filename):
        return self.shock.curl_post_file(filename)

    def submit_job(self, data):
        url = 'http://{}/user/{}/job/new'.format(self.url, self.user)
        r = requests.post(url, data=data, headers=self.headers)
        return r.text

    def get_job_status(self, stat_n, job_id=None):
        if job_id:
            url = 'http://{}/user/{}/job/{}/status'.format(self.url, self.user, job_id)
        else:
            url = 'http://{}/user/{}/job/status?records={}'.format(
                self.url, self.user, stat_n)
        r = requests.get(url)
        return r.text



class Shock:
    def __init__(self, shockurl, user, password):
        self.shockurl = shockurl
        self.user = user
        self.password = password


    def curl_post_file(self, filename):
        if self.user and self.password:
            cmd = " --user " + self.user + ":" + self.password
        cmd = "curl -X POST -F upload=@" + filename + cmd + " " + self.shockurl + 'node/'
        ret = subprocess.check_output(cmd.split())
        res = json.loads(ret)
        return res

    def curl_download_file(self, node_id, outdir=None):
        # Get filename
        r = requests.get('{}/node/{}'.format(self.shockurl, node_id),
                         auth=(self.user, self.password))
        filename = json.loads(r.text)['D']['file']['name']
        if outdir:
            try:
                os.makedirs(outdir)
            except:
                raise Exception('Unable to create download directory:\n{}'.format(outdir))
        else:
            outdir = os.getcwd()
        d_url = '{}/node/{}?download'.format(self.shockurl, node_id)
        p = subprocess.Popen('curl --user {}:{} -o {} {}'.format(
                self.user, self.password, filename, d_url).split())
        p.wait()
        print "File downloaded: {}/{}".format(outdir, filename)
