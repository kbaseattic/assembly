#! /bin/bash

sudo apt-get -y install cpanminus cmake

sudo cpanm install Cwd
sudo cpanm install Data::Dumper
sudo cpanm install File::Basename
sudo cpanm install File::Copy
sudo cpanm install Getopt::Long

sudo pip install pika python-daemon pymongo requests yapsy numpy biopython
