#
# Wrap a python script for execution in the development runtime environment.
#

if [ $# -ne 2 ] ; then
    echo "Usage: $0 source dest" 1>&2 
    exit 1
fi

src=$1
dst=$2

cat > $dst <<EOF
#!/bin/sh
export KB_TOP=$KB_TOP
export KB_RUNTIME=$KB_RUNTIME
export KB_PYTHON_PATH=$KB_PYTHON_PATH
export PATH=$KB_RUNTIME/bin:$KB_TOP/bin:\$PATH
export PYTHONPATH=$KB_PYTHON_PATH:\$PYTHONPATH
python $src "\$@"
EOF

chmod +x $dst