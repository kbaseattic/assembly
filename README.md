Assembly Services
===================

Overview
----------
Services to assemble genomes and metagenomes with user's choice of assembler. 
Currently supports single microbial genome assembly using velvet and/or kiki.
More to come...


Dependencies
----------
See scripts/install_dependencies.sh 


Deploying on KBase infrastructure
----------
* start with a fresh KBase image (last tested on v14) with security group 'assembly-rast-group'
* log in as ubuntu and get root access with 'sudo su'
* enter the following commands:

cd /kb
git clone kbase@git.kbase.us/dev_container
cd /kb/dev_container/modules
git clone kbase@git.kbase.us/assembly
cd /kb/dev_container
./bootstrap /kb/runtime
source user-env.sh
make deploy


Starting/Stopping the service
---------------------------
* the assembly service includes one control server and at least one computer server
* for now, we assume a long-running computer server, and use 'service' to refer to the control server
* to start and stop the service, use the 'start_service' and 'stop_service' scripts in /kb/deployment/services/assemly
* on test machines, assembly services listen on port 5672, so this port must be open
* after starting the service, the process id of the serivice is stored in the 'service.pid' file in /kb/deployment/services/assembly/








