import glob
import logging
import os
import copy
import itertools
import subprocess
from plugins import BaseMetaAssembler
from yapsy.IPlugin import IPlugin

class GamNgsAssembler(BaseMetaAssembler, IPlugin):
    def run(self, contigs, type='pairwise'):
        """ 
        Other types: iterative, smart
        """
        libfiles = []
        if len(contigs) < 2:
            return []
        for data in contigs:
            libfile = os.path.join(self.outpath, data['name'] + '.txt')
            lib = open(libfile, 'w')
            if not data['alignment_bam']:
                #Map with BWA and produce bam
                bwa_data = copy.deepcopy(self.job_data)
                bwa_data['contigs'] = data['files']
                bwa_data['out_report'] = open(os.path.join(self.outpath, 'bwa.log'), 'w')
                samfiles, _, _ = self.pmanager.run_module('bwa', bwa_data)
                for samfile in samfiles:
                    #insert, stdev = self.estimate_insert_stdev()
                    bamfile = samfile.replace('.sam', '.bam')
                    cmd_args = ['samtools', 'view',
                                '-bSho', bamfile, samfile]
                    self.arast_popen(cmd_args, overrides=False)
                    sortedfile = os.path.join(self.outpath, data['name'])
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

                    data['alignment_bam'].append(undupfile)
                    lib.write('{}\n'.format(undupfile))
                    lib.write('50 10000\n')
            lib.close()
            libfiles.append({'file': libfile, 'name': data['name'], 'contigs': data['files'][0]})
            
        merged_files = []

        if type == 'pairwise':
            pairwise = itertools.product(libfiles, libfiles)
            for pair in pairwise:
                if pair[0] == pair[1]:
                    continue
                mfile = self.merge(pair[0], pair[1])
                if mfile:
                    merged_files.append(mfile)
        #elif type == 'iterative':
            
        return merged_files

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
        
