#! /bin/bash
sudo apt-get update
sudo apt-get -y install mongodb rabbitmq-server
sudo pip install pymongo requests cherrypy daemon lockfile rsa python-novaclient

