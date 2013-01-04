import glob
import logging
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class KikiAssembler(BaseAssembler, IPlugin):
    name = "kiki"

    def run(self, reads):
        """ 
        Build the command and run.
        Return list of contig file(s)
        """
        
        cmd_args = [self.executable, '-k', self.k, '-i',]
        for tuple in reads:
            cmd_args.append(tuple[0])
            try:
                cmd_args.append(tuple[1])
            except:
                pass #no pair
        cmd_args.append('-o')
        cmd_args.append(self.outpath + '/kiki')
        p = subprocess.Popen(cmd_args)
        p.wait()
        contigs = glob.glob(self.outpath + '/*.contig')
        if not contigs:
            raise Exception("No contigs")
        return contigs

