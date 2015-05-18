import glob
import logging
import os
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

logger = logging.getLogger(__name__)

class DiscovarAssembler(BaseAssembler, IPlugin):
    def run(self):
        """
        Build the command and run.
        Return list of contig file(s)
        """

        reads = self.data.readsets

        self.fastq_to_bam(reads)

        os.environ["MALLOC_PER_THREAD"] = "1"

        cmd_args = [self.executable, 'NUM_THREADS=4', 'READS='+self.outpath+'sample.bam', 'REGIONS=all', 'TMP='+self.outpath, 'OUT_HEAD='+self.outpath+'/discovar']

        self.arast_popen(cmd_args)

        contigs = glob.glob(self.outpath + '/*.final.fasta')
        if not contigs:
            #raise Exception("No contigs")
            logger.warning("No contigs")
        return {'contigs': contigs}


    def fastq_to_bam(self, reads):
        # cmd_args = [self.picard, 'FastqToSam', 'V=Illumina', 'O='+self.outpath+'/sample.bam', 'SM=sample']
        cmd_args = [self.picard, 'FastqToSam','TMP_DIR='+self.outpath,
                    'V=Standard', 'O='+self.outpath+'/sample.bam', 'SM=sample']
        for d in reads:
            if d.type == 'paired':
                read1 = d.files[0]
                cmd_args.append('F1=' + read1)
                try:
                    read2 = d.files[1] # If 2 files
                    cmd_args.append('F2=' + read2)
                except:
                    pass

        if len(cmd_args) == 1:
            raise Exception("No paired-end reads")

        self.arast_popen(cmd_args)
