import shlex
import os
from setuptools import setup, find_packages
from subprocess import check_output
from assembly import __version__

CLIENT_VERSION = __version__
GIT_HEAD_REV = check_output(shlex.split('git rev-parse --short HEAD')).strip()
STABLE_VERSION = False

if STABLE_VERSION:
    tag_build = "stable"
else:
    tag_build = "dev_" + GIT_HEAD_REV

# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "ar_client",
    version = CLIENT_VERSION,
    author = "Chris Bun",
    author_email = "chrisbun@gmail.com",
    description = ("A commandline client for the KBASE Assembly Service"),
    url = "http://www.kbase.us/services/assembly",
    options = dict(egg_info = dict(tag_build = tag_build)),
    packages = find_packages(),
    install_requires = ['requests>=2.1.0', 'httplib2', 'appdirs', 'prettytable'],
    entry_points={'console_scripts':[
            'arast = assembly.arast:main']},
)
