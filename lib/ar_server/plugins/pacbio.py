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
        
        cmd_args = [self.executable, '-help']
        logging.info("Running subprocess:{}".format(cmd_args))
        print " ".join(cmd_args)
        self.arast_popen(cmd_args)        

