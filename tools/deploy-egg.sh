#! /bin/sh

mkdir egg
mkdir egg/assembly
cp setup.py egg
cp ../lib/assembly/auth_token.py egg/assembly/
cp ../lib/assembly/asmtypes.py egg/assembly/
cp ../lib/assembly/client.py egg/assembly/
cp ../lib/assembly/kbase.py egg/assembly/
cp ../lib/assembly/shock.py egg/assembly/
cp ../lib/assembly/__init__.py egg/assembly/

cp ../client/config.py egg/assembly/
cp ../client/arast.py egg/assembly
cd egg
python setup.py bdist_egg