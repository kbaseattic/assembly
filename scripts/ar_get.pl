
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

Usage: ar_get [-h] -j JOB_ID [-a [ASSEMBLERS [ASSEMBLERS ...]]]

Download result data

optional arguments:
  -h, --help            show this help message and exit
  -j JOB_ID, --job JOB_ID
                        specify which job data to get
  -a [ASSEMBLERS [ASSEMBLERS ...]], --assemblers [ASSEMBLERS [ASSEMBLERS ...]]
                        specify which assembly data to get

End_of_Usage

my $help;

my $rc = GetOptions("h|help" => \$help);

($rc && !$help) or die $usage;

my $target = $ENV{HOME}. "/kb/assembly";
my $arast  = "ar_client/ar_client/ar_client.py";

system "$target/$arast get @ARGV";
                    
