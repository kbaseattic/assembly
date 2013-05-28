import glob
import logging
import os
import subprocess
from plugins import BaseAligner
from yapsy.IPlugin import IPlugin
from assembly import get_qual_encoding

class BwaAligner(BaseAligner, IPlugin):
    def run(self, contig_file, reads, merged_pair=False):
        """ 
        Map READS to CONTIGS and return alignment.
        Set MERGED_PAIR to True if reads[1] is a merged
        paired end file
        """
        ## Index contigs using IS algorithm
        cmd_args = [self.executable, 'index', '-a', 'is', contig_file]
        logging.info("BWA Plugin: {}".format(cmd_args))
        self.arast_popen(cmd_args)

        ## Align reads
        samfile = os.path.join(self.outpath,
                               os.path.basename(contig_file) + '.sam')
        aln_file1 = os.path.join(self.outpath,
                                 os.path.basename(reads[0]) + '.sai')
        cmd_args = [self.executable, 'aln', contig_file, reads[0],
                    '-f', aln_file1]
        self.arast_popen(cmd_args)
        if len(reads) == 2:
            aln_file2 = os.path.join(self.outpath,
                                     os.path.basename(reads[1]) + '.sai')

            cmd_args = [self.executable, 'aln', contig_file, reads[1],
                        '-f', aln_file2]
            self.arast_popen(cmd_args)

        # Create SAM
            cmd_args = [self.executable, 'sampe', contig_file, 
                        aln_file1, aln_file2,
                        reads[0], reads[1],
                        '-f', samfile]
            self.arast_popen(cmd_args)
        else: ## Single end
            if merged_pair:
                raise Exception('Merged pair files not implemented')
            cmd_args = [self.executable, 'samse', contig_file, 
                        aln_file1, reads[0], '-f', samfile]
            self.arast_popen(cmd_args)

        if not os.path.exists(samfile):
            raise Exception('Unable to complete alignment')
        return samfile
