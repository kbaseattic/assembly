
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

Usage: ar-run  [-h]
               [-f [SINGLE [SINGLE ...]]]
               [--pair [PAIR [PAIR ...]]]
               [--pair_url [PAIR_URL [PAIR_URL ...]]]
               [--single [SINGLE [SINGLE ...]]]
               [--single_url [SINGLE_URL [SINGLE_URL ...]]]
               [--reference [REFERENCE [REFERENCE ...]]]
               [--reference_url [REFERENCE_URL [REFERENCE_URL ...]]]
               [--data DATA_ID]
               [-a [ASSEMBLERS [ASSEMBLERS ...]] |
                -p [PIPELINE [PIPELINE ...]] |
                -r [RECIPE [RECIPE ...]] |
                -w [WASP [WASP ...]]]
               [-m MESSAGE] [--curl]
               [-s server_addr]

Run an Assembly RAST job

Optional arguments:
  -h, --help            Show this help message and exit
  -s server_addr        Specify ARAST server address
  -a [ASSEMBLERS [ASSEMBLERS ...]], --assemblers [ASSEMBLERS [ASSEMBLERS ...]]
                        Specify assemblers to use. None will invoke automatic
                        mode
  -p [PIPELINE [PIPELINE ...]], --pipeline [PIPELINE [PIPELINE ...]]
                        Invoke a pipeline. None will invoke automatic mode
  -r [RECIPE [RECIPE ...]], --recipe [RECIPE [RECIPE ...]]
                        Invoke a recipe
  -w [WASP [WASP ...]], --wasp [WASP [WASP ...]]
                        Invoke a wasp expression
  -m MESSAGE, --message MESSAGE
                        Attach a description to job
  --data DATA_ID        Reuse uploaded data
  --data-json JSON      Reuse uploaded data from a json file
  --reference [REFERENCE [REFERENCE ...]]
                        Specify sequence file(s)
  --reference_url [REFERENCE_URL [REFERENCE_URL ...]]
                        Specify a URL for a reference contig file and parameters
  --pair [PAIR [PAIR ...]]
                        Specify a paired-end library and parameters
  --pair_url [PAIR_URL [PAIR_URL ...]]
                        Specify URLs for a paired-end library and parameters
  -f [SINGLE [SINGLE ...]]
  --single [SINGLE [SINGLE ...]]
                        Specify a single end file and parameters
  --single_url [SINGLE_URL [SINGLE_URL ...]]
                        Specify a URL for a single end file and parameters
  --contigs [CONTIGS [CONTIGS ...]]
                        Specify a contig file
  --curl                Use curl for http requests

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

my $have_data;
my $argv;
for (@ARGV) {
    if (/ /) { $argv .= "\"$_\" " } else { $argv .= "$_ " }
    $have_data = 1 if /(-f|--single|--single_url|--pair|--pair_url|--data|--contigs)\b/;
}

if (!$have_data) {
    my @lines = <STDIN>;
    my $line = pop @lines;
    my ($data_id) = $line =~ /(\d+)/;
    $argv .= "--data $data_id";
}

!system "$arast run $argv" or die $!."\n";
