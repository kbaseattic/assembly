import glob
import logging
import os
import subprocess
from plugins import BasePreprocessor
from yapsy.IPlugin import IPlugin
from assembly import get_qual_encoding

class FilterByLengthPreprocessor(BasePreprocessor, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.

        """
        processed_reads = []
        for file_set in reads:
            new_file_set = file_set
            new_files = []
            for f in file_set['files']:
                fixes = os.path.basename(f).rsplit('.', 1)
                try:
                    qnum = get_qual_encoding(f).split('phred')[1]
                except:
                    self.out_module.write('WARNING: Unable to trim!')
                    return reads
                filtered_file = os.path.join(self.outpath, fixes[0] + '.filtered.' + fixes[1])
                cmd_string = '{} seq -L {} {} | {} -Q{} -l {} > {}'.format(
                    self.seqtk_bin, self.min, f, 
                    self.fastx_bin, qnum, self.max, filtered_file)
                self.arast_popen(cmd_string, cwd=self.outpath, shell=True)
                if os.path.getsize(filtered_file) == 0:
                    raise Exception('Error trimming')
                new_files.append(filtered_file)
            new_file_set['files'] = new_files
            processed_reads.append(new_file_set)
        return processed_reads

