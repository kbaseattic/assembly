#!/kb/runtime/bin/perl

use strict vars;
use warnings;
use Test::More;
use Data::Dumper;

my $arg_url   = "-s $ENV{ARAST_URL}"   if $ENV{ARAST_URL};   # default: 140.221.84.124
my $arg_queue = "-q $ENV{ARAST_QUEUE}" if $ENV{ARAST_QUEUE};

$ENV{KB_DEPLOYMENT} = "/kb/deployment" unless defined $ENV{KB_DEPLOYMENT};
$ENV{PATH}          = "$ENV{KB_DEPLOYMENT}/bin:$ENV{PATH}";



# Test new assemblers: SPAdes, Ray, PacBio
#   using the new upload and run mechanism

my $testCount = 0;

my @pe_assemblers = qw(spades ray); 
my @pe_libs = ( "--pair /mnt/b99_1.fq /mnt/b99_2.fq" );

my @pb_assemblers = ('pacbio ?min_long_read_length=3500 ?genome_size=40000');
my @pb_libs = ( "--single /mnt/m120404.bas.h5 -r /mnt/lambda.fasta" );

my @cases;

foreach my $assember (@pe_assemblers) {
    foreach my $lib (@pe_libs) {
        push @cases, [ $assember, $lib ];
    }
}
foreach my $assember (@pb_assemblers) {
    foreach my $lib (@pb_libs) {
        push @cases, [ $assember, $lib ];
    }
}

setup();

for (@cases) {
    my ($assembler, $dataset) = @$_;
    my ($name) = split(/\s+/, $assembler);
    print "Performing assembler tests for $name \n";
    my $data_id = upload($dataset);
    $testCount++;
    my $job_id = run_on_data($assembler, $data_id, $dataset);
    $testCount++;
    stat_try($ENV{ARAST_URL});
    $testCount++;
    my @results = get($job_id) if $job_id;
    $testCount++ if $job_id;
    stat_try($ENV{ARAST_URL});
    $testCount++;
    for my $f (@results) {
        print "Moving file $f to /mnt\n"; 
        my $command = "sudo mv $f /mnt/."; 
        eval {!system("$command > /dev/null") or die $!;}; 
        diag("unable to run $command") if $@; 
    }
}

done_testing($testCount);



sub upload {
    my $dataset = shift;
    my $data_id;
    my $command = "ar-upload $arg_url $dataset";
    eval {$data_id = `$command` or die $!;};
    ok($? == 0, (caller(0))[3] . " Data ID: $data_id");
    diag("unable to run $command") if $@;
    chomp($data_id);
    $data_id = $1 if $data_id =~ /(\d+)/;
    return $data_id;
}

sub run_on_data {
    my $assembler = shift;
    my $data_id = shift;
    my $dataset = shift;
    my $jobid;
    my $command = "ar-run $arg_url $arg_queue -a $assembler --data $data_id -m \"Run $assembler on $dataset (id=$data_id)\"";
    print "$command\n";
    eval {$jobid = `$command` or die $!;};
    ok($? == 0, (caller(0))[3] . " jobid: $jobid");
    diag("unable to run $command") if $@;
    chomp($jobid);
    $jobid = $1 if $jobid =~ /(\d+)/;
    return $jobid;
}

sub run {
    my $assembler = shift;
    my $file_inputs = shift;
    my ($name) = split(/\s+/, $assembler);
    my $jobid;
    my $command = "ar-run $arg_url $arg_queue -a $assembler $file_inputs -m \"$name run command on $file_inputs\"";
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
	my $stat = `ar-stat $arg_url -j $jobid 2>/dev/null`;
        if ($stat =~ /(success|complete)/i) {
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
        my $command = "ar-get $arg_url -j $jobid";
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

    my @files = qw(b99_1.fq b99_2.fq m120404.bas.h5 lambda.fasta lambda.fasta);

    foreach my $f (@files) {
        next if -s "/mnt/$f";
        my $cmd = "sudo wget -P /mnt/ http://www.mcs.anl.gov/~fangfang/test/$f";
        eval {!system("$cmd > /dev/null") or die $!;}; 
        diag("unable to run $cmd") if $@; 
    }

}



