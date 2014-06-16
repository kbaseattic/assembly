import os
from plugins import BaseAssessment
from yapsy.IPlugin import IPlugin

class ReaprAssessment(BaseAssessment, IPlugin):
    OUTPUT = 'contigs'
    def run(self):
        """ 
        Build the command and run.
        Return list of file(s)
        """
        contigs = self.data.contigfiles
        reads = self.data.readsets
        if len(contigs) > 1:
            raise Exception('Reapr: multiple contig files!')

        #### Generate Bamfiles
        exp = '(bwa (contigs {}) READS)'.format(contigs[0])
        samfile = self.plugin_engine.run_expression(exp).files[0]
        bamfile = samfile.replace('.sam', '.bam')
        cmd_args = ['samtools', 'view',
                    '-bSho', bamfile, samfile]
        self.arast_popen(cmd_args, overrides=False)
        sortedfile = os.path.join(self.outpath, 'sorted')
        cmd_args = ['samtools', 'sort', bamfile, sortedfile]
        self.arast_popen(cmd_args, overrides=False)
        undupfile = sortedfile + '_undup.bam'
        sortedfile = sortedfile + '.bam'
        cmd_args = ['samtools', 'rmdup', sortedfile, undupfile]
        self.arast_popen(cmd_args, overrides=False)

        #### Run REAPR Pipeline
        rpr_outpath = os.path.join(self.outpath, 'output')
        cmd_args = [self.executable, 'pipeline', contigs[0], undupfile, rpr_outpath]
        self.arast_popen(cmd_args)

        # Move files into root dir
        for f in os.listdir(rpr_outpath):
            old = os.path.join(rpr_outpath, f)
            new = os.path.join(self.outpath, f)
            os.rename(old, new)

        broken = os.path.join(self.outpath, '04.break.broken_assembly.fa')
        if os.path.exists(broken):
            return {'contigs': [broken]}


