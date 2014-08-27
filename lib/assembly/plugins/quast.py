import glob
import logging
import os
import subprocess
from plugins import BaseAssessment
from yapsy.IPlugin import IPlugin
import asmtypes

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
        cmd_args += ['-l', '"{}"'.format(', '.join([cset.name for cset in contigsets]))]
        

        #### Run Quast ####
        self.arast_popen(cmd_args)
        
        output = {}
        report = os.path.join(self.outpath, 'report.txt')
        ttsv = os.path.join(self.outpath, 'transposed_report.tsv')
        if not os.path.exists(report):
            print 'No Quast Output'
            report = None
        else: 
            output['report'] = report
            output['stats'] = self.parse_ttsv(ttsv)
        return output
    
    def parse_ttsv(self, ttsv):
        "Parse the transposed TSV report"
        stats = {}
        with open(ttsv) as report:
            labels = report.readline().split('\t')
            for line in report:
                vals = line.split('\t')
                stats[vals[0]] = dict(zip(labels[1:], vals[1:]))
        return stats
            
