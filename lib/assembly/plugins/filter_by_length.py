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
        raw_reads = self.job_data['raw_reads']
        for i, file_set in enumerate(reads):
            new_file_set = file_set
            new_files = []
            new_synced_files = []
            for f in file_set['files']:
                fixes = os.path.basename(f).rsplit('.', 1)
                filtered_file = os.path.join(self.outpath, fixes[0] + '.filtered.' + fixes[1])
                synced_file = os.path.join(self.outpath, fixes[0] + '.filtered_sync.' + fixes[1])
                cmd_string = '{} seq -U -L {} -N {} {} > {}'.format(
                    self.seqtk_bin, self.min, self.end, f, filtered_file)
                self.arast_popen(cmd_string, cwd=self.outpath, shell=True)
                if os.path.getsize(filtered_file) == 0:
                    raise Exception('Error trimming')
                new_files.append(filtered_file)
                new_synced_files.append(synced_file)
            
            if self.sync == 'True':
                if file_set['type'] == 'paired' and len(new_files) == 2:
                    # sync
                    raw_file = raw_reads[i]['files'][0]
                    cmd_args = [self.sync_bin, raw_file, 
                                new_files[0], new_files[1],
                                new_synced_files[0], new_synced_files[1]]
                    self.arast_popen(cmd_args, cwd=self.outpath)
                new_file_set['files'] = new_synced_files
            else:
                new_file_set['files'] = new_files

            processed_reads.append(new_file_set)
        return processed_reads

