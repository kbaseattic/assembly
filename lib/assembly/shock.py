
""" Module for shock """
import errno
import json
import logging
import os
import StringIO
import requests
import subprocess
import sys
import time
import tempfile

import utils

class Error(Exception):
    """Base class for exceptions in this module"""
    pass


# def download(url, node_id, outdir):
#     logging.info("Downloading id: %s" % node_id)
#     u = url
#     u += "/node/%s" % node_id
#     print u
#     r = get(u)
#     print r
#     print r.text
#     res = json.loads(r.text)
#     filename = res['data']['file']['name']
#     durl = url + "/node/%s?download" % node_id
#     utils.verify_dir(outdir)
#     dfile = outdir + filename
#     print dfile
#     r = get(durl)
#     with open(dfile, "wb") as code:
#         code.write(r.content)
#     logging.info("File downloaded: %s" % dfile)
#     print "File downloaded: %s" % dfile
#     return dfile

# def post(url, files, user, password):
# 	r = None
# 	if user and password:
#             r = requests.post(url, auth=(user, password), files=files)
# 	else:
#             r = requests.post(url, files=files)

#         res = json.loads(r.text)
#         logging.info(r.text)
# 	return res


# def get(url, user='assembly', password='service1234'):

#     r = None
#     r = requests.get(url, auth=(user, password), timeout=20)

#     return r


# def curl_download_file(url, node_id, token, outdir=None):
#     cmd = ['curl',
#            '-X', 'GET', '{}/node/{}'.format(url, node_id)]
#     r = subprocess.check_output(cmd)
#     filename = json.loads(r)['data']['file']['name']
#     if outdir:
#         utils.verify_dir(outdir)
#     else:
#         outdir = os.getcwd()
#     d_url = '{}/node/{}?download'.format(url, node_id)
#     cmd = ['curl', '-k',
#            '-o', filename, d_url]
#     p = subprocess.Popen(cmd, cwd=outdir)
#     p.wait()
#     print "File downloaded: {}/{}".format(outdir, filename)
#     return os.path.join(outdir, filename)

# def parse_handle(sn_handle):
#     handle_parts = sn_handle.split('.')
#     if handle_parts[-1] == 'shock': # Is shock file
#         shockfile = open(sn_handle)
#         shockinfo = json.loads(shockfile.read())
#         try:
#             shock_id = shockinfo['id']
#             shock_url = shockinfo['url']
#             return shock_url, shock_id
#         except AttributeError:
#             return False
#     return False


def verify_shock_url(url):
    return utils.verify_url(url, 7445)


