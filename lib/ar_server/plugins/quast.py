import glob
import logging
import os
import subprocess
from plugins import BaseAssessment
from yapsy.IPlugin import IPlugin

class QuastAssessment(BaseAssessment, IPlugin):
    def run(self, contigs, reads):
        """ 
        Build the command and run.
        Return list of file(s)
        """
        
        cmd_args = [os.path.join(os.getcwd(),self.executable), 
                    '--min-contig', self.min_contig,
                    '-o', self.outpath]
        scaffolds = True
        for t in self.job_data['contig_types']:
            if t != 'scaffolds':
                scaffolds = False
                break
        if scaffolds and self.scaffold_mode == 'True':
            cmd_args.append('--scaffolds')

        # ref = job_data['reference']
        # if ref:
        #     cmd_args += ['-R', ref[0]]
        cmd_args += contigs

        self.arast_popen(cmd_args)
        
        all_files = []
        for root, sub, files in os.walk(self.outpath):
            for file in files:
                all_files.append(os.path.join(root, file))
                
        report = os.path.join(self.outpath, 'report.txt')
        return [report]

