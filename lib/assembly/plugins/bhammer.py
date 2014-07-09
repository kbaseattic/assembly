import glob
import logging
import os
import re
import yaml
from plugins import BasePreprocessor
from yapsy.IPlugin import IPlugin

class BhammerPreprocessor(BasePreprocessor, IPlugin):
    def run(self):
        """ 
        Build the command and run.
        Return list of contig file(s)

        SPAdes takes as input forward-reverse paired-end reads as well as single (unpaired) reads in FASTA or FASTQ format. However, in order to run read error correction, reads should be in FASTQ format. Currently SPAdes accepts only one paired-end library, which can be stored in several files or several pairs of files. The number of unpaired libraries is unlimited.
        """
        
        cmd_args = [self.executable]
        reads = self.data.readsets
        single_count = 0
        for lib in reads:
            if lib.type == 'paired':
                if len(lib.files) == 1: # Interleaved
                    cmd_args += ['--12', lib.files[0]]
                elif len(lib.files) == 2: # 2 Files
                    cmd_args += ['-1', lib.files[0],
                                 '-2', lib.files[1]]
                else:
                    raise Exception('Spades module file error')
            elif lib.type == 'single':
                cmd_args += ['-s', lib.files[0]]
                single_count += 1
        cmd_args += ['-t', self.process_threads_allowed,
                     '--only-error-correction', '--disable-gzip-output',
                     '-o', self.outpath]

        self.arast_popen(cmd_args)

        # Get processed reads

        processed_reads = []
        extra_reads = []

        cpath = os.path.join(self.outpath, 'corrected')
        
        if os.path.exists(os.path.join(cpath, 'dataset.info')):
            raise Exception('Outdated Spades installation')

        #### Plugin should return multiple libraries in same order as consumed
        elif os.path.exists(os.path.join(cpath, 'corrected.yaml')):
            info_file = open(os.path.join(cpath, 'corrected.yaml'))
            cor = yaml.load(info_file)[0]
            for read in reads:
                if read.type == 'paired':
                    processed_reads.append([cor['left reads'].pop(0), cor['right reads'].pop(0)])
                    if len(cor['single reads']) > single_count: # Check if extra
                        extra_reads.append([cor['single reads'].pop(0)])
                elif read.type == 'single':
                    processed_reads.append([cor['single reads'].pop(0)])

        return {'reads': processed_reads,
                'extra': extra_reads}
