import os
from setuptools import setup

# Utility function to read the README file.
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "arast",
    version = "0.0.1",
    author = "Chris Bun",
    author_email = "chrisbun@gmail.com",
    description = ("The control daemon for the Assembly Service")
    license = "BSD",
    url = "http://www.kbase.us/services/assembly",
    packages=['arast', 'tests'],
    long_description=read('README.md'),
)
