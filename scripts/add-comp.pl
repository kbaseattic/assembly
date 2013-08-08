#! /usr/bin/env perl

# This script can be run from any directory

use strict;
use Carp;
use Cwd;
use Data::Dumper;
use File::Basename;
use Getopt::Long;

my $usage =<<"End_of_Usage";

Usage: sudo add-comp.pl [ options ] components

Options:
      -d dest_dir  - destination directory (D = assembly/bin/)
      -t tmp_dir   - temporary directory (D = /mnt/tmp)

Compute server components:
      basic        - basic dependencies (apt-get, pip, cpan, etc)
      all          - all components

      a5           - A5 pipeline (v.20120518)
      a6           - Modified A5 pipeline (git)
      ale          - ALE reference-free assembler evaluator (git)
      bowtie       - Bowtie aligner (v2.1)
      bwa          - BWA aligner (git)
      discovar     - Discovar assembler (FTP latest)
      fastx        - FastX preprocessing toolkit (v0.0.13)
      gam_ngs      - GAM-NGS assembler merger (git)
      idba         - IDBA_UD assembler (v1.1.0)
      kiki         - Kiki assembler (git)
      masurca      - MaSuRCA assembler (v2.0.0)
      quast        - QUAST assembly evaluator (v2.2)
      reapr        - REAPR reference-free evaluator (v1.0.15)
      screed       - Screed assembly statistics library (git)
      seqtk        - Modified Seqtk preprocessing toolkit (git)
      solexa       - SolexaQA preprocessing tool (v2.1)
      spades       - SPAdes assembler (v2.5)
      velvet       - Velvet assembler (git)

Examples:
      sudo add-comp.pl basic velvet spades
      sudo add-comp.pl -t /space/tmp -d /usr/bin all

End_of_Usage

my ($help, $dest_dir, $tmp_dir);

GetOptions( 'd|dest=s' => \$dest_dir,
            't|tmp=s'  => \$tmp_dir,
            'h|help'   => \$help);

if ($help) { print $usage; exit 0 }

my @all_comps = qw (basic a5 a6 ale bowtie bwa discovar fastx gam_ngs idba kiki masurca quast reapr screed seqtk solexa spades velvet); 
my %supported = map { $_ => 1 } @all_comps;
my @comps = @ARGV; @comps = @all_comps if join(' ', @comps) =~ /\ball\b/;

my $curr_dir = cwd();
my $base_dir = dirname(Cwd::abs_path($0));
$dest_dir  ||= "$base_dir/../bin";
$tmp_dir     = make_tmp_dir($tmp_dir);

for my $c (@comps) {
    if (!$supported{$c}) { print "Warning: $c not supported.\n"; next; }
    my $found = check_if_installed($c);
    if ($found) { print "Found component $c, skipping...\n"; next; }

    print "Installing $c...\n";
    my $func = "install_$c";    
    
    chdir($tmp_dir);
    { no strict 'refs'; &$func(); }
    chdir($curr_dir);
    print "\n";
}


# Core dependencies

# TODO: python: fallback: strip path prefix and check exe in path

sub install_template {
    # we are in the $tmp_dir 
    # 1. download source files
    # 2. compile
    # 3. copy executables to $dest_dir
}

sub install_basic {
    my @apt = qw(python-nova build-essential python-pip rabbitmq-server git mongodb cmake zlib1g-dev mpich2 samtools openjdk-7-jre subversion python-matplotlib unzip r-base unp cpanminus picard-tools gcc-4.7 g++-4.7 graphviz csh pkg-config sparsehash libboost-all-dev gawk);
    my @pip = qw(pika python-daemon pymongo requests yapsy numpy biopython);

    # run("apt-get -q -y update");
    for (@apt) { run("apt-get -y install $_") }
    for (@pip) { run("pip install $_") }
}

sub install_a5 {
    run("mkdir -p a5");
    chdir("a5");
    my $dir = "ngopt_a5pipeline_linux-x64_20120518";
    my $file = "$dir.tar.gz";
    download($dir, $file, "http://ngopt.googlecode.com/files");
    run("cp -r -T $dir $dest_dir/a5")
}

