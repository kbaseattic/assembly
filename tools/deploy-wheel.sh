#! /bin/sh

mkdir wheel
mkdir wheel/assembly
cp setup.py wheel
cp ../lib/assembly/auth.py wheel/assembly/
cp ../lib/assembly/asmtypes.py wheel/assembly/
cp ../lib/assembly/client.py wheel/assembly/
cp ../lib/assembly/config.py wheel/assembly/
cp ../lib/assembly/kbase.py wheel/assembly/
cp ../lib/assembly/shock.py wheel/assembly/
cp ../lib/assembly/utils.py wheel/assembly/
cp ../lib/assembly/__init__.py wheel/assembly/

cp ../client/arast.py wheel/assembly
cd wheel
python setup.py bdist_wheel --universal
