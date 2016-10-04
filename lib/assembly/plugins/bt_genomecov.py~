import logging
import os
from plugins import BaseAssessment
from yapsy.IPlugin import IPlugin
from asmtypes import ArastDataOutputError

logger = logging.getLogger(__name__)

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
        if len(reads) > 1:
            self.out_module.write('WARNING: Reapr will use only one read library')
        read_pair = reads[0].files
        bamfile =  os.path.join(self.outpath, 'out.bam')
        cmd_args = [self.executable, 'smaltmap', contigs[0],
                    read_pair[0], read_pair[1], bamfile]
        self.arast_popen(cmd_args)

        if not os.path.exists(bamfile):
            raise ArastDataOutputError('REAPR: Unable to create alignment')

        #### Run REAPR Pipeline
        rpr_outpath = os.path.join(self.outpath, 'output')
        cmd_args = [self.executable, 'pipeline', contigs[0], bamfile, rpr_outpath]
        self.arast_popen(cmd_args)

        # Move files into root dir
        for f in os.listdir(rpr_outpath):
            old = os.path.join(rpr_outpath, f)
            new = os.path.join(self.outpath, f)
            os.rename(old, new)

        broken = os.path.join(self.outpath, '04.break.broken_assembly.fa')
        if os.path.exists(broken):
            return {'contigs': [broken]}
