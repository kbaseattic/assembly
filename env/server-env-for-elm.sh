
# export KB_TOP="/disks/p3c/deployment"
export KB_RUNTIME="/disks/patric-common/runtime"
export KB_PERL_PATH="/disks/p3c/deployment/lib"
export PERL5LIB=$KB_PERL_PATH:$KB_PERL_PATH/perl5
export PYTHONPATH="$KB_PERL_PATH:$PYTHONPATH"
export R_LIBS="$KB_PERL_PATH:$KB_R_PATH"
export JAVA_HOME="$KB_RUNTIME/java"
export CATALINA_HOME="$KB_RUNTIME/tomcat"
# export PATH="$JAVA_HOME/bin:$KB_TOP/bin:$KB_RUNTIME/bin:$PATH"
export PATH="$JAVA_HOME/bin:$KB_RUNTIME/bin:$PATH"

# source /vol/kbase/deployment/user-env.sh


export PATH=/disks/mpich/bin:$PATH
export LD_LIBRARY_PATH=/disks/gcc/gcc-4.7.4/lib64:/disks/gcc/gcc-4.7.4/lib:$LD_LIBRARY_PATH


export ARAST_URL=http://tutorial.theseed.org/assembly
export ARAST_SHOCK_URL=http://p3.theseed.org/services/shock_api
export ARAST_CONFIG=/disks/arast/assembly/lib/assembly/arast.p3.conf
# export ARAST_QUEUE=

export ARAST_LIB_DIR=/disks/arast/assembly/lib
export ARAST_MODULE_DIR=/disks/arast/assembly/module_bin
export ARAST_BIN_DIR=/disks/arast/third_party
export ARAST_VAR_DIR=/disks/arast/deployment/var
export ARAST_DATA_DIR=/disks/arast/data
export ARAST_WORKER_THREADS=6



