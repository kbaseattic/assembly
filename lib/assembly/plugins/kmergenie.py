import os
from plugins import BaseAnalyzer
from yapsy.IPlugin import IPlugin

class KmergenieAnalyzer(BaseAnalyzer, IPlugin):
    def run(self):
        cmd_args = [self.executable]
        cmd_args += ['-t', self.process_threads_allowed]
        cmd_args += [self.data.readfiles[0]]
        self.arast_popen(cmd_args, cwd=self.outpath)
        report = os.path.join(self.outpath, 'histograms_report.html')
        output = {}
        if os.path.exists(report):
            output['report'] =  report

        ### Get last line of log. Close, reopen for reading
        logname = self.out_module.name
        self.out_module.close()
        with open(logname, 'r') as log:
            for line in log:
                last = line
        self.out_module = open(logname, 'a')
        output['best_k'] = last.split(' ')[-1].strip()
        return output


