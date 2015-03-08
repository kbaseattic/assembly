import glob
import logging
import os
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

logger = logging.getLogger(__name__)

class KikiAssembler(BaseAssembler, IPlugin):
    new_version = True

    def run(self, reads=None):
        ### Run Kiki Assembler
        self.arast_popen([self.executable, '-k', self.k, '-i'] + self.data.readfiles + ['-o', self.outpath + '/kiki'])

        ### Find Contig Files
        contigs = glob.glob(self.outpath + '/*.contig')
        contigs_renamed = [contig + '.fa' for contig in contigs]

        ### Convert to standard FastA
        for i in range(len(contigs)):
            self.tab_to_fasta(contigs[i], contigs_renamed[i], self.contig_threshold)

        return {'contigs': contigs_renamed}

    def tab_to_fasta(self, tabbed_file, outfile, threshold):
        """ Converter for Kiki format """
        tabbed = open(tabbed_file, 'r')
        fasta = open(outfile, 'w')
        prefixes = ['>', ' len_', ' cov_', ' stdev_', ' GC_', ' seed_', '\n']
        for line in tabbed:
            l = line.split('\t')
            if int(l[1]) >= int(threshold):
                for i in range(len(l)):
                    fasta.write(prefixes[i] + l[i])
        tabbed.close()
        fasta.close()
