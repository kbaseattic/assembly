import glob
import logging
import os
import subprocess
from plugins import BasePreprocessor
from yapsy.IPlugin import IPlugin
from assembly import get_qual_encoding

class TagdustPreprocessor(BasePreprocessor, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.

        """
        processed_reads = []
        for file_set in reads:
            new_file_set = file_set
            new_files = []
            for f in file_set['files']:
                cmd_args = [os.path.join(os.getcwd(), self.executable), '-s', '-o']
                lib_file = os.path.join(os.getcwd(), self.library)
                if not os.path.exists(lib_file):
                    raise Exception('TagDust: lib file missing!')
                fixes = os.path.basename(f).rsplit('.', 1)
                td_file = os.path.join(self.outpath, fixes[0] + '.tagdust.' + fixes[1])
                cmd_args += [td_file, os.path.join(os.getcwd(), self.library), f]
                logging.info("TagDust Plugin: {}".format(cmd_args))
                self.out_module.write(subprocess.check_output(cmd_args, cwd=self.outpath))
                new_files.append(td_file)
            new_file_set['files'] = new_files
            processed_reads.append(new_file_set)
        return processed_reads

