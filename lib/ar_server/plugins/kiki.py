import glob
import logging
import os
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class KikiAssembler(BaseAssembler, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.
        Return list of contig file(s)
        """
        
        cmd_args = [self.executable, '-k', self.k, '-i',]
        cmd_args += self.get_files(reads)
        cmd_args.append('-o')
        cmd_args.append(self.outpath + '/kiki')
        #self.out_module.write(subprocess.check_output(cmd_args))
        self.arast_popen(cmd_args)

        contigs = glob.glob(self.outpath + '/*.contig')
        contigs_renamed = [contig + '.fa' for contig in contigs]
        for i in range(len(contigs)):
            self.tab_to_fasta(contigs[i], contigs_renamed[i], self.contig_threshold)
        if not contigs_renamed:
            pass
            #raise Exception("No contigs")
        return contigs_renamed

    def tab_to_fasta(self, tabbed_file, outfile, threshold):
        tabbed = open(tabbed_file, 'r')
        fasta = open(outfile, 'w')
        prefixes = ['>_', ' len_', ' cov_', ' stdev_', ' GC_', ' seed_', '\n']
        for line in tabbed:
            l = line.split('\t')
            if int(l[1]) >= int(threshold):
                for i in range(len(l)):
                    fasta.write(prefixes[i] + l[i])
        tabbed.close()
        fasta.close()
