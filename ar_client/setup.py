import os
from setuptools import setup, find_packages

# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "ar_client",
    version = "0.2.1",
    author = "Chris Bun",
    author_email = "chrisbun@gmail.com",
    description = ("A commandline client for the KBASE Assembly Service"),
    url = "http://www.kbase.us/services/assembly",
    packages = find_packages(),
    install_requires = ['requests>=0.13.0', 'appdirs'],
    long_description=read('README.md'),
    entry_points={'console_scripts':[
            'arast = ar_client.ar_client:main']},
    package_data = {'':['*.conf']},
)
