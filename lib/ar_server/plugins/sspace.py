import glob
import logging
import math
import os
import subprocess
from plugins import BaseScaffolder
from vendor import assemstats2 as astats
from yapsy.IPlugin import IPlugin

class SspaceScaffolder(BaseScaffolder, IPlugin):
    def run(self, read_records, contig_file, job_data):
        """ 
        Build the command and run.
        Return list of contig file(s)
        """
        ## Get insert size
        if len(read_records) > 1:
            raise NotImplementedError
        reads = read_records[0]
        read_files = reads['files']

        if reads['type'] == 'single':
            raise Exception('Cannot scaffold with single end')
        try:
            insert_size = int(reads['insert'])
        except:
            insert_size, _ = self.estimate_insert_stdev(contig_file, read_files)
            
        genome_size = sum(astats.getLens(contig_file))
        ## Min overlap for extension, decision based on A5
        if  self.m == '-1':

            min_overlap = max(self.minimum_overlap, 
                              int(math.log(genome_size, 2) + 3.99))
        else:
            min_overlap = int(self.m)
        
        ## Min overlap for merging, decision based on A5
        if self.n == '-1':
            min_merge_overlap = int(math.log(insert_size, 2) * 1.25 + 0.99)
        else:
            min_merge_overlap = int(self.n)

        ## K minimal links, based on A5
        if self.k == '-1':
            max_read_length, read_count = self.calculate_read_info(job_data)
            coverage = max_read_length * read_count / genome_size
            expected_links = coverage * insert_size / max_read_length
            min_links = int(math.log(expected_links)/math.log(1.4)-11.5)
        else:
            min_links = int(self.k)

        ## Pair ratio A
        pair_ratio = self.a

        ## Create library file
        lib_filename = os.path.join(self.outpath,
                                    str(job_data['job_id']) + '_libs.txt')
        lib_file = open(lib_filename, 'w')
        lib_data = [job_data['job_id']]
        lib_data += read_files
        lib_data.append(insert_size)
        # insert error ratio
        lib_data.append('0.2')
        print lib_data
        for word in lib_data:
            lib_file.write(str(word) + ' ')
        lib_file.write(str(int(self.reverse_complement == 'True')))
        lib_file.close()

        cmd_args = [self.executable, 
                    '-m', str(min_overlap),
                    '-n', str(min_merge_overlap),
                    '-k', str(min_links),
                    '-a', str(pair_ratio),
                    '-l', lib_filename,
                    '-s', contig_file,
                    '-b', str(job_data['job_id']),
                    '-x', self.x]
        
        self.arast_popen(cmd_args, cwd=self.outpath)

        final_scaffolds = os.path.join(self.outpath,
                                       str(job_data['job_id']) + 
                                       '.final.scaffolds.fasta')
        return [final_scaffolds]
        
