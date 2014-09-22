#! /bin/bash

sudo apt-get -y install cpanminus cmake

sudo cpanm install Config::Simple
sudo cpanm install Cwd
sudo cpanm install Data::Dumper
sudo cpanm install DateTime
sudo cpanm install File::Basename
sudo cpanm install File::Copy
sudo cpanm install Getopt::Long
sudo cpanm install Term::ReadKey
sudo cpanm install Text::Table

sudo pip install pika python-daemon pymongo requests yapsy numpy biopython
