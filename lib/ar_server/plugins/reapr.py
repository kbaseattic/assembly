import copy
import glob
import logging
import os
import subprocess
from plugins import BaseAssessment
from yapsy.IPlugin import IPlugin

class ReaprAssessment(BaseAssessment, IPlugin):
    def run(self, contigs, reads):
        """ 
        Build the command and run.
        Return list of file(s)
        """
        # Fix contig names with 'reapr facheck'
        if len(contigs) > 1:
            raise Exception('Reapr: multiple contig files!')
        fixed_contig = os.path.join(self.outpath,
                     os.path.basename(contigs[0]).rsplit('.', 1)[0] + '_fixed')
        cmd_args = [self.executable, 'facheck', contigs[0], fixed_contig]
        self.arast_popen(cmd_args, overrides=False)
        fixed_contig = fixed_contig + '.fa'
        if len(reads) > 1:
            raise Exception('Reapr: multiple libraries not yet supported!')
        readfiles = reads[0]['files']
        
        #Map with BWA and produce bam
        bwa_data = copy.deepcopy(self.job_data)
        bwa_data['processed_reads'][0]['files'] = readfiles
        bwa_data['contigs'] = [fixed_contig]
        bwa_data['out_report'] = open(os.path.join(self.outpath, 'bwa.log'), 'w')
        samfiles, _, _ = self.pmanager.run_module('bwa', bwa_data)
        samfile = samfiles[0]
        bamfile = samfile.replace('.sam', '.bam')
        cmd_args = ['samtools', 'view',
                    '-bSho', bamfile, samfile]
        self.arast_popen(cmd_args, overrides=False)
        sortedfile = os.path.join(self.outpath, 'sorted')
        cmd_args = ['samtools', 'sort', bamfile, sortedfile]
        self.arast_popen(cmd_args, overrides=False)
        undupfile = sortedfile + '_undup.bam'
        sortedfile = sortedfile + '.bam'

        ## Remove duplicates
        cmd_args = ['samtools', 'rmdup', sortedfile, undupfile]
        self.arast_popen(cmd_args, overrides=False)

        ## reapr preprocess
        rpr_outpath = os.path.join(self.outpath, 'output')
        cmd_args = [self.executable, 'preprocess', fixed_contig, undupfile, rpr_outpath]
        self.arast_popen(cmd_args, overrides=False)

        ## reapr stats
        stats_prefix = '01.stats'
        cmd_args = [self.executable, 'stats', rpr_outpath, stats_prefix]
        self.arast_popen(cmd_args, overrides=False, cwd=rpr_outpath)

        ## reapr fcdrate
        fcd_prefix = '02.fcdrate'
        cmd_args = [self.executable, 'fcdrate', rpr_outpath, stats_prefix, fcd_prefix]
        self.arast_popen(cmd_args, overrides=False, cwd=rpr_outpath)

        ## reapr score
        fcd_file = open(os.path.join(rpr_outpath, fcd_prefix + '.info.txt'), 'r')
        for line in fcd_file:
            pass
        fcd_cutoff = line.split('\t')[0]
        score_prefix = '03.score'
        cmd_args = [self.executable, 'score', '00.assembly.fa.gaps.gz', 
                    #undupfile, stats_prefix, fcd_cutoff, score_prefix]
                    '00.in.bam', stats_prefix, fcd_cutoff, score_prefix]
        self.arast_popen(cmd_args, overrides=False, cwd=rpr_outpath)

        ## reapr break
        break_prefix = '04.break'
        cmd_args = [self.executable, 'break']
        if self.a == 'True':
            cmd_args.append('-a')
        cmd_args += [fixed_contig, '03.score.errors.gff.gz', break_prefix]
        self.arast_popen(cmd_args, overrides=True, cwd=rpr_outpath)

        # Move files into root dir
        for f in os.listdir(rpr_outpath):
            old = os.path.join(rpr_outpath, f)
            new = os.path.join(self.outpath, f)
            os.rename(old, new)

        self.job_data['bam_sorted'] = undupfile
        broken = os.path.join(self.outpath, '04.break.broken_assembly.fa')
        if os.path.exists(broken):
            return [broken]
        return

