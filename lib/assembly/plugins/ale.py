import copy
import glob
import logging
import os
import subprocess
from plugins import BaseAssessment
from yapsy.IPlugin import IPlugin

class AleAssessment(BaseAssessment, IPlugin):
    def run(self):
        """ 
        Build the command and run.
        Return list of file(s)
        """
        contigs = self.data.contigfiles[0]
        exp = '(bowtie2 (contigs {}) READS)'.format(contigs)
        samfile = self.plugin_engine.run_expression(exp).files[0]
        cmd_args = [self.executable, samfile, contigs,
                    os.path.join(self.outpath, 'ale.txt')]
        self.arast_popen(cmd_args)
        report = os.path.join(self.outpath, 'ale.txt')
        output = {}
        if os.path.exists(report):
            output['report'] =  report
            ## Parse report for ALE Score
            with open(report) as r:
                ale_score = float(r.readline().split(' ')[2].strip())
                self.out_module.write('ALE Score: {}'.format(ale_score))
                print('ALE Score: {}'.format(ale_score))
                output['ale_score'] = ale_score
        return output


