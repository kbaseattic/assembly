import logging
import os
from plugins import BaseMetaAssembler
from yapsy.IPlugin import IPlugin
import asmtypes

logger = logging.getLogger(__name__)

class GamNgsAssembler(BaseMetaAssembler, IPlugin):
    new_version = True

    def run(self):
        contigsets = self.data.contigsets
        if len(contigsets) < 2:
            raise Exception('Fewer than 2 contig sets')
        merged_files = []

        if len(contigsets) == 2:
            mfile = self.merge(contigsets[0], contigsets[1])
            if mfile:
                merged_files.append(mfile)
        elif len(contigsets) > 2:
            mfile = contigsets[0]
            for i, cset in enumerate(contigsets[1:]):
                mfile = asmtypes.set_factory('contigs', [self.merge(mfile, cset)],
                                             name='merged{}_contigs'.format(i+1))
            merged_files = mfile.files

        return {'contigs': merged_files}

    def merge(self, contigset1, contigset2):
        asm1 = self.prepare_lib(contigset1)
        asm2 = self.prepare_lib(contigset2)
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


    def prepare_lib(self, cset):
        libfile = os.path.join(self.outpath, cset.name + '.lib')
        lib = open(libfile, 'w')
        bwa_results = self.plugin_engine.run_expression('(bwa (contigs {}) READS)'.format(cset.files[0]))
        samfile = bwa_results.files[0]
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
            logger.warning('Unable to perform alignment')
            raise Exception('Unable to perform alignment')
        cmd_args = ['samtools', 'index', undupfile]
        self.arast_popen(cmd_args, overrides=False)

        lib.write('{}\n'.format(undupfile))
        lib.write('50 10000\n')
        lib.close()
        return {'file': libfile,
                'name': cset.name,
                'contigs': cset.files[0]}
