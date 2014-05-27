import glob
import logging
import os
import copy
import itertools
import subprocess
from plugins import BaseMetaAssembler
from yapsy.IPlugin import IPlugin

class GamNgsAssembler(BaseMetaAssembler, IPlugin):
    new_version = True

    def run(self, contigs=None, type='in_order'):
        """ 
        Other types: iterative, smart
        """

        libfiles = []
        contigs = self.data.contigfiles
        contigsets = self.data.contigsets
        if len(contigs) < 2:
            return []
        for cset in contigsets:
            libfile = os.path.join(self.outpath, cset.name + '.lib')
            lib = open(libfile, 'w')
            bwa_results = self.plugin_engine.run_expression('(bwa (contigs {}) READS)'.format(cset.files[0]))
            for samfile in bwa_results.files:
                bamfile = samfile.replace('.sam', '.bam')
                cmd_args = ['samtools', 'view',
                            '-bSho', bamfile, samfile]
                self.arast_popen(cmd_args, overrides=False)
                sortedfile = os.path.join(self.outpath, cset.name)
                cmd_args = ['samtools', 'sort', bamfile, sortedfile]
                self.arast_popen(cmd_args, overrides=False)
                undupfile = sortedfile + '_undup.bam'
                sortedfile = sortedfile + '.bam'

                ## Remove duplicates
                cmd_args = ['samtools', 'rmdup', sortedfile, undupfile]
                self.arast_popen(cmd_args, overrides=False)
                if not os.path.exists(undupfile):
                    logging.warning('Unable to perform alignment')
                    continue
                cmd_args = ['samtools', 'index', undupfile]
                self.arast_popen(cmd_args, overrides=False)

                lib.write('{}\n'.format(undupfile))
                lib.write('50 10000\n')
            lib.close()
            libfiles.append({'file': libfile, 'name': cset.name, 'contigs': cset.files[0]})
            
        merged_files = []

        if type == 'pairwise':
            pairwise = itertools.product(libfiles, libfiles)
            for pair in pairwise:
                if pair[0] == pair[1]:
                    continue
                mfile = self.merge(pair[0], pair[1])
                if mfile:
                    merged_files.append(mfile)
        elif type == 'in_order':
            mfile = self.merge(libfiles[0], libfiles[1])
            if mfile:
                merged_files.append(mfile)
        #elif type == 'iterative':
            
        return {'contigs': merged_files}

    def merge(self, asm1, asm2):
        a1_name = asm1['name']
        a2_name = asm2['name']
        merge_name = a1_name + '_gam_' + a2_name
        merge_prefix = os.path.join(self.outpath, merge_name)
        cmd_args = [self.bin_create, '--master-bam', asm1['file'], '--slave-bam', asm2['file'],
                    '--output', merge_prefix]
        self.arast_popen(cmd_args)
        cmd_args = [self.bin_merge, '--master-bam', asm1['file'], '--slave-bam', asm2['file'],
                    '--master-fasta', asm1['contigs'], '--slave-fasta', asm2['contigs'],
                    '--blocks-file', merge_prefix + '.blocks',
                    '--output', merge_prefix]
        self.arast_popen(cmd_args)
        merged_file = merge_prefix + '.gam.fasta'
        if os.path.exists(merged_file):
            return merged_file
        
