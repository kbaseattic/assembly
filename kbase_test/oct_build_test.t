#!/kb/runtime/bin/perl
use strict vars;
use warnings;
use Test::More;

$ENV{ARASTURL}      = "140.221.84.124";
$ENV{KB_DEPLOYMENT} = "/kb/deployment" unless defined $ENV{KB_DEPLOYMENT};
$ENV{PATH}          = "$ENV{KB_DEPLOYMENT}/bin:$ENV{PATH}";

my $testCount = 0;
#NOTE ALL FILES CREATED OR BROUGHT IN BY THIS TEST SHOULD BE REMOVED IN THE zzz_teardown_of_files_test.t


# keep adding tests to this list
my @tests = qw(stat get stat);  #run was also in this list but it appears to be duplicate code to the beginning of get
my @assemblers = qw(kiki velvet);
my @files = qw(smg.fa);

#THIS FILE was to test bad input files and how the program responds.
#Unfortunately the program hangs on this.  It stays in a perpetual Queued state and does not let any other subsequent jobs to be run.
#bad_input.fa);

setup();
# add other fastq file type.  Do testing on fasta, fastq, and fasta and fastq together
# do testing having gobbly gook file input

foreach my $file_inputs (@files)
{
    foreach my $assembler (@assemblers)
    {
	print "Performing Assembler tests for $assembler \n";
	foreach my $test (@tests) {
	    &$test($assembler,$file_inputs);
	    $testCount++;
	}
    }
}

done_testing($testCount);
teardown();

#write your tests as subroutnes, add the sub name to @tests
#Should really break up run and get properly passing out the job id to be used later by the get command.
#removed its call because as of now it is exactly the same as the early part of the get function
sub run {
    my $assembler = shift;
    my $file_inputs = shift;
    my $jobid;
    my $command = "arast -s $ENV{ARASTURL} run -a $assembler -f $file_inputs --bwa -m \"$assembler run command\"";
    eval {$jobid = `$command` or die $!;};
    ok($? == 0, (caller(0))[3] . " jobid: $jobid");
    diag("unable to run $command") if $@;
}

sub stat {
    my $assembler = shift;
    my $file_inputs = shift;
    my $command = "arast -s $ENV{ARASTURL} stat";
    eval {!system($command) or die $!;};
    ok(!$@, (caller(0))[3]);
    diag("could not execute $command") if $@;
}

sub get {
    my $assembler = shift;
    my $file_inputs = shift;
    # needs code change to arast to only return the job id
    my $jobid;
    my $command = "arast -s $ENV{ARASTURL} run -a $assembler -f $file_inputs --bwa -m \"$assembler get command\"";
    eval {$jobid = `$command` or die $!;};
    ok($? == 0, (caller(0))[3] . " jobid: $jobid");
    diag("unable to run $command") if $@;
    $jobid = $1 if $jobid =~ /\'(\d+)\'/;
    
    my $done;
    print "Waiting for job to complete.";
    while (!$done) {
	my $stat = `arast -s $ENV{ARASTURL} stat -j $jobid`;
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


# needed to set up the tests, should be called before any tests are run
sub setup {
	unlink "smg.fa" if -e "smg.fa";
	my $command_1 = "wget http://www.mcs.anl.gov/~fangfang/test/smg.fa";
	eval {!system("$command_1 > /dev/null") or die $!;};
	diag("unable to run $command_1") if $@;
# needto add more files types in here.
}

#tear down is no longer needed and is handled by the zzz_teardown 
sub teardown {
#	unlink "smg.fa" if -e "smg.fa";
#	unlink glob "job*.tar";
}
