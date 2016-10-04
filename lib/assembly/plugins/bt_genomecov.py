import logging
import os
from plugins import BaseAssessment
from yapsy.IPlugin import IPlugin
from asmtypes import ArastDataOutputError

logger = logging.getLogger(__name__)

class BtGenomecovAssessment(BaseAssessment, IPlugin):
    OUTPUT = 'report'
    def run(self):
        """
        Build the command and run.
        Return list of file(s)
        """
        contigs = self.data.contigfiles
        reads = self.data.readsets
        if len(contigs) > 1:
            raise Exception('Reapr: multiple contig files!')

        if len(reads) > 1:
            self.out_module.write('WARNING: Coverage analysis will use only one read library')

        #### Reapr changes headers, so we need do it here so downstream feature mapping works
        target_contigs_prefix = contigs[0] + '.facheck'
        target_contigs = contigs[0] + '.facheck.fa'
        if not os.path.exists(target_contigs):
            cmd_args = [self.reapr_bin, 'facheck', contigs[0], target_contigs_prefix]
            self.arast_popen(cmd_args)

        #### Run Reapr
        reapr_results = self.plugin_engine.run_expression('(reapr (contigs {}) READS)'.format(target_contigs))
        reapr_file = reapr_results.files[0]
        reapr_file2 = reapr_results.files[1]
        reapr_filename = os.path.basename(reapr_file)
        reapr_filename2 = os.path.basename(reapr_file2)
        os.rename(reapr_file, os.path.join(self.outpath, reapr_filename))
        os.rename(reapr_file2, os.path.join(self.outpath, reapr_filename2))
        print reapr_file
        print reapr_file2
        #### Generate Bamfiles
        bwa_results = self.plugin_engine.run_expression('(bwa (contigs {}) READS)'.format(target_contigs))
        samfile = bwa_results.files[0]
        bamfile = samfile.replace('.sam', '.bam')
        cmd_args = ['samtools', 'view',
                    '-bSho', bamfile, samfile]
        self.arast_popen(cmd_args, overrides=False)
        sortedfile = os.path.join(self.outpath, 'out')
        cmd_args = ['samtools', 'sort', bamfile, sortedfile]
        self.arast_popen(cmd_args, overrides=False)
        sortedfile = sortedfile + '.bam'

        genomecov_hist_file = sortedfile + '.covhist.tsv'
        genomecov_perbase_file = sortedfile + '.cov.perbase.tsv'
        cmd_args = [self.executable, '-ibam', sortedfile, '>', genomecov_hist_file]
        self.arast_popen(' '.join(cmd_args), shell=True, overrides=False)
        cmd_args = [self.executable, '-d', '-split', '-ibam', 
                    sortedfile, '>', genomecov_perbase_file]
        self.arast_popen(' '.join(cmd_args), shell=True, overrides=False)

        # Generate Pileup
        pileup_file = os.path.join(self.outpath, 'out.pileup')
        cmd_args = ['samtools', 'mpileup', '-f', target_contigs, sortedfile, '>', pileup_file]
        self.arast_popen(' '.join(cmd_args), shell=True, overrides=False)


        # Generate SNPs
        ref = self.initial_data.referencefiles[0] or None
        asm = target_contigs
        prefix = os.path.join(self.outpath, os.path.basename(asm) + '.nucmer')
        min_align_len = 9000
        min_len = 50

        cmd = 'nucmer {} {} -p {} -l {} --maxmatch'.format(ref, asm, prefix, min_len)    
        self.arast_popen(cmd, shell=True)

        delta_cmd = 'delta-filter -l {0} {1}.delta > {1}.filtered.delta'.format(min_align_len, prefix)
        self.arast_popen(delta_cmd, shell=True)

        filtered_nucmer_file = '{}.filtered.delta'.format(prefix)
        snps_file = filtered_nucmer_file + '.snps'
        showsnps_cmd = 'show-snps -T {} > {}'.format(filtered_nucmer_file, snps_file)
        self.arast_popen(showsnps_cmd, shell=True)

        output = {'report': pileup_file,
                  'genomecov_hist': genomecov_hist_file,
                  'genomecov_perbase': genomecov_perbase_file,
                  'delta_filtered' : filtered_nucmer_file,
                  'snp_file': snps_file
        }

        return output

