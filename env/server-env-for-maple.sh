
# export KB_TOP="/disks/p3c/deployment"
export KB_RUNTIME="/disks/patric-common/runtime"
# export KB_PERL_PATH="/disks/p3c/deployment/lib"
# export PERL5LIB=$KB_PERL_PATH:$KB_PERL_PATH/perl5
# export PYTHONPATH="$KB_PERL_PATH:$PYTHONPATH"
# export R_LIBS="$KB_PERL_PATH:$KB_R_PATH"
export JAVA_HOME="$KB_RUNTIME/java"
export CATALINA_HOME="$KB_RUNTIME/tomcat"
# export PATH="$JAVA_HOME/bin:$KB_TOP/bin:$KB_RUNTIME/bin:$PATH"
export PATH="$JAVA_HOME/bin:$KB_RUNTIME/bin:$PATH"

# source /vol/kbase/deployment/user-env.sh

export AR_TOP=/disks/arast

export RUNTIME=$AR_TOP/runtime
export CMAKE_ROOT=$RUNTIME/share/cmake
export PATH=$RUNTIME/bin/:$RUNTIME/mpich/bin:$RUNTIME/gcc/gcc-4.7.4/bin:$PATH
export LD_LIBRARY_PATH=$RUNTIME/lib64:$RUNTIME/gcc/gcc-4.7.4/lib64:$RUNTIME/gcc/gcc-4.7.4/lib:$LD_LIBRARY_PATH


export ARAST_URL=140.221.78.16
export ARAST_SHOCK_URL=http://p3.theseed.org/services/shock_api
export ARAST_CONFIG=$AR_TOP/assembly/lib/assembly/arast.maple.conf
# export ARAST_QUEUE=

export ARAST_LIB_DIR=$AR_TOP/assembly/lib
export ARAST_MODULE_DIR=$AR_TOP/assembly/module_bin
export ARAST_BIN_DIR=$AR_TOP/third_party
export ARAST_VAR_DIR=$AR_TOP/deployment/var
export ARAST_DATA_DIR=$AR_TOP/data
export ARAST_WORKER_THREADS=8
