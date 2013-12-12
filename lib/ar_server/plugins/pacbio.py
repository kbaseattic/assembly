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
        
        smrt_env = self.get_smrt_env()

        cmd_args = [self.executable, '-help']
        logging.info("Running subprocess:{}".format(cmd_args))

        print " ".join(cmd_args)

        self.arast_popen(cmd_args, env=smrt_env)


    def get_smrt_env(self):
        source_cmd = " ".join(['source', self.setup, ';', 'printenv' ]);
        proc = subprocess.Popen([source_cmd], stdout=subprocess.PIPE, shell=True, executable='/bin/bash')
        lines = proc.stdout.readlines()
        env = os.environ.copy()
        for line in lines:
            k, v = line.split('=', 1)
            env[k] = v
        print env
        
        
