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
        for tuple in reads:
            read1 = tuple[0]
            cmd_args.append('-' + infer_filetype(read1))
            try:
                read2 = tuple[1]
                cmd_args.append('-' + 'shortPaired' + str(paired_count))
                paired_count += 1
                cmd_args.append(read1)
                cmd_args.append(read2)
            except:
                cmd_args.append(read1)

        logging.info("Running subprocess:{}".format(cmd_args))
        p = subprocess.Popen(cmd_args)
        p.wait()
        
        cmd_args = [self.velvetg, self.outpath]
        logging.info("Running subprocess:{}".format(cmd_args))
        p = subprocess.Popen(cmd_args)
        p.wait()

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
