#! /usr/bin/env perl

# 2014/07/07 new client integration test
# 
# Respects environmental variables:
#
#   ARAST_URL
#   ARAST_QUEUE
#

use strict vars;

use Carp;
use Test::More;
use Data::Dumper;
use English;
use Getopt::Long;

my $usage = "$0 [options] [test1 test2 ...]\n";

my ($help, $dir, $dry);

my $rc = GetOptions("h|help"  => \$help,
                    "d|dir=s" => \$dir,
                    "dry"     => \$dry,
                   ) or die $usage;

my @all_tests = discover_own_tests();
my @tests = @ARGV > 0 ? @ARGV : @all_tests;

if ($dir) {
    run("mkdir -p $dir");
    chdir($dir);
}

my $testCount = 0;
foreach my $testname (@tests) {
    my $test = "test_" . $testname;
    print "\n> Testing $testname...\n";
    if (!defined &$test) {
        print "Test routine doesn't exist: $test\n";
        next;
    }
    &$test();

}
done_testing($testCount);


sub test_simple_cases {
    # This test takes 19 minutes to run on a server with 2+ queues

    my $ref = 'http://www.mcs.anl.gov/~fangfang/arast/b99.ref.fa';
    my $pe1 = 'http://www.mcs.anl.gov/~fangfang/arast/b99_1.fq';
    my $pe2 = 'http://www.mcs.anl.gov/~fangfang/arast/b99_2.fq';
    my $se  = 'http://www.mcs.anl.gov/~fangfang/arast/se.fastq';

    sysrun("ar-login");

    sysrun("curl $ref > ref.fa");
    sysrun("curl $pe1 > p1.fq");
    sysrun("curl $pe2 > p2.fq");
    sysrun("curl $se > se.fq");

    sysrun("ar-stat > stat.0");

    sysrun("ar-upload --pair p1.fq p2.fq --reference ref.fa > data.1");
    sysrun("cat data.1 | ar-run -m 'first: auto' > job.1");
    sysrun('ar-stat --job $(cat job.1|sed "s/[^0-9]*//g") > stat.1');

    sysrun("ar-upload --pair_url $pe1 $pe2 > data.2");
    sysrun("cat data.2 | ar-run -r rast -m 'RAST recipe' > job.2");

    sysrun("arast upload --pair p1.fq p2.fq --reference_url $ref > data.3");
    sysrun("ar-run --pipeline tagdust idba --pair p1.fq p2.fq -m 'my test job' > job.3");
    sysrun("ar-stat -n 50 --detail > stat.3");
    sysrun("ar-stat --list-data > stat.data.3");

    sysrun("ar-upload -f se.fq -m 'my test data' > data.4");
    sysrun("ar-run -a velvet --single_url $se | ar-get --wait --pick > contigs.4");

    sysrun("ar-upload --single se.fq --cov 10 --gs 1000000 > data.5");
    sysrun("cat data.5 | ar-run -r fast -m fast | ar-get -w -p 1 > contigs.5");
    sysrun("ar-stat -l > stat.data.5");
    sysrun("ar-filter -c 2.5 -l 500 < contigs.5 > filter.5");

    sysrun("ar-upload --pair p1.fq p2.fq insert=300 stdev=60 > data.6");
    sysrun("cat data.6 | ar-run -p kiki -m 'k sweep' -p 'none tagdust' velvet ?hash_length=29-37:4 > job.6");
    sysrun("ar-stat -d > stat.6");
    sysrun('ar-stat --job $(cat data.6|sed "s/[^0-9]*//g") > stat.data.json.6');

    sysrun("cat job.3 | ar-get -w -a -o out.3");

    sysrun("cat job.2 | ar-get -w -o out.2");
    sysrun('cp out.2/$(cat job.2|sed "s/[^0-9]*//g")_analysis/report.html html.2');

    sysrun('ar-run -a spades --data $(cat data.2|sed "s/[^0-9]*//g") -m "to be terminated" >job.7');
    sysrun('ar-kill -j $(cat job.7|sed "s/[^0-9]*//g")');

    sysrun("cat job.2 | ar-get -w -a 1");
    sysrun("cat job.1 | ar-get -w");

    sysrun("cat job.6 | ar-get -w -l > log.6");
    sysrun("cat job.6 | ar-get -w -r > report.6");

    sysrun('ar-stat -j $(cat job.7|sed "s/[^0-9]*//g") > stat.term.7');

    sysrun("ar-login --rast");
    sysrun("ar-run -a kiki -f se.fq -m 'last: rast account' > job.8");
    sysrun("ar-stat -j 1 > stat.8");

    sysrun('ar-get -j $(cat job.8|sed "s/[^0-9]*//g") -w');
    sysrun('cp $(cat job.8|sed "s/[^0-9]*//g")_1.kiki_contigs.fa contigs.8');

    sysrun("ar-avail > modules");
    sysrun("ar-avail -d > modules.detail");
    sysrun("ar-avail --recipe > recipes");
    sysrun("ar-avail --r --detail > recipes.detail");

    sysrun("ar-logout");

}


sub discover_own_tests {
    my $self = $0;
    my @funcs = map { /^sub test_(\S+)/ ? $1 : () } `cat $self`;
    wantarray ? @funcs : \@funcs;
}

sub sysrun {
    my ($command, $message) = @_;
    $message ||= abbrev_cmd($command);

    if ($dry) {
        print $command."\n"; return;
    }

    $testCount++;

    eval { !system($command) or die $ERRNO };
    diag("unable to run: $command") if $EVAL_ERROR;
    ok(!$EVAL_ERROR, (caller(1))[3] ." > ". $message);
}

sub abbrev_cmd { length $_[0] < 60 ? $_[0] : substr($_[0], 0, 60)."..." }

sub whoami { (caller(1))[3] }

sub run { system(@_) == 0 or confess("FAILED: ". join(" ", @_)); }
