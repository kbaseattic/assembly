import glob
import logging
import os
import subprocess
from plugins import BaseAssessment
from yapsy.IPlugin import IPlugin
import asmtypes

logger = logging.getLogger(__name__)

class QuastAssessment(BaseAssessment, IPlugin):
    new_version = True

    def run(self):
        contigsets = self.data.contigsets
        for i,c, in enumerate(contigsets):
            c['tags'].append('quast-{}'.format(i+1))
        contigfiles = self.data.contigfiles
        if len(contigsets) == 0: #Check for scaffolds
            contigsets = self.data.scaffoldsets
            contigfiles = self.data.scaffoldfiles
            scaffolds = True
            assert len(contigsets) != 0
        else: scaffolds = False

        ref = self.initial_data.referencefiles or None

        cmd_args = [os.path.join(os.getcwd(),self.executable),
                    '--threads', self.process_threads_allowed,
                    '--min-contig', self.min_contig,
                    '-o', self.outpath,
                    '--gene-finding']
        if scaffolds: cmd_args.append('--scaffolds')

        #### Add Reference ####
        if ref:
            rfile = ref[0]
            cmd_args += ['-R', rfile, '--gage']

        #### Add Contig files ####
        cmd_args += contigfiles
        try:
            cmd_args += ['-l', '"{}"'.format(', '.join([cset.name for cset in contigsets]))]
        except TypeError: # Contigset has no names
            pass

        #### Run Quast ####
        self.arast_popen(cmd_args)

        output = {}
        report = os.path.join(self.outpath, 'report.txt')
        if not os.path.exists(report):
            logger.warning('No Quast Output')
            report = None
        else: output['report'] = report
        return output
