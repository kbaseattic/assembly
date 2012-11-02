#!/kb/runtime/bin/perl
use strict vars;
use warnings;

#THIS IS SOLELY A CLEANUP OF THE FILES THAT WERE CREATED BY THE oct_build_test.t
#If this test is not run the files will persist, but allow for further inspection by the tester.
#Note the name of this starts with zzz to insure it runs last with the automated testing.

teardown();
exit 0;


sub teardown {
	unlink "smg.fa" if -e "smg.fa";
	unlink glob "job*.tar";
}
