
ARAST_TOP=${VAR_DIR:-/home/ubuntu/arast.p3}

export ARAST_URL=http://tutorial.theseed.org/assembly
export ARAST_CONFIG=$ARAST_TOP/mnt/assembly/lib/assembly/arast.p3.conf
# export ARAST_QUEUE=

export ARAST_LIB_DIR=$ARAST_TOP/mnt/assembly/lib
export ARAST_MODULE_DIR=$ARAST_TOP/mnt/assembly/module_bin
export ARAST_BIN_DIR=$ARAST_TOP/mnt/third_party
export ARAST_VAR_DIR=$ARAST_TOP/deployment/var
export ARAST_DATA_DIR=/mnt/ramdisk
export ARAST_WORKER_THREADS=8

