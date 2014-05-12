import glob
import logging
import os
import subprocess
from plugins import BaseAssessment
from yapsy.IPlugin import IPlugin
import asmtypes

class QuastAssessment(BaseAssessment, IPlugin):
    def run(self, contigs, reads, ref=None):
        """ 
        Build the command and run.
        Return list of file(s)
        """
        
        cmd_args = [os.path.join(os.getcwd(),self.executable), 
                    '--min-contig', self.min_contig,
                    '-o', self.outpath,
                    '--gene-finding']
        # scaffolds = True
        # for t in self.job_data['contig_types']:
        #     if t != 'scaffolds':
        #         scaffolds = False
        #         break
        
        # if self.job_data['contig_type'] == 'scaffolds':
        #     cmd_args.append('--scaffolds')

        # if scaffolds and self.scaffold_mode == 'True':
        #     cmd_args.append('--scaffolds')

        #ref = self.job_data['reference']

        #### Add Reference ####
        if ref:
            rfile = ref[0]['files'][0]
            cmd_args += ['-R', rfile, '--gage']

        #### Add Contig files ####
        contig_files = []
        for data in contigs:
            print 'type: ', type(data)
            print data
            if type(data) == asmtypes.FileInfo:
                contig_files.append(data['filename'])
            else:## Legacy 
                for f in data['files']:
                    contig_files.append(f)
        cmd_args += contig_files

        #### Run Quast ####
        self.arast_popen(cmd_args)
        
        #### Collect and return all files ####
        all_files = []
        for root, sub, files in os.walk(self.outpath):
            for file in files:
                all_files.append(os.path.join(root, file))
                
        report = os.path.join(self.outpath, 'report.txt')
        if not os.path.exists(report):
            return []
        return [report]

