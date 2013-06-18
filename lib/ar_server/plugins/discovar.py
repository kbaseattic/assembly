import glob
import logging
import os
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class DiscovarAssembler(BaseAssembler, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.
        Return list of contig file(s)
        """

        self.fastq_to_bam(reads)

        cmd_args = [self.executable, 'READS='+self.outpath+'sample.bam', 'REGIONS=all', 'TMP='+self.outpath, 'OUT_HEAD='+self.outpath+'/discovar']
        print ' '.join(cmd_args)
        cmd_string = ' '.join(cmd_args)
        self.arast_popen(cmd_string, shell=True)        


    def fastq_to_bam(self, reads):
        cmd_args = [self.picard, 'FastqToSam', 'V=Illumina', 'SM=sample', 'O='+self.outpath+'/sample.bam']
        for d in reads:
            if d['type'] == 'paired':
                read1 = d['files'][0]
                cmd_args.append('F1=' + read1)
                try:
                    read2 = d['files'][1] # If 2 files
                    cmd_args.append('F2=' + read2)
                except:
                    pass

        if len(cmd_args) == 1:
            raise Exception("No paired-end reads")
              
        logging.info("Running subprocess:{}".format(cmd_args))
        self.arast_popen(cmd_args)        
                    
