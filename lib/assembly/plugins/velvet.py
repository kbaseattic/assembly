import os
import logging
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

logger = logging.getLogger(__name__)

class VelvetAssembler(BaseAssembler, IPlugin):
    new_version = True


    def run(self, reads=None):
        """
        Build the command and run.
        Return list of contig file(s)
        """

        cmd_args = [self.bin_velveth, self.outpath, self.hash_length]

        #### Add Paired Reads ####
        pair_info = {}
        for pair_num, pairset in enumerate(self.data.readsets_paired):
            if pair_num == 0: p_suffix = ''
            else: p_suffix = str(pair_num + 1)
            read1 = pairset.files[0]
            cmd_args.append('-shortPaired' + p_suffix)
            if infer_filetype(read1):
                cmd_args.append('-' + infer_filetype(read1))
            try:
                read2 = pairset.files[1]
                cmd_args.append('-separate')
                cmd_args.append(read1)
                cmd_args.append(read2)
            except:
                cmd_args.append('-interleaved')
                cmd_args.append(read1)
            ## Store (insert,stdev)
            if pairset.insert:
                pair_info[p_suffix] = (pairset.insert, pairset.stdev)
            elif self.auto_insert == 'True':
                velvet_results = self.plugin_engine.run_expression('(velvet (paired {}))'.format(' '.join(pairset.files)))
                insert, stdev = self.estimate_insert_stdev(velvet_results.files[0], pairset.files)
                pair_info[p_suffix] = (insert, stdev)
        #### Add Single Reads ####
        for s_num, s_set in enumerate(self.data.readsets_single):
            if s_num == 0: s_suffix = ''
            else: s_suffix = str(s_num + 1)
            read = s_set.files[0]
            cmd_args.append('-' + 'short' + s_suffix)
            cmd_args.append('-' + infer_filetype(read))
            cmd_args.append(read)

        self.arast_popen(cmd_args)

        cmd_args = [self.bin_velvetg, self.outpath, '-exp_cov', 'auto']

        ## Velvet only supports one library?

        for suf in pair_info.keys():
            try:
                insert = pair_info[suf][0]
                stdev = pair_info[suf][1]
                cmd_args += ['-ins_length{}'.format(suf), str(insert),
                             '-ins_length{}_sd'.format(suf), str(stdev)]
            except:pass

        logger.debug(cmd_args)
        self.arast_popen(cmd_args)
        contigs = [self.outpath + '/contigs.fa']
        if not os.path.exists(contigs[0]):
            contigs = []
        return {'contigs': contigs}

def infer_filetype(file):
    filemap = {'.fa':'fasta',
               '.fasta' :'fasta',
               '.fq':'fastq',
               '.fastq' :'fastq'}
    for ext in filemap:
        if file.endswith(ext):
            return filemap[ext]
    return ''
