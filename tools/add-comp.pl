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
      -d dest_dir  - absolute destination directory (D = /repo/third_party)
      -f           - force reinstall even if component exists
      -t tmp_dir   - temporary directory (D = /mnt/tmp)
      --dry        - dry run: check if modules exist

Compute server components:
      basic        - basic dependencies (apt-get, pip, cpan, etc)
      regular      - regular components (modules to be deployed on all compute nodes)
      special      - special components (large modules: smrt, allpathslg, etc)
      all          - all components

      a5           - A5 pipeline (v.20140604)
      a6           - Modified A5 pipeline (git)
      ale          - ALE reference-free assembler evaluator (git)
      allpathslg   - AllPaths-LG (FTP latest)
      bowtie2      - Bowtie aligner (v2.1)
      bwa          - BWA aligner (git)
      discovar     - Discovar assembler (FTP latest)
      fastqc       - FastQC quality control (v0.11.2)
      fastx        - FastX preprocessing toolkit (v0.0.13)
      gam_ngs      - GAM-NGS assembler merger (git)
      idba         - IDBA_UD assembler (v1.1.1)
      jgi_rqc      - JGI rolling QC (git)
      kiki         - Kiki assembler (git)
      kmergenie    - KmerGenie (v1.6663)
      masurca      - MaSuRCA assembler (v2.2.1)
      megahit      - MEGAHIT assembler (git)
      miniasm      - MiniASM assembler for long noisy reads (git)
      prodigal     - Prodigal Prokaryotic Gene Prediction (v2.60)
      quast        - QUAST assembly evaluator (v2.3)
      ray          - Ray assembler (git)
      reapr        - REAPR reference-free evaluator (v1.0.17)
      seqtk        - Modified Seqtk preprocessing toolkit (git)
      smrt         - SMRT Analysis Software (v2.1.1)
      solexa       - SolexaQA preprocessing tool (v2.1)
      spate        - Spate metagenome assembler (v0.4.1)
      spades       - SPAdes assembler (v3.6.2)
      velvet       - Velvet assembler (git)

Examples:
      sudo add-comp.pl basic velvet spades
      sudo add-comp.pl -t /space/tmp -d /usr/bin regular

End_of_Usage

my ($help, $dest_dir, $dry_run, $tmp_dir, $force_reinstall);

GetOptions( 'd|dest=s' => \$dest_dir,
            'dry'      => \$dry_run,
            'f|force'  => \$force_reinstall,
            't|tmp=s'  => \$tmp_dir,
            'h|help'   => \$help);

if ($help || @ARGV == 0) { print $usage; exit 0 }

my @regular_comps = qw (a5 a6 ale bowtie2 bwa fastqc fastx gam_ngs idba kiki kmergenie masurca megahit miniasm quast prodigal ray reapr seqtk solexa spades velvet);
my @special_comps = qw (allpathslg discovar jgi_rqc smrt spate);
my @extra_depends = qw (cmake3);

my @all_comps = (@regular_comps, @special_comps);
my %supported = map { $_ => 1 } (@all_comps, @extra_depends);

my @comps;
for (@ARGV) {
    if (/\ball\b/) {
        @comps = @all_comps; last;
    } elsif (/\bregular\b/) {
        @comps = (@comps, @regular_comps);
    } elsif (/\bspecial\b/) {
        @comps = (@comps, @special_comps);
    } else {
        push @comps, $_;
    }
}


my $curr_dir = cwd();
my $base_dir = dirname(Cwd::abs_path($0));
$dest_dir  ||= "$base_dir/../third_party"; run("mkdir -p $dest_dir") if !$dry_run;
$tmp_dir     = make_tmp_dir($tmp_dir) if !$dry_run;

for my $c (@comps) {
    if (!$supported{$c}) { print "Warning: $c not supported.\n"; next; }
    my $found = !$force_reinstall && check_if_installed($c);
    if ($found) { print "Found component $c, skipping...\n"; next; }

    print "Installing $c...\n";
    next if $dry_run;

    my $func = "install_$c";

    chdir($tmp_dir);
    { no strict 'refs'; &$func(); }
    chdir($curr_dir);
    print "\n";
}


# Core dependencies

# TODO: python: fallback: strip path prefix and check exe in path

sub install_template {
    # we are in the $tmp_dir directory
    # 1. download source files
    # 2. compile
    # 3. copy executables to $dest_dir
}

