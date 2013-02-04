
""" Module for shock """
import logging
import requests
import json
import os
import subprocess

def download(url, node_id, outdir):
    logging.info("Downloading id: %s" % node_id)
    u = url
    u += "/node/%s" % node_id
    print u
    r = get(u)
    print r
    print r.text
    res = json.loads(r.text)
    filename = res['D']['file']['name']
    durl = url + "/node/%s?download" % node_id
    try:
        os.makedirs(outdir)
    except:
        pass
    dfile = outdir + filename
    print dfile
    r = get(durl)
    with open(dfile, "wb") as code:
        code.write(r.content)
    logging.info("File downloaded: %s" % dfile)
    print "File downloaded: %s" % dfile
    return dfile

def post(url, files, user, password):
	r = None
	if user and password:
            r = requests.post(url, auth=(user, password), files=files)
	else:
            r = requests.post(url, files=files)

        res = json.loads(r.text)
        logging.info(r.text)
	return res


def get(url, user='assembly', password='service1234'):
    
    r = None
    r = requests.get(url, auth=(user, password), timeout=20)       

    return r


def curl_download_file(url, node_id, token, outdir=None):
    cmd = ['curl', '-H', 'Authorization: Globus-Goauthtoken {} '.format(token),
           '-X', 'GET', '{}/node/{}'.format(url, node_id)]


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
    d_url = '{}/node/{}?download'.format(url, node_id)
    cmd = ['curl', '-H', 'Authorization: Globus-Goauthtoken {} '.format(token),
           '-o', filename, d_url]

    p = subprocess.Popen(cmd, cwd=outdir)
    p.wait()
    print "File downloaded: {}/{}".format(outdir, filename)
    return os.path.join(outdir, filename)

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
        print res
        return res

    def curl_download_file(self, node_id, outdir=None):
        cmd = ['curl', '-H', 'Authorization: Globus-Goauthtoken {} '.format(self.token),
               '-X', 'GET', '{}/node/{}'.format(self.shockurl, node_id)]
        r = subprocess.check_output(cmd)
        print r
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

        downloaded = os.path.join(outdir, filename)
        if os.path.exists(downloaded):
            print "File downloaded: {}".format(downloaded)
            return downloaded
        else:
            raise Exception ('Data does not exist')
