import glob
import logging
import os
import subprocess
from plugins import BaseAligner
from yapsy.IPlugin import IPlugin
from assembly import get_qual_encoding

class BwaAligner(BaseAligner, IPlugin):
    def run(self, contig_file=None, reads=None, merged_pair=False):
        contig_file = self.data.contigfiles[0]
        ## Index contigs using IS algorithm
        cmd_args = [self.executable, 'index', '-a', 'is', contig_file]
        self.arast_popen(cmd_args, overrides=False)

        ## Align reads
        samfile = os.path.join(self.outpath,
                               os.path.basename(contig_file) + '.sam')
        cmd_args = [self.executable, 'mem', '-t', '8', contig_file] + self.data.readfiles
        cmd_args += ['>', samfile]
        
        ## Need to use shell mode since BWA doesn't specify an output file
        self.arast_popen(' '.join(cmd_args), shell=True, overrides=False)

        if not os.path.exists(samfile):
            raise Exception('Unable to complete alignment')

        return {'alignment': samfile}