sub install_basic {
    my @apt = qw(python-nova build-essential python-pip rabbitmq-server git mongodb cmake zlib1g-dev mpich2 samtools openjdk-7-jre subversion python-matplotlib unzip r-base unp cpanminus picard-tools gcc-4.7 g++-4.7 graphviz csh pkg-config sparsehash libboost-all-dev gawk);
    my @pip = qw(pika python-daemon pymongo requests yapsy numpy biopython requests_toolbelt);

    # run("apt-get -q -y update");
    run("apt-get -y install " . join(" ", @apt));
    run("pip install "        . join(" ", @pip));

    run('curl -L http://cpanmin.us | perl - App::cpanminus');
    run('cpanm File::Spec::Link');
    run('cpanm Perl4::CoreLibs');

    install_cmake3();
}

sub install_cmake3 {
    # spades requires v2.8.8+
    my ($ver) = `cmake --version` =~ /version (\d[0-9.]+)/;
    return if $ver >= 3.0;
    my $dir = 'cmake-3.0.0';
    my $file = "$dir.tar.gz";
    download($dir, $file, 'http://www.cmake.org/files/v3.0');
    chdir($dir);
    run('./bootstrap; make -j && make install');
}

sub install_a5 {
    run("mkdir -p a5");
    chdir("a5");
    my $dir = "a5_miseq_linux_20140604";
    my $file = "$dir.tar.gz";
    download($dir, $file, "http://sourceforge.net/projects/ngopt/files");
    run("cp -r -T $dir $dest_dir/a5");
}

sub install_a6 {
    git("git://github.com/levinas/a5.git", "a6");
    run("cp -r a6 $dest_dir/");
}

sub install_ale {
    my $dir = 'ale';
    git("git://github.com/sc932/ALE.git");
    run("mkdir -p $dest_dir/$dir");
    run("cd ALE/src; make ALE; cp -r ALE samtools-0.1.19 *.sh *.py *.pl $dest_dir/$dir/");
}

sub install_allpathslg {
    check_gcc();
    my $file = "LATEST_VERSION.tar.gz";
    my $dir = "allpathslg";
    download($dir, $file, 'ftp://ftp.broadinstitute.org/pub/crd/ALLPATHS/Release-LG/latest_source_code');
    run("mv allpathslg-* $dir");
    run("mkdir -p $dest_dir/$dir");
    run("cd $dir; ./configure --prefix=$dest_dir/$dir; make -j 8; make install");
}

sub install_bowtie2 {
    my $file = "bowtie2-2.1.0-linux-x86_64.zip";
    my $dir = "bowtie2-2.1.0";
    download($dir, $file, "http://sourceforge.net/projects/bowtie-bio/files/bowtie2/2.1.0");
    run("cp -r -T $dir $dest_dir/bowtie2");
}

sub install_bwa {
    git("git://github.com/lh3/bwa.git");
    run("cd bwa; make -j; cp bwa $dest_dir/");
}

sub install_discovar {
    check_gcc();
    my $file = "LATEST_VERSION.tar.gz";
    my $dir = "discovar";
    download($dir, $file, 'ftp://ftp.broadinstitute.org/pub/crd/Discovar/latest_source_code');
    run("mv discovar-* $dir");
    run("cd $dir; ./configure; make -j; cp src/Discovar $dest_dir/discovar");
}

sub install_fastqc {
    my $dir = 'FastQC';
    my $file = 'fastqc_v0.11.2.zip';
    download($dir, $file, 'http://www.bioinformatics.babraham.ac.uk/projects/fastqc');
    run("chmod a+x $dir/fastqc");
    run("cp -r $dir $dest_dir/");
}

sub install_fastx {
    my $dir = 'fastx_toolkit';
    # there is no fastx plugin; so we need this extra check
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
    run("cd $dir; mkdir -p build; cd build; cmake ..; make -j");
    run("cp -r $dir $dest_dir/");
}

sub install_idba {
    my $dir = 'idba-1.1.1';
    my $file = "$dir.tar.gz";
    download($dir, $file, 'http://hku-idba.googlecode.com/files');
    run("cd $dir; ./configure; make -j");
    run("cp -r -T $dir/bin $dest_dir/idba");
}

sub install_kiki {
    run("apt-get -y purge openmpi*");
    git('git://github.com/GeneAssembly/kiki.git');
    chdir("kiki");
    run("mkdir -p bin; cd bin; cmake ..; make -j ki");
    run("cp bin/ki $dest_dir/");
}

