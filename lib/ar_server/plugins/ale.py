import copy
import glob
import logging
import os
import subprocess
from plugins import BaseAssessment
from yapsy.IPlugin import IPlugin

class AleAssessment(BaseAssessment, IPlugin):
    def run(self, contigs, reads):
        """ 
        Build the command and run.
        Return list of file(s)
        """
        bamfile = self.job_data['bam_sorted']
        if bamfile == '':
            #Map with BWA and produce bam
            bwa_data = copy.deepcopy(self.job_data)
            bwa_data['processed_reads'][0]['files'] = reads[0]['files']
            bwa_data['contigs'] = contigs
            bwa_data['out_report'] = open(os.path.join(self.outpath, 'ale_bwa.log'), 'w')
            samfile, _, _ = self.pmanager.run_module('bwa', bwa_data)
            bamfile = samfile.replace('.sam', '.bam')
            cmd_args = ['samtools', 'view',
                        '-bSho', bamfile, samfile]
            self.arast_popen(cmd_args, overrides=False)
            sortedfile = os.path.join(self.outpath, 'sorted')
            cmd_args = ['samtools', 'sort', bamfile, sortedfile]
            self.arast_popen(cmd_args, overrides=False)
            sortedfile = sortedfile + '.bam'

        cmd_args = [self.executable, sortedfile, contigs[0],
                    os.path.join(self.outpath, 'ale.txt')]
        self.arast_popen(cmd_args)
        report = os.path.join(self.outpath, 'ale.txt')
        if os.path.exists(report):
            return report

