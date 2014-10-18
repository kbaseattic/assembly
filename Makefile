TOP_DIR = ../..
DEPLOY_RUNTIME ?= /kb/runtime
TARGET ?= /kb/deployment
SERVICE = assembly
SERVICE_NAME = assembly
SERVICE_DIR = $(TARGET)/services/$(SERVICE)
VAR_DIR = $(SERVICE_DIR)/var

ARAST_URL = http://kbase.us/services/assembly
ARAST_AUTH_SERVICE = KBase

include $(TOP_DIR)/tools/Makefile.common

TPAGE_ARGS = --define arast_url=$(ARAST_URL) \
	--define arast_auth_service=$(ARAST_AUTH_SERVICE)


# to wrap scripts and deploy them to $(TARGET)/bin using tools in
# the dev_container. right now, these vars are defined in
# Makefile.common, so it's redundant here.
TOOLS_DIR = $(TOP_DIR)/tools
WRAP_PERL_TOOL = wrap_perl
WRAP_PERL_SCRIPT = bash $(TOOLS_DIR)/$(WRAP_PERL_TOOL).sh
SRC_PERL = $(wildcard client/*.pl)
WRAP_PYTHON_TOOL = wrap_python
WRAP_PYTHON_SCRIPT = bash $(TOOLS_DIR)/$(WRAP_PYTHON_TOOL).sh
SRC_PYTHON = $(wildcard client/*.py)


SERVER_TESTS = $(wildcard server-tests/*.t)
CLIENT_TESTS = $(wildcard client-tests/*.t)
SCRIPT_TESTS = $(wildcard test/*.t)


CLIENT_DIR = $(TARGET)/bin
CLIENT_EXE = $(CLIENT_DIR)/arast
MODULE_DIR = $(TARGET)/modules/assembly
LIB_PYTHON = $(MODULE_DIR)/lib/python2.7/site-packages


default: build-config

# Test

test: test-core

# test: test-scripts

# test: test-client test-scripts test-service
# 	@echo "running client and script tests"

test-core:
	test/arast.t -d temp

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
# deploy: deploy-client deploy-service

# deploy-client: install-client-dep deploy-dir install-client deploy-client-scripts deploy-docs
deploy-client: install-client-dep build-config deploy-libs deploy-scripts deploy-docs

build-config:
	$(TPAGE) $(TPAGE_ARGS) config.py.tt > lib/assembly/config.py	

# deploy-libs: 
# 	rsync --exclude '*.bak*' -arv lib/. $(TARGET)/lib/.

# deploy-scripts:
# 	export KB_TOP=$(TARGET); \
# 	export KB_RUNTIME=$(DEPLOY_RUNTIME); \
# 	export KB_PERL_PATH=$(TARGET)/lib bash ; \
# 	for src in $(SRC_PERL) ; do \
# 		basefile=`basename $$src`; \
# 		base=`basename $$src .pl`; \
# 		echo install $$src $$base ; \
# 		cp $$src $(TARGET)/plbin ; \
# 		$(WRAP_PERL_SCRIPT) "$(TARGET)/plbin/$$basefile" $(TARGET)/bin/$$base ; \
# 	done; \
# 	export KB_PYTHON_PATH=$(TARGET)/lib bash ; \
# 	for src in $(SRC_PYTHON) ; do \
# 		basefile=`basename $$src`; \
# 		base=`basename $$src .py`; \
# 		echo install $$src $$base ; \
# 		cp $$src $(TARGET)/pybin ; \
# 		$(WRAP_PYTHON_SCRIPT) "$(TARGET)/pybin/$$basefile" $(TARGET)/bin/$$base ; \
# 	done

deploy-docs:
	mkdir -p $(TARGET)/services/$(SERVICE)/webroot
	cp doc/*.html $(TARGET)/services/$(SERVICE)/webroot/.
	cp doc/*.png $(TARGET)/services/$(SERVICE)/webroot/.

deploy-service: install-dep install-service-scripts deploy-mongo deploy-testworker

redeploy-service: clean install-dep create-scripts deploy-mongo
deploy-compute: install-dep

deploy-testworker:
	./tools/install-basic-dependencies.sh
	./tools/add-comp.pl kiki velvet

deploy-dir:
	if [ ! -d $(LIB_PYTHON) ] ; then mkdir -p $(LIB_PYTHON) ; fi

install-dep:
	sh ./tools/install-server-dependencies.sh

install-client-dep:
	sh ./tools/install-client-dependencies.sh

install-service-scripts:
	cp ./tools/start_service $(SERVICE_DIR)

deploy-mongo:
	mkdir -p /data/db
	sed -i "s/bind_ip = 127.0.0.1/bind_ip = 0.0.0.0/" /etc/mongodb.conf
	service mongodb restart

clean:
	rm -rfv $(SERVICE_DIR)
	rm -f start_service stop_service
	echo "OK ... Removed all deployed files."

include $(TOP_DIR)/tools/Makefile.common.rules
