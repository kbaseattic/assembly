import os
from plugins import BaseAnalyzer
from yapsy.IPlugin import IPlugin

class FastQCAnalyzer(BaseAnalyzer, IPlugin):
    def run(self):
        """ 
        Build the command and run.
        """

        self.arast_popen([self.executable, '-o', self.outpath] + self.data.readfiles)
        
        # Return reports
        reports = []
        for f in os.listdir(self.outpath):
            read_dir = os.path.join(self.outpath, f)
            if os.path.isdir(read_dir):
                fastqc_data = os.path.join(read_dir, 'fastqc_data.txt')
                new_name = os.path.join(read_dir, f + '.txt')
                os.rename(fastqc_data, new_name)
                reports.append(new_name)

        return {'report': reports}
