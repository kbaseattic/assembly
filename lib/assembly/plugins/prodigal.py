import glob
import os
from plugins import BaseAssessment
from yapsy.IPlugin import IPlugin

class ProdigalAssessment(BaseAssessment, IPlugin):
    def run(self):
        outfiles = []
        for contigfile in self.data.contigfiles:
            newfile = '{}.genes'.format(os.path.basename(contigfile))
            outfile = os.path.join(self.outpath, newfile)
            self.arast_popen([self.executable, 
                              '-i', contigfile,
                              '-o', outfile])
            if os.path.exists(outfile):
                outfiles.append(outfile)
        return {'report': outfiles}
    
