import glob
import logging
import os
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class A5Assembler(BaseAssembler, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.
        Return list of contig file(s)
        """
        
        cmd_args = [self.executable]
        for tuple in reads:
            cmd_args.append(tuple[0])
            try:
                cmd_args.append(tuple[1])
            except:
                pass #no pair

        cmd_args.append('a5')
        print cmd_args
        p = subprocess.Popen(cmd_args, cwd=self.outpath)
        p.wait()

        contigs = glob.glob(self.outpath + '/*.contigs.fasta')

        if not contigs:
            raise Exception("No contigs")
        return contigs

