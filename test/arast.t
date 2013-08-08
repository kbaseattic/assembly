#!/kb/runtime/bin/perl
use strict vars;
use warnings;
use Test::More;

$ENV{ARASTURL}      = "140.221.84.124";
$ENV{KB_DEPLOYMENT} = "/kb/deployment" unless defined $ENV{KB_DEPLOYMENT};
$ENV{PATH}          = "$ENV{KB_DEPLOYMENT}/bin:$ENV{PATH}";

my $testCount = 0;

# keep adding tests to this list
my @tests = qw(setup run stat get prep);

foreach my $test (@tests) {
    &$test();
    $testCount++;
}

done_testing($testCount);
teardown();

# write your tests as subroutnes, add the sub name to @tests

sub login {
    my $command = "ar-login";
    eval {!system($command) or die $!;};
    ok(!$@, (caller(0))[3]);
    diag("could not execute $command") if $@;
}

sub run {
    my $jobid;
    my $command = "ar-run -s $ENV{ARASTURL} -a kiki -f smg.fa";
    eval {$jobid = `$command` or die $!;};
    ok($? == 0, (caller(0))[3] . " jobid: $jobid");
    diag("unable to run $command") if $@;
    if ($@) {
        return undef;
    } else {
        return $jobid;
    }
}

sub stat {
    my $command = "ar-stat -s $ENV{ARASTURL}";
    eval {!system($command) or die $!;};
    ok(!$@, (caller(0))[3]);
    diag("could not execute $command") if $@;
}

sub get {
    my $jobid;
    my $command = "ar-run -s $ENV{ARASTURL}  -a kiki -f smg.fa";
    eval {$jobid = `$command` or die $!;};
    ok($? == 0, (caller(0))[3] . " jobid: $jobid");
    diag("unable to run $command") if $@;
    chomp($jobid);
    $jobid = $1 if $jobid =~ /(\d+)/;

    `ar-stat -s $ENV{ARASTURL}`;
    print "Waiting for job to complete.";
    my $done;
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

    if ($done) {
        print "Get results for completed job $jobid..\n";
        $command = "ar-get -s $ENV{ARASTURL} -j $jobid";
        eval {!system($command) or die $!;};
        ok(!$@, (caller(0))[3]);
        diag("unable to run $command") if $@;
    }

    my $invalid_id = '999999999999999999';
    my $stat = `ar-get -s $ENV{ARASTURL} -j $invalid_id`;
    if ($stat =~ /invalid/) {
        print "Correctly identified invalid job\n";
    }
    
}
sub prep {
}


# needed to set up the tests, should be called before any tests are run
sub setup {
    $testCount++;
    login();

    system "rm -rf tmpdir" if -d "tmpdir";
    system "mkdir -p tmpdir";
    chdir("tmpdir");
    unlink "smg.fa" if -e "smg.fa";
    my $command = "wget http://www.mcs.anl.gov/~fangfang/test/smg.fa";
    eval {!system("$command > /dev/null") or die $!;};
    ok(!$@, (caller(0))[3]);
    diag("unable to run $command") if $@;
}

sub teardown {
    unlink "smg.fa" if -e "smg.fa";
    # unlink glob "job*.tar";
}
