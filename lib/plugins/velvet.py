import os
import logging
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class VelvetAssembler(BaseAssembler, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.
        Return list of contig file(s)
        """
        
        cmd_args = [self.velveth, self.outpath, self.hash_length]

        paired_count = 1                    
        for d in reads:
            read1 = d['files'][0]
            cmd_args.append('-' + infer_filetype(read1))
            if d['type'] == 'paired':
                cmd_args.append('-' + 'shortPaired' + str(paired_count))
                paired_count += 1
            try:
                read2 = d['files'][1] # If 2 files
                cmd_args.append(read1)
                cmd_args.append(read2)
            except:
                cmd_args.append(read1)

        logging.info("Running subprocess:{}".format(cmd_args))
        self.out_report.write('Command: {}\n'.format(cmd_args))
        self.arast_popen(cmd_args)        

        cmd_args = [self.velvetg, self.outpath]
        logging.info("Running subprocess:{}".format(cmd_args))
        self.out_report.write('Command: {}\n'.format(cmd_args))
        self.arast_popen(cmd_args)        
        contigs = [self.outpath + '/contigs.fa']
        if not os.path.exists(contigs[0]):
            raise Exception("No contigs")
        return contigs

def infer_filetype(file):
    filemap = {'.fa':'fasta',
               '.fasta' :'fasta',
               '.fq':'fastq',
               '.fastq' :'fastq'}
    for ext in filemap:
        if file.endswith(ext):
            return filemap[ext]
    return ''
