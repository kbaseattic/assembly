
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

Usage: ar-get [-h] -j JOB_ID [-a [ASSEMBLY]] [--stdout] [-s server_addr]

Download or print assembly result data

Mandatory arguments:
  -j JOB_ID, --job JOB_ID
                        specify which job data to get

Optional arguments:
  -h, --help            show this help message and exit
  -s server_addr        specify ARAST server address
  -a [ASSEMBLY], --assembly [ASSEMBLY]
                        Download an assembly or assemblies
  -p [PICK], --pick [PICK]
                        Print a set of assembled contigs
                        specified by an optional assembly ID
                        (e.g., '2' or 'velvet', defaults to auto selection)
  -r, --report          Print assembly stats report
  -l, --log             Print assembly job log
  -o OUTDIR, --outdir OUTDIR
                        Download to specified directory
  -w, --wait            Wait until job is done

End_of_Usage

my $help;
my $server;
my $jobid;

my $rc = GetOptions("h|help" => \$help,
                    "s=s" => \$server,
                    "j|job=i" => \$jobid);

$rc or die $usage;
if ($help) {
    print $usage;
    exit 0;
}

if (!$jobid) {
    my @lines = <STDIN>;
    my $line = pop @lines;
    ($jobid) = $line =~ /(\d+)/;
}

$jobid or die $usage;

my $arast = 'arast';
$arast .= " -s $server" if $server;

!system "$arast get -j $jobid @ARGV" or die $!."\n";
                    
if ($ENV{KB_RUNNING_IN_IRIS}) {
    my $dir = "AR$jobid";
    my @tarballs = grep { -s $_ } map { $jobid . "_$_" } qw(ctg_qst.tar.gz assemblies.tar.gz);
    for my $f (@tarballs) {
        system "mkdir -p $dir";
        system "tar xf $f -C $dir";
    }
    print "Contig FASTA files and reports saved in $dir\n" if @tarballs > 0;
}
