import os
import logging
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class IdbaAssembler(BaseAssembler, IPlugin):
    new_version = True

    def run(self):
        """ 
        Build the command and run.
        Return list of contig file(s)
        """
        # Only supports one set of reads
        
        if not len(self.data.readsets_paired) == 1:
            raise Exception('IDBA assembler requires one paired-end library')

        readset = self.data.readsets[0]
        if self.data.readsets_single:
            self.out_module.write('Warning, discarding single end files\n')

        cmd_args = [self.bin_idba_ud,
                    '--num_threads', self.process_threads_allowed]
        read_file = readset.files[0]

        #Merge file if pairs are separate
        if len(readset.files) == 2 :
            parts = readset.files[0].rsplit('.',1)
            ## TODO move this to idba folder
            merged_read = parts[0] + '.idba_merged.fa'
            merge_cmd = [self.bin_fq2fa, '--merge', '--filter',
                         readset.files[0],
                         readset.files[1],
                         merged_read]
            self.arast_popen(merge_cmd, overrides=False)
            read_file = merged_read

        # Convert if files are fastq
        if infer_filetype(read_file) == 'fastq':
            parts = read_file.rsplit('.', 1)
            fa_file = '{}.fasta'.format(parts[0])
            fqfa_command = [self.bin_fq2fa, read_file, fa_file]
            self.arast_popen(fqfa_command, overrides=False)
            read_file = fa_file

        base = os.path.join(self.outpath, 'run')
        cmd_args += ['-r', read_file, '-o', base, '--maxk', self.max_k] 
        self.arast_popen(cmd_args, cwd=self.outpath)

        contigs = os.path.join(base, 'contig.fa')
        scaffolds = os.path.join(base, 'scaffold.fa')

        output = {}
        if os.path.exists(contigs):
            output['contigs'] = [contigs]
        if os.path.exists(scaffolds):
            output['scaffolds'] = [scaffolds]
        return output

def infer_filetype(file):
    filemap = {'.fa':'fasta',
               '.fasta' :'fasta',
               '.fq':'fastq',
               '.fastq' :'fastq'}
    for ext in filemap:
        if file.endswith(ext):
            return filemap[ext]
    return ''



    
