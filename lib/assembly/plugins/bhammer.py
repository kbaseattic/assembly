import glob
import logging
import os
import re
import yaml
from plugins import BasePreprocessor
from yapsy.IPlugin import IPlugin

logger = logging.getLogger(__name__)

class BhammerPreprocessor(BasePreprocessor, IPlugin):
    def run(self):
        """
        Build the command and run.
        Return list of contig file(s)

        SPAdes takes as input forward-reverse paired-end reads as well as single (unpaired) reads in FASTA or FASTQ format. However, in order to run read error correction, reads should be in FASTQ format. Currently SPAdes accepts only one paired-end library, which can be stored in several files or several pairs of files. The number of unpaired libraries is unlimited.
        """

        cmd_args = [self.executable]
        reads = self.data.readsets
        lib_num = 1
        single_count = 0
        for readset in self.data.readsets:
            if readset.type == 'paired':
                if lib_num > 5:
                    logger.error('> 5 pairs not supported!')
                    break
                if len(readset.files) == 1: # Interleaved
                    cmd_args += ['--pe{}-12'.format(lib_num), readset.files[0]]
                elif len(readset.files) >= 2: # 2 Files
                    cmd_args += ['--pe{}-1'.format(lib_num), readset.files[0],
                                 '--pe{}-2'.format(lib_num), readset.files[1]]
                    for extra in readset.files[2:]:
                        self.out_module.write('WARNING: Not using extra data: {}'.format(extra))
                        logger.warn('Not using extra data: {}'.format(extra))
                else:
                    raise Exception('Bhammer module file error')
            elif readset.type == 'single':
                cmd_args += ['--pe{}-s'.format(lib_num), readset.files[0]]
                single_count += 1
            lib_num += 1

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
            corrected = yaml.load(info_file)
            cor_pair = [c for c in corrected if c['type'] == 'paired-end']
            cor_single = [c for c in corrected if c['type'] == 'single']
            for read in reads:
                if read.type == 'paired':
                    cor = cor_pair.pop(0)
                    processed_reads.append([cor['left reads'].pop(0), cor['right reads'].pop(0)])
                    if cor['single reads']: # Check if extra
                        extra_reads.append([cor['single reads'].pop(0)])
                elif read.type == 'single':
                    cor = cor_single.pop(0)
                    processed_reads.append([cor['single reads'].pop(0)])

        output = {'reads': processed_reads,
                  'extra': extra_reads}

        logger.debug('Output = {}'.format(output))

        return output
