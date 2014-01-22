#! /usr/bin/env perl

use strict;
use Carp;
use Cwd;
use Data::Dumper;
use File::Basename;
use File::Temp;
use Getopt::Long;

my $usage =<<'End_of_Usage';

usage: pacbio.pl [ options ] components
       
       -h --help                   - print this usage statement
       -d dir                      - SMRT installation directory (D = $cwd/smrt)
       -f seq.bax.h5 [foo.fa ...]  - one or more single end sequence files:
                                     bas.h5 & bax.h5 will be used as PacBio reads
                                     fasta or fastq files will be used as Illumina reads
       -o dir                      - output directory (D = ./out)
       -p p1.fq p2.fq [...]        - one or more paired end libraries as Illumina reads
       -t dir                      - temporary directory (D = /mnt/tmp/smrt)

       --cov float                 - sequencing coverage (D = 15)
       --gs int                    - genome size (D = 5000000)
       --minlong int               - minimum long read length (D = 6000)
       --np int                    - number of processors (D = 8)

End_of_Usage

my ($help, $out_dir, $smrt_dir, $tmp_dir, $setup_sh, @se_files, @pe_files,
    $bigmem, $nproc, $min_long_read_length, $genome_size, $coverage);

GetOptions( 'h|help'         => \$help,
            'd|dir=s'        => \$smrt_dir,
            'f|single=s{1,}' => \@se_files,
            'p|pair=s{2}'    => \@pe_files,
            'o|output=s'     => \$out_dir,   # supercedes smrtpipe.py --output
            's|setup=s'      => \$setup_sh,
            't|tmp=s'        => \$tmp_dir,
            'bigmem'         => \$bigmem,
            'cov=f'          => \$coverage,
            'gs=i'           => \$genome_size,
            'minlong=i'      => \$min_long_read_length,
            'np=i'           => \$nproc
          );

# -m modules
# -p parameters Module.Parameter=xxx
# p_celeraassembler.asmWatchTime = 600
# -r recipe: small demo, ecoli

if ($help) { print $usage; exit 0 }

my ($se_libs, $pe_libs) = process_read_lib_args(\@se_files, \@pe_files, \@ARGV);

smrt_run({ se_libs => $se_libs, pe_libs => $pe_libs, setup_sh => $setup_sh, 
           out_dir => $out_dir, tmp_dir => $tmp_dir, smrt_dir => $smrt_dir,
           coverage => $coverage, genome_size => $genome_size,
           min_long => $min_long_read_length, nproc => $nproc
         });

sub smrt_run {
    my ($opts) = @_;

    my $se_libs  = $opts->{se_libs};
    my $pe_libs  = $opts->{pe_libs};
    my $setup_sh = $opts->{setup_sh};
    my $smrt_dir = $opts->{smrt_dir};
    my $out_dir  = $opts->{out_dir} || 'out';
    my $nproc    = $opts->{nproc}   || 8;
    my $bigmem   = $opts->{bigmem};

    my $tmp_dir  = $opts->{tmp_dir} || '/mnt/tmp/smrt';
    my $cov      = $opts->{coverage};   
    my $gs       = $opts->{genome_size};
    my $min_long = $opts->{min_long};

    my $self_dir = dirname(Cwd::abs_path($0));
    my $rel_path = "install/smrtanalysis-2.1.1.128549/etc/setup.sh";
    $setup_sh  ||= $smrt_dir ? "$smrt_dir/$rel_path" : "$self_dir/smrt/$rel_path";
    $setup_sh && -s $setup_sh or die "Cannot find setup.sh: $setup_sh\n";

    my @files;  # pacbio files: bax.h5 / bas.h5
    if ($se_libs && @$se_libs) {
        for (@$se_libs) { push @files, $_ if /(bax|bas)\.h5$/; }
    }
    @files or die "No pacbio sequence file found: bax.h5 / bas.h5";

    run("mkdir -p $out_dir") if ! -d $out_dir;
    chdir($out_dir);
    
    write_file('runCA.spec', gen_runCA_spec({ nproc => $nproc, bigmem => $bigmem }));
    write_file('input.xml', gen_input_xml(@files));
    write_file('pipeline.xml', gen_hgap2_settings({ tmp_dir => $tmp_dir, run_CA_spec => 'runCA.spec',
                                                    coverage => $cov, genome_size => $gs, min_long => $min_long }));

    # Currently nproc is controlled by runCA.spec, so NPROC here likely makes no difference
    my $smrt_cmd = "smrtpipe.py -D NPROC=$nproc --param=pipeline.xml xml:input.xml";
    my @cmd = ('bash', '-c', "source $setup_sh && $smrt_cmd"); 
    
    run(@cmd);

    my $result_file = "data/polished_assembly.fasta.gz";
    run("zcat $result_file > contigs.fa") if -s $result_file;
}


