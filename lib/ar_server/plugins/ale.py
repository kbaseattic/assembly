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
        bamfile = ''
        #bamfile = self.job_data['bam_sorted']
        if bamfile == '':
            #Map with BWA and produce bam
            bwa_data = dict(self.job_data)
            bwa_data['contigs'] = contigs
            bwa_data['out_report'] = open(os.path.join(self.outpath, 'ale_bwa.log'), 'w')
            samfiles, _, _ = self.pmanager.run_module('bowtie2', bwa_data)
            samfile = samfiles[0]
        cmd_args = [self.executable, samfile, contigs[0],
                    os.path.join(self.outpath, 'ale.txt')]
        self.arast_popen(cmd_args)
        report = os.path.join(self.outpath, 'ale.txt')
        if os.path.exists(report):
            return report


