#!/kb/runtime/bin/perl
use strict vars;
use warnings;
use Test::More;
use Data::Dumper;

$ENV{ARASTURL}      = "140.221.84.124";
$ENV{KB_DEPLOYMENT} = "/kb/deployment" unless defined $ENV{KB_DEPLOYMENT};
$ENV{PATH}          = "$ENV{KB_DEPLOYMENT}/bin:$ENV{PATH}";

my $testCount = 0;
#NOTE ALL FILES CREATED OR BROUGHT IN BY THIS TEST SHOULD BE REMOVED IN THE zzz_teardown_of_files_test.t


# keep adding tests to this list
my @assemblers = qw(kiki velvet); #kiki velvet
my @files = (
             "-f /mnt/smg.fa", 
             "-f /mnt/bad_file_input.fa", 
             "-f /mnt/smg.fa /mnt/bad_file_input.fa",  
             "-f /mnt/SUB328463_1.fastq", 
             "--pair /mnt/SUB328463_1.fastq /mnt/SUB328463_2.fastq", 
             "-f /mnt/smg.fa /mnt/SUB328463_1.fastq"
            );

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
	my $job_id = run($assembler,$file_inputs);
	$testCount++;
	stat_try($ENV{ARASTURL});
	$testCount++;
	my @results = get($job_id) if $job_id;
	$testCount++ if $job_id;
	stat_try($ENV{ARASTURL});
	$testCount++;
        for my $f (@results) {
            print "Moving file $f to /mnt\n"; 
            my $command = "sudo mv $f /mnt/."; 
            eval {!system("$command > /dev/null") or die $!;}; 
            diag("unable to run $command") if $@; 
        }
    }
}

done_testing($testCount);

#write your tests as subroutnes, add the sub name to @tests
#Should really break up run and get properly passing out the job id to be used later by the get command.
#removed its call because as of now it is exactly the same as the early part of the get function
sub run {
    my $assembler = shift;
    my $file_inputs = shift;
    my $jobid;
    my $command = "ar-run -s $ENV{ARASTURL} -a $assembler $file_inputs -m \"$assembler run command on $file_inputs\"";
    eval {$jobid = `$command` or die $!;};
    ok($? == 0, (caller(0))[3] . " jobid: $jobid");
    diag("unable to run $command") if $@;
    chomp($jobid);
    $jobid = $1 if $jobid =~ /(\d+)/;
    return $jobid;
}

sub stat_try {
    my $env = shift;
    my $command = "ar-stat -s $env";
    eval {!system($command) or die $!;};
    ok(!$@, (caller(0))[3]);
    diag("could not execute $command") if $@;
}

sub get {
    my $jobid = shift;
    my $done;
    print "Waiting for job $jobid to complete.";
    while (1) {
	my $stat = `ar-stat -s $ENV{ARASTURL} -j $jobid 2>/dev/null`;
        if ($stat =~ /success/i) {
            $done = 1;
            print " [done]\n";
            last;
        } elsif ($stat =~ /fail/i) {
            print " Job $jobid completed with no contigs.\n";
            last;
        }
        print ".";
        sleep 10;
    }
    print " [done]\n";
    
    if ($done) {
        my $command = "ar-get -s $ENV{ARASTURL} -j $jobid";
        eval {!system($command) or die $!;};
        ok(!$@, (caller(0))[3]);
        diag("unable to run $command") if $@;
        my @results = map { $jobid ."_". $_ } qw(ctg_qst.tar.gz assemblies.tar.gz report.txt);
        return @results unless $@;
    } else {
        $testCount--;
    }

    return ();
}

sub login {
    my $command = "ar-login";
    eval {!system($command) or die $!;};
    ok(!$@, (caller(0))[3]);
    diag("could not execute $command") if $@;
}


# needed to set up the tests, should be called before any tests are run
sub setup {

    login();
    $testCount++;

    unless (-e "/mnt/smg.fa") {
        my $command_1 = "sudo wget -P /mnt/ http://www.mcs.anl.gov/~fangfang/test/smg.fa";
        eval {!system("$command_1 > /dev/null") or die $!;}; 
        diag("unable to run $command_1") if $@; 
	print "FILE DOES NOT EXIST 1";
    }
    if ((!(-e "/mnt/SUB328463_1.fastq.bz2"))&&(!(-e "/mnt/SUB328463_1.fastq"))) {
	#get zip file
        my $command_2 = "sudo wget -P /mnt/ http://www.mcs.anl.gov/~fangfang/test/SUB328463_1.fastq.bz2";
        eval {!system("$command_2 > /dev/null") or die $!;}; 
        diag("unable to run $command_2") if $@;
    }
    unless  (-e "/mnt/SUB328463_1.fastq") {
	#have zip file no unzip it
        print "Unzipping /mnt/SUB328463_2.fastq.bz2\n"; 
	my $command_3 = "sudo bzip2 -d /mnt/SUB328463_1.fastq.bz2";
        eval {!system("$command_3 > /dev/null") or die $!;}; 
        diag("unable to run $command_3") if $@; 
    }
    if ((!(-e "/mnt/SUB328463_2.fastq.bz2"))&&(!(-e "/mnt/SUB328463_2.fastq"))) {
        #get zip file     
        my $command_4 = "sudo wget -P /mnt/ http://www.mcs.anl.gov/~fangfang/test/SUB328463_2.fastq.bz2"; 
        eval {!system("$command_4 > /dev/null") or die $!;}; 
        diag("unable to run $command_4") if $@;
    }
    unless  (-e "/mnt/SUB328463_2.fastq") {
	#get zip file
        print "Unzipping /mnt/SUB328463_2.fastq.bz2\n"; 
        my $command_5 = "sudo bzip2 -d /mnt/SUB328463_2.fastq.bz2";
        eval {!system("$command_5 > /dev/null") or die $!;};
        diag("unable to run $command_5") if $@;
    }
    unless  (-e "/mnt/bad_file_input.fa") {
	#get bad fasta file to testing
        print "Download /mnt/bad_file_input.fa\n"; 
        my $command_6 = "sudo wget -P /mnt/ http://www.mcs.anl.gov/~fangfang/test/bad_file_input.fa";
        eval {!system("$command_6 > /dev/null") or die $!;};
        diag("unable to run $command_6") if $@;
    }
    # need to add more files types in here.
}


