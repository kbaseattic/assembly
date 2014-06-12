import asmtypes
import glob
import logging
import os
import subprocess
from plugins import BasePreprocessor
from yapsy.IPlugin import IPlugin
from assembly import get_qual_encoding

class TrimSortPreprocessor(BasePreprocessor, IPlugin):
    new_version = True

    def run(self, reads=None):
        """ 
        Build the command and run.
        Return list of reads
        """

        processed_reads = []
        for readset in self.data.readsets:
            cmd_args = [os.path.join(os.getcwd(), self.bin_dynamictrim)]
            cmd_args += readset.files
            cmd_args += ['-p', self.probcutoff, '-d', self.outpath]
            self.arast_popen(cmd_args, cwd=self.outpath)

            trimmed = [os.path.join(self.outpath, 
                         "{}.{}".format(os.path.basename(f), "trimmed"))
                       for f in readset.files]

            cmd_args = ([os.path.join(os.getcwd(), self.bin_lengthsort)] + 
                        trimmed + 
                        ['-l', self.length] +
                        ['-d', self.outpath])

            self.arast_popen(cmd_args, cwd=self.outpath)

            if readset.type == 'single':
                sorted_files = glob.glob(self.outpath + '/*.single')
            else:
                sorted_files = glob.glob(self.outpath + '/*.paired*')
            for f in sorted_files:
                os.rename(f, "{}.fq".format(f))
            new_files = ["{}.fq".format(f) for f in sorted_files]
        processed_reads.append(new_files)
        return {'reads': processed_reads}