sub process_read_lib_args {
    my ($se_files, $pe_files, $args) = @_;

    my (@se_libs, @pe_libs);

    if ($args && ref $args eq 'ARRAY') {
        for (@$args) {
            push (@se_libs, $_) if valid_seq_file_type($_) && -s $_;
        }       
    }     
    if ($se_files && ref $se_files eq 'ARRAY') {
        for (@$se_files) {
            push (@se_libs, $_) if valid_seq_file_type($_) && -s $_;
        }       
    }     
    if ($pe_files && ref $pe_files eq 'ARRAY' && @$pe_files >= 2) {
        my $n = @$pe_files;
        $n % 2 and die "Number of paired end files = $n, should be an even number.";
        while (@pe_files) {
            my $p1 = shift @pe_files;
            my $p2 = shift @pe_files;
            die "Paired end file unrecognized or not found: $p1." unless valid_seq_file_type($p1) && -s $p1;
            die "Paired end file unrecognized or not found: $p2." unless valid_seq_file_type($p2) && -s $p2;
            push (@pe_libs, [$p1, $p2]);
        }
    }
    return (\@se_libs, \@pe_libs);
}

sub valid_seq_file_type {
    my ($file) = @_;
    $file =~ s/\.(gz|bz|bz2|zip)$//;
    $file =~ s/\.tar$//;
    return 1 if $file =~ /\.(fasta|fastq|fa|fq|fna|bas\.h5|bax\.h5)$/;
}

# my %env_old = %ENV;
# my %env_new = get_smrt_env($setup_sh, $smrt_dir);
sub get_smrt_env {
    my ($setup_sh, $smrt_dir) = @_;
    my $self_dir = dirname(Cwd::abs_path($0));
    my $rel_path = "install/smrtanalysis-2.1.1.128549/etc/setup.sh";
    $setup_sh ||= $smrt_dir ? "$smrt_dir/$rel_path" : "$self_dir/smrt/$rel_path";
    $setup_sh && -s $setup_sh or die "Cannot find setup.sh: $setup_sh\n";
    open SOURCE, "bash -c '. $setup_sh >& /dev/null; env'|" or die "Can't fork: $!";
    my %env = map { chomp; my ($k, $v) = split(/=/, $_, 2); $k => $v }
              split(/\n(?!\s)/, join('', <SOURCE>));
    close SOURCE;
    wantarray ? %env : \%env;
}

sub run { system(@_) == 0 or confess("FAILED: ". join(" ", @_)); }

sub write_file {
    my ($filename, $output) = @_;
    open(F, ">$filename") or die "Could not open $filename";
    print F $output;
    close(F);
}

sub gen_input_xml {
    my (@files) = @_;
    my @xml;
    push @xml, '<?xml version="1.0"?>';
    push @xml, '<pacbioAnalysisInputs>';
    push @xml, '    <dataReferences>';
    my $i = 0;
    for my $file (@files) {
        push @xml, '    <url ref="run:0000000-000'.$i++.'"><location>'.$file.'</location></url>';
    }
    push @xml, '  </dataReferences>';
    push @xml, '</pacbioAnalysisInputs>';
    return join('', map { $_."\n" } @xml);
}

sub gen_runCA_spec {
    my ($opts) = @_;

    my $nproc  = $opts->{nproc}  || 8;
    my $bigmem = $opts->{bigmem} || guess_system_memory() > 16000000 ? 1 : 0;

    my $merylMemory        = $bigmem ?     128000 : 6000;
    my $ovlStoreMemory     = $bigmem ?      32000 : 6000;
    my $ovlHashBits        = $bigmem ?         26 : 24;
    my $ovlHashBlockLength = $bigmem ? 2000000000 : 200000000;
    my $ovlRefBlockSize    = $bigmem ?   32000000 : 2000000;

    return <<End_of_runCA_spec;
utgErrorRate = 0.06
utgErrorLimit = 4.5

cnsErrorRate = 0.25
cgwErrorRate = 0.25
ovlErrorRate = 0.06

frgMinLen = 500
ovlMinLen = 40

merSize=14

# in MB
merylMemory = $merylMemory
merylThreads = $nproc

ovlStoreMemory = $ovlStoreMemory

# grid info
useGrid = 0
scriptOnGrid = 0
frgCorrOnGrid = 0
ovlCorrOnGrid = 0

sge = -S /bin/bash -sync y -V -q None
sgeScript = -pe None 28
sgeConsensus = -pe None 1
sgeOverlap = -pe None 1
sgeFragmentCorrection = -pe None 2
sgeOverlapCorrection = -pe None 1

ovlHashBits = $ovlHashBits
ovlHashBlockLength = $ovlHashBlockLength
ovlRefBlockSize =  $ovlRefBlockSize

ovlThreads = $nproc
ovlConcurrency = 1
frgCorrThreads = 2
frgCorrBatchSize = 100000
ovlCorrBatchSize = 100000

sgeName = pacbioReads
End_of_runCA_spec
}


