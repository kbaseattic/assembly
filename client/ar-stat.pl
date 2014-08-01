
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

Usage: ar-stat [-h] [-w] [-j JOB | -l | --data-json DATA] [-n STAT_N] [-s server_addr]

Query status of running jobs

Optional arguments:
  -h, --help            show this help message and exit
  -j JOB, --job JOB     get status of a specific job ID
  -n STAT_N             specify number of records to show
  -d, --detail          show pipeline/recipe/wasp details in status table
  -l, --list-data       list data objects
  --data-json DATA      print the information of a data ID
  -s server_addr        specify ARAST server address
  -w, --watch           monitor in realtime (only works in Linux and Mac shell)
  --version             print ARAST client version number

End_of_Usage

my $help;
my $server;
my $version;

my $rc = GetOptions("h|help"  => \$help,
                    "s=s"     => \$server,
                    "version" => \$version);

$rc or die $usage;
if ($help) {
    print $usage;
    exit 0;
}

my $arast = 'arast';
$arast .= " -s $server" if $server;

if ($version) {
    system "$arast --version"; 
} else {
    !system "$arast stat @ARGV" or die $!."\n";
}
                    
