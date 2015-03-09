import glob
import logging
import os
import subprocess
from plugins import BasePreprocessor
from yapsy.IPlugin import IPlugin
from assembly import get_qual_encoding

logger = logging.getLogger(__name__)

class SgaEcPreprocessor(BasePreprocessor, IPlugin):
    def run(self):
        """
        Build the command and run.

        """
        processed_reads = []

        for file_set in self.data.readsets:
            new_files = []
            for f in file_set.files:
                cmd_args = [os.path.join(os.getcwd(), self.executable), 'index', f]
                fixes = os.path.basename(f).rsplit('.', 1)
                ec_file = os.path.join(self.outpath, fixes[0] + '.ec.' + fixes[1])
                self.arast_popen(cmd_args, cwd=self.outpath)
                cmd_args = [os.path.join(os.getcwd(), self.executable), 'correct',
                            '-o', ec_file, f]
                self.arast_popen(cmd_args, cwd=self.outpath)
                new_files.append(ec_file)
                if not os.path.exists(ec_file):
                    return []
            processed_reads.append(new_files)
        return {'reads': processed_reads}
