#!/kb/runtime/bin/perl
use strict vars;
use warnings;

#THIS IS SOLELY A CLEANUP OF THE FILES THAT WERE CREATED BY THE oct_build_test.t
#If this test is not run the files will persist, but allow for further inspection by the tester.
#Note the name of this starts with zzz to insure it runs last with the automated testing.

teardown();
exit 0;


sub teardown {
    print "Delete uploaded sequence files and assembly results\n";
    if (-e "/mnt/smg.fa") {
        my $command = "sudo rm /mnt/smg.fa"; 
        eval {!system("$command > /dev/null") or die $!;};
        diag("unable to run $command") if $@;
    } 
    if (-e "/mnt/SUB328463_1.fastq.bz2") { 
        my $command = "sudo rm /mnt/SUB328463_1.fastq.bz2";
        eval {!system("$command > /dev/null") or die $!;}; 
        diag("unable to run $command") if $@; 
    }
    if (-e "/mnt/SUB328463_1.fastq") {
	my $command = "sudo rm /mnt/SUB328463_1.fastq"; 
	eval {!system("$command > /dev/null") or die $!;};
	diag("unable to run $command") if $@;
    }
    if (-e "/mnt/SUB328463_2.fastq.bz2") {
        my $command = "sudo rm /mnt/SUB328463_2.fastq.bz2"; 
        eval {!system("$command > /dev/null") or die $!;}; 
        diag("unable to run $command") if $@; 
    } 
    if (-e "/mnt/SUB328463_2.fastq") {
        my $command = "sudo rm /mnt/SUB328463_2.fastq"; 
        eval {!system("$command > /dev/null") or die $!;};
        diag("unable to run $command") if $@;
    } 
    if (-e "/mnt/bad_file_input.fa") {
        my $command = "sudo rm /mnt/bad_file_input.fa"; 
        eval {!system("$command > /dev/null") or die $!;};
        diag("unable to run $command") if $@;
    } 
    my $command = "sudo rm -f /mnt/*_report.txt /mnt/*_assemblies.tar.gz /mnt/*_ctg_qst.tar.gz"; 
    eval {!system("$command > /dev/null") or die $!;}; 
    diag("unable to run $command") if $@; 

#    unlink glob "job*.tar";
}
