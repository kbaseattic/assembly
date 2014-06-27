import os
from setuptools import setup, find_packages

# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "ar_client",
    version = "0.4.0.0",
    author = "Chris Bun",
    author_email = "chrisbun@gmail.com",
    description = ("A commandline client for the KBASE Assembly Service"),
    url = "http://www.kbase.us/services/assembly",
    packages = find_packages(),
    install_requires = ['requests>=2.1.0', 'appdirs', 'httplib2'],
    entry_points={'console_scripts':[
            'arast = assembly.arast:main']},
)
