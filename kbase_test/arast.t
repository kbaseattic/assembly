#!/kb/runtime/bin/perl
use strict vars;
use warnings;
use Test::More;

$ENV{ARASTURL}      = "140.221.84.124";
$ENV{KB_DEPLOYMENT} = "/kb/deployment";
$ENV{PATH}          = "$ENV{KB_DEPLOYMENT}/bin:$ENV{PATH}";

my $testCount = 0;

# keep adding tests to this list
my @tests = qw(run stat get prep);

setup();
foreach my $test (@tests) {
        &$test();
        $testCount++;
}

done_testing($testCount);

# write your tests as subroutnes, add the sub name to @tests
sub run {
	my $jobid;
	my $command = "arast -s $ENV{ARASTURL} run -a kiki -f smg.fa --bwa";
        eval {$jobid = `$command` or die $!;};
        ok($? == 0, (caller(0))[3] . " jobid: $jobid");
        diag("unable to run $command") if $@;
}

sub stat {
	my $command = "arast -s $ENV{ARASTURL} stat";
	eval {!system($command) or die $!;};
	ok(!$@, (caller(0))[3]);
	diag("could not execute $command") if $@;
}

sub get {
	# needs code change to arast to only return the job id
	my $jobid;
	my $command = "arast -s $ENV{ARASTURL} run -a kiki -f smg.fa --bwa";
        eval {$jobid = `$command` or die $!;};
        ok($? == 0, (caller(0))[3] . " jobid: $jobid");
        diag("unable to run $command") if $@;
	$jobid = $1 if $jobid =~ /\'(\d+)\'/;

        my $done;
        print "Waiting for job to complete.";
        while (!$done) {
            my $stat = `arast -s $ENV{ARASTURL} get -j $jobid`;
            $done = 1 if $stat =~ /complete/;
            print ".";
            sleep 10;
        }
        print " [done]\n";
	
	$command = "arast -s $ENV{ARASTURL} get -j $jobid";
        eval {!system($command) or die $!;};
        ok(!$@, (caller(0))[3]);
        diag("unable to run $command") if $@;

}
sub prep {
}


# needed to set up the tests, should be called before any tests are run
sub setup {
	unlink "smg.fa" if -e "smg.fa";
	my $command = "wget http://www.mcs.anl.gov/~fangfang/test/smg.fa";
	eval {!system("$command > /dev/null") or die $!;};
	ok(!$@, (caller(0))[3]);
	diag("unable to run $command") if $@;
}

