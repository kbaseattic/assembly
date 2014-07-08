Assembly Service
===================

Overview
----------
This is a service to assemble genomes and metagenomes with user's choice of assembly
software.
It currently supports more than 20 assemblers and processing modules.

[REST API](REST_API.md)

Deploying only the client
----------

Toolchain:
- make
- git

Interpreters:
- Python 2.7.x (with SSL support)
- Perl 5

Python packages (with pip):
- appdirs
- argparse
- httplib2
- pkg_resources
- prettytable
- requests
- setuptools
- ssl (built in)

Perl modules (with CPAN http://perl.about.com/od/packagesmodules/qt/perlcpan.htm):
- Config/Simple.pm
- DateTime.pm
- JSON.pm
- HTTP/Request.pm
- LWP/UserAgent.pm
- Term/ReadKey.pm
- Text/Table.pm

```
git clone https://github.com/kbase/assembly.git
cd assembly
make -f Makefile.standalone
```

Deploying and Testing AssemblyRAST client on KBase infrastructure
----------
* start with a fresh KBase image (last tested on v15) with security group 'default' or 'assembly-rast-group'
* log in as ubuntu and get root access with 'sudo su'
* enter the following commands:

```bash
cd /kb
git clone ssh://kbase@git.kbase.us/dev_container
cd /kb/dev_container
./bootstrap /kb/runtime
source user-env.sh
cd /kb/dev_container/modules
git clone ssh://kbase@git.kbase.us/assembly
git fetch origin
git checkout RC
make deploy
make test
```


Deploying AssemblyRAST server on KBase infrastructure
----------
* start with a fresh KBase image (last tested on v14) with security group 'assembly-rast-group'
* log in as ubuntu and get root access with 'sudo su'
* enter the following commands:

```bash
cd /kb
git clone ssh://kbase@git.kbase.us/dev_container
cd /kb/dev_container/modules
git clone ssh://kbase@git.kbase.us/assembly
cd /kb/dev_container
./bootstrap /kb/runtime
source user-env.sh
make deploy-service
```


Dependencies
----------
The current deployment first invokes scripts/install_dependencies.sh.
This will be no longer necessary once a kbase image is built with these dependencies.



Starting/Stopping the service
---------------------------
* the assembly service includes one control server and at least one compute server
* for now, we assume a long-running compute server, and use 'service' to refer to the control server
* to start and stop the service, use the 'start_service' and 'stop_service' scripts in /kb/deployment/services/assemly
* on test machines, assembly service listen on port 5672, so this port must be open
* after starting the service, the process id of the service is stored in the 'service.pid' file in /kb/deployment/services/assembly/



TODO
---------------------------
* Client deployment
* Testing
* Support for more assemblers
* Support for large eukaryotic genome assembly
* Support for metagenome assembly on supercomputer
