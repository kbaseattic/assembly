#! /bin/bash
sudo apt-get update
sudo apt-get -y install python-nova build-essential python-pip rabbitmq-server git mongodb 
sudo pip install pika
sudo pip install python-daemon
sudo pip install pymongo
sudo pip install requests
sudo pip install cherrypy
sudo pip install --upgrade python-novaclient

