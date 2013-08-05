#! /usr/bin/env perl

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

      a5           - A5 pipeline
      a6           - Modified A5 pipeline
      ale          - ALE reference-free assembler evaluator
      bowtie       - Bowtie aligner
      bwa          - BWA aligner
      discovar     - Discovar assembler
      fastx        - FastX preprocessing toolkit
      gam          - GAM-NGS assembler merger
      idba         - IDBA_UD assembler
      kiki         - Kiki assembler
      mascular     - Masurca assembler
      quast        - QUAST assembly evaluator (v2.2)
      reapr        - REAPR reference-free evaluator (v1.0.15)
      screed       - Screed assembly statistics calculator
      seqtk        - Modified Seqtk preprocessing toolkit
      solexa       - SolexaQA preprocessing tool (v2.1)
      spades       - SPAdes assembler (v2.4)
      velvet       - Velvet assembler

Examples:
      sudo add-comp.pl basic velvet spades
      sudo add-comp.pl -t /space/tmp -d /usr/bin all

End_of_Usage

my ($help, $dest_dir, $tmp_dir);

GetOptions( 'd|dest=s' => \$dest_dir,
            't|tmp=s'  => \$tmp_dir,
            'h|help'   => \$help);

if ($help) { print $usage; exit 0 }

my @all_comps = qw (basic a5 a6 ale bowtie bwa discovar fastx gam idba kiki mascular quast reapr screed seqtk solexa spades velvet); 
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

# TODO: change velvet, kiki and discovar destination
# TODO: python: fallback: strip path prefix and check exe in path

sub install_template {
    # we are in the $tmp_dir 
    # 1. download source files
    # 2. compile
    # 3. copy executables to $dest_dir
}

sub install_basic {}

sub install_a5 {
    run("mkdir -p a5");
    chdir("a5");
    my $prefix = "ngopt_a5pipeline_linux-x64_20120518";
    my $file = "$prefix.tar.gz";
    run("rm -f $file");
    run("wget http://ngopt.googlecode.com/files/$file");
    run("tar xf $file");
    run("cp -R $prefix/bin/* $dest_dir/a5/")
}

sub install_a6 {
    print `pwd`;
    
    run("mkdir -p a6");
    chdir("a6");
    git("https://github.com/levinas/a5.git");
    run("cp -r ../a6 $dest_dir/");
}

sub install_ale {}
sub install_bowtie {}

sub install_bwa {
    git("git://github.com/lh3/bwa.git");
    run("cd bwa; make; cp bwa $dest_dir");
}

sub install_discovar {}
sub install_fastx {}
sub install_gam {}
sub install_idba {}
sub install_kiki {}
sub install_mascular {}
sub install_quast {}
sub install_reapr {}
sub install_screed {}
sub install_seqtk {}
sub install_solexa {}
sub install_spades {}
sub install_velvet {}


sub install_idba {

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
        if (/^(executable|bin_\S+) = (\S+)/) {
            my $exe = "$base_dir/../lib/ar_server/$2";
            print "$exe\n";
            
            if (! -e $exe) { $found = 0; last; }
        }
    }
    close(F);
    return $found;
}

sub git {
    my ($url, $repo) = @_;
    if (!$repo) { $repo = $url; $repo =~ s|.*/||; $repo =~ s|\.git$||; }
    
    if (-d "$tmp_dir/$repo") {
        run("cd $repo; git pull");
    } else {
        run("git clone $url $repo");
    }
}

sub make_tmp_dir {
    my ($dir) = @_;
    $dir ||= "/mnt/tmp";
    run("mkdir -p $dir");
    return $dir;
}

sub run { system(@_) == 0 or confess("FAILED: ". join(" ", @_)); }

