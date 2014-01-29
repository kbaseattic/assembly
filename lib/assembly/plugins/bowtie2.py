import glob
import logging
import os
import subprocess
from plugins import BaseAligner
from yapsy.IPlugin import IPlugin
from assembly import get_qual_encoding

class Bowtie2Aligner(BaseAligner, IPlugin):
    def run(self, contig_file, reads, merged_pair=False):
        """ 
        Map READS to CONTIGS and return alignment.
        Set MERGED_PAIR to True if reads[1] is a merged
        paired end file
        """
        ## Index contigs using IS algorithm
        prefix = os.path.join(self.outpath, 'bt2')
        cmd_args = [self.build_bin, '-f', contig_file, prefix]
        self.arast_popen(cmd_args, overrides=False)

        ## Align reads
        samfile = os.path.join(self.outpath, 'align.sam')
        cmd_args = [self.executable, '-x', prefix, '-S', samfile,
                    '-p', self.process_threads_allowed]
        if len(reads) == 2:
            cmd_args += ['-1', reads[0], '-2', reads[1]]
        elif len(reads) == 1:
            cmd_args += ['-U', reads[0]]
        else:
            raise Exception('Bowtie plugin error')
        self.arast_popen(cmd_args, overrides=False)

        if not os.path.exists(samfile):
            raise Exception('Unable to complete alignment')
        return samfile