sub gen_hgap2_settings {
    my ($opts) = @_;

    my $tmp_dir  = $opts->{tmp_dir}     || '/mnt/tmp/smrt';
    my $cov      = $opts->{coverage}    || 15;
    my $gs       = $opts->{genome_size} || 5000000;
    my $min_long = $opts->{min_long}    || 6000;
    my $CA_spec  = $opts->{run_CA_spec};

    return <<End_of_HGAP2_Settings;
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smrtpipeSettings>
    <protocol id="ARAST_HGAP2">
        <param name="otfReference"><value>reference</value></param>
        <param name="deferRefCheck"><value>True</value></param>
    </protocol>
    <module id="P_Fetch" />
    <module id="P_Filter" >
        <param name="minLength"><value>100</value></param>
        <param name="minSubReadLength"><value>500</value></param>
        <param name="readScore"><value>0.80</value></param>
    </module>
    <module id="P_PreAssemblerDagcon">
        <param name="computeLengthCutoff"><value>true</value></param>
        <param name="minLongReadLength"><value>$min_long</value></param>
        <param name="targetChunks"><value>6</value></param>
        <param name="splitBestn"><value>11</value></param>
        <param name="totalBestn"><value>24</value></param>
        <param name="blasrOpts"><value> -noSplitSubreads -minReadLength 200 -maxScore -1000 -maxLCPLength 16 </value></param>
    </module>
    <module id="P_CeleraAssembler">
        <param name="genomeSize"><value>$genome_size</value></param>
        <param name="libraryName"><value>pacbioReads</value></param>
        <param name="asmWatchTime"><value>2592000</value></param>
        <param name="xCoverage"><value>$coverage</value></param>
        <param name="ovlErrorRate"><value>0.06</value></param>
        <param name="ovlMinLen"><value>40</value></param>
        <param name="merSize"><value>14</value></param>
        <param name="defaultFrgMinLen"><value>500</value></param>
        <param name="genFrgFile"><value>True</value></param>
        <param name="runCA"><value>False</value></param>
        <param name="asm2afg"><value>False</value></param>
        <param name="castats"><value>False</value></param>
        <param name="afg2bank"><value>False</value></param>
        <param name="runBank2CmpH5"><value>False</value></param>
        <param name="assemblyBnkReport"><value>False</value></param>
        <param name="sortCmpH5"><value>False</value></param>
        <param name="gzipGff"><value>False</value></param>
        <param name="specInRunCA"><value>$CA_spec</value></param>
    </module>
    <module id="P_ReferenceUploader">
        <param name="runUploaderHgap"><value>True</value></param>
        <param name="runUploader"><value>False</value></param>
        <param name="name"><value>reference</value></param>
        <param name="sawriter"><value>sawriter -blt 8 -welter</value></param>
        <param name="gatkDict"><value>createSequenceDictionary</value></param>
        <param name="samIdx"><value>samtools faidx</value></param>
    </module>
    <module id="P_Mapping">
        <param name="align_opts"><value>--tmpDir=$tmp_dir --minAccuracy=0.75 --minLength=50 </value></param>
    </module>
    <module id="P_AssemblyPolishing">
    </module>
</smrtpipeSettings>
End_of_HGAP2_Settings
}

sub guess_system_memory {
    my ($cpu, $mem);
    $cpu = `cat /proc/cpuinfo |grep processor|wc -l` if -e '/proc/cpuinfo'; chomp($cpu);
    $mem = `cat /proc/meminfo |grep MemTotal` if -e '/proc/meminfo'; ($mem) = $mem =~ /(\d+)/; 
    my $mem_per_core = int($mem / $cpu) if $mem > 0 && $cpu > 0;
    return $mem_per_core;
}
