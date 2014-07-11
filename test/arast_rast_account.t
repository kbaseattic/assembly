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

my ($ref, $pe1, $pe2, $se);

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

sub test_login {
    sysrun("ar-login");
}

sub test_setup {
    $ref = 'http://www.mcs.anl.gov/~fangfang/arast/b99.ref.fa';
    $pe1 = 'http://www.mcs.anl.gov/~fangfang/arast/b99_1.fq';
    $pe2 = 'http://www.mcs.anl.gov/~fangfang/arast/b99_2.fq';
    $se  = 'http://www.mcs.anl.gov/~fangfang/arast/se.fastq';    

    sysrun("curl -s $ref > ref.fa");
    sysrun("curl -s $pe1 > p1.fq");
    sysrun("curl -s $pe2 > p2.fq");
    sysrun("curl -s $se > se.fq");
}

sub test_rast_account {
    sysrun("ar-login --rast");
    sysrun("ar-run -p kiki -f se.fq -m 'rast account' > rast.job");
    sysrun("ar-stat -j 1 > rast.stat");
    sysrun('ar-get -j $(cat rast.job|sed "s/[^0-9]*//g") -w');
    sysrun('cp $(cat rast.job|sed "s/[^0-9]*//g")_1.kiki_contigs.fa rast.contigs');
    validate_contigs('rast.contigs');
}

sub test_log_out {
    sysrun("ar-logout");
}

sub validate_contigs {
    my ($file) = @_;
    my $out = sysout("head $file |grep '^>'");
    like($out, qr/\S/, "$file has valid contigs"); $testCount++;
}

sub validate_report {
    my ($file) = @_;
    my $out = sysout("head -n 12 $file");
    ok($out =~ /QUAST.*statistics.*N50/sg, "$file is valid assembly report"); $testCount++;
}

sub validate_log {
    my ($file, $check_errors) = @_;
    my $out = sysout("head $file");
    like($out, qr/Arast Pipeline: Job/, "$file is valid assembly log"); $testCount++;
    if ($check_errors) {
        unlike($out, qr/PIPELINE ERRORS/, "$file has no reported errors");
        $testCount++;
    }
}

sub validate_stat {
    my ($file) = @_;
    my $out = sysout("head $file |head -n 3");
    like($out, qr/Job ID.*Data ID.*Status.*Run time.*Description/, "$file is valid stat table");
    $testCount++;
}

sub validate_stat_detail {
    my ($file) = @_;
    my $out = sysout("head $file |head -n 3");
    like($out, qr/Job ID.*Data ID.*Status.*Run time.*Description.*Parameters/, "$file is valid stat table with details");
    $testCount++;
}

sub validate_stat_list_data {
    my ($file) = @_;
    my $out = sysout("head $file |head -n 3");
    like($out, qr/Data.*Description.*Type.*Files/, "$file is valid stat data list");
    $testCount++;
}

sub validate_modules {
    my ($file) = @_;
    my $out = sysout("cat $file");
    like($out, qr/Module.*Stages.*Description/, "$file has valid module headers"); $testCount++;
    ok($out =~ /bhammer.*preprocess.*component.*velvet/sg, "$file has valid modules"); $testCount++;
}

sub validate_modules_detail {
    my ($file) = @_;
    my $out = sysout("cat $file");
    ok($out =~ /Module.*Version.*doi.*hash_length/sg, "$file has valid module details");  $testCount++;
}

sub validate_recipes {
    my ($file) = @_;
    my $out = sysout("cat $file");
    ok($out =~ /Recipe.*auto.*fast.*rast/sg, "$file has valid recipes"); $testCount++;
}

sub validate_recipes_detail {
    my ($file) = @_;
    my $out = sysout("cat $file");
    ok($out =~ /Recipe.*auto.*GAM-NGS.*define.*gam.*analysis/sg, "$file has valid recipe details");  $testCount++;
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

    exit_if_ctrl_c($CHILD_ERROR);
}


sub sysout {
    my ($command, $message) = @_;
    $message ||= abbrev_cmd($command);

    $testCount++;

    my $out;
    eval { $out = `$command` };
    diag("unable to run: $command") if $EVAL_ERROR;
    
    ok(!$CHILD_ERROR, (caller(1))[3] ." > ". $message);
    diag("errno: $CHILD_ERROR") if $CHILD_ERROR;

    exit_if_ctrl_c($CHILD_ERROR);
    
    wantarray ? split(/\n/, $out) : $out;
}

sub exit_if_ctrl_c {
    my ($errno) = @_;
    if ($errno != -1 && (($errno & 127) == 2) && (!($errno & 128))) {
        print "\nTest terminated by user interrupt.\n\n";
        exit;
    }
}

sub abbrev_cmd { length $_[0] < 60 ? $_[0] : substr($_[0], 0, 60)."..." }

sub whoami { (caller(1))[3] }

sub run { system(@_) == 0 or confess("FAILED: ". join(" ", @_)); }
