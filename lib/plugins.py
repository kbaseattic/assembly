import abc
import logging 
import os
import uuid
from yapsy.PluginManager import PluginManager

# A-Rast modules
import assembly

class BasePlugin(object):
    """ 
    job_data dictionary must contain:
    - job_id
    - uid

    job_data could contain (dependent on stage of pipeline or input data)
    - reads: list of tuples eg. [('/data/unpaired.fa,), ('/data/1a.fa', '/data/1b.fa')]
    - contigs: list of contig files

    Available instance attributes:
    - self.outpath
    - self.PARAM_IN_CONFIG_FILE
        eg. self.k = 29
    """
        
    def create_directories(self, job_data):
        datapath = (job_data['datapath'] + '/' + str(job_data['job_id']) + 
                    '/' + self.name + '_' + str(uuid.uuid4())) + '/'
        logging.info("Creating directory: {}".format(datapath))
        os.makedirs(datapath)
        return datapath

    def get_valid_reads(self, job_data):
        """
        Based on plugin config file, filters for valid filetypes
        """

        filetypes = self.filetypes.split(',')
        filetypes = ['.' + filetype for filetype in filetypes]
        valid_files = []
        for filetype in filetypes:
            for d in job_data['reads']:
                if d['files'][0].endswith(filetype):
                    valid_files.append(d)
        if not valid_files:
            raise Exception('No valid input files (Compression unsupported)')
        return valid_files

    # def get_file_pair(reads):
    #     """ Return list of first and second (if possible) paired files 
    #         Returns empty list if single ended
    #     """
    #     pair = []
    #     for d in reads:
    #         if d['type'] == 'paired':
    #             pair.append(d['files'][0])
    #             try:
    #                 pair.append(d['files'][1])
    #             except:
    #                 pass
    #         return pair

    # def get_singled(reads):
    #     """ Return list of first and second (if possible) paired files 
    #         Returns empty list if single ended
    #     """
    #     pair = []
    #     for d in reads:
    #         if d['type'] == 'paired':
    #             pair.append(d['files'][0])
    #             try:
    #                 pair.append(d['files'][1])
    #             except:
    #                 pass
    #         return pair

    def init_settings(self, settings, job_data):
        for kv in settings:
            print kv
            setattr(self, kv[0], kv[1])

        for kv in job_data['params']:
            print "Override: {}".format(kv)
            setattr(self, kv[0], kv[1])


    def run_checks(self, settings, job_data):
        logging.info("Doing checks")
        #Check binary exists
        #Check data is valid
        pass

    def setname(self, name):
        self.name = name

    def tar(self, files, job_id):
        return assembly.tar_list(self.outpath, files, 
                                 self.name + str(job_id) + '.tar.gz')

    def tar_output(self, job_id):
        files = [self.outpath + file for file in os.listdir(self.outpath)]
        return assembly.tar_list(self.outpath, files, 
                                 self.name + str(job_id) + '.tar.gz')


    def update_settings(self, job_data):
        """
        Overwrite any new settings passed in JOB_DATA
        """
        pass

    def update_status(self):
        pass

    def write_report(self):
        pass

    
class BaseAssembler(BasePlugin):
    """
    An assembler plugin should implement a run() function

    """

    def __call__(self, settings, job_data):
        self.run_checks(settings, job_data)
        logging.info("{} Settings: {}".format(self.name, settings))
        self.init_settings(settings, job_data)
        self.outpath = self.create_directories(job_data)
        valid_files = self.get_valid_reads(job_data)
        return self.run(valid_files)


    def get_files(self, file_dicts):
        """ Return a list of files from dicts. """
        files = []
        for d in file_dicts:
            files += d['files']
        return files


    # Must implement run() method
    @abc.abstractmethod
    def run(self, reads):
        """
        Input: list of dicts contain file and read info
        Output: list of full paths to contig files.  File extensions should reflect
          the file type
          eg. return ['/data/contigs1.fa', '/data/contigs2.fa']
        """
        return

class BasePreprocessor(BasePlugin):
    """
    A preprocessing plugin should implement a run() function

    """

    def __call__(self, settings, job_data):
        self.run_checks(settings, job_data)
        logging.info("{} Settings: {}".format(self.name, settings))
        self.init_settings(settings, job_data)
        self.outpath = self.create_directories(job_data)
        valid_files = self.get_valid_reads(job_data)
        return self.run(valid_files)

    # Must implement run() method
    @abc.abstractmethod
    def run(self, reads):
        """
        Input: list of dicts contain file and read info
        Output: list of full paths to processed files.  File extensions should reflect
          the file type
          eg. return ['/data/read1.fa', '/data/read2.fa']
        """
        return

class ModuleManager():
    def __init__(self):
        self.pmanager = PluginManager()
        self.pmanager.setPluginPlaces(["plugins"])
        self.pmanager.collectPlugins()
        self.pmanager.locatePlugins()
        self.plugins = []
        if len(self.pmanager.getAllPlugins()) == 0:
            raise Exception("No Plugins Found!")
        for plugin in self.pmanager.getAllPlugins():
            self.plugins.append(plugin.name)
            plugin.plugin_object.setname(plugin.name)
            print "Plugin found: {}".format(plugin.name)

    def run_module(self, module, job_data, tar=False):
        if not self.has_plugin(module):
            raise Exception("No plugin named {}".format(module))
        plugin = self.pmanager.getPluginByName(module)
        settings = plugin.details.items('Settings')
        plugin.plugin_object.update_settings(job_data)
        if tar:
            plugin.plugin_object(settings, job_data)
            return plugin.plugin_object.tar_output(job_data['job_id'])

        return plugin.plugin_object(settings, job_data)

    def has_plugin(self, plugin):
        if not plugin in self.plugins:
            logging.error("{} plugin not found".format(plugin))
            return False
        return True