sub install_a6 {
    git("git://github.com/levinas/a5.git", "a6");
    run("cp -r a6 $dest_dir/");
}

sub install_ale {
    my $dir = 'ale';
    git("git://github.com/sc932/ALE.git");
    run("mkdir -p $dest_dir/$dir");
    run("cd ALE/src; make ALE; cp -r ALE samtools-0.1.19 *.sh *.py synthReadGen readFileSplitter $dest_dir/$dir/");
}

sub install_bowtie {
    my $file = "bowtie2-2.1.0-linux-x86_64.zip";
    my $dir = "bowtie2-2.1.0";
    # there is no bowtie plugin; so we need this extra check
    if (-e "$dest_dir/$dir/bowtie2") {
        print "Found component bowtie, skipping...\n"; 
        return;
    }
    download($dir, $file, "http://sourceforge.net/projects/bowtie-bio/files/bowtie2/2.1.0");
    run("cp -r -T $dir $dest_dir/bowtie");
}

sub install_bwa {
    git("git://github.com/lh3/bwa.git");
    run("cd bwa; make; cp bwa $dest_dir/");
}

sub install_discovar {
    check_gcc();
    my $file = "LATEST_VERSION.tar.gz";
    my $dir = "discovar";
    download($dir, $file, 'ftp://ftp.broadinstitute.org/pub/crd/Discovar/latest_source_code');
    run("mv discovar-* $dir");
    run("cd $dir; ./configure; make; cp src/Discovar $dest_dir/discovar");
}

sub install_fastx {
    my $dir = 'fastx_toolkit';
    # there is no bowtie plugin; so we need this extra check
    if (-e "$dest_dir/$dir/fastx_trimmer") {
        print "Found component fastx, skipping...\n"; 
        return;
    }
    run("mkdir -p $dir");
    chdir($dir);
    download('bin', 'fastx_toolkit_0.0.13_binaries_Linux_2.6_amd64.tar.bz2', 'http://hannonlab.cshl.edu/fastx_toolkit');
    run("cp -r -T bin $dest_dir/$dir");
}

sub install_gam_ngs {
    my $dir = 'gam-ngs';
    git('git://github.com/vice87/gam-ngs.git');
    run("cd $dir; mkdir -p build; cd build; cmake ..; make");
    run("cp -r $dir $dest_dir/");
}

sub install_idba {
    my $dir = 'idba-1.1.0';
    my $file = "$dir.tar.gz";
    download($dir, $file, 'http://hku-idba.googlecode.com/files');
    run("cd $dir; ./configure; make");
    run("cp -r -T $dir/bin $dest_dir/idba");
}

sub install_kiki {
    git('git://github.com/GeneAssembly/kiki.git');
    chdir("kiki");
    run("mkdir -p bin; cd bin; cmake ..; make ki");
    run("cp bin/ki $dest_dir/");
}

sub install_masurca {
    my $dir = 'MaSuRCA-2.0.0';
    my $file = "$dir.tar.gz";
    download($dir, $file, 'ftp://ftp.genome.umd.edu/pub/MaSuRCA');
    run("cd $dir; ./install.sh");
    run("cp -r -T $dir $dest_dir/masurca");
}

sub install_quast {
    my $dir = 'quast-2.2';
    my $file = "$dir.tar.gz";
    download($dir, $file, "https://downloads.sourceforge.net/project/quast");
    run("cp -r -T $dir $dest_dir/quast");
}

sub install_reapr {
    my $dir = 'Reapr_1.0.15';
    my $file = "$dir.tar.gz";
    download($dir, $file, "ftp://ftp.sanger.ac.uk/pub4/resources/software/reapr");
    run("cd $dir; ./install.sh");
    run("cp -r -T $dir $dest_dir/reapr");
}

sub install_screed {
    # screed is a python library; check if it exists
    my $info = `pydoc screed`;
    if ($info =~ m|screed/__init__\.py|) {
        print "Found component screed, skipping...\n"; 
        return;
    }
    git('git://github.com/ged-lab/screed.git');
    run("cd screed; python setup.py install");
}

