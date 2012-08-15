#! /bin/bash

echo "Installing dependencies..."
sudo apt-get -y update
#sudo apt-get -y upgrade
sudo apt-get -y install python-nova build-essential python-pip rabbitmq-server git mongodb
sudo pip install pika
sudo pip install python-daemon
sudo pip install pymongo
sudo pip install requests
sudo pip install --upgrade python-novaclient

