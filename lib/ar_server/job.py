import os
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy.numarray as na

class ArastJob(dict):
    """

    """
    def __init__(self, *args):
        dict.__init__(self, *args)
        self['pipelines'] = [] # List of ArastPipeline
        
    def make_plots(self):
        pass

    def plot_ale(self):
        a_scores = []
        names = []
        for pl in self['pipelines']:
            try:
                a_scores.append(pl['stats']['ale_score'])
                names.append(pl['name'])
            except:
                pass
            
        if len(a_scores) < 2:
            print ('Not enough ALE scores')
            return

        ## normalize scores
        old_min = min(a_scores)
        old_max = max(a_scores)
        new_min = 5
        new_max = 100
        old_range = old_max - old_min
        new_range = new_max - new_min
        n_scores = []
        for a in a_scores:
            n = (((a - old_min) * new_range) / old_range) + new_min
            n_scores.append(n)

        xlocations = na.array(range(len(n_scores))) + 0.5
        width = 0.5
        fig = plt.figure()
        plt.bar(xlocations, n_scores, width=width)
        plt.xticks(xlocations + width/2, names)
        plt.xlim(0, xlocations[-1]+width*2)
        plt.title("Relative ALE Scores")
        plt.yticks(range(0, new_max + 10, 10))
        ale_fig = os.path.join(self['datapath'], str(self['job_id']), 'ale.png')
        plt.savefig(ale_fig)
        return ale_fig
        

    def export(self):
        pass

    def import_quast(self, qreport):
        if self['reference']:
            n50_line = 14
        else:
            n50_line = 12
        f = open(qreport)
        for i in range(n50_line):
            line = f.readline()
        n50_scores = [int(x) for x in re.split('\s*', line)[1:-1]]
        if len(n50_scores) == len(self['pipelines']):
            for i,pipe in enumerate(self['pipelines']):
                pipe['stats']['N50'] = n50_scores[i]


    def add_pipeline(self, num, modules):
        """ MODULES is a list or dict """
        pipeline = ArastPipeline({'number': num})
                                
        if type(modules) is list:
            for i, module in enumerate(modules):
                new_module = ArastModule({'number': i+1,
                                          'module': module})
                pipeline['modules'].append(new_module)
        self['pipelines'].append(pipeline)
        return pipeline

    def get_pipeline(self, number):
        for pipeline in self['pipelines']:
            if pipeline['number'] == number:
                return pipeline


class ArastPipeline(dict):
    """ Pipeline object """
    
    def __init__(self, *args):
        dict.__init__(self, *args)
        self['modules'] = []
        self['stats'] = {}

    def get_module(self, number):
        for module in self['modules']:
            if module['number'] == number:
                return module

    def import_reapr(self):
        pass

    def import_ale(self, ale_report):
        f = open(ale_report)
        line = f.readline()
        self['stats']['ale_score'] = float(line.split(' ')[2])
        f.close()

class ArastModule(dict):
    def __init__(self, *args):
        dict.__init__(self, *args)

