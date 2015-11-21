import os
import re
# import matplotlib
# matplotlib.use('Agg')
# import matplotlib.pyplot as plt

import asmtypes
import shock

class ArastJob(dict):
    """

    """
    def __init__(self, *args):
        dict.__init__(self, *args)
        self['pipelines'] = [] # List of ArastPipeline
        self['out_contigs'] = []
        self['out_scaffolds'] = []
        self['logfiles'] = []
        self['out_reports'] = []
        self['out_results'] = []
        self['plugin_output'] = []

    def make_plots(self):
        pass

    # def plot_ale(self):
    #     a_scores = []
    #     names = []
    #     for pl in self['pipelines']:
    #         try:
    #             a_scores.append(pl['stats']['ale_score'])
    #             names.append(pl['name'])
    #         except:
    #             pass

    #     if len(a_scores) < 2:
    #         print ('Not enough ALE scores')
    #         return

    #     ## normalize scores
    #     old_min = min(a_scores)
    #     old_max = max(a_scores)
    #     new_min = 5
    #     new_max = 100
    #     old_range = old_max - old_min
    #     new_range = new_max - new_min
    #     n_scores = []
    #     for a in a_scores:
    #         n = (((a - old_min) * new_range) / old_range) + new_min
    #         n_scores.append(n)

    #     xlocations = na.array(range(len(n_scores))) + 0.5
    #     width = 0.5
    #     fig = plt.figure()
    #     plt.bar(xlocations, n_scores, width=width, linewidth=0, color='#CC99FF')
    #     plt.xticks(xlocations + width/2, names)
    #     plt.xlim(0, xlocations[-1]+width*2)
    #     plt.title("Relative ALE Scores")
    #     plt.yticks(range(0, new_max + 10, 10))
    #     ale_fig = os.path.join(self['datapath'], str(self['job_id']), 'ale.png')
    #     plt.savefig(ale_fig)
    #     return ale_fig


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

    def add_results(self, filesets):
        if filesets:
            if not type(filesets) is list:
                filesets = [filesets]
            for f in filesets:
                self['out_results'].append(f)

    @property
    def results(self):
        """Return all output FileSets"""
        return self['out_results']

    def get_all_ftypes(self):
        ft = []
        for fileset in self.get_all_filesets():
            for fileinfo in fileset['file_infos']:
                ft.append((fileinfo['local_file'], fileset['type']))
        return ft

    def upload_results(self, url, token):
        """ Renames and uploads all filesets and updates shock info """
        new_sets = []
        rank = 1
        for i,fset in enumerate(self.results):
            if fset.type == 'contigs' or fset.type == 'scaffolds':
                fset.add_tag('rank-' + str(rank))
                rank += 1
            new_files = []
            for j, f in enumerate(fset['file_infos']):
                if len(fset['file_infos']) > 1:
                    file_suffix = '_{}'.format(j+1)
                else: file_suffix = ''
                ext = f['local_file'].split('.')[-1]
                if not f['keep_name']:
                    new_file = '{}/{}.{}{}.{}'.format(os.path.dirname(f['local_file']),
                                                      i+1, fset.name, file_suffix, ext)
                    os.symlink(f['local_file'], new_file)
                else: new_file = f['local_file']
                res = self.upload_file(url, self['user'], token, new_file, filetype=fset.type)
                f.update({'shock_url': url, 'shock_id': res['data']['id'],
                          'filename': os.path.basename(new_file)})
                new_files.append(f)
            fset.update_fileinfo(new_files)
            new_sets.append(fset)
        self['result_data'] = new_sets
        return new_sets

    def upload_file(self, url, user, token, file, filetype='default'):
        files = {}
        files["file"] = (os.path.basename(file), open(file, 'rb'))
        sclient = shock.Shock(url, user, token)
        res = sclient.upload_file(file, filetype, curl=True)
        return res

    def wasp_data(self):
        """
        Compatibility layer for wasp data types.
        Scans self for certain data types and populates a FileSetContainer
        """
        all_sets = []
        #### Convert Old Reads Format to ReadSets
        for set_type in ['reads', 'reference', 'contigs']:
            if set_type in self:
                for fs in self[set_type]:
                    ### Get supported set attributes (ins, std, etc)
                    kwargs = {}
                    for key in ['insert', 'stdev', 'tags']:
                        if key in fs:
                            kwargs[key] = fs[key]
                    all_sets.append(asmtypes.set_factory(fs['type'],
                                                         [asmtypes.FileInfo(f) for f in fs['files']],
                                                         **kwargs))

        #### Convert final_contigs from pipeline mode
        if 'final_contigs' in self:
            if self['final_contigs']: ## Not empty
                ## Remove left over contigs
                del(self['contigs'])
                for contig_data in self['final_contigs']:
                    all_sets.append(asmtypes.set_factory('contigs',
                                                         [asmtypes.FileInfo(fs,) for fs in contig_data['files']],
                                                         #{'name':contig_data['name']}))
                                                         name=contig_data['name']))

        #### Convert Contig/Ref format
        # for set_type in ['contigs', 'reference']:
        #     if set_type in self:
        #         all_sets.append(asmtypes.set_factory(set_type, [asmtypes.FileInfo(fs) for fs in self[set_type]]))

        return asmtypes.FileSetContainer(all_sets)


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
