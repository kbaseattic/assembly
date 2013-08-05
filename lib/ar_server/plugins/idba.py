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
	d = reads[0]
        cwd = os.getcwd()
        cmd_args = [os.path.join(cwd, self.bin_idba_ud)]
        read_file = d['files'][0]
        if d['type'] == 'paired':
            if len(d['files']) == 2 :
                parts = d['files'][0].rsplit('.',1)
                ## TODO move this to idba folder
                merged_read = parts[0] + '.idba_merged.fa'
                merge_cmd = [os.path.join(cwd, self.bin_fq2fa), '--merge', '--filter',
                             d['files'][0],
                             d['files'][1],
                             merged_read]
                self.arast_popen(merge_cmd, overrides=False)
                read_file = merged_read

        # If in fastq
        if infer_filetype(read_file) == 'fastq':
            parts = read_file.rsplit('.', 1)
            fa_file = '{}.fasta'.format(parts[0])
            fqfa_command = [os.path.join(cwd, self.bin_fq2fa), read_file, fa_file]
            self.arast_popen(fqfa_command, overrides=False)
            read_file = fa_file

        base = os.path.join(self.outpath, 'run')
        cmd_args += ['-r', read_file, '-o', base, '--maxk', self.max_k] 
        self.arast_popen(cmd_args, cwd=self.outpath)
        self.outpath = base
        contig ="{}/contig.fa".format(base)
        if os.path.exists(contig):
            return [contig]
        else:
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



    
