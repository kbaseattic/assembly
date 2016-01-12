import errno
import json
import os
import re

class Error(Exception):
    """Base class for exceptions in this module"""
    pass


class URLError(Error, ValueError):
    pass


def verify_url(url, port=8000):
    """Returns complete URL with http prefix and port number
    """
    pattern = re.compile(
        r'^(https?://)?'   # capture 1: http prefix
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'      # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'       # optional port
        r'(/?|[/?]\S+)$',  # capture 2: trailing args
        re.IGNORECASE)
    match = pattern.search(url)
    if not match:
        raise URLError(url)
    if not match.group(1):
        url = 'http://' + url
    if not match.group(2) and url.count(':') < 2 and port:
        url += ":{}".format(port)
    return url


def test_verify_url():
    """unittest: py.test client.py -v"""
    assert verify_url('localhost') == 'http://localhost:8000'
    assert verify_url('140.221.84.203') == 'http://140.221.84.203:8000'
    assert verify_url('kbase.us/services/assembly') == 'http://kbase.us/services/assembly'
    assert verify_url('http://kbase.us/services/assembly') == 'http://kbase.us/services/assembly'
    assert verify_url('https://kbase.us/services/assembly') == 'https://kbase.us/services/assembly'
    try:
        import pytest
        with pytest.raises(URLError):
            verify_url('badURL')
            verify_url('badURL/with/path:8000')
            verify_url('http://very bad url.com')
            verify_url('')
    except ImportError:
        pass


def verify_dir(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    return path


def load_json_from_file(json_file):
    try:
        with open(json_file) as f: js = f.read()
        doc = json.loads(js)
    except (IOError, ValueError) as e:
        raise Error(e)
    return doc


def is_non_zero_file(fpath):
    return True if os.path.isfile(fpath) and os.path.getsize(fpath) > 0 else False


def parse_user_from_token(token):
    user = None
    if token:
        match = re.match('^un=([^|]*)', token)
        if match:
            user = match.group(1)
    return user
