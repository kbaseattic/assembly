
use strict;
use Carp;
use Cwd;
use Config::Simple;
use Data::Dumper;
use File::Basename;
use Getopt::Long;

my $usage = <<End_of_Usage;

Usage: ar-upload [-h]

Upload a dataset to the ARAST server. The dataset can be a combination
of paired-end libraries, single-end libraries and reference genomes.

Optional arguments:
  -h, --help            show this help message and exit
  -f [SINGLE [SINGLE ...]], --single [SINGLE [SINGLE ...]]
                        specify sequence file(s)
  --pair [PAIR [PAIR ...]]
                        Specify a paired-end library and parameters

                        Specify a single end file and parameters
  -r [REFERENCE [REFERENCE ...]], --reference [REFERENCE [REFERENCE ...]]
                        specify sequence file(s)
  -m MESSAGE, --message MESSAGE
                        Attach a description to dataset

End_of_Usage

my ($help, $server, $message, $prefix,
    @se_args, @pe_args, @ref_args);

my $rc = GetOptions(
                    "h|help"             => \$help,
                    'f|single=s{1,}'     => \@se_args,
                    'p|pair=s{2,}'       => \@pe_args,
                    'r|references=s{1,}' => \@ref_args,
                    "m=s"                => \$message,
                    "s=s"                => \$server,
                    # "prefix=s"           => \$prefix,
                   ) or die $usage;

if ($help) { print $usage; exit 0;}


my $config = get_config();
print STDERR '$config = '. Dumper($config);

my $input_data = process_input_args(\@se_args, \@pe_args, \@ref_args, \@ARGV);



sub process_input_args {
    my ($se_args, $pe_args, $ref_args, $other_args) = @_;

    my $data;

    my (@se_libs, @pe_libs, @refs);

    while (@$pe_args) {
        
    }
    
    print STDERR '$pe_args = '. Dumper($pe_args);
    print STDERR '$se_args = '. Dumper($se_args);
}

sub get_config {
    my $self_dir = dirname(Cwd::abs_path($0));
    my $config_dir = "$self_dir/../lib/ar_client";
    my $config_file = "$config_dir/config.py";
    my $cfg = new Config::Simple($config_file);
    my $config = $cfg->param(-block => 'default');
    return $config;
}

sub valid_seq_file_type {
    my ($file) = @_;
    $file =~ s/\.(gz|bz|bz2|zip)$//;
    $file =~ s/\.tar$//;
    return 1 if $file =~ /\.(fasta|fastq|fa|fq|fna|bas\.h5|bax\.h5)$/;
}
