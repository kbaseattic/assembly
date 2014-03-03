import glob
import logging
import os
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class SpadesAssembler(BaseAssembler, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.
        Return list of contig file(s)

        SPAdes takes as input forward-reverse paired-end reads as well as single (unpaired) reads in FASTA or FASTQ format. However, in order to run read error correction, reads should be in FASTQ format. Currently SPAdes accepts only one paired-end library, which can be stored in several files or several pairs of files. The number of unpaired libraries is unlimited.
        """
        
        cmd_args = [self.executable]
        pe_num = 1
        for lib in reads:
            if lib['type'] == 'paired':
                if len(lib['files']) == 1: # Interleaved
                    cmd_args += ['--pe{}-12'.format(pe_num), lib['files'][0]]
                elif len(lib['files']) == 2: # 2 Files
                    cmd_args += ['--pe{}-1'.format(pe_num), lib['files'][0],
                                 '--pe{}-2'.format(pe_num), lib['files'][1]]
                else:
                    print len(lib['files'])
                    print lib['files']
                    raise Exception('Spades module file error')
                pe_num += 1
            elif lib['type'] == 'single':
                cmd_args += ['-s', lib['files'][0]]
        if self.only_assembler == 'True':
            cmd_args.append('--only-assembler')

        if self.read_length == 'medium' or self.read_length == '150':
            cmd_args += ['-k', '21,33,55,77']

        if self.read_length == 'medium2' or self.read_length == '200':
            cmd_args += ['-k', '21,33,55,77,99']

        if self.read_length == 'long' or self.read_length == '250':
            cmd_args += ['-k', '21,33,55,77,99,127']


        cmd_args += ['-o', self.outpath]
        cmd_args += ['-t', self.process_threads_allowed]  # number of threads = 4
        self.arast_popen(cmd_args)
        contigs = os.path.join(self.outpath, 'contigs.fasta')
        #contigs = os.path.join(self.outpath, 'scaffolds.fasta')

        if os.path.exists(contigs):
            return [contigs]
        return
