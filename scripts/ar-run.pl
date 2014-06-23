
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

Usage: ar-run  [-h] [-f [SINGLE [SINGLE ...]]] [-r [REFERENCE [REFERENCE ...]]]
                    [-a [ASSEMBLERS [ASSEMBLERS ...]]] [-p [PIPELINE [PIPELINE ...]]]
                    [--pair [PAIR [PAIR ...]]] [--single [SINGLE [SINGLE ...]]] 
                    [-m MESSAGE] [--data DATA_ID]
                    [-s server_addr]

Run an Assembly RAST job

Optional arguments:
  -h, --help            show this help message and exit
  -a [ASSEMBLERS [ASSEMBLERS ...]], --assemblers [ASSEMBLERS [ASSEMBLERS ...]]
                        specify assemblers to use. None will invoke automatic mode
  -f [SINGLE [SINGLE ...]]
                        specify sequence file(s)
  -m MESSAGE, --message MESSAGE
                        Attach a description to job
  -p [PIPELINE [PIPELINE ...]], --pipeline [PIPELINE [PIPELINE ...]]
                        invoke a pipeline. None will invoke automatic mode
  -r [REFERENCE [REFERENCE ...]], --reference [REFERENCE [REFERENCE ...]]
                        specify sequence file(s)
  -s server_addr        Specify ARAST server address
  --data DATA_ID        Reuse uploaded data
  --pair [PAIR [PAIR ...]]
                        Specify a paired-end library and parameters
  --single [SINGLE [SINGLE ...]]
                        Specify a single end file and parameters

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
    $have_data = 1 if /(-f|--single|--pair|--data)/;
}

if (!$have_data) {
    my @lines = <STDIN>;
    my $line = pop @lines;
    my ($data_id) = $line =~ /(\d+)/;
    $argv .= "--data $data_id";
}

system "$arast run $argv";

