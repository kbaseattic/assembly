
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

Usage: ar-login  [-h]

Authenticate in shell with username and password, or switch account if already logged in.

End_of_Usage

my $help;
my $server;

my $rc = GetOptions("h|help" => \$help);

$rc or die $usage;
if ($help) {
    print $usage;
    exit 0;
}

!system "arast login @ARGV" or die $!."\n";

