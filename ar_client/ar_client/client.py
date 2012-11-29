import requests
import subprocess

class Client(url, user, password):
    def __init__(self, url):
        self.url = url
        self.user = user
        self.password = password

    def upload_data(self, filename):
        curl_cmd = "curl -X GET %s/shock" % self.url
        print subprocess.check_output(curl_cmd)
        #shock = Shock(subprocess.check_output(curl_cmd), self.user, self.password)
        #return shock.curl_post_file(filename)



    def submit_job(self):
        pass

    def get_status(self):
        pass


class Shock(shockurl, user, password):
    def __init__(self, url):
        self.shockurl = shockurl
        self.user = user
        self.password = password


    def curl_post_file(self, filename):
        if self.user and self.password
            cmd = " --user " + self.user + ":" + self.password

        cmd = "curl -X POST -F upload=@" + filename + cmd + " " + self.url
        ret = subprocess.check_output(cmd.split())
        res = json.loads(ret)

        return res
