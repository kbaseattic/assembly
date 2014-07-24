import glob
import logging
import os
import subprocess
from plugins import BaseAligner
from yapsy.IPlugin import IPlugin
from assembly import get_qual_encoding

class Bowtie2Aligner(BaseAligner, IPlugin):
    def run(self):
        """ 
        Map READS to CONTIGS and return alignment.
        Set MERGED_PAIR to True if reads[1] is a merged
        paired end file
        """
        contig_file = self.data.contigfiles[0]
        reads = self.data.readfiles

        ## Index contigs 
        prefix = os.path.join(self.outpath, 'bt2')
        cmd_args = [self.build_bin, '-f', contig_file, prefix]
        self.arast_popen(cmd_args, overrides=False)

        ### Align reads
        bamfiles = []
        for i, readset in enumerate(self.data.readsets):
            samfile = os.path.join(self.outpath, 'align.sam')
            reads = readset.files
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

            ## Convert to BAM
            bamfile = samfile.replace('.sam', '.bam')
            cmd_args = ['samtools', 'view',
                        '-bSho', bamfile, samfile]
            self.arast_popen(cmd_args)
            bamfiles.append(bamfile)

        ### Merge samfiles if multiple
        if len(bamfiles) > 1:
            bamfile = os.path.join(self.outpath, '{}_{}.bam'.format(os.path.basename(contig_file), i))
            self.arast_popen(['samtools', 'merge', bamfile] + bamfiles)
            if not os.path.exists(bamfile):
                raise Exception('Unable to complete alignment')
        else:
            bamfile = bamfiles[0]
            if not os.path.exists(bamfile):
                raise Exception('Unable to complete alignment')

        ## Convert back to sam    
        samfile = bamfile.replace('.bam', '.sam')
        self.arast_popen(['samtools', 'view', '-h', '-o', samfile, bamfile])

        return {'alignment': samfile,
                'alignment_bam': bamfile}
