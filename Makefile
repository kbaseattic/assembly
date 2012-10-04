# configurable variables
SERVICE = assembly
SERVICE_PORT = 5672
SERVICE_EXEC = arastd.py

#standalone variables, replaced when run via /kb/dev_container/Makefile
TARGET ?= /kb/deployment
DEPLOY_RUNTIME ?= /kb/runtime

CLIENT_DIR = $(TARGET)/bin
MODULE_DIR = /kb/dev_container/modules/assembly
LIB_PYTHON = $(MODULE_DIR)/lib/python2.7/site-packages
CLIENT_EXE = $(CLIENT_DIR)/arast

#do not make changes below this line
TOP_DIR = ../..
include $(TOP_DIR)/tools/Makefile.common
PID_FILE = $(SERVICE_DIR)/service.pid
ACCESS_LOG_FILE = $(SERVICE_DIR)/log/access.log
ERR_LOG_FILE = $(SERVICE_DIR)/log/error.log

all:

deploy: deploy-client
deploy-service: install-dep create-scripts deploy-mongo
deploy-client: deploy-dir install-client-dep install-client

redeploy-service: clean install-dep create-scripts deploy-mongo

deploy-compute: install-dep

deploy-dir:
	if [ ! -d $(LIB_PYTHON) ] ; then mkdir -p $(LIB_PYTHON) ; fi

install-dep:
	sh ./scripts/install_server_dependencies.sh

install-client-dep:
	sh ./scripts/install_client_dependencies.sh

create-scripts:
	echo '#!/bin/sh' > ./start_service
	echo "echo starting $(SERVICE) services." >> ./start_service
	echo "export PYTHONPATH=$(SERVICE_DIR)/lib/" >> ./start_service
#	echo "$(DEPLOY_RUNTIME)/bin/python $(SERVICE_DIR)/lib/$(SERVICE_EXEC) -p $(PID_FILE) -c $(SERVICE_DIR)/lib/arast.conf" >> ./start_service
	echo "python $(SERVICE_DIR)/lib/$(SERVICE_EXEC) -p $(PID_FILE) -c $(SERVICE_DIR)/lib/arast.conf" >> ./start_service
	echo "echo $(SERVICE) service is listening on port $(SERVICE_PORT).\n" >> ./start_service

	echo '#!/bin/sh' > ./stop_service
	echo "echo trying to stop $(SERVICE) services." >> ./stop_service
	echo "pid_file=$(PID_FILE)" >> ./stop_service
	echo "if [ ! -f \$$pid_file ] ; then " >> ./stop_service
	echo "\techo \"No pid file: \$$pid_file found for service $(SERVICE).\"\n\texit 1\nfi" >> ./stop_service
	echo "pid=\$$(cat \$$pid_file)\nkill \$$pid\n" >> ./stop_service

	chmod +x start_service stop_service
	mkdir -p $(SERVICE_DIR)
	mkdir -p $(SERVICE_DIR)/log
	cp -rv . $(SERVICE_DIR)/
	echo "OK ... Done deploying $(SERVICE) services."

deploy-mongo:
	mkdir -p /data/db
	sed -i "s/bind_ip = 127.0.0.1/bind_ip = 0.0.0.0/" /etc/mongodb.conf
	service mongodb restart

install-client:
	cd ar_client; env PYTHONPATH=$(LIB_PYTHON) python setup.py install --prefix $(MODULE_DIR)
	echo '#!/bin/sh' > $(CLIENT_EXE)
	echo "export PYTHONPATH=$(LIB_PYTHON)" >> $(CLIENT_EXE)
#	echo "export KB_TOP=/kb/dev_container" >> $(CLIENT_EXE)
#	echo "export KB_RUNTIME=/kb/runtime"  >> $(CLIENT_EXE)
#	echo "export PATH=/kb/runtime/bin:/kb/dev_container/bin:$PATH" >> $(CLIENT_EXE)
	echo "python /kb/dev_container/modules/assembly/bin/arast" '"\$@"' >> $(CLIENT_EXE)

	chmod a+x $(CLIENT_EXE)
# 	env PYTHONPATH=/kb/deployment/lib/python2.7/site-packages mkdir -p $PYTHONPATH; easy_install --prefix /kb/deployment ar_client-0.0.7-py2.7.egg

clean:
	rm -rfv $(SERVICE_DIR)
	rm -f start_service stop_service
	echo "OK ... Removed all deployed files."

