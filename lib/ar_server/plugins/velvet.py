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
        
        cmd_args = [self.bin_velveth, self.outpath, self.hash_length]
        paired_count = 1                    
        single_count = 1
        pair_data = {}
        for d in reads:
            if paired_count == 1:
                p_suffix = ''
            else:
                p_suffix = str(single_count)
            if single_count == 1:
                s_suffix = ''
            else:
                s_suffix = str(single_count)

            read1 = d['files'][0]

            if d['type'] == 'paired':
                cmd_args.append('-' + 'shortPaired' + p_suffix)
                cmd_args.append('-' + infer_filetype(read1))
                paired_count += 1
                try:
                    read2 = d['files'][1] # If 2 files
                    cmd_args.append('-separate')
                    cmd_args.append(read1)
                    cmd_args.append(read2)
                except:
                    cmd_args.append(read1)

                try:
                    pair_data[p_suffix] = (d['insert'], d['stdev'])
                except:
                    pass
            elif d['type'] == 'single':
                cmd_args.append('-' + 'short' + s_suffix)
                cmd_args.append('-' + infer_filetype(read1))
                cmd_args.append(read1)
                single_count += 1
                
        logging.info("Running subprocess:{}".format(cmd_args))
        self.arast_popen(cmd_args)        
        cmd_args = [self.bin_velvetg, self.outpath, '-exp_cov', 'auto']
        for suf in pair_data.keys():
            insert = pair_data[suf][0]
            stdev = pair_data[suf][1]
            cmd_args += ['-ins_length{}'.format(suf), insert, 
                         '-ins_length{}_sd'.format(suf), stdev]
        self.arast_popen(cmd_args)        
        contigs = [self.outpath + '/contigs.fa']
        if not os.path.exists(contigs[0]):
            contigs = []
            #raise Exception("No contigs")
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
