import glob
import logging
import os
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class PacbioAssembler(BaseAssembler, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.
        Return list of contig file(s)
        """
        
        cmd_args = [self.executable]
        cmd_args += self.get_files(reads)

        cmd_args.append('-o')
        cmd_args.append(self.outpath + 'pacbio')

        self.arast_popen(cmd_args)

        contigs = self.outpath + 'contigs.fa'

        return contigs
        