sub install_spate {
    my $app = "spate";
    my $version = "0.4.1";
    my $tag = "v$version";
    my $file = "$tag.tar.gz";
    my $url = "https://github.com/GeneAssembly/biosal/archive";
    download($tag, $file, $url);
    chdir("biosal-$version");
    run("make -j applications/spate_metagenome_assembler/spate");
    run("cp applications/spate_metagenome_assembler/spate $dest_dir/");
}

sub install_kmergenie {
    my $dir = 'kmergenie-1.6663';
    my $file = "$dir.tar.gz";
    download($dir, $file, 'http://kmergenie.bx.psu.edu');
    run("cd $dir; make");
    run("cp -r -T $dir $dest_dir/kmergenie");
}

sub install_masurca {
    my $dir = 'MaSuRCA-2.2.1';
    my $file = "$dir.tar.gz";
    # download($dir, $file, 'ftp://ftp.genome.umd.edu/pub/MaSuRCA');
    download($dir, $file, 'ftp://ftp.genome.umd.edu/pub/MaSuRCA/v2.2.1');
    run("cd $dir; ./install.sh");
    run("cp -r -T $dir $dest_dir/masurca");
}

sub install_miniasm {
    git("git://github.com/lh3/minimap");
    git("git://github.com/lh3/miniasm");
    run("cd minimap; make clean; make -j");
    run("cd miniasm; make clean; make -j");

    run("wget http://lh3lh3.users.sf.net/download/pls2fasta && chmod 755 pls2fasta");
    run("wget https://github.com/levinas/soot/raw/master/misc/gfa2fasta.pl && chmod 755 gfa2fasta.pl");

    run("cp minimap/minimap $dest_dir/");
    run("cp miniasm/miniasm $dest_dir/");
    run("cp pls2fasta $dest_dir/");
    run("cp gfa2fasta.pl $dest_dir/");
}

sub install_smrt {
    my $dir = 'smrtanalysis-2.1.1';
    my $file = '2tqk61';
    my $url = 'http://programs.pacificbiosciences.com/l/1652/2013-11-05';
    download($dir, $file, $url);

    # current configurations
    #
    # directories
    #   tmpdir   -> /mnt/tmp           # chmod 777 /mnt/tmp
    #   userdata -> /space/smrtdata    # mkdir -p /space/smrtdata; chown ubuntu:ubuntu /space/smrtdata;
    #                                    ln -s /space/smrtdata $AR_DIR/third_party/smrt/userdata
    #
    # SMRT Analysis user:     ubuntu
    # MySQL user/password:    root/root
    # Job management system:  NONE
    # Max parallel processes: 28
    # TMP directory symlink:  /mnt/tmp
    my $dest = "$dest_dir/smrt";
    run("mkdir -p $dest");
    run("bash $file --rootdir $dest");

    # install patch
    $file = 'smrtanalysis-2.1.1-patch-0.1.run';
    $url = 'http://files.pacb.com/software/smrtanalysis/2.1.1';
    download($dir, $file, $url);
    run("bash $dest_dir/smrt/admin/bin/smrtupdater --force $file");

    # source $AR_DIR/third_party/smrt/install/smrtanalysis-2.1.1.128549/etc/setup.sh
    # https://github.com/PacificBiosciences/SMRT-Analysis/wiki/SMRT-Pipe-Reference-Guide-v2.1
}

sub install_prodigal {
    my $dir = 'Prodigal-2.60';
    my $file = "$dir.tar.gz";
    download($dir, $file, "https://prodigal.googlecode.com/files");
    run("cd $dir; make -j");
    run("cp -r -T $dir $dest_dir/prodigal");
}

sub install_quast {
    my $dir = 'quast-2.3';
    my $file = "$dir.tar.gz";
    download($dir, $file, "https://downloads.sourceforge.net/project/quast");
    run("cd $dir/libs/MUMmer3.23-linux; make");
    run("cp -r -T $dir $dest_dir/quast");
}

