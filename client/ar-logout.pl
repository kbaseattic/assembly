
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

Usage: ar-logout  [-h] 

Log out in shell.

End_of_Usage

my $help;

my $rc = GetOptions("h|help" => \$help);

$rc or die $usage;
if ($help) {
    print $usage;
    exit 0;
}

!system "arast logout @ARGV" or die $!."\n";

