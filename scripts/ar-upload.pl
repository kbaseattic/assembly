
use strict;
use Carp;
use Cwd;
use Config::Simple;
use Data::Dumper;
use File::Basename;
use Getopt::Long;

my $usage = <<End_of_Usage;

Usage: ar-upload [ options ]

Upload a dataset to the ARAST server. The dataset can be a combination
of paired-end libraries, single-end libraries and reference genomes.

Optional arguments:
  -h, --help                         - show this help message and exit
  -f --single     file ...           - single end sequence file(s)
  --pair          f1 f2 key=val ...  - paired end sequence file(s) and parameters
  -r --reference  file key=val ...   - reference genome(s) and parameters
  --cov           float              - expected coverage
  --gs            int                - estimated genome size in base pairs
  -m              "text"             - dataset description
  --prefix        string             - dataset prefix string

Supported sequence file types:
  fasta fa fna  (FASTA and compressed forms)
  fastq fq      (FASTQ and compressed forms)
  bas.h5 bax.h5 (PacBio reads)

Examples:
  Upload a hybrid library of paired and single reads:
    % ar-upload --pair r1.fastq r2.fastq insert=300 stdev=60 --single unpaired.fasta --pair f1.fq f2.fq insert=180
  Upload PacBio reads with a reference assembly:
    % ar-upload -f pb1.bas.h5 -f pb2.bas.h5 --cov 15.0 --gs 40000 -r lambda.fa name="Lambda phage"

End_of_Usage

my ($help, $server, %params,
    @se_args, @pe_args, @ref_args);

my $rc = GetOptions(
                    "h|help"             => \$help,
                    'f|single=s{1,}'     => \@se_args,
                    'p|pair=s{2,}'       => \@pe_args,
                    'r|references=s{1,}' => \@ref_args,
                    "s=s"                => \$server,
                    "cov=f"              => sub { $params{expected_coverage}     = $_[1] },
                    "gs=i"               => sub { $params{estimated_genome_size} = $_[1] },
                    "m=s"                => sub { $params{dataset_description}   = $_[1] },
                    "prefix=s"           => sub { $params{dataset_prefix}        = $_[1] },
                   ) or die $usage;

if ($help) { print $usage; exit 0;}


my $config = get_config();
print STDERR '$config = '. Dumper($config);

my ($user, $token) = authenticate($config);

my $input_data = process_input_args(\@se_args, \@pe_args, \@ref_args, \%params);

sub authenticate {
    my ($config) = @_;
    my ($user, $token);
    if ($ENV{KB_RUNNING_IN_IRIS}) {
        $user  = $ENV{KB_AUTH_USER_ID};
        $token = $ENV{KB_AUTH_TOKEN};
        if (!$user || $token) {
            print "Please authenticate with KBase credentials\n";
            exit 0;
        }
    } else {
        
    }
    
}

sub post {
    my ($json, $user, $pass) = @_;
}


sub process_input_args {
    my ($se_args, $pe_args, $ref_args, $params) = @_;

    my (@se_libs, @pe_libs, @refs);

    my %se_param_map;
    my %pe_param_map  = ( insert => 'insert_size_mean', stdev => 'insert_size_std_dev' );
    my %ref_param_map = ( name => 'reference_name' );

    my $i;
    for (@$ref_args) {
        if (/(\S.*?)=(.*)/) {
            my $param_key = $ref_param_map{$1} ? $ref_param_map{$1} : $1;
            $refs[$i]->{$param_key} = $2;
        } else {
            my $file = validate_seq_file($_);
            $refs[$i++]->{handle} = $file;
        }
    }

    $i = 0;
    for (@$se_args) {
        if (/(\S.*?)=(.*)/) {
            my $param_key = $se_param_map{$1} ? $se_param_map{$1} : $1;
            $se_libs[$i]->{$param_key} = $2;
        } else {
            my $file = validate_seq_file($_);
            $se_libs[$i++]->{handle} = $file;
        }
    }

    my @pair;
    $i = 0;
    for (@$pe_args) {
        if (/(\S.*?)=(.*)/) {
            my $param_key = $pe_param_map{$1} ? $pe_param_map{$1} : $1;
            $pe_libs[$i]->{$param_key} = $2;
        } else {
            my $file = validate_seq_file($_);
            if (@pair == 2) { 
                $pe_libs[$i]->{handle_1} = $pair[0];
                $pe_libs[$i]->{handle_2} = $pair[1];
                @pair = ( $file );
                $i++;
            } else {
                push @pair, $file;
            }
        }
    }
    if (@pair == 2) {
        $pe_libs[$i]->{handle_1} = $pair[0];
        $pe_libs[$i]->{handle_2} = $pair[1];
    } else {
        die "Incorrect number of paired end files.\n"
    }

    my $data = { paired_end_libs => \@pe_libs,
                 single_end_libs => \@se_libs,
                 references      => \@refs,
                 %params
               };

    print STDERR '$data = '. Dumper($data);
}

sub get_config {
    my $self_dir = dirname(Cwd::abs_path($0));
    my $config_dir = "$self_dir/../lib/ar_client";
    my $config_file = "$config_dir/config.py";
    my $cfg = new Config::Simple($config_file);
    my $config = $cfg->param(-block => 'default');
    return $config;
}

sub validate_seq_file {
    my ($file) = @_;
    -s $file or die "Invalid file: $file\n";
    my $name = $file;
    $name =~ s/\.(gz|gzip|bzip|bzip2|bz|bz2|zip)$//;
    $name =~ s/\.tar$//;
    $name =~ /\.(fasta|fastq|fa|fq|fna|bas\.h5|bax\.h5)$/ or die "Unrecognized file type: $file\n";
    return { file_name => $file, type => '_handle_to_be_' };
}
