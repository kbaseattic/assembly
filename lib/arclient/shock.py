
""" Module for shock """
import logging
import requests
import json
import os

def download(url, node_id, outdir, user=False, password=False):
    logging.info("Downloading id: %s" % node_id)
    u = url
    u += "/node/%s" % node_id
    r = get(u, user, password)
    res = json.loads(r.text)
    filename = res['D']['file']['name']
    durl = url + "/node/%s?download" % node_id
    try:
        os.makedirs(outdir)
    except:
        pass
    dfile = outdir + filename
    if user and password:
        r = get(durl, user, password)
    else:
        r = get(durl)
    with open(dfile, "wb") as code:
        code.write(r.content)
    logging.info("File downloaded: %s" % dfile)
    print "File downloaded: %s" % dfile

def post(url, files, user, password):
	r = None
	if user and password:
            r = requests.post(url, auth=(user, password), files=files)
	else:
            r = requests.post(url, files=files)

        res = json.loads(r.text)
        logging.info(r.text)
	return res


def get(url, user, password ):     
    
    r = None
    if user and password:
        r = requests.get(url, auth=(user, password), timeout=20)       
    else:
        r = requests.get(url, timeout=20)
    return r
