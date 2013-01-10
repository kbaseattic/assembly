#! /bin/bash
sudo apt-get update
sudo apt-get -y install python-nova build-essential python-pip rabbitmq-server git mongodb cmake zlib1g-dev mpich2 samtools openjdk-7-jre subversion
sudo pip install pika
sudo pip install python-daemon
sudo pip install pymongo
sudo pip install requests
sudo pip install --upgrade python-novaclient

# Install Velvet
pushd /tmp/
sudo git clone git://github.com/dzerbino/velvet.git
cd velvet
sudo make 'CATEGORIES=9' 'MAXKMERLENGTH=99' 'LONGSEQUENCES=1' 'OPENMP=1'
sudo cp velveth /usr/bin
sudo cp velvetg /usr/bin

# Install Kiki
cd ..
sudo git clone git://github.com/GeneAssembly/kiki.git
cd kiki
sudo mkdir bin
cd bin
sudo cmake ..
sudo make ki
cp ki /usr/bin

# Install BWA
cd ..
sudo git clone git://github.com/lh3/bwa.git bwa
cd bwa
sudo make
sudo cp bwa /usr/bin

# Install A5
cd ..
mkdir a5
cd a5
wget http://ngopt.googlecode.com/files/ngopt_a5pipeline_linux-x64_20120518.tar.gz
tar -xvf ngopt*
cd ngopt*
cp -R bin/ ../../../bin/a5/
cd ../..
rm -rf a5/

# Install IDBA toolkit
mkdir idba
cd idba
wget http://hku-idba.googlecode.com/files/idba-1.1.0.tar.gz
tar -xf idba*
cd idba*
./configure
make
cd bin
rm *.o
rm Make*
cd ..
cp -R bin/ ../../../bin/idba/
cd ../..
rm -rf idba

sudo mkdir /mnt/data
sudo chown ubuntu:ubuntu /mnt/data

cd ..
sudo git clone kbase@git.kbase.us:assembly.git
cd assembly/lib/


