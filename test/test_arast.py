#!/usr/bin/env python

# export PYTHONPATH=$(pwd)/../deployment/lib:$PYTHONPATH
import os

import parser
import logging

def include(filename):
    if os.path.exists(filename): 
        execfile(filename)

__name__ = '__main__'

include("../deployment/pybin/arast.py")


