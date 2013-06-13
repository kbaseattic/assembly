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
        self.arast_popen(cmd_args, overrides=False)

        ## Align reads
        samfile = os.path.join(self.outpath,
                               os.path.basename(contig_file) + '.sam')
        cmd_args = [self.executable, 'mem', '-t', '8', contig_file, reads[0]]
        if len(reads) == 2:
            cmd_args+=[reads[1], '>', samfile]
            
        else:
            cmd_args+=['>', samfile]
        cmd_string = ' '.join(cmd_args)
        
        ## Need to use shell mode since BWA doesn't specify an output file
        self.arast_popen(cmd_string, shell=True, overrides=False)

        if not os.path.exists(samfile):
            raise Exception('Unable to complete alignment')
        self.job_data['samfile'] = samfile
        return samfile
