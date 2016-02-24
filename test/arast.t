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
use JSON;

my $usage = "$0 [options] [test1 test2 ...]\n";

my ($help, $dir, $dry);

my $rc = GetOptions("h|help"  => \$help,
                    "d|dir=s" => \$dir,
                    "dry"     => \$dry,
                   ) or die $usage;

my @all_tests = discover_own_tests();

print("Test list:");
print(join(', ', @all_tests));

my @tests = @ARGV > 0 ? @ARGV : @all_tests;

if ($dir) {
    run("mkdir -p $dir");
    chdir($dir);
}

my ($ref, $pe1, $pe2, $se, $seb, $pb);

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

sub test_setup {
    $ref = 'http://www.mcs.anl.gov/~fangfang/arast/b99.ref.fa';
    $pe1 = 'http://www.mcs.anl.gov/~fangfang/arast/b99_1.fq';
    $pe2 = 'http://www.mcs.anl.gov/~fangfang/arast/b99_2.fq';
    $se  = 'http://www.mcs.anl.gov/~fangfang/arast/se.fastq';
    $seb = 'http://www.mcs.anl.gov/~fangfang/arast/se.fastq.bz2';
    $pb  = 'http://www.mcs.anl.gov/~fangfang/arast/pacbio.lambda.fa';

    sysrun("curl -s $ref > ref.fa");
    sysrun("curl -s $pe1 > p1.fq");
    sysrun("curl -s $pe2 > p2.fq");
    sysrun("curl -s $se  > se.fq");
}

sub test_simple_cases {
    # This test takes 20 minutes to run on a server with 2+ queues
    sysrun("ar-stat > stat.0");

    sysrun("ar-upload --pair p1.fq p2.fq --reference ref.fa > data.1");
    sysrun("cat data.1 | ar-run -m 'first: auto' > job.1");
    sysrun('ar-stat --job $(cat job.1|sed "s/[^0-9]*//g") > stat.1');

    sysrun("ar-upload --pair_url $pe1 $pe2 > data.2");
    sysrun("cat data.2 | ar-run -r rast -m 'RAST recipe' > job.2");

    sysrun("arast upload --pair p1.fq p2.fq --reference_url $ref > data.3");
    sysrun("ar-run --pipeline tagdust idba --pair p1.fq p2.fq -m 'my test: tagdust-idba' > job.3");
    sysrun("ar-stat -n 50 --detail > stat.3");
    sysrun("ar-stat --list-data > stat.data.3");

    sysrun("ar-upload -f se.fq -m 'my test data' > data.4");
    sysrun("ar-run -a velvet --single_url $seb | ar-get --wait --pick > contigs.4");
    validate_contigs('contigs.4');

    sysrun("ar-upload --single se.fq --cov 10 --gs 1000000 > data.5");
    sysrun("cat data.5 | ar-run -r fast -m fast | ar-get -w -p 1 > contigs.5");
    sysrun("ar-stat -l > stat.data.5");
    sysrun("ar-filter -c 2.5 -l 500 < contigs.5 > filter.5"); validate_contigs('filter.5');

    sysrun("ar-run --contigs contigs.4 filter.5 -r contig_compare -m compare_contigs_4vs5 | ar-get -w -r >report.4vs5"); validate_report('report.4vs5');

    sysrun("ar-upload --pair p1.fq p2.fq insert=300 stdev=100 > data.6");
    sysrun("cat data.6 | ar-run -p megahit -m 'k sweep' -p 'none tagdust' velvet ?hash_length=29-37:4 > job.6");
    sysrun("ar-stat -n 9999 -d > stat.detail.6");
    sysrun('ar-stat --job $(cat data.6|sed "s/[^0-9]*//g") > stat.data.json.6');

    sysrun("cat job.3 | ar-get -w -a -o out.3");

    sysrun("cat job.2 | ar-get -w -o out.2");
    sysrun('cp out.2/$(cat job.2|sed "s/[^0-9]*//g")_analysis/report.html html.2');

    sysrun('ar-run -a spades --data $(cat data.2|sed "s/[^0-9]*//g") -m "to be terminated" >job.7');
    sysrun('ar-kill -j $(cat job.7|sed "s/[^0-9]*//g")');

    sysrun('cat data.6 | tee data.8 | ar-run -a a5 a6 > job.8');
    sysrun("ar-run --single_url $pb -m pacbio > job.9");

    sysrun("cat job.2 | ar-get -w -a 1");
    sysrun("cat job.2 | ar-get -p > contigs.2"); validate_contigs('contigs.2');
    sysrun("cat job.2 | ar-get -r > report.2"); validate_report('report.2');
    sysrun("cat job.2 | ar-get -l > log.2"); validate_log('log.2', 1);

    sysrun("cat job.1 | ar-get -w");
    sysrun("cat job.1 | ar-get -p > contigs.1"); validate_contigs('contigs.1');
    sysrun("cat job.1 | ar-get -r > report.1"); validate_report('report.1');
    sysrun("cat job.1 | ar-get -l > log.1"); validate_log('log.1', 1);

    sysrun("cat job.6 | ar-get -w -log > log.6"); validate_log('log.6');
    sysrun("cat job.6 | ar-get -w --report > report.6"); validate_report('report.6');

    sysrun("cat job.8 | ar-get -w --report > report.8"); validate_report('report.8');
    sysrun("cat job.8 | ar-get -l > log.8"); validate_log('log.8', 1);

    sysrun("cat job.9 | ar-get -w --report > report.9"); validate_report('report.9');

    sysrun('ar-stat -j $(cat job.7|sed "s/[^0-9]*//g") > stat.term.7');
    like(`cat stat.term.7`, qr/Terminated/, 'job properly terminated'); $testCount++;

    sysrun("ar-avail > modules");
    sysrun("ar-avail -d > modules.detail");
    sysrun("ar-avail --recipe > recipes");
    sysrun("ar-avail --r --detail > recipes.detail");

    validate_modules('modules');
    validate_modules_detail('modules.detail');
    validate_recipes('recipes');
    validate_recipes_detail('recipes.detail');
}

