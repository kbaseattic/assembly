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
        file_idx = 0
        file_stats = {}
        for f in os.listdir(self.outpath):
            read_dir = os.path.join(self.outpath, f)
            if os.path.isdir(read_dir):

                fastqc_data = os.path.join(read_dir, 'fastqc_data.txt')
                new_name = os.path.join(read_dir, f + '.txt')
                os.rename(fastqc_data, new_name)

                ## Read in stats
                file_stats[str(file_idx)] = {}
                with open(new_name) as f:
                    for line in f:
                        if '>>' in line:
                            stat_pair = line.split('\t')
                            if len(stat_pair) == 2:
                                file_stats[str(file_idx)][stat_pair[0][2:]] = stat_pair[1].strip()
                file_idx += 1
                reports.append(new_name)
        return {'report': reports, "file_stats": file_stats}
