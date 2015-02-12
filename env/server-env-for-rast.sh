source /vol/kbase/deployment/user-env.sh
export PATH=/disks/mpich/bin:$PATH
export LD_LIBRARY_PATH=/disks/gcc/gcc-4.7.4/lib64:/disks/gcc/gcc-4.7.4/lib:$LD_LIBRARY_PATH

export ARAST_URL=http://tutorial.theseed.org/assembly
export ARAST_SHOCK_URL=http://p3.theseed.org/services/shock_api
export ARAST_CONFIG=/disks/arast/assembly/lib/assembly/arast.p3.conf
export ARAST_QUEUE=

export ARAST_LIB_DIR=/disks/arast/assembly/lib
export ARAST_VAR_DIR=/disks/arast/deployment/var
export ARAST_BIN_DIR=/disks/arast/third_party
export ARAST_DATA_DIR=/disks/arast/data
export ARAST_WORKER_THREADS=6
