
""" Module for shock """
import logging
import requests
import json
import os

def download(url, node_id, outdir):
    logging.info("Downloading id: %s" % node_id)
    u = url
    u += "/node/%s" % node_id
    r = get(u)
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


def get(url, user='cbun', password='1234'):
    
    r = None
    if user and password:
        r = requests.get(url, auth=(user, password), timeout=20)       
    else:
        r = requests.get(url, timeout=20)
    return r
