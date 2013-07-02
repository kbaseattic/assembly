import glob
import logging
import os
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class A5Assembler(BaseAssembler, IPlugin):
    OUTPUT = 'scaffolds'
    def run(self, reads):
        """ 
        Build the command and run.
        Return list of contig file(s)
        """
        
        cmd_args = [os.path.join(os.getcwd(),self.executable)]
        files = self.get_files(reads)
        if len(files) > 2:
            files = files[:2]
        cmd_args += files
        cmd_args.append('a5')
        self.arast_popen(cmd_args, cwd=self.outpath)

        contigs = glob.glob(self.outpath + '/*.contigs.fasta')
        #scaffolds = glob.glob(self.outpath + '/*.final.scaffolds.fasta')

        if not contigs:
            #raise Exception("No contigs")
            print "No contigs"
        #return contigs, scaffolds
        return contigs

