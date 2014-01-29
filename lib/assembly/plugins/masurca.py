import os
import logging
import time
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class MasurcaAssembler(BaseAssembler, IPlugin):
    def run(self, reads):
        """ 
        Build the command and run.
        Return list of contig file(s)
        """
        
        ## Build config file
        config_fname = os.path.join(self.outpath, 
                                    str(self.job_data['job_id']) + '_config.txt')
        cf = open(config_fname, 'w')

        cf.write('PATHS\n')
        cf.write('JELLYFISH_PATH={}\n'.format(self.jellyfish_path))
        cf.write('SR_PATH={}\n'.format(self.sr_path))
        cf.write('CA_PATH={}\n'.format(self.ca_path))
        cf.write('END\n')

        cf.write('DATA\n')
        for pair in [lib for lib in reads if lib['type'] == 'paired']:
            lib_count = 1
            try:
                insert = pair['insert']
                stdev = pair['stdev']
            except:
                print 'No insert size data'
                return
            files = ' '.join(pair['files'])
            cf.write('PE= p{} {} {} {}\n'.format(
                    lib_count, insert, stdev, files))
            lib_count += 1
        for jump in [lib for lib in reads if lib['type'] == 'jump']:
            lib_count = 1
            try:
                insert = jump['insert']
                stdev = jump['stdev']
            except:
                print 'No insert size data'
                return
            files = ' '.join(jump['files'])
            cf.write('PE= p{} {} {} {}\n'.format(
                    lib_count, insert, stdev, files))
            lib_count += 1
        cf.write('END\n')

        cf.write('PARAMETERS\n')
        cf.write('GRAPH_KMER_SIZE={}\n'.format(self.graph_kmer_size))

        ## Determine if Illumina (1) or longer (2)
        if self.use_linking_mates == 'auto':
            max_read_length, _ = self.calculate_read_info()
            if max_read_length > 300:
                use_linking_mates = 0
            else:
                use_linking_mates = 1
        cf.write('USE_LINKING_MATES={}\n'.format(use_linking_mates))
        cf.write('LIMIT_JUMP_COVERAGE = {}\n'.format(self.limit_jump_coverage))
        cf.write('CA_PARAMETERS = {}\n'.format(self.ca_parameters))
        cf.write('KMER_COUNT_THREASHOLD = {}\n'.format(self.kmer_count_threshold))
        if self.num_threads == 'auto':
            num_threads = self.process_threads_allowed
        else:
            num_threads = self.num_threads
        cf.write('NUM_THREADS = {}\n'.format(num_threads))
        cf.write('JF_SIZE={}\n'.format(self.jf_size))
        cf.write('DO_HOMOPOLYMER_TRIM={}\n'.format(self.do_homopolymer_trim))
        cf.write('END\n')
        cf.close()

        self.arast_popen([self.executable, config_fname], cwd=self.outpath)
        self.arast_popen('bash {}'.format(os.path.join(self.outpath, 'assemble.sh')), cwd=self.outpath, shell=True)

        try:
            mv_scaffolds = os.path.join(self.outpath, 'genome.scf.fasta')
            scaffolds = os.path.join(self.outpath, 'CA', '10-gapclose', 'genome.scf.fasta')
            os.rename(scaffolds, mv_scaffolds)
            contigs = os.path.join(self.outpath, 'CA', '10-gapclose','genome.ctg.fasta')
            mv_contigs = os.path.join(self.outpath, 'genome.ctg.fasta')
            os.rename(contigs, mv_contigs)
            if os.path.exists(mv_contigs):
                return [mv_contigs]
            # if os.path.exists(mv_scaffolds):
            #     return [mv_scaffolds]
        except:
            pass
        return []


    
