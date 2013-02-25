
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

Usage: ar_run  [-h] [-f [SINGLE [SINGLE ...]]]
                    [-a [PIPELINE [PIPELINE ...]]]
                    [-p [PIPELINE [PIPELINE ...]]] [-m MESSAGE]
                    [--data DATA_ID] [--pair [PAIR [PAIR ...]]]
                    [--single [SINGLE [SINGLE ...]]]
                    [-s server_addr]

Run an Assembly RAST job

optional arguments:
  -h, --help            show this help message and exit
  -f [SINGLE [SINGLE ...]]
                        specify sequence file(s)
  -a [PIPELINE [PIPELINE ...]], --assemblers [PIPELINE [PIPELINE ...]]
  -p [PIPELINE [PIPELINE ...]], --pipeline [PIPELINE [PIPELINE ...]]
                        Pipeline
  -m MESSAGE, --message MESSAGE
                        Attach a description to job
  --data DATA_ID        Reuse uploaded data
  --pair [PAIR [PAIR ...]]
                        Specify a paired-end library and parameters
  --single [SINGLE [SINGLE ...]]
                        Specify a single end file and parameters
  -s server_addr        Specify ARAST server address

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
# system "$target/$arast run @ARGV";

my $arast = 'arast';
$arast .= " -s $server" if $server;

my $argv;
for (@ARGV) {
    if (/ /) { $argv .= "\"$_\" " } else { $argv .= "$_ " }
}

system "$arast run $argv";

