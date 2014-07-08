
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

Usage: ar-avail [-h]

List available AssemblyRAST modules or recipes

Optional arguments:
  -h, --help     show this help message and exit
  -r, --recipe   list recipes
  -d, --detail   show module or recipe details

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

!system "$arast avail @ARGV" or die $!."\n";
                    
