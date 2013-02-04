
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

End_of_Usage

my $help;

my $rc = GetOptions("h|help" => \$help);

($rc && !$help) or die $usage;

# my $target = $ENV{HOME}. "/kb/assembly";
# my $arast  = "ar_client/ar_client/ar_client.py";
# system "$target/$arast run @ARGV";

system "arast run @ARGV";

