import glob
import logging
import os
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class SmrtAssembler(BaseAssembler, IPlugin):
    def run(self):
        """
        Build the command and run.
        Return list of contig file(s)
        """

        cmd_args = [self.executable]

        cmd_args += ['--cov',     self.coverage]
        cmd_args += ['--gs',      self.genome_size]
        cmd_args += ['--minlong', self.min_long_read_length]
        cmd_args += ['--np',      self.nproc]

        reads = self.data.readsets
        for lib in reads:
            if lib['type'] == 'paired':
                if len(lib.files) == 2: # 2 Files
                    cmd_args += ['-p', lib.files[0], lib.files[1]]
            elif lib['type'] == 'single':
                cmd_args += ['-f', lib.files[0]]

        cmd_args.append('-o')
        cmd_args.append(self.outpath + 'smrt')

        self.arast_popen(cmd_args)
        self.arast_popen(['cp', os.path.join(self.outpath+'smrt', 'contigs.fa'), self.outpath])

        contigs = os.path.join(self.outpath, 'contigs.fa')

        if os.path.exists(contigs):
            return {'contigs': [contigs]}
        return
