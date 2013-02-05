TOP_DIR = ../..
DEPLOY_RUNTIME ?= /kb/runtime
TARGET ?= /kb/deployment

# configurable variables
SERVICE = assembly
SERVICE_NAME = assembly
SERVICE_DIR = assembly
SERVICE_PORT = 5672
SERVICE_EXEC = arastd.py

# TPAGE_ARGS = --define kb_top=$(TARGET) \
# 	--define kb_runtime=$(DEPLOY_RUNTIME) \
# 	--define kb_service_name=$(SERVICE) \
# 	--define kb_service_port=$(SERVICE_PORT) \
# 	--define kb_psgi=$(SERVICE_NAME).psgi

include $(TOP_DIR)/tools/Makefile.common

# to wrap scripts and deploy them to $(TARGET)/bin using tools in
# the dev_container. right now, these vars are defined in
# Makefile.common, so it's redundant here.
TOOLS_DIR = $(TOP_DIR)/tools
WRAP_PERL_TOOL = wrap_perl
WRAP_PERL_SCRIPT = bash $(TOOLS_DIR)/$(WRAP_PERL_TOOL).sh
SRC_PERL = $(wildcard scripts/*.pl)
WRAP_PYTHON_TOOL = wrap_python
WRAP_PYTHON_SCRIPT = bash $(TOOLS_DIR)/$(WRAP_PYTHON_TOOL).sh
SRC_PYTHON = $(wildcard scripts/*.py)


CLIENT_TESTS = $(wildcard client-tests/*.t)
SCRIPTS_TESTS = $(wildcard script-tests/*.t)
SERVER_TESTS = $(wildcard server-tests/*.t)


CLIENT_DIR = $(TARGET)/bin
CLIENT_EXE = $(CLIENT_DIR)/arast
MODULE_DIR = $(TARGET)/modules/assembly
LIB_PYTHON = $(MODULE_DIR)/lib/python2.7/site-packages


default:

# Test

test: test-sh test-scripts

# test: test-client test-scripts test-service
# 	@echo "running client and script tests"

test-sh:
	cd test && ./test_arast_client.sh

test-client:
	for t in $(CLIENT_TESTS) ; do \
		if [ -f $$t ] ; then \
			$(DEPLOY_RUNTIME)/bin/perl $$t ; \
			if [ $$? -ne 0 ] ; then \
				exit 1 ; \
			fi \
		fi \
	done


test-scripts:
	for t in $(SCRIPT_TESTS) ; do \
		if [ -f $$t ] ; then \
			$(DEPLOY_RUNTIME)/bin/perl $$t ; \
			if [ $$? -ne 0 ] ; then \
				exit 1 ; \
			fi \
		fi \
	done

test-service:
	for t in $(SERVER_TESTS) ; do \
		if [ -f $$t ] ; then \
			$(DEPLOY_RUNTIME)/bin/perl $$t ; \
			if [ $$? -ne 0 ] ; then \
				exit 1 ; \
			fi \
		fi \
	done


# Deployment

deploy: deploy-client

# deploy-client: install-client-dep deploy-dir install-client deploy-client-scripts deploy-docs
deploy-client: install-client-dep deploy-libs deploy-scripts deploy-docs

deploy-libs: 
	rsync --exclude '*.bak*' -arv lib/. $(TARGET)/lib/.

deploy-scripts:
	export KB_TOP=$(TARGET); \
	export KB_RUNTIME=$(DEPLOY_RUNTIME); \
	export KB_PERL_PATH=$(TARGET)/lib bash ; \
	for src in $(SRC_PERL) ; do \
		basefile=`basename $$src`; \
		base=`basename $$src .pl`; \
		echo install $$src $$base ; \
		cp $$src $(TARGET)/plbin ; \
		$(WRAP_PERL_SCRIPT) "$(TARGET)/plbin/$$basefile" $(TARGET)/bin/$$base ; \
	done; \
	export KB_PYTHON_PATH=$(TARGET)/lib bash ; \
	for src in $(SRC_PYTHON) ; do \
		basefile=`basename $$src`; \
		base=`basename $$src .pl`; \
		echo install $$src $$base ; \
		cp $$src $(TARGET)/pybin ; \
		$(WRAP_PYTHON_SCRIPT) "$(TARGET)/pybin/$$basefile" $(TARGET)/bin/$$base ; \
	done

deploy-docs:
	mkdir -p $(TARGET)/services/$(SERVICE)/webroot
	cp doc/*.html $(TARGET)/services/$(SERVICE)/webroot/.

deploy-service: install-dep create-scripts deploy-mongo
redeploy-service: clean install-dep create-scripts deploy-mongo
deploy-compute: install-dep

deploy-dir:
	if [ ! -d $(LIB_PYTHON) ] ; then mkdir -p $(LIB_PYTHON) ; fi

install-dep:
	sh ./scripts/install_server_dependencies.sh

install-client-dep:
	sh ./scripts/install_client_dependencies.sh

deploy-mongo:
	mkdir -p /data/db
	sed -i "s/bind_ip = 127.0.0.1/bind_ip = 0.0.0.0/" /etc/mongodb.conf
	service mongodb restart

clean:
	rm -rfv $(SERVICE_DIR)
	rm -f start_service stop_service
	echo "OK ... Removed all deployed files."

include $(TOP_DIR)/tools/Makefile.common.rules