# $dest_dir is a global variable
# global variables are bad.
# the run() command does not save the current
# working directory, so this is hard to write
# an installer with this function...
# I think there should be a single shell script for every
# product that is being installed.
sub install_jgi_rqc {
    my $app = 'jgi_rqc';

    # fetch product assets
    git('git@bitbucket.org:sebhtml/jgi-rqc-pipeline.git');

    # apply patches

    my @patches = ();
    push(@patches, "jgi_rqc-dash-support.patch");
    push(@patches, "jgi_rqc-dash-support-for-os_utility2.patch");
    push(@patches, "fix_logger.patch");

    for my $patch (@patches) {
        run("wget https://raw.githubusercontent.com/sebhtml/assembly/issue-26/patches/jgi-rqc-pipeline/$patch");
        run("patch -p1 < $patch");
    }

    git('git@bitbucket.org:sebhtml/jgi-assets.git');
    run("mv jgi-rqc-pipeline $app");
    run("mv jgi-assets/*zip $app");
    run("cd $app; rm -rf .git");
    run("cd $app; unzip cplusmersampler.zip");
    run("mkdir $app/assets");
    run("mv $app/cplusmersampler $app/assets");
    run("cd $app; rm cplusmersampler.zip");

    # install the product
    run("mv $app $dest_dir");

    # install dependencies
    run("pip install pymysql");
    run("pip install MySQL-python");

    # apt-get install -y gnuplot

    # clean everything
    run("rm -rf *");
}

sub install_ray {
    my $dir = 'ray';
    git("git://github.com/sebhtml/ray.git");
    git("git://github.com/sebhtml/RayPlatform.git");
    run("cd ray; make clean; make -j8 PREFIX=build MAXKMERLENGTH=64 DEBUG=n ASSERT=y HAVE_LIBZ=y");
    run("mkdir -p $dest_dir/$dir");
    run("cd ray; cp -r scripts $dest_dir/$dir/; cp Ray $dest_dir/$dir/");
}

sub install_reapr {
    my $dir = 'Reapr_1.0.17';
    my $file = "$dir.tar.gz";
    download($dir, $file, "ftp://ftp.sanger.ac.uk/pub4/resources/software/reapr");
    run("cd $dir; ./install.sh");
    run("cp -r -T $dir $dest_dir/reapr");
}

sub install_seqtk {
    # seqtk is not a plugin; need to check if it exists
    if (-e "$dest_dir/seqtk") {
        print "Found component seqtk, skipping...\n";
        return;
    }
    git('git://github.com/levinas/seqtk.git');
    run("cd seqtk; make -j");
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
    check_gcc();
    my $dir = 'SPAdes-3.6.2-Linux';
    my $file = "$dir.tar.gz";
    download($dir, $file, 'http://spades.bioinf.spbau.ru/release3.6.2');
    run("cp -r -T SPAdes-3.6.2-Linux $dest_dir/spades");
}

sub install_velvet {
    git("git://github.com/dzerbino/velvet.git");
    chdir("velvet");
    run("rm -f obj/*.o");
    run("make -j 'CATEGORIES=9' 'BIGASSEMBLY=1' 'MAXKMERLENGTH=99' 'LONGSEQUENCES=1' 'OPENMP=1' -j zlib velveth velvetg");
    run("cp velveth $dest_dir/");
    run("cp velvetg $dest_dir/");
}

sub install_megahit {
    git("git://github.com/voutcn/megahit.git");
    run("cd megahit; make clean; make -j");
    run("mkdir -p $dest_dir/megahit");

    my @products = qw(megahit megahit_toolkit megahit_sdbg_build megahit_asm_core);
    for my $product (@products) {
        run("cp megahit/$product $dest_dir/megahit/");
    }
}

sub check_gcc {
    my $info = `gcc --version |head -1`;
    my ($version) = $info =~ /(4[0-9.]+)/;
    if ($version < 4.7) {
        die "gcc verion 4.7 or above required.\n" if ! `which apt-get 2>/dev/null`;
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
    my $dir = "$base_dir/../lib/assembly/plugins";
    my $yapsy = "$dir/$c.asm-plugin";

    return 0 unless -s $yapsy;
    my $found = 1;

    my $in_exec;
    open(F, "<$yapsy") or die "Could not open plugin file $yapsy";
    while (<F>) {
        last if $in_exec && /^\[/;
        if ($in_exec && /\S+\s*=\s*(\S+)/) {
            my $exe = "$dest_dir/$1";
            if (! -e $exe) { $found = 0; last; }
        }
        $in_exec = 1 if /^\[Executables\]/;
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
        run("unzip -o $file");
    } elsif ($file =~ /(\.tar\.gz|\.tgz|\.tar\.bz2)$/) {
        run("tar --no-same-owner -x -f $file");
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

sub verify_user {
    my ($user) = @_;
    my $rc = system "id -u $user >/dev/null 2>/dev/null";
    run("sudo useradd -m $user 2>/dev/null") if $rc;
}

sub run { system(@_) == 0 or confess("FAILED: ". join(" ", @_)); }
