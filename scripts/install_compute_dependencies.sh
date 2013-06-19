#! /bin/bash
sudo apt-get update
sudo apt-get -y install python-nova build-essential python-pip rabbitmq-server git mongodb cmake zlib1g-dev mpich2 samtools openjdk-7-jre subversion python-matplotlib unzip r-base unp cpanminus picard-tools csh
sudo pip install pika
sudo pip install python-daemon
sudo pip install pymongo
sudo pip install requests
sudo pip install yapsy
sudo pip install numpy
sudo pip install biopython
#sudo pip install --upgrade python-novaclient

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
cd ../..
sudo git clone git://github.com/lh3/bwa.git bwa
cd bwa
sudo make
sudo cp bwa ../../bin/

# Install A5
cd ../..
mkdir a5
cd a5
wget http://ngopt.googlecode.com/files/ngopt_a5pipeline_linux-x64_20120518.tar.gz
tar -xvf ngopt*
cd ngopt*
cp -R bin/* ../../../bin/a5/
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

#Install QUAST
mkdir ../bin/quast
wget https://downloads.sourceforge.net/project/quast/quast-2.1.tar.gz
tar -xf quast-2.1.tar.gz
cd quast-2.1/
cp -R * ../../bin/quast
cd ..

#Install SolexaQA
mkdir solexa
mkdir ../bin/solexa
cd solexa
wget http://sourceforge.net/projects/solexaqa/files/src/SolexaQA_v.2.1.zip
unzip SolexaQA_v.2.1.zip
cd SolexaQA_v.2.1/
cp * ../../../bin/solexa
chmod +x ../../../bin/solexa/DynamicTrim.pl
chmod +x ../../../bin/solexa/LengthSort.pl
cd ../..
rm -rf solexa

#Install Spades
cd ../bin
wget http://spades.bioinf.spbau.ru/release2.4.0/SPAdes-2.4.0.tar.gz
tar -xvf SPAdes-2.4.0.tar.gz
cd SPAdes-2.4.0/
sh spades_compile.sh
cd ..
mv SPAdes-2.4.0/ ../bin/
rm SPAdes-2.4.0.tar.gz
cd ../scripts

#Install REAPR
mkdir ../bin/Reapr
wget ftp://ftp.sanger.ac.uk/pub4/resources/software/reapr/Reapr_1.0.15.tar.gz
tar -xvf Reapr_1.0.15.tar.gz
mv Reapr_1.0.15/* ../bin/Reapr
cd ../bin/Reapr/
sudo sh install.sh
cd ../../scripts

sudo cpanm install File::Basename
sudo cpanm install File::Copy
sudo cpanm install File::Spec
sudo cpanm install File::Spec::Link
sudo cpanm install Getopt::Long
sudo cpanm install List::Util
wget ftp://ftp.sanger.ac.uk/pub4/resources/software/smalt/smalt-0.7.4.tgz
tar -xvf smalt-0.7.4.tgz
cd smalt-0.7.4
mv smalt_x86_64 ../../bin/Reapr/src/smalt

#Install Screed
git clone git://github.com/ged-lab/screed.git
cd screed
python setup.py install
cd ..

#Install seqtk
#git clone https://github.com/lh3/seqtk.git
#cd seqtk
#make
#cp seqtk ../../bin/
#cd ..
#rm -rf seqtk


#cd ../bin/
#wget http://standardized-velvet-assembly-report.googlecode.com/svn/trunk/mergePairs.py
#chmod +x mergePairs.py



sudo mkdir /mnt/data
sudo chown ubuntu:ubuntu /mnt/data

#cd ..
#sudo git clone kbase@git.kbase.us:assembly.git
#cd assembly/lib/


