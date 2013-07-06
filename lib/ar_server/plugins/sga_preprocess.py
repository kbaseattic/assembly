import glob
import logging
import os
import subprocess
from plugins import BasePreprocessor
from yapsy.IPlugin import IPlugin
from assembly import get_qual_encoding

class SgaPreprocessor(BasePreprocessor, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.
        Return list of reads
        """
        processed_reads = []
        for file_set in reads: # preprocess all pairs/reads!!!
            new_file_set = dict(file_set)
            new_file_set['files'] = []
            for f in file_set['files']:
                cmd_args = [os.path.join(os.getcwd(), self.executable), 'preprocess']
                if self.quality_trim:
                    cmd_args += ['-q', self.quality_trim]
                if self.quality_filter:
                    cmd_args += ['-f', self.quality_filter]
                if self.min_length:
                    cmd_args += ['-m', self.min_length]
                if self.permute_ambiguous:
                    cmd_args.append('--permute-ambiguous')
                # if file_set['type'] == 'paired':
                #     cmd_args += ['-p', '1']
                # elif file_set['type'] == 'single':
                #     cmd_args += ['-p', '0']                
                files = file_set['files']                    
                # Get file name for prefix
                cmd_args.append('-o')
                # if len(files) == 2:
                #     base = os.path.basename(files[0]).split('.')[0][:-1]
                # else:
                base = os.path.basename(f).split('.')[0]
                pp_file = os.path.join(self.outpath,
                                       "{}.pp.fastq".format(base))
                cmd_args.append(pp_file)
                cmd_args.append(f)
                if get_qual_encoding(files[0]) == 'phred64':
                    cmd_args.append('--phred64')
                logging.info("SGA Plugin: {}".format(cmd_args))
                self.arast_popen(cmd_args, cwd=self.outpath)
                new_file_set['files'].append(pp_file)
            processed_reads.append(new_file_set)
        print processed_reads
        return processed_reads

