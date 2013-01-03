import glob
import logging
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class KikiAssembler(BaseAssembler, IPlugin):
    name = "kiki"

    def run(self, settings, job_data, outpath, contigs=True, tarfile=True, report=True):
        """ 
        Build the command and run.
        Return list of contig file(s) and optionally the tarball and report file
        """
        
        cmd_args = [self.executable, '-k', self.k, '-i',]
        
        for tuple in job_data['reads']:
            cmd_args.append(tuple[0])
            try:
                cmd_args.append(tuple[1])
            except:
                pass #no pair

        cmd_args.append('-o')
        cmd_args.append(outpath)
        print cmd_args

        p = subprocess.Popen(cmd_args)
        p.wait()

        contigfile = kiki_data + '*.contig'
        contigs = glob.glob(contigfile)
        print "Contigs: {}".format(contigs)

        if not contigs:
            raise Exception("No contigs")

        return contigs, "tarfile",  "report"


    def run_checks(self, settings, job_data):
        pass
