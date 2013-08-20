
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

Usage: ar_stat [-h] [-w] [-d [FILES] | -j STAT_JOB] [-n STAT_N] [-s server_addr]

Query status of running jobs

optional arguments:
  -h, --help            show this help message and exit
  -w, --watch           monitor in realtime
  -d [FILES], --data [FILES]
                        list latest or data-id specific files
  -j STAT_JOB, --job STAT_JOB
                        display job status
  -n STAT_N             specify number of records to show
  -s server_addr        specify ARAST server address

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

# my $target = $ENV{HOME}. "/kb/assembly";
# my $arast  = "ar_client/ar_client/ar_client.py";
# system "$target/$arast stat @ARGV";


my $arast = 'arast';
$arast .= " -s $server" if $server;

system "$arast stat @ARGV";
                    
