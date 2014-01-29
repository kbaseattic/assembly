import glob
import logging
import os
import subprocess
from plugins import BaseAnalyzer
from yapsy.IPlugin import IPlugin


class FastQCAnalyzer(BaseAnalyzer, IPlugin):
    def run(self, libs):
        """ 
        Build the command and run.

        """
        cmd_args = [self.executable]
        for lib in libs:
            for f in lib['files']:
                cmd_args.append(f)
        cmd_args += ['-o', self.outpath]
        self.arast_popen(cmd_args)
        
        # Return reports
        reports = []
        for f in os.listdir(self.outpath):
            read_dir = os.path.join(self.outpath, f)
            if os.path.isdir(read_dir):
                fastqc_data = os.path.join(read_dir, 'fastqc_data.txt')
                new_name = os.path.join(read_dir, f + '.txt')
                os.rename(fastqc_data, new_name)
                reports.append(new_name)
        return reports
