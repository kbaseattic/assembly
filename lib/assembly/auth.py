
import base64
import datetime
import errno
import getpass
import httplib2
import json
import os

import ConfigParser
from ConfigParser import SafeConfigParser

import config as conf


NEXUS_URL="https://nexus.api.globusonline.org/goauth/token?grant_type=client_credentials"
RAST_URL="http://rast.nmpdr.org/goauth/token?grant_type=client_credentials"

USER_DIR = os.path.expanduser('/'.join(['~', '.config', conf.APPNAME]))
OAUTH_FILE = os.path.join(USER_DIR, conf.OAUTH_FILENAME)
OAUTH_EXP_DAYS = conf.OAUTH_EXP_DAYS or 10


class Error(Exception):
    """Base class for exceptions in this module"""
    pass


def get_service_auth_url(service):
    return {'KBase': NEXUS_URL,
            'RAST': RAST_URL
            }.get(service)


def authenticate(service='KBase', save=True):
    print("Please authenticate with {} credentials".format(service))
    username = raw_input("{} Login: ".format(service))
    password = getpass.getpass(prompt="{} Password: ".format(service))

    success = False
    for attempt in range(2):
        try:
            token_map = get_token_map(username, password, service)
            token = token_map['access_token']
            success = True
            break
        except Error as e:
            password = getpass.getpass(prompt="{} Password: ".format(service))
            error = e
        except AttributeError as e:
            raise Error(e)

    if not success: raise error

    # ARAST server on P3 is configured with RAST-only shock
    # if service == 'RAST':
        # username = '{}_rast'.format(username)

    if save:
        try:
            os.makedirs(USER_DIR)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        try:
            parse = SafeConfigParser()
            parse.add_section('auth')
            parse.set('auth', 'user', username)
            parse.set('auth', 'token', token)
            parse.set('auth', 'token_date', str(datetime.date.today()))
            parse.write(open(OAUTH_FILE, 'wb'))
        except ConfigParser.Error as e:
            raise Error(e)

    return username, token


def get_token_map(username, password, service='KBase'):
    h = httplib2.Http(disable_ssl_certificate_validation=True)

    auth = base64.encodestring(username + ':' + password)
    headers = {'Authorization' : 'Basic ' + auth}

    h.add_credentials(username, password)
    h.follow_all_redirects = True
    url = get_service_auth_url(service)

    resp, content = h.request(url, 'GET', headers=headers)
    status = int(resp['status'])
    if status>=200 and status<=299:
        globus_map = json.loads(content)
    elif status == 403:
        raise Error('Bad username/password combination')
    else:
        raise Error(str(resp))

    return globus_map


def verify_token(user, token):
    if not user or not token:
        user, token = get_stored_token()
    return user, token


def get_stored_token():
    """Retrieve unexpired (user, token) combination stored in user config file"""
    try:
        parser = SafeConfigParser()
        parser.read(OAUTH_FILE)
        user = parser.get('auth', 'user')
        token = parser.get('auth', 'token')
        token_date_str = parser.get('auth', 'token_date')
    except ConfigParser.Error as e:
        return None, None

    if user and token and token_date_str:
        date1 = datetime.datetime.strptime(token_date_str, '%Y-%m-%d').date()
        date2 = datetime.date.today()
        if (date2 - date1).days > OAUTH_EXP_DAYS:
            user, token = None, None

    return user, token


def remove_stored_token():
    try:
        os.remove(OAUTH_FILE)
    except OSError:
        pass
