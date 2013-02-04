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
    def __init__(self, url, user, token):
        self.port = 8000 ## change
        self.url = url + ':{}'.format(self.port)
        self.user = user
        #self.password = password
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
        r = requests.get(url, headers=self.headers)
        return r.text



class Shock:
    def __init__(self, shockurl, user, token):
        self.shockurl = shockurl
        self.user = user
        self.token = token

    def curl_post_file(self, filename):
        cmd = ['curl', '-H', 'Authorization: Globus-Goauthtoken {} '.format(self.token),
               '-X', 'POST', '-F', 'upload=@{}'.format(filename),
               '{}node/'.format(self.shockurl)]

        ret = subprocess.check_output(cmd)
        res = json.loads(ret)
        return res

    def curl_download_file(self, node_id, outdir=None):
        cmd = ['curl', '-H', 'Authorization: Globus-Goauthtoken {} '.format(self.token),
               '-X', 'GET', '{}/node/{}'.format(self.shockurl, node_id)]
        r = subprocess.check_output(cmd)
        filename = json.loads(r)['D']['file']['name']
        if outdir:
            try:
                os.makedirs(outdir)
            except:
                pass
                #raise Exception('Unable to create download directory:\n{}'.format(outdir))

        else:
            outdir = os.getcwd()
        d_url = '{}/node/{}?download'.format(self.shockurl, node_id)
        cmd = ['curl', '-H', 'Authorization: Globus-Goauthtoken {} '.format(self.token),
               '-o', filename, d_url]

        p = subprocess.Popen(cmd, cwd=outdir)
        p.wait()
        print "File downloaded: {}/{}".format(outdir, filename)
        return os.path.join(outdir, filename)
