
use strict;
use Getopt::Long;
use assembly::gjoseqlib;

my $usage = <<End_of_Usage;

Usage: ar-filter [-h] [-l min_len]

Filter contigs 

Optional arguments:
  -h, --help            show this help message and exit
  -l min_contig_len     filter contigs by minimal length (D = 1000)

End_of_Usage

my $help;
my $minlen = 1000;

my $rc = GetOptions("h|help"     => \$help,
                    "l|minlen=i" => \$minlen);

$rc or die $usage;
if ($help) {
    print $usage;
    exit 0;
}

my @seqs = gjoseqlib::read_fasta();
@seqs = grep { length $_->[2] >= $minlen } @seqs;

gjoseqlib::print_alignment_as_fasta(\@seqs);


