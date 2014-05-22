import glob
import logging
import os
import subprocess
from plugins import BaseAssessment
from yapsy.IPlugin import IPlugin
import asmtypes

class QuastAssessment(BaseAssessment, IPlugin):
    new_version = True

    def run(self):
        contigsets = self.data.contigsets
        contigfiles = self.data.contigfiles
        ref = self.data.referencefiles or None
        
        cmd_args = [os.path.join(os.getcwd(),self.executable), 
                    '--min-contig', self.min_contig,
                    '-o', self.outpath,
                    '--gene-finding']

        #### Add Reference ####
        if ref:
            rfile = ref[0]
            cmd_args += ['-R', rfile, '--gage']

        #### Add Contig files ####
        cmd_args += self.data.contigfiles

        #### Run Quast ####
        self.arast_popen(cmd_args)
        
        #### Collect and return all files ####
        all_files = []
        for root, sub, files in os.walk(self.outpath):
            for file in files:
                all_files.append(os.path.join(root, file))
                
        output = {}
        report = os.path.join(self.outpath, 'report.txt')
        if not os.path.exists(report):
            print 'No Quast Output'
            report = None
        else: output['report'] = report
        output['all_files'] = all_files
        output['n50s'] = (100000, 1)
        return output
    
