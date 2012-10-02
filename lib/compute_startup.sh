#! /bin/bash
# This file is to be run by cloud-init when the cloud monitor launches a new instance

sudo su
cd /home/ubuntu/assembly/lib/
git checkout cbun_dev
git pull origin cbun_dev


