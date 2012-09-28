#! /bin/bash
# This file is to be run by cloud-init when the cloud monitor launches a new instance

sudo apt-get update
sudo apt-get -y install python-nova build-essential python-pip rabbitmq-server git mongodb cmake zlib1g-dev mpich2 samtools
sudo pip install pika
sudo pip install python-daemon
sudo pip install pymongo
sudo pip install requests
sudo pip install --upgrade python-novaclient

pushd /tmp/
sudo git clone git://github.com/dzerbino/velvet.git
cd velvet
sudo make 'CATEGORIES=9' 'MAXKMERLENGTH=99' 'LONGSEQUENCES=1' 'OPENMP=1'
sudo cp velveth /usr/bin
sudo cp velvetg /usr/bin

cd ..
sudo git clone git://github.com/GeneAssembly/kiki.git
cd kiki
sudo mkdir bin
cd bin
sudo cmake ..
sudo make ki
cp ki /usr/bin

cd ..
sudo git clone git://github.com/lh3/bwa.git bwa
cd bwa
sudo make
sudo cp bwa /usr/bin

sudo mkdir /mnt/data
sudo chown ubuntu:ubuntu /mnt/data


#TODO clone assembly.git and run

