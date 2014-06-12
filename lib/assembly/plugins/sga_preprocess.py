import glob
import logging
import os
import subprocess
from plugins import BasePreprocessor
from yapsy.IPlugin import IPlugin
from assembly import get_qual_encoding

class SgaPreprocessor(BasePreprocessor, IPlugin):
    new_version = True

    def run(self, reads=None):
        """ 
        Build the command and run.
        Return list of reads
        """
        processed_reads = []
        for readset in self.data.readsets:
            new_reads = []
            for f in readset.files:
                cmd_args = [os.path.join(os.getcwd(), self.executable), 'preprocess']
                if self.quality_trim:
                    cmd_args += ['-q', self.quality_trim]
                if self.quality_filter:
                    cmd_args += ['-f', self.quality_filter]
                if self.min_length:
                    cmd_args += ['-m', self.min_length]
                if self.permute_ambiguous:
                    cmd_args.append('--permute-ambiguous')

                # Get file name for prefix
                cmd_args.append('-o')
                basename = os.path.basename(f)
                base = basename[0:basename.rfind('.')]
                pp_file = os.path.join(self.outpath,
                                       "{}.pp.fastq".format(base))
                cmd_args.append(pp_file)
                cmd_args.append(f)
                if get_qual_encoding(f) == 'phred64':
                    cmd_args.append('--phred64')
                self.arast_popen(cmd_args, cwd=self.outpath)
                new_reads.append(pp_file)
            processed_reads.append(new_reads)
        return {'reads': processed_reads}