sub test_json_input {
    sysrun('ar-upload --pair p1.fq p2.fq --ws-json > data.11.ws.json');
    sysrun('ar-run --data-json data.11.ws.json -a kiki > job.11');

    sysrun('arast upload --pair p1.fq p2.fq --json > data.12.json');
    sysrun('ar-run --data-json data.12.json -a kiki > job.12');

    sysrun('cat job.11 | ar-get -w -p > contigs.11');
    sysrun('cat job.12 | ar-get -w -p > contigs.12');
}

sub test_duplicated_files {
    # sysrun('ar-upload --pair p1.fq p1.fq', undef, 1);
    my $out;
    $out = sysout('ar-run --pair p1.fq p1.fq', undef, 1);
    like($out, qr/duplicate/, "Duplication identified correctly: '$out'"); $testCount++;
    $out = sysout('ar-upload --pair p1.fq p2.fq --single p1.fq', undef, 1);
    like($out, qr/duplicate/, "Duplication identified correctly: '$out'"); $testCount++;
    $out = sysout('ar-run --pair_url http://www.mcs.anl.gov/~fangfang/arast/b99_1.fq  http://www.mcs.anl.gov/~fangfang/arast/b99_1.fq', undef, 1);
    like($out, qr/duplicate/, "Duplication identified correctly: '$out'"); $testCount++;
}

sub test_mixed_input_with_smart {
    sysrun('ar-run -r smart -m mixed_1s2p --pair p1.fq p2.fq --single_url http://www.mcs.anl.gov/~fangfang/arast/se.fastq --pair_url http://www.mcs.anl.gov/~fangfang/arast/b99_1.fq http://www.mcs.anl.gov/~fangfang/arast/b99_2.fq > job.21');
    sysrun("cat job.21 | ar-get -w --report > report.21"); validate_report('report.21');
    sysrun('cat job.21 | ar-get -w -p > contigs.21'); validate_contigs('contigs.21');
}

sub test_compressed_files {
    my $pe1 = 'http://www.mcs.anl.gov/~fangfang/arast/b99_1.fq.gz';
    my $pe2 = 'http://www.mcs.anl.gov/~fangfang/arast/b99_2.fq.gz';
    sysrun("ar-run --pair_url $pe1 $pe2 -a kiki > job.31");
    sysrun('cat job.31 | ar-get -w -p > contigs.31'); validate_contigs('contigs.31');
}

sub test_shock_url_input {
    my $json = sysout('ar-upload --single se.fq --ws-json');
    my $obj;
    my $handle;
    eval {
        $obj = decode_json($json);
        $handle = $obj->{'single_end_libs'}->[0]->{'handle'};
    };
    ok($obj, 'AssemblyInput is valid json'); $testCount++;
    ok($handle, 'AssemblyInput contains a handle'); $testCount++;
    return unless $handle;
    # "https://kbase.us/services/shock-api/node/95d35067-ccb2-40ac-8fb3-47aadbcf0b5a?download"
    my $url = sprintf("%s/node/%s?download", $handle->{url} || $handle->{shock_url}, $handle->{id} || $handle->{shock_id});
    sysrun("ar-run -a kiki --single_url '$url' -m test_shock_token_url > job.41");
    sysrun('cat job.41 | ar-get -w -p > contigs.41'); validate_contigs('contigs.41');
}

sub test_kill_requests {
    my $out;
    $se  = 'http://www.mcs.anl.gov/~fangfang/arast/se.fastq';
    sysrun("ar-run -a kiki --single_url $se -m 'kill after done' >job.51");

    $out = sysout('ar-kill -j 9999999');
    like($out, qr/Invalid/, "Invalid job handled correctly for kill request: '$out'"); $testCount++;

    sysrun("cat job.51 | ar-get --wait --pick > contigs.51");
    validate_contigs('contigs.51');

    $out = sysout('ar-kill -j $(cat job.51|sed "s/[^0-9]*//g")');
    like($out, qr/No longer running/, "Completed job handled correctly for kill request: '$out'"); $testCount++;
}

sub validate_contigs {
    my ($file) = @_;
    my $out = sysout("head $file |grep '^>'");
    like($out, qr/\S/, "$file has valid contigs"); $testCount++;
}

sub validate_report {
    my ($file) = @_;
    my $out = sysout("head -n 20 $file");
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
    ok($out =~ /Recipe.*fast.*rast/sg && $out =~ /auto/, "$file has valid recipes"); $testCount++;
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
    my ($command, $message, $expected_error) = @_;
    $message ||= abbrev_cmd($command);

    $testCount++;

    my $out;
    if (! $expected_error) {
        eval { $out = `$command` };
        diag("unable to run: $command") if $EVAL_ERROR;
        ok(!$CHILD_ERROR, (caller(1))[3] ." > ". $message);
        diag("errno: $CHILD_ERROR") if $CHILD_ERROR;
    } else {
        eval { $out = `$command 2>/dev/stdout` };
        my $rc = ($CHILD_ERROR >> 8);
        ok($rc == $expected_error || $rc == 255, # perl die returns 65280 (=255<<8)
           "Expecting error $expected_error: ". (caller(1))[3] ." > ". $message);
    }

    exit_if_ctrl_c($CHILD_ERROR);

    chomp($out); $out =~ s/\n$//;
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
