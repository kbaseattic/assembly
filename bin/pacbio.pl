#! /usr/bin/env perl

use strict;
use Carp;
use Cwd;
use Data::Dumper;
use File::Basename;
use File::Temp;
use Getopt::Long;

my $usage =<<"End_of_Usage";

Usage pacbio.pl [ options ] components

End_of_Usage

my ($help, $in_files, $out_dir, $smrt_dir, $tmp_dir, $setup_sh);

GetOptions( 'h|help'     => \$help,
            'd|dir=s'    => \$smrt_dir,
            'i|input=s'  => \$in_files,
            'o|output=s' => \$out_dir,   # supercedes smrtpipe.py --output
            's|setup=s'  => \$setup_sh,
            't|tmp=s'    => \$tmp_dir
          );

# -m modules
# -p parameters Module.Parameter=xxx
# p_celeraassembler.asmWatchTime = 600
# -r recipe: small demo, ecoli

if ($help) { print $usage; exit 0 }


form_smrt_cmd(undef, { in_files => $in_files, out_dir => $out_dir, setup_sh => $setup_sh, smrt_dir => $smrt_dir } );

sub form_smrt_cmd {
    my ($files, $opts) = @_;

    my $setup_sh = $opts->{setup_sh};
    my $smrt_dir = $opts->{smrt_dir};
    my $out_dir  = $opts->{out_dir};

    my $self_dir = dirname(Cwd::abs_path($0));
    my $rel_path = "install/smrtanalysis-2.1.1.128549/etc/setup.sh";
    $setup_sh  ||= $smrt_dir ? "$smrt_dir/$rel_path" : "$self_dir/smrt/$rel_path";
    $setup_sh && -s $setup_sh or die "Cannot find setup.sh: $setup_sh\n";

    # my $file = '/space/ar-compute/assembly-rast/bin/smrt/current/common/test/primary/lambda/Analysis_Results/m120404_104101_00114_c100318002550000001523015908241265_s1_p0.bas.h5';
    my @files = @ARGV;

    run("mkdir -p $out_dir") if ! -d $out_dir;
    chdir($out_dir);

    my $input_xml = 'input.xml';
    open(F, ">$input_xml") or die "Could not open $input_xml";
    print F '<?xml version="1.0"?>
<pacbioAnalysisInputs>
  <dataReferences>
';
    my $i = 0;
    for my $file (@files) {
        print F '    <url ref="run:0000000-000'.$i++.'"><location>'.$file.'</location></url>'."\n";
    }
    print F '  </dataReferences>
</pacbioAnalysisInputs>
';
    close(F);

    my $pipeline_xml = 'pipeline.xml';
    open(F, ">$pipeline_xml") or die "Could not open $pipeline_xml";

    # <param name="otfReference" hidden="true"><value>reference</value></param>
    # <param name="minLongReadLength"><value>1000</value></param>
    # <module id="P_Mapping">
    # </module>
    # <module id="P_AssemblyPolishing">
    # </module>

    # P_CeleraAssembler
    # defaultFrgMinLen (500), xCoverage (30, typically 15-25), ovlMinLen (40)
#     print F '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
# <smrtpipeSettings>
#     <module id="P_Fetch" />
#     <module id="P_Filter" >
#         <param name="minLength"><value>100</value></param>
#         <param name="minSubReadLength"><value>500</value></param>
#         <param name="readScore"><value>0.80</value></param>
#     </module>
#     <module id="P_PreAssemblerDagcon">
#         <param name="computeLengthCutoff"><value>true</value></param>
#         <param name="minLongReadLength"><value>3500</value></param>
#         <param name="targetChunks"><value>6</value></param>
#         <param name="splitBestn"><value>11</value></param>
#         <param name="totalBestn"><value>24</value></param>
#         <param name="blasrOpts"><value> -noSplitSubreads -minReadLength 200 -maxScore -1000 -maxLCPLength 16 </value></param>
#     </module>
#     <module id="P_CeleraAssembler">
#         <param name="genomeSize"><value>40000</value></param>
#         <param name="libraryName"><value>pacbioReads</value></param>
#         <param name="asmWatchTime"><value>60000</value></param>
#     </module>
# </smrtpipeSettings>
# ';

#     print F '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
# <smrtpipeSettings>
#     <protocol id="ARAST_HGAP2">
#         <param name="otfReference"><value>reference</value></param>
#         <param name="deferRefCheck"><value>True</value></param>
#     </protocol>
#     <module id="P_Fetch" />
#     <module id="P_Filter" >
#         <param name="minLength"><value>100</value></param>
#         <param name="minSubReadLength"><value>500</value></param>
#         <param name="readScore"><value>0.80</value></param>
#     </module>
#     <module id="P_PreAssemblerDagcon">
#         <param name="computeLengthCutoff"><value>true</value></param>
#         <param name="minLongReadLength"><value>3500</value></param>
#         <param name="targetChunks"><value>6</value></param>
#         <param name="splitBestn"><value>11</value></param>
#         <param name="totalBestn"><value>24</value></param>
#         <param name="blasrOpts"><value> -noSplitSubreads -minReadLength 200 -maxScore -1000 -maxLCPLength 16 </value></param>
#     </module>
#     <module id="P_CeleraAssembler">
#         <param name="genomeSize"><value>40000</value></param>
#         <param name="libraryName"><value>pacbioReads</value></param>
#         <param name="asmWatchTime"><value>2592000</value></param>
#         <param name="xCoverage"><value>15</value></param>
#     </module>
#     <module id="P_ReferenceUploader">
#         <param name="runUploaderHgap"><value>True</value></param>
#         <param name="runUploader"><value>False</value></param>
#         <param name="name"><value>reference</value></param>
#         <param name="sawriter"><value>sawriter -blt 8 -welter</value></param>
#         <param name="gatkDict"><value>createSequenceDictionary</value></param>
#         <param name="samIdx"><value>samtools faidx</value></param>
#     </module>
#     <module id="P_Mapping">
#         <param name="align_opts"><value>--tmpDir=/mnt/tmp/smrt --minAccuracy=0.75 --minLength=50 </value></param>
#     </module>
#     <module id="P_AssemblyPolishing">
#     </module>
# </smrtpipeSettings>
# ';

    print F '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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
        <param name="minLongReadLength"><value>6000</value></param>
        <param name="targetChunks"><value>6</value></param>
        <param name="splitBestn"><value>11</value></param>
        <param name="totalBestn"><value>24</value></param>
        <param name="blasrOpts"><value> -noSplitSubreads -minReadLength 200 -maxScore -1000 -maxLCPLength 16 </value></param>
    </module>
    <module id="P_CeleraAssembler">
        <param name="genomeSize"><value>5000000</value></param>
        <param name="libraryName"><value>pacbioReads</value></param>
        <param name="asmWatchTime"><value>2592000</value></param>
        <param name="xCoverage"><value>15</value></param>
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
        <param name="align_opts"><value>--tmpDir=/mnt/tmp/smrt --minAccuracy=0.75 --minLength=50 </value></param>
    </module>
    <module id="P_AssemblyPolishing">
    </module>
</smrtpipeSettings>
';

    close(F);

    # my $smrt_cmd = 'smrtpipe.py -h';
    # my $smrt_cmd = 'smrtpipe.py --version';
    # my $smrt_cmd = 'smrtpipe.py --examples';
    # my $smrt_cmd = 'smrtpipe.py --output /mnt/tmp/test';
    # my $smrt_cmd = 'smrtpipe.py --recover --param=pipeline.xml xml:input.xml';

    my $smrt_cmd = 'smrtpipe.py -D NPROC=16 --param=pipeline.xml xml:input.xml';
    my @cmd = ('bash', '-c', "source $setup_sh && $smrt_cmd"); 
    # print STDERR '\@cmd = '. Dumper(\@cmd);
    
    run(@cmd);

    my $result_file = "data/polished_assembly.fasta.gz";
    run("zcat $result_file > contigs.fa") if -s $result_file;

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
