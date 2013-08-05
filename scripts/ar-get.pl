
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

Usage: ar_get [-h] -j JOB_ID [-a [ASSEMBLERS [ASSEMBLERS ...]]] [-s server_addr]

Download result data

optional arguments:
  -h, --help            show this help message and exit
  -j JOB_ID, --job JOB_ID
                        specify which job data to get
  -a [ASSEMBLERS [ASSEMBLERS ...]], --assemblers [ASSEMBLERS [ASSEMBLERS ...]]
                        specify which assembly data to get
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
# system "$target/$arast get @ARGV";

my $arast = 'arast';
$arast .= " -s $server" if $server;

system "$arast get @ARGV";
                    
