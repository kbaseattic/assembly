import glob
import logging
import os
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class RayAssembler(BaseAssembler, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.
        Return list of contig file(s)
        """
        
        cmd_args = ["mpirun", "-np", "4", self.executable, '-k', self.k]
        
        for lib in reads:
            if lib['type'] == 'paired':
                if len(lib['files']) == 1: # Interleaved
                    cmd_args += ['-i', lib['files'][0]]
                elif len(lib['files']) == 2: # 2 Files
                    cmd_args += ['-p', lib['files'][0], lib['files'][1]]
                else:
                    raise Exception('Ray module file error')
            elif lib['type'] == 'single':
                cmd_args += ['-s', lib['files'][0]]

        cmd_args += ['-o', self.outpath+'RayOutput']

        self.arast_popen(cmd_args)
        self.arast_popen(['cp', os.path.join(self.outpath+'RayOutput', 'Contigs.fasta'), self.outpath])
        self.arast_popen(['cp', os.path.join(self.outpath+'RayOutput', 'Scaffolds.fasta'), self.outpath])

        contigs = os.path.join(self.outpath, 'Scaffolds.fasta')

        return contigs

