import glob
import logging
import os
import subprocess
from plugins import BasePreprocessor
from yapsy.IPlugin import IPlugin
from assembly import get_qual_encoding

class TrimSortPreprocessor(BasePreprocessor, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.
        Return list of reads
        """
        processed_reads = []
        for file_set in reads: # preprocess all pairs/reads!!!
            cmd_args = [os.path.join(os.getcwd(), self.bin_dynamictrim)]
            files = file_set['files']                    
            # Get file name for prefix
            cmd_args += files
            cmd_args += ['-p', self.probcutoff, '-d', self.outpath]
            logging.info("TrimSort Plugin: {}".format(cmd_args))
            self.arast_popen(cmd_args, cwd=self.outpath)

            trimmed = [os.path.join(self.outpath, 
                         "{}.{}".format(os.path.basename(f), "trimmed"))
                       for f in files]

            #trimmed = ["{}.{}".format(f, "trimmed") for f in files]
            cmd_args = ([os.path.join(os.getcwd(), self.bin_lengthsort)] + 
                        trimmed + 
                        ['-l', self.length] +
                        ['-d', self.outpath])

            self.arast_popen(cmd_args, cwd=self.outpath)

            if file_set['type'] == 'single':
                sorted_files = glob.glob(self.outpath + '/*.single')

            else:
                sorted_files = glob.glob(self.outpath + '/*.paired*')
            for f in sorted_files:
                os.rename(f, "{}.fq".format(f))
            new_file_set = file_set
            new_file_set['files'] = ["{}.fq".format(f) for f in sorted_files]
            processed_reads.append(new_file_set)

        return processed_reads

