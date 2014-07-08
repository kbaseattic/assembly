
use strict;
use Getopt::Long;
use assembly::gjoseqlib;

my $usage = <<End_of_Usage;

Usage: ar-filter [-h] [-l min_len]

Filter contigs 

Optional arguments:
  -h, --help     show this help message and exit
  -l minlen      filter contigs by minimal length (D = 1000)
  -c mincov      filter contigs by minimal coverage info in FASTA headers (D = 0.0)

End_of_Usage

my $help;
my $minlen = 1000;
my $mincov = 0.0;

my $rc = GetOptions("h|help"     => \$help,
                    "l|minlen=i" => \$minlen,
                    "c|minlen=f" => \$mincov);

$rc or die $usage;
if ($help) {
    print $usage;
    exit 0;
}

my @seqs = gjoseqlib::read_fasta();
@seqs = grep { length $_->[2] >= $minlen } @seqs;

if ($mincov > 0) {
    @seqs = grep { ($_->[0].$_->[1]) !~ /cov[_ :=]([0-9.]+)/i || $1 >= $mincov } @seqs;
}

gjoseqlib::print_alignment_as_fasta(\@seqs);

