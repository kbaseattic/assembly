import glob
import logging
import os
import re
import yaml
from plugins import BasePreprocessor
from yapsy.IPlugin import IPlugin

class BhammerPreprocessor(BasePreprocessor, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.
        Return list of contig file(s)

        SPAdes takes as input forward-reverse paired-end reads as well as single (unpaired) reads in FASTA or FASTQ format. However, in order to run read error correction, reads should be in FASTQ format. Currently SPAdes accepts only one paired-end library, which can be stored in several files or several pairs of files. The number of unpaired libraries is unlimited.
        """
        
        cmd_args = [self.executable]
        for lib in reads:
            if lib['type'] == 'paired':
                if len(lib['files']) == 1: # Interleaved
                    cmd_args += ['--12', lib['files'][0]]
                elif len(lib['files']) == 2: # 2 Files
                    cmd_args += ['-1', lib['files'][0],
                                 '-2', lib['files'][1]]
                else:
                    raise Exception('Spades module file error')
            elif lib['type'] == 'single':
                cmd_args += ['-s', lib['files'][0]]
        cmd_args += ['--only-error-correction', '--disable-gzip-output',
                     '-o', self.outpath]

        self.arast_popen(cmd_args)

        # Get processed reads

        processed_reads = []
        cpath = os.path.join(self.outpath, 'corrected')
        
        # Older versions of spades
        if os.path.exists(os.path.join(cpath, 'dataset.info')):
            file_info = open(os.path.join(cpath, 'dataset.info'))

            for line in file_info:
                l = line.split('\t')
                if l[0] == 'paired_reads':
                    paired_files = re.split('\"|\s', l[1])
                    p1 = os.path.join(cpath, paired_files[1])
                    p2 = os.path.join(cpath, paired_files[3])
                    processed_reads.append({'files': [p1, p2],
                                            'type': 'paired'})
                elif l[0] == 'single_reads':
                    single_file = os.path.join(cpath,
                                               re.split('\"|\s', l[1])[1])
                    processed_reads.append({'files': [single_file],
                                            'type': 'single'})
        # Newer versions of spades
        elif os.path.exists(os.path.join(cpath, 'corrected.yaml')):
            info_file = open(os.path.join(cpath, 'corrected.yaml'))
            cor = yaml.load(info_file)[0]
            if 'left reads' in cor and 'right reads' in cor:
                for i,left in enumerate(cor['left reads']):
                    pair_info = {'files': [left, cor['right reads'][i]],
                                 'type': 'paired'}
                    
                    # ## Try to preserve initial insert info if avail
                    # try:
                    #     pair_info['insert'] =  self.insert_info[i][0]
                    #     pair_info['stdev'] =  self.insert_info[i][1]
                    # except:
                    #     pass
                    processed_reads.append(pair_info)
            if 'single reads' in cor:
                for single in cor['single reads']:
                    processed_reads.append({'files': [single], 'type': 'single'})

        return processed_reads
