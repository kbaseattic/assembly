
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

usage: arast kill [-h] [-j JOB] [-a]

Send a kill signal to jobs

optional arguments:
  -h, --help         show this help message and exit
  -j JOB, --job JOB  kill specific job

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

!system "$arast kill @ARGV" or die $!."\n";
                    
