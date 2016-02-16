import logging
import os
from plugins import BaseAligner
from yapsy.IPlugin import IPlugin

from asmtypes import ArastDataInputError

logger = logging.getLogger(__name__)

class BwaAligner(BaseAligner, IPlugin):
    def run(self, contig_file=None, reads=None, merged_pair=False):
        ### Data Checks
        if len(self.data.contigfiles) != 1:
            raise ArastDataInputError('BWA requires exactly 1 contigs file')

        ### Index contigs using IS algorithm
        contig_file = self.data.contigfiles[0]
        cmd_args = [self.executable, 'index', '-a', 'is', contig_file]
        self.arast_popen(cmd_args, overrides=False)

        ### Align reads
        bamfiles = []
        for i, readset in enumerate(self.data.readsets):
            samfile = os.path.join(self.outpath, '{}_{}.sam'.format(os.path.basename(readset.files[0]), i))
            cmd_args = [self.executable, 'mem', '-t', self.process_threads_allowed, contig_file] + readset.files
            # Note: -p should not be set for regular paired end reads; maybe for interleaved PE libs
            # if readset.type == 'paired':
                # cmd_args.append('-p')
            cmd_args += ['>', samfile]
            self.arast_popen(' '.join(cmd_args), shell=True, overrides=False)
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
