
""" Module for shock """
import errno
import json
import logging
import os
import re
import requests
from requests_toolbelt import MultipartEncoder
import copy
import StringIO
import subprocess
import sys
import time
import tempfile

import utils


logger = logging.getLogger(__name__)


def verify_shock_url(url):
    return utils.verify_url(url, 7445)


def handle_to_url(handle):
    shock_url = handle.get('shock_url') or handle.get('url')
    shock_id  = handle.get('shock_id')  or handle.get('id')
    if not shock_url or not shock_id:
        raise Error("Invalid shock handle: {}".format(handle))
    return '{}/node/{}?download'.format(shock_url, shock_id)


def token_to_req_headers(token):
    headers = {'Authorization': 'OAuth {}'.format(token)} if token else None
    return headers


def get_handle(handle, token=None, ret=None):
    url = handle_to_url(handle)
    headers = token_to_req_headers(token)
    try:
        r = requests.get(url, headers=headers)
    except requests.exceptions.ConnectionError as e:
        raise Error("requests.get error: {}".format(e))
    if r.status_code != requests.codes.ok:
        raise Error("requests.get failed: {}: {}".format(r.status_code, r.reason))
    return {'text': r.text, 'json': r.json}.get(ret, r.content)


def curl_download_url(url, outdir=None, filename=None, token=None, silent=False):
    if outdir:
        try: os.makedirs(outdir)
        except OSError: pass
    else:
        outdir = os.getcwd()

    if not filename:
        filename = os.path.basename(url)
        filename = re.sub(r'\?download', '', filename)
        filename = re.sub(r'[?&]', '_', filename)

    cmd = ['curl', '-k', '-X', 'GET',
           '-o', filename, '"{}"'.format(url) ]

    if silent:
        cmd += ['-s']
    if token:
        cmd += ['-H', '"Authorization: OAuth {}"'.format(token)]

    sys.stderr.write("Downloading: {}\n".format(' '.join(cmd)))
    logger.debug("curl_download_url: {}".format(' '.join(cmd)))
    p = subprocess.Popen(' '.join(cmd), cwd=outdir, shell=True)
    p.wait()
    sys.stderr.write("\n")

    downloaded = os.path.join(outdir, filename)
    if os.path.exists(downloaded):
        logger.info('File downloaded: {}'.format(downloaded))
        return downloaded
    else:
        raise Error('Data does not exist')


class Error(Exception):
    """Base class for exceptions in this module"""
    pass


class Shock:
    def __init__(self, shockurl, user, token):

        self._validate_endpoint(shockurl)
        self.shockurl = shockurl

        self.posturl = '{}/node/'.format(shockurl)
        self.user = user
        self.token = token
        self.attrs = {'user': user}
        self.headers = token_to_req_headers(token)
        self.auth_checked = False
        self.auth = True

    def _validate_endpoint(self, url):
        """
        Make sure that the endpoint is online.
        Otherwise, the endpoint will need to be started.
        """
        try:
            request = requests.get(url)

        except Exception, e:
            print("Error, service {} is not available.".format(url))

            # propagate the exception
            raise e

    def check_anonymous_post_allowed(self):
        cmd = ['curl', '-s', '-k', '-X', 'POST', self.posturl]
        r = subprocess.check_output(' '.join(cmd), shell=True)
        res = json.loads(r)
        status = res.get("status", 0)
        self.auth = False if status == 200 else True
        self.auth_checked = True
        return self.auth

    def upload_file(self, filename, filetype, curl=False, auth=False, silent=False):
        if not self.auth_checked:
            self.check_anonymous_post_allowed()
        auth = auth or self.auth

        if curl:
            res = self._curl_post_file(filename, filetype, auth, silent)
        else:
            res = self._post_file(filename, filetype, auth)

        try:
            if res['status'] == 200:
                logger.info("Upload complete: {}".format(filename))
            else:
                raise Error("Upload failed: {}. {}".format(res['status'], res.get("error")))
        except AttributeError:
            raise Error("Upload error, shock reponse = {}".format(res))

        return res

    def upload_reads(self, filename, curl=False, auth=False):
        return self.upload_file(filename, filetype='reads', curl=curl, auth=auth, silent=False)

    def upload_contigs(self, filename, curl=False, auth=False):
        return self.upload_file(filename, filetype='contigs', curl=curl, auth=auth)

    def upload_results(self, filename, curl=False, auth=False):
        return self.upload_file(filename, filetype='results', curl=curl, auth=auth)

    def curl_download_file(self, node_id, outdir=None):
        ## Authenticated download
        cmd = ['curl', '-k',
               '-X', 'GET', '{}/node/{}'.format(self.shockurl, node_id)]

        cmd += ['-H', '"Authorization: OAuth {}"'.format(self.token)]

        r = subprocess.check_output(' '.join(cmd), shell=True)
        try:
            filename = json.loads(r)['data']['file']['name']
        except:
            raise Error('Data transfer error: {}'.format(r))

        d_url = '{}/node/{}?download'.format(self.shockurl, node_id)
        return curl_download_url(d_url, outdir, filename, self.token)


    # see implementation in client.download_shock_handle
    #
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

        try:
            with open(filename) as f:

                multipart_data = MultipartEncoder(fields = {
                        'attributes': ('attributes', attr_fd),
                        'upload': (filename, f)
                        })

                content_type = {'Content-Type': multipart_data.content_type}
                my_headers = copy.deepcopy(self.headers)
                my_headers.update(content_type)

                if auth:
                    r = requests.post(self.posturl, data=multipart_data, headers=my_headers)
                else:
                    r = requests.post(self.posturl, data=multipart_data, headers=content_type)

        except requests.exceptions.RequestException as e:
            raise Error("python-requests error: {}. Try with --curl flag.".format(e))

        attr_fd.close()
        res = json.loads(r.text)

	return res

    def _curl_post_file(self, filename, filetype='', auth=False, silent=False):
        tmp_attr = dict(self.attrs)
        tmp_attr['filetype'] = filetype
        attr_file = self._create_attr_file(tmp_attr, 'attrs')
        cmd = ['curl',
               '-X', 'POST',
               '-F', 'attributes=@{}'.format(attr_file),
               '-F', 'upload=@{}'.format(filename),
               '{}/node/'.format(self.shockurl)]

        if silent:
            cmd += ['-s']
        if auth:
            cmd += ['-H', '"Authorization: OAuth {}"'.format(self.token)]

        sys.stderr.write("Uploading: {}\n".format(' '.join(cmd)))
        logger.debug("curl_post_file: {}".format(' '.join(cmd)))
        r = subprocess.check_output(' '.join(cmd), shell=True)
        sys.stderr.write("\n")

        res = json.loads(r)
        return res
