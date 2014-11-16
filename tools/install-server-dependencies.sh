#! /bin/bash
sudo apt-get update
sudo apt-get -y install mongodb rabbitmq-server python-pip
sudo pip install -U pymongo requests cherrypy daemon lockfile rsa python-novaclient prettytable

