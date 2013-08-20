#! /bin/bash

#
# Install arast in a user specified directory
#

if [ $# -ne 1 ] ; then
    echo "Usage: $0 dest_dir" 1>&2
    exit 1
fi

src=$(cd $(dirname $0); pwd)
dst=$1

if [ ! -d "$dst" ] ; then
    echo "Usage: $0 dest_dir" 1>&2
    echo "Invalid directory: $dst" 1>&2
    exit 1
fi

cat > $dst/arast <<EOF
#!/bin/sh
export PATH=$dst:\$PATH
export PYTHONPATH=$src/../lib:\$PYTHONPATH
python $src/arast.py "\$@"
EOF

chmod +x $dst/arast
