import glob
import logging
import os
import subprocess
from plugins import BasePreprocessor
from yapsy.IPlugin import IPlugin
from assembly import get_qual_encoding

class SgaEcPreprocessor(BasePreprocessor, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.

        """
        processed_reads = []

        for file_set in reads:
            new_file_set = file_set
            new_files = []
            for f in file_set['files']:
                cmd_args = [os.path.join(os.getcwd(), self.executable), 'index', f]
                fixes = os.path.basename(f).rsplit('.', 1)
                ec_file = os.path.join(self.outpath, fixes[0] + '.ec.' + fixes[1])
                logging.info("SGA Ec Plugin -- indexing: {}".format(cmd_args))
                self.arast_popen(cmd_args, cwd=self.outpath)
                cmd_args = [os.path.join(os.getcwd(), self.executable), 'correct',
                            '-o', ec_file, f]
                logging.info("SGA Ec Plugin -- error correction: {}".format(cmd_args))
                self.arast_popen(cmd_args, cwd=self.outpath)
                new_files.append(ec_file)
                if not os.path.exists(ec_file):
                    return []
            new_file_set['files'] = new_files
            processed_reads.append(new_file_set)

        return processed_reads

