#! /usr/bin/env perl

use strict;

use Carp;
use Cwd;
use File::Basename;
use Getopt::Long;

my $usage =<<"End_of_Usage";
Usage: $0 [-v new_version] [-m commit_message] [--push]

Increments version number, commits the code, and tag it with the new version.

Examples:

    Suppose the old version number is 0.5.9:

    $0                : 0.5.9 -> 0.6.0
    $0 -v 1.1         : 0.5.9 -> 1.1.0

End_of_Usage

my ($help, $version, $message, $push);

GetOptions( 'v=s'    => \$version,
            'm=s'    => \$message,
            'p|push' => \$push,
            'h|help' => \$help);

$help and die $usage;


my $curr_dir = dirname(Cwd::abs_path($0));
my $ver_file = $curr_dir."/../lib/assembly/__init__.py";

my ($ver_old) = `cat $ver_file` =~ /__version__\s+=\s+['"]?([0-9.]+)['"]?/;
my $ver_new = correct_version($version) || increment_version($ver_old);

print("Current git status:\n\n");
run('git status');

print "\nProposed version change: $ver_old => $ver_new\n\n";

if (!$message) {
    my $default = "new version $ver_new\n";
    print "The default commit message is:\n\n  $default\n";
    print "One-line commit message: ";
    $message = <STDIN>;
    chomp($message);
    $message ||= $default;
} else {
    print "Press ENTER to proceed";
    my $ignore = <STDIN>;
}

run("perl -pi -e 's/__version__\\s+=\\s+\\S+/__version__ = \"$ver_new\"/' $ver_file");

run("git add $ver_file");
run("git commit -m '$message'");
run("git tag -a v$ver_new -m 'new version $version'");
run("git push --tags") if $push;

sub correct_version {
    my ($version, $segments) = @_;
    return unless $version;
    $segments = 3;
    my $dots = $version =~ tr/\./\./;
    if ($dots < $segments) {
        my $zeros = $dots < $segments ? ($segments - $dots - 1) : 0;
        $version .= '.0' x $zeros;
    } else {
        for (0..$dots-$segments) {
            $version =~ s/\.[^.]+?$//;
        }
    }
    return $version;
}

sub increment_version {
    my ($ver) = @_;
    my @digits = reverse split(/\./, $ver);
    $digits[0]++;
    for my $i (0..$#digits-1) {
        if ($digits[$i] > 9) {
            $digits[$i] = 0;
            $digits[$i+1]++;
        };
    }
    return join('.', reverse @digits);
}


sub run { system(@_) == 0 or confess("FAILED: ". join(" ", @_)); }
