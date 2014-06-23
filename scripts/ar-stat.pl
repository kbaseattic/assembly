
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

Usage: ar-stat [-h] [-w] [-d [FILES] | -j STAT_JOB] [-n STAT_N] [-s server_addr]

Query status of running jobs

Optional arguments:
  -h, --help            show this help message and exit
  -j JOB, --job JOB     get status of specific job
  -n STAT_N             specify number of records to show
  -s server_addr        specify ARAST server address
  -w, --watch           monitor in realtime (only works in Linux and Mac shell)

End_of_Usage

my $help;
my $server;

my $rc = GetOptions("h|help" => \$help,
                    "s=s" => \$server);

$rc or die $usage;
if ($help) {
    print $usage;
    exit 0;
}

my $arast = 'arast';
$arast .= " -s $server" if $server;

!system "$arast stat @ARGV" or die $!;
                    
