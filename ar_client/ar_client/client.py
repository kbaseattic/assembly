import json
import requests
import subprocess


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
Get status of recent jobs         GET  URL/user/USER_ID/job/status/?start=<N>&end=<N>
Get status of one job             GET  URL/user/USER_ID/job/JOB_ID/status
Download data results of job      GET  URL/user/USER_ID/job/JOB_ID/download
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

    def upload_data_shock(self, filename):
        shockres = requests.get('http://{}/shock'.format(self.url)).text
        shockurl = 'http://{}/node'.format(json.loads(shockres)['shockurl'])
        shock = Shock(shockurl, self.user, self.password)
        return shock.curl_post_file(filename)

    def submit_job(self, data):
        url = 'http://{}/user/{}/job/new'.format(self.url, self.user)
        r = requests.post(url, data=data, headers=self.headers)
        return r.text

    def get_job_status(self, job_id=None):
        if job_id:
            url = 'http://{}/user/{}/job/{}/status'.format(self.url, self.user, job_id)
        else:
            url = 'http://{}/user/{}/job/status'.format(self.url, self.user)
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

        cmd = "curl -X POST -F upload=@" + filename + cmd + " " + self.shockurl
        ret = subprocess.check_output(cmd.split())
        res = json.loads(ret)
        return res
