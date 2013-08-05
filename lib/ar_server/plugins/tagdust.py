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
        raw_reads = self.job_data['raw_reads']
        for i, file_set in enumerate(reads):
            new_file_set = file_set
            new_files = []
            td_unsynced_files = []
            td_synced_files = []
            for f in file_set['files']:
                cmd_args = [os.path.join(os.getcwd(), self.executable), '-f', '0.05', '-s', '-o']
                lib_file = os.path.join(os.getcwd(), self.library)
                if not os.path.exists(lib_file):
                    raise Exception('TagDust: lib file missing!')
                fixes = os.path.basename(f).rsplit('.', 1)
                td_file = os.path.join(self.outpath, fixes[0] + '.td.' + fixes[1])
                synced_file = os.path.join(self.outpath, fixes[0] + '.td_sync.' + fixes[1])
                cmd_args += [td_file, os.path.join(os.getcwd(), self.library), f]
                logging.info("TagDust Plugin: {}".format(cmd_args))
                self.arast_popen(cmd_args, cwd=self.outpath)
                td_unsynced_files.append(td_file)
                td_synced_files.append(synced_file)

            if file_set['type'] == 'paired' and len(td_unsynced_files) == 2:
                #sync
                print i
                print raw_reads
                raw_file = raw_reads[i]['files'][0]
                #cmd_args = [self.sync, file_set['files'][0]
                cmd_args = [self.sync, raw_file, 
                            td_unsynced_files[0], td_unsynced_files[1],
                            td_synced_files[0], td_synced_files[1]]
                self.arast_popen(cmd_args, cwd=self.outpath)
                new_files += td_synced_files
            else:
                new_files += td_unsynced_files
            new_file_set['files'] = new_files
            processed_reads.append(new_file_set)
        return processed_reads

