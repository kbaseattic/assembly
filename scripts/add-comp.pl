#! /usr/bin/env perl

use strict;
use Carp;
use Cwd;
use Data::Dumper;
use File::Basename;
use Getopt::Long;

my $usage =<<"End_of_Usage";

Usage: add_comp [ options ] modules\n\n";

End_of_Usage

my ($help, $tmp_dir);

GetOptions( 'd|tmpdir=s' => \$tmp_dir,
            'h|help' => \$help);

if ($help) { print $usage; exit 0 }


my $base_dir = dirname(Cwd::abs_path($0));
my $tmp_dir  = make_tmp_dir();

print "$base_dir\n";


sub make_tmp_dir {
    my ($dir) = @_;
    $dir ||= "/mnt/tmp";
    run("mkdir -p $dir");
    return $dir;
}




sub run  { system(@_) == 0 or confess("FAILED: ". join(" ", @_)); }

