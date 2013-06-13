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
        self.arast_popen(cmd_args)
        fixed_contig = fixed_contig + '.fa'
        if len(reads) > 1:
            raise Exception('Reapr: multiple libraries not yet supported!')
        readfiles = reads[0]['files']
        
        #Map with BWA and produce bam
        bwa_data = copy.deepcopy(self.job_data)
        bwa_data['processed_reads'][0]['files'] = readfiles
        bwa_data['contigs'] = [fixed_contig]
        bwa_data['out_report'] = open(os.path.join(self.outpath, 'bwa.log'), 'w')
        samfile, _, _ = self.pmanager.run_module('bwa', bwa_data)
        bamfile = samfile.replace('.sam', '.bam')
        cmd_args = ['samtools', 'view',
                    '-bSho', bamfile, samfile]
        self.arast_popen(cmd_args)
        sortedfile = os.path.join(self.outpath, 'sorted')
        cmd_args = ['samtools', 'sort', bamfile, sortedfile]
        self.arast_popen(cmd_args)
        sortedfile = sortedfile + '.bam'
        reapr_outdir = os.path.join(self.outpath, 'output')
        cmd_args = [self.executable, 'pipeline', fixed_contig, sortedfile, 
                    reapr_outdir]
        self.arast_popen(cmd_args)

        # Move files into root dir
        for f in os.listdir(reapr_outdir):
            old = os.path.join(reapr_outdir, f)
            new = os.path.join(self.outpath, f)
            os.rename(old, new)

        self.job_data['bam_sorted'] = sortedfile
        broken = os.path.join(self.outpath, '04.break.broken_assembly.fa')
        if os.path.exists(broken):
            return [broken]
        return