sub install_seqtk {
    # seqtk is not a plugin; need to check if it exists
    if (-e "$dest_dir/seqtk") {
        print "Found component seqtk, skipping...\n"; 
        return;
    }
    git('git://github.com/levinas/seqtk.git');
    run("cd seqtk; make");
    run("cp -r seqtk/seqtk $dest_dir/");
}

sub install_solexa {
    # solexa is not a plugin; need to check if it exists
    my @exes = qw(DynamicTrim.pl LengthSort.pl SolexaQA.pl);
    my $found = 1;
    for (@exes) { $found = 0 unless -e "$dest_dir/solexa/$_"; }
    if ($found) {
        print "Found component seqtk, skipping...\n"; 
        return;
    }
    my $dir = 'SolexaQA_v.2.1';
    my $file = "$dir.zip";
    run("rm -rf __MACOSX");
    download($dir, $file, "http://sourceforge.net/projects/solexaqa/files/src");
    run("rm -rf __MACOSX");
    run("chmod 755 -f $dir");
    run("chmod +x $dir/*.pl");
    run("mkdir -p $dest_dir/solexa");
    run("cp $dir/*.pl $dest_dir/solexa/");
}

sub install_spades {
    my $dir = 'SPAdes-2.5.0';
    my $file = "$dir.tar.gz";
    download($dir, $file, 'http://spades.bioinf.spbau.ru/release2.5.0');
    chdir($dir);
    run("PREFIX=$tmp_dir/$dir/install ./spades_compile.sh");
    run("chmod 755 install/bin/spades.py");
    run("cp -r -T install $dest_dir/spades");
}

sub install_velvet {
    git("git://github.com/dzerbino/velvet.git");
    chdir("velvet");
    run("rm -f obj/*.o");
    run("make 'CATEGORIES=9' 'MAXKMERLENGTH=99' 'LONGSEQUENCES=1' 'OPENMP=1' zlib velveth velvetg");
    run("cp velveth $dest_dir/");
    run("cp velvetg $dest_dir/");
}

sub check_gcc {
    my $info = `gcc --version |head -1`;
    my ($version) = $info =~ /(4[0-9.]+)/;
    if ($version < 4.7) {
        run("add-apt-repository -y ppa:ubuntu-toolchain-r/test");
        # run("apt-get -q -y update");
        run("apt-get -y install gcc-4.7 g++-4.7");
        run("rm /usr/bin/gcc /usr/bin/g++");
        run("ln -s /usr/bin/gcc-4.7 /usr/bin/gcc");
        run("ln -s /usr/bin/g++-4.7 /usr/bin/g++");
    }
}

# Helper routines

sub check_if_installed {
    my ($c) = @_;
    my $dir = "$base_dir/../lib/ar_server/plugins";
    my $yapsy = "$dir/$c.yapsy-plugin";
    
    return 0 unless -s $yapsy;
    my $found = 1;
    open(F, "<$yapsy") or die "Could not open plugin file $yapsy";
    while (<F>) {
        if (/^(executable|bin_\S+|\S+_bin) = (\S+)/) {
            my $exe = "$base_dir/../lib/ar_server/$2";
            if (! -e $exe) { $found = 0; last; }
        }
    }
    close(F);
    return $found;
}

sub git {
    my ($url, $repo) = @_;
    if (!$repo) { $repo = $url; $repo =~ s|.*/||; $repo =~ s|\.git$||; }
    
    if (-d "$repo") {
        run("cd $repo; git pull");
    } else {
        run("git clone $url $repo");
    }
}

sub download {
    my ($dir, $file, $url) = @_;
    $dir && $file && $url or die "Subroutine download needs three paramters: dir, file, url";
    run("rm -rf $file $dir");
    print("wget $url/$file\n");
    run("wget $url/$file");
    if ($file =~ /\.zip$/) {
        run("unzip $file");
    } elsif ($file =~ /(\.tar\.gz|\.tgz|\.tar\.bz2)$/) {
        run("tar xf $file");
    } elsif ($file =~ /\.gz$/) {
        run("gunzip $file");
    }
}

sub make_tmp_dir {
    my ($dir) = @_;
    $dir ||= "/mnt/tmp";
    run("mkdir -p $dir");
    return $dir;
}

sub run { system(@_) == 0 or confess("FAILED: ". join(" ", @_)); }

