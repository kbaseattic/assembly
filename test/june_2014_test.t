#!/kb/runtime/bin/perl

# 2014/06/22 new client interface test

use strict vars;

use Carp;
use Test::More;
use Data::Dumper;
use English;

my $arg_url   = "-s $ENV{ARASTURL}"   if $ENV{ARASTURL};   # default: 140.221.84.124
my $arg_queue = "-q $ENV{ARASTQUEUE}" if $ENV{ARASTQUEUE};

$ENV{KB_DEPLOYMENT} ||= "/kb/deployment";
$ENV{PATH}            = "$ENV{KB_DEPLOYMENT}/bin:$ENV{PATH}";

my @all_tests = qw(login );
my @tests = @ARGV > 0 ? @ARGV : @all_tests;

setup();

my $testCount = 0;
foreach my $testname (@tests) {
    my $test = "test_" . $testname;
    print "\n> Testing $testname\n";
    if (!defined &$test) {
        print "Test routine doesn't exist: $test\n";
        next;
    }
    &$test();
}
done_testing($testCount);

teardown();

# ----------------------------------------------------------
#   Tests
# ----------------------------------------------------------

sub test_upload {
    my $lib = "--pair b99_1.fq b99_2.fq";
    my $cmd = "ar-upload $arg_url $lib";
    my $out = sysout($cmd);
}


sub test_setup {
    test_login();
    test_download_simple_file();
}

sub test_login {
    sysrun("ar-login");
}

sub test_download_simple_file {
    unlink "smg.fa" if -e "smg.fa";
    sysrun("wget http://www.mcs.anl.gov/~fangfang/test/smg.fa");
}

sub test_date {
    my $out = sysout("date");
    like($out, qr/ 20\d+/, whoami(). " date matches");
}

sub test_crash  { sysrun("sh -c 'echo crashed > /dev/stderr; exit 99'") }
sub test_crash2 { sysrun("sh -c 'echo bad exit...; exit 99'") }


# ----------------------------------------------------------
#   Maintenance routines
# ----------------------------------------------------------

sub setup {
    my $dir  = "ar_tmp_dir"; 
    my $root = -w "/mnt" ? "/mnt" : ".";
    my $tmp = "$root/$dir";
    # run("rm -rf $tmp");
    run("mkdir -p $tmp");
    chdir($tmp);
    download_reads();
}

sub download_reads {
    my @files = qw(b99_1.fq b99_2.fq m120404.bas.h5 lambda.fasta lambda.fasta);
    foreach my $f (@files) {
        next if -s $f;
        my $cmd = "wget http://www.mcs.anl.gov/~fangfang/test/$f";
        run($cmd);
    }
}

sub teardown {
    # unlink "smg.fa" if -e "smg.fa";
    # unlink glob "job*.tar";
}

# ----------------------------------------------------------
#   Helper routines
# ----------------------------------------------------------

sub sysrun {
    my ($command, $message) = @_;
    $message ||= abbrev_cmd($command);

    $testCount++;

    eval { !system($command) or die $ERRNO };
    diag("unable to run: $command") if $EVAL_ERROR;
    ok(!$EVAL_ERROR, (caller(1))[3] ." > ". $message);
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

    print $out;
    return $out;
}


sub run { system(@_) == 0 or confess("FAILED: ". join(" ", @_)); }

sub abbrev_cmd { length $_[0] < 50 ? $_[0] : substr($_[0], 0, 50)."..." }

sub whoami { (caller(1))[3] }