class Shock:
    def __init__(self, shockurl, user, token):
        self.shockurl = shockurl
        self.posturl = '{}/node/'.format(shockurl)
        self.user = user
        self.token = token
        self.attrs = {'user': user}
        self.headers = {'Authorization': 'OAuth {}'.format(token)}
        self.auth_checked = False
        self.auth = True

    def check_anonymous_post_allowed(self):
        cmd = ['curl', '-s', '-k', '-X', 'POST', self.posturl]
        r = subprocess.check_output(' '.join(cmd), shell=True)
        res = json.loads(r)
        status = res.get("status", 0)
        self.auth = False if status == 200 else True
        self.auth_checked = True
        return self.auth

    def upload_file(self, filename, filetype, curl=False, auth=False):
        if not self.auth_checked:
            self.check_anonymous_post_allowed()
        auth = auth or self.auth
        print >> sys.stderr, "upload: filename={}, filetype={}, curl={}, auth={}".format(filename, filetype, curl, auth)
        if curl:
            res = self._curl_post_file(filename, filetype, auth)
        else:
            res = self._post_file(filename, filetype, auth)

        print res
        try:
            if res['status'] == 200:
                print >> sys.stderr, "Upload complete: {}".format(filename)
            else:
                raise Error("Upload failed: {}. {}".format(res['status'], res.get("error")))
        except AttributeError:
            raise Error("Upload error, shock reponse = {}".format(res))

        return res

    def upload_reads(self, filename, curl=False, auth=False):
        return self.upload_file(filename, filetype='reads', curl=curl, auth=auth)

    def upload_contigs(self, filename, curl=False, auth=False):
        return self.upload_file(filename, filetype='contigs', curl=curl, auth=auth)

    def upload_results(self, filename, curl=False, auth=False):
        return self.upload_file(filename, filetype='results', curl=curl, auth=auth)

    def curl_download_file(self, node_id, outdir=None):
        ## Authenticated download
        cmd = ['curl', '-k',
               '-X', 'GET', '{}/node/{}'.format(self.shockurl, node_id)]

        cmd += ['-H', '"Authorization: OAuth {}"'.format(self.token)]
        # for k,v in self.headers.items():
            # cmd += ['-H', '"{}: OAuth {}"'.format(k,v)]

        r = subprocess.check_output(' '.join(cmd), shell=True)
        try:
            filename = json.loads(r)['data']['file']['name']
        except:
            raise Error('Data transfer error: {}'.format(r))
        if outdir:
            utils.verify_dir(outdir)
        else:
            outdir = os.getcwd()
        d_url = '{}/node/{}?download'.format(self.shockurl, node_id)

        cmd = ['curl', '-k',
               '-o', filename, d_url]

        cmd += ['-H', '"Authorization: OAuth {}"'.format(self.token)]

        # for k,v in self.headers.items():
            # cmd += ['-H', '"{}: OAuth {}"'.format(k,v)]

        p = subprocess.Popen(' '.join(cmd), cwd=outdir, shell=True)
        p.wait()

        downloaded = os.path.join(outdir, filename)
        if os.path.exists(downloaded):
            print "File downloaded: {}".format(downloaded)
            return downloaded
        else:
            raise Error('Data does not exist')

    # def download_file(self, node_id, outdir=None):
    #     r = requests.get('{}/node/{}'.format(self.shockurl, node_id))
    #     filename = json.loads(r.content)['data']['file']['name'].split('/')[-1]
    #     if outdir:
    #         utils.verify_dir(outdir)
    #     else:
    #         outdir = os.getcwd()

    #     d_url = '{}/node/{}?download'.format(self.shockurl, node_id)
    #     downloaded = os.path.join(outdir, filename)
    #     r = requests.get(d_url, stream=True)
    #     with open(downloaded, 'wb') as f:
    #         for chunk in r.iter_content(chunk_size=1024):
    #             if chunk: # filter out keep-alive new chunks
    #                 f.write(chunk)
    #                 f.flush()

    #     if os.path.exists(downloaded):
    #         print "File downloaded: {}".format(downloaded)
    #         return downloaded
    #     else:
    #         raise Error('Data does not exist')





    ######## Internal Methods ##############
    def _create_attr_mem(self, attrs):
        """ Create in mem filehandle """
        return StringIO.StringIO(json.dumps(attrs))

    def _create_attr_file(self, attrs, outname):
        """ Writes to attr OUTFILE from dict of attrs """
        f = tempfile.NamedTemporaryFile(delete=False)
        outjson = f.name
        f.write(json.dumps(attrs))
        f.close()
        return outjson

    def _post_file(self, filename, filetype='', auth=False):
        """ Upload using requests """
        tmp_attr = dict(self.attrs)
        tmp_attr['filetype'] = filetype
        attr_fd = self._create_attr_mem(tmp_attr)
        r = None
        files = None
        try:
            with open(filename) as f:
                files = {'upload': f,
                         'attributes': attr_fd}
                if auth:
                    r = requests.post(self.posturl, files=files, headers=self.headers)
                else:
                    r = requests.post(self.posturl, files=files)

        except requests.exceptions.RequestException as e:
            raise Error("python-requests error: {}. Try with --curl flag.".format(e))

        attr_fd.close()
        res = json.loads(r.text)

	return res

    def _curl_post_file(self, filename, filetype='', auth=False):
        tmp_attr = dict(self.attrs)
        tmp_attr['filetype'] = filetype
        attr_file = self._create_attr_file(tmp_attr, 'attrs')
        cmd = ['curl',
               '-X', 'POST',
               '-F', 'attributes=@{}'.format(attr_file),
               '-F', 'upload=@{}'.format(filename),
               '{}/node/'.format(self.shockurl)]

        if auth:
            cmd += ['-H', '"Authorization: OAuth {}"'.format(self.token)]

        # print >> sys.stderr, "curl_post_file: {}".format(' '.join(cmd))
        r = subprocess.check_output(' '.join(cmd), shell=True)
        res = json.loads(r)
        return res
