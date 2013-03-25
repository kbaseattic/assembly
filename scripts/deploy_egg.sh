#! /bin/sh

mkdir egg
cp setup.py egg
cp -R ../lib/ar_client egg
cp arast.py egg/ar_client
cd egg
python setup.py bdist_egg