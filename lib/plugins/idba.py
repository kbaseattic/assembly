import os
import logging
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class IdbaAssembler(BaseAssembler, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.
        Return list of contig file(s)
        """

        read_file = d['files'][0]
        if d['type'] == 'paired':
            if self.scaffold:
                cmd_args.append('--scaffold')
            if len(d['files']) == 2:
                parts = d['files'][0].rsplit('.',1)
                ## TODO move this to idba folder
                merged_read = parts[0][:-1] + '.idba_merged.' + parts[1]
                merge_cmd = [self.bin_mergeReads,
                             d['files'][0],
                             d['files'][1],
                             merged_read]
                self.arast_popen(merge_cmd)
                read_file = merged_read

        # If in fastq
        if infer_filetype(read_file) == 'fastq':
            parts = read_file.rsplit('.', 1)
            fa_file = '{}.fasta'.format(parts[0])
            fqfa_command = [self.bin_fq2fa, read_file, fa_file]
            read_file = fa_file

        cmd_args = [self.bin_idba_ud, '--read', read_file, '-o', 'idba']        
        self.arast_popen(cmd_args, cwd=self.outpath)
        
        return []

def infer_filetype(file):
    filemap = {'.fa':'fasta',
               '.fasta' :'fasta',
               '.fq':'fastq',
               '.fastq' :'fastq'}
    for ext in filemap:
        if file.endswith(ext):
            return filemap[ext]
    return ''
