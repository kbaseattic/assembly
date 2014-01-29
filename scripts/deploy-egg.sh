#! /bin/sh

mkdir egg
mkdir egg/ar_client
cp setup.py egg
cp ../lib/assembly/auth_token.py egg/ar_client/
cp ../lib/assembly/client.py egg/ar_client/
cp ../lib/assembly/config.py egg/ar_client/
cp ../lib/assembly/shock.py egg/ar_client/
cp ../lib/assembly/__init__.py egg/ar_client/

cp arast.py egg/ar_client
cd egg
python setup.py bdist_egg