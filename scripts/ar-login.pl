
use strict;
use Carp;
use Data::Dumper;
use Getopt::Long;
Getopt::Long::Configure("pass_through");

my $usage = <<End_of_Usage;

Usage: ar_login  [-h]

Authenticate with username and password, or switch account if already logged in.

End_of_Usage

my $help;
my $server;

my $rc = GetOptions("h|help" => \$help);

$rc or die $usage;
if ($help) {
    print $usage;
    exit 0;
}

# my $target = $ENV{HOME}. "/kb/assembly";
# my $arast  = "ar_client/ar_client/ar_client.py";
# system "$target/$arast run @ARGV";

system "arast login @ARGV";

