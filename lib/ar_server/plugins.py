import abc
import copy
import logging 
import itertools
import os
import uuid
import sys
import time
import datetime 
import subprocess
import re
import multiprocessing
from yapsy.PluginManager import PluginManager

# A-Rast modules
import assembly
import pipe as phelper

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
        
    def arast_popen(self, cmd_args, overrides=True, **kwargs):
        """
        Set overrides to FALSE if flags should not be applied to this binary.
        """
        if overrides:
            for kv in self.extra_params:
                dashes = '-'
                if len(kv[0]) != 1:
                    dashes += '-'
                flag = '{}{}'.format(dashes, kv[0])
                if kv[1] == 'False':
                    try:
                        cmd_args.remove(flag)
                    except:
                        pass
                else:
                    cmd_args.append(flag)
                if kv[1] != 'True':
                    cmd_args.append(kv[1])
        try:
            shell = kwargs['shell']
        except:
            shell = False
        if not shell:
            cmd_human = []
            for w in cmd_args:
                if w.endswith('/'):
                    cmd_human.append(os.path.basename(w[:-1]))
                else:
                    cmd_human.append(os.path.basename(w))
            cmd_string = ''.join(['{} '.format(w) for w in cmd_human])
        else:
            cmd_string = cmd_args

        if cmd_args[0].find('..') != -1 and not shell:
            cmd_args[0] = os.path.abspath(cmd_args[0])
        self.out_module.write("Command: {}\n".format(cmd_string))
        self.out_report.write('Command: {}\n'.format(cmd_string))
        m_start_time = time.time()
        print cmd_args
        try:
            p = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, 
                                     stderr=subprocess.STDOUT, **kwargs)
            for line in p.stdout:
                logging.info(line)
                self.out_module.write(line)
            p.wait()
        except subprocess.CalledProcessError as e:
            out = 'Process Failed.\nExit Code: {}\nOutput:{}\n'.format(
                e.returncode, e.output)
        m_elapsed_time = time.time() - m_start_time
        m_ftime = str(datetime.timedelta(seconds=int(m_elapsed_time)))
        self.out_report.write("Process time: {}\n\n".format(m_ftime))


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
        invalid_files = []
        for filetype in filetypes:
            f_valid = False
            for d in job_data['reads']:
                if d['files'][0].endswith(filetype):
                    valid_files.append(d)
                    invalid_files.append(os.path.basename(d['files'][0]))
                try:
                    if self.single_library: # only one library
                        break
                except:
                    pass
        if not valid_files:
            raise Exception('{}: File(s) not supported: {}'.format(
                    self.name,
                    [os.path.basename(d['files'][0]) for
                     d in job_data['reads']]))
        return valid_files

    def init_settings(self, settings, job_data, manager):
        self.pmanager = manager
        self.threads = 1
        self.process_cores = multiprocessing.cpu_count()
        self.arast_threads = int(manager.threads)
        self.process_threads_allowed = str(self.process_cores / self.arast_threads)
        self.job_data = job_data
        self.tools = {'ins_from_sam': '../../bin/getinsertsize.py'}
        self.out_report = job_data['out_report'] #Job log file
        self.out_module = open(os.path.join(self.outpath, '{}.out'.format(self.name)), 'w')
        for kv in settings:
            ## set absolute paths
            abs = os.path.abspath(kv[1])
            if os.path.exists(abs) or os.path.isfile(abs):
                setattr(self, kv[0], abs)
            else:
                setattr(self, kv[0], kv[1])

        self.extra_params = []
        for kv in job_data['params']:
            if not hasattr(self, kv[0]):
                self.extra_params.append(kv)
            print "Override: {}".format(kv)
            setattr(self, kv[0], kv[1])

    def linuxRam(self):
        """Returns the RAM of a linux system"""
        totalMemory = os.popen("free -m").readlines()[1].split()[1]
        return int(totalMemory)

    def get_all_output_files(self):
        """ Returns list of all files created after run. """
        if os.path.exists(self.outpath):
            return [os.path.join(self.outpath, f) for 
                    f in os.listdir(self.outpath)]
        raise Exception("No output files in directory")

    def run_checks(self, settings, job_data):
        logging.info("Doing checks")
        # TODO Check binary exists
        # TODO Check data is valid
        pass

    def setname(self, name):
        self.name = name

    def tar(self, files, job_id):
        return assembly.tar_list(self.outpath, files, 
                                 self.name + str(job_id) + '.tar.gz')

    def tar_output(self, job_id):
        """ Tars all files in module run's directory """
        files = [self.outpath + file for file in os.listdir(self.outpath)]
        return assembly.tar_directory(self.outpath, self.outpath,
                                      self.name + str(job_id) + '.tar.gz')

    def get_version(self):
        """ Module plugin should implement get_version. """
        return 'get_version not implemented!'

    def update_settings(self, job_data):
        """
        Overwrite any new settings passed in JOB_DATA
        """
        pass

    def update_status(self):
        pass

    def calculate_read_info(self, job_data=None):
        """ 
        Analyze subset of reads to infer:
        - Max read length
        - ...
        Modifies each read library in JOB_DATA as well as returns global 
        values.
        """
        if not job_data:
            job_data = self.job_data
        all_max_read_length = []
        total_read_count = 0
        for lib in job_data['initial_reads']:
            max_read_length = -1
            read_count = 0
            readfiles = lib['files']
            for r in readfiles:
                f = open(r, 'r')
                for line in f:
                    read_count += 1
                    if read_count % 4 == 2 and len(line) > max_read_length:
                        max_read_length = len(line)
                f.close()
            read_count /= 4
            lib['max_read_length'] = max_read_length
            lib['count'] = read_count
            all_max_read_length.append(max_read_length)
            total_read_count += read_count
        return max(all_max_read_length), total_read_count
    

    def estimate_insert_stdev(self, contig_file, reads, min_lines=4000):
        """ Map READS to CONTIGS using bwa and return insert size """
        logging.info('Estimating insert size')
        min_reads = min_lines * 4
        sub_reads = []
        for r in reads:
            sub_name = r + '.sub'
            sub_file = open(sub_name, 'w')

            ## getting subset of reads
            with open(r) as readfile:
                for line in itertools.islice(readfile, min_reads):
                    sub_file.write(line)
            sub_file.close()
            sub_reads.append(sub_name)
            
        bwa_data = copy.deepcopy(self.job_data)
        bwa_data['processed_reads'][0]['files'] = sub_reads
        bwa_data['contigs'] = [contig_file]
        bwa_data['out_report'] = open(os.path.join(self.outpath, 'estimate_ins.log'), 'w')
        #job_data['final_contigs'] = [contig_file]
        samfiles, _, _ = self.pmanager.run_module('bwa', bwa_data)
        samfile = samfiles[0]
        if os.path.getsize(samfile) == 0:
            logging.error('Error estimating insert length')
            raise Exception('estimate ins failed')
        cmd_args = [self.tools['ins_from_sam'], samfile]
        results = subprocess.check_output(cmd_args)
        insert_size = int(float(re.split('\s|,', results)[9]))
        stdev = int(float(re.split('\=|\s', results)[-2]))
        logging.info('Estimated Insert Length: {}'.format(insert_size))
        return insert_size, stdev

    
class BaseAssembler(BasePlugin):
    """
    An assembler plugin should implement a run() function

    """
    # Default behavior for run()
    INPUT = 'reads'
    OUTPUT = 'contigs'

    def __call__(self, settings, job_data, manager):
        self.run_checks(settings, job_data)
        logging.info("{} Settings: {}".format(self.name, settings))
        self.outpath = self.create_directories(job_data)
        self.init_settings(settings, job_data, manager)
        valid_files = self.get_valid_reads(job_data)
        output = self.run(valid_files)
        if type(output) is tuple and len(output) == 2:
            contigs = output[0]
            scaffolds = output[1]
            return contigs, scaffolds
        self.out_module.close()
        return output


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


class BaseScaffolder(BasePlugin):
    """
    A preprocessing plugin should implement a run() function

    """
    # Default behavior for run()
    INPUT = 'reads, contigs'
    OUTPUT = 'scaffolds'

    def __call__(self, settings, job_data, manager):
        self.pmanager = manager
        self.run_checks(settings, job_data)
        logging.info("{} Settings: {}".format(self.name, settings))
        self.outpath = self.create_directories(job_data)
        self.init_settings(settings, job_data, manager)

        if len(job_data['initial_reads']) > 1:
            raise NotImplementedError
        else:
            contig_file = job_data['contigs'][0]
        #read_records = job_data['processed_reads']
        read_records = copy.deepcopy(job_data['initial_reads'])
        output = self.run(read_records, contig_file, job_data)

        self.out_module.close()
        return output

    # Must implement run() method
    @abc.abstractmethod
    def run(self, job_data, read_records, contig_file):
        """
        Input: READS: list of dicts contain file and read info
        Output: Updated READS (each read['files'] list should be updated 
        with the new processed reads
          
        """
        return

class BasePreprocessor(BasePlugin):
    """
    A postprocessing plugin should implement a run() function

    """
    # Default behavior for run()
    INPUT = 'reads'
    OUTPUT = 'reads'

    def __call__(self, settings, job_data, manager):
        self.run_checks(settings, job_data)
        logging.info("{} Settings: {}".format(self.name, settings))
        self.outpath = self.create_directories(job_data)
        self.init_settings(settings, job_data, manager)
        valid_files = self.get_valid_reads(job_data)
        output = self.run(valid_files)

        self.out_module.close()
        return output

    # Must implement run() method
    @abc.abstractmethod
    def run(self, reads, contigs):
        """
        Input: READS: list of dicts contain file and read info
               CONTIGS: ...
        Output: list of full paths to contig files.  File extensions should reflect
          the file type
          eg. return ['/data/contigs1.fa', '/data/contigs2.fa']
          
        """
        return


class BasePostprocessor(BasePlugin):
    """
    A postprocessing plugin should implement a run() function

    """
    # Default behavior for run()
    INPUT = 'contigs, reads'
    OUTPUT = 'contigs'

    def __call__(self, settings, job_data, manager):
        self.run_checks(settings, job_data)
        logging.info("{} Settings: {}".format(self.name, settings))
        self.outpath = self.create_directories(job_data)
        self.init_settings(settings, job_data, manager)
        valid_files = self.get_valid_reads(job_data)
        output = self.run(valid_files)

        self.out_module.close()
        return output

    # Must implement run() method
    @abc.abstractmethod
    def run(self, reads, contigs):
        """
        Input: READS: list of dicts contain file and read info
               CONTIGS: ...
        Output: list of full paths to contig files.  File extensions should reflect
          the file type
          eg. return ['/data/contigs1.fa', '/data/contigs2.fa']
          
        """
        return


class BaseAssessment(BasePlugin):
    """
    A assessment plugin should implement a run() function

    """
    # Default behavior for run()
    INPUT = 'contigs'
    OUTPUT = 'contigs' #for reapr used in pipe!

    def __call__(self, settings, job_data, manager, meta=False):
        self.run_checks(settings, job_data)
        logging.info("{} Settings: {}".format(self.name, settings))
        self.outpath = self.create_directories(job_data)
        self.init_settings(settings, job_data, manager)
        
        if meta: # Use all contigs for whole job
            contigs = job_data['final_contigs']
            
        else:
            contigs = job_data['contigs']
        a_reads = copy.deepcopy(job_data['raw_reads'])
        output = self.run(contigs, a_reads)

        self.out_module.close()
        return output

    # Must implement run() method
    @abc.abstractmethod
    def run(self, contigs, reads):
        """
        Return reports
          
        """
        return

class BaseMetaAssembler(BasePlugin):
    """

    """
    # Default behavior for run()
    INPUT = 'contigs'
    OUTPUT = 'contigs'

    def __call__(self, settings, job_data, manager):
        self.run_checks(settings, job_data)
        logging.info("{} Settings: {}".format(self.name, settings))
        self.outpath = self.create_directories(job_data)
        self.init_settings(settings, job_data, manager)
        contigs = job_data['final_contigs']
        output = self.run(contigs)
        self.out_module.close()
        return output

    # Must implement run() method
    @abc.abstractmethod
    def run(self, contigs):
        """
        Return contigs
          
        """
        return

class BaseAligner(BasePlugin):
    """
    A alignment plugin should implement a run() function

    """
    # Default behavior for run()
    INPUT = 'contigs'
    OUTPUT = 'sam'

    def __call__(self, settings, job_data, manager):
        self.run_checks(settings, job_data)
        logging.info("{} Settings: {}".format(self.name, settings))
        self.outpath = self.create_directories(job_data)
        self.init_settings(settings, job_data, manager)
        contig_file = job_data['contigs'][0]
        #read_records = job_data['processed_reads']
        read_records = job_data['initial_reads']
        if len(read_records) > 1:
            raise NotImplementedError('Alignment of multiple libraries not impl')
        read_lib = read_records[0]
        read_files = read_lib['files']
        if len(read_files) == 1 and read_lib['type'] == 'paired':
            merged_pair = True
        else:
            merged_pair = False
        
        output = self.run(contig_file, read_files, merged_pair)

        self.out_module.close()
        return [output] #TODO return multiple samfiles for each library

    # Must implement run() method
    @abc.abstractmethod
    def run(self, contigs, reads, merged_pair=False):
        """
        Return SAM file
          
        """
        return


class ModuleManager():
    def __init__(self, threads):
        self.threads = threads
        self.pmanager = PluginManager()
        self.pmanager.setPluginPlaces(["plugins"])
        self.pmanager.collectPlugins()
        self.pmanager.locatePlugins()
        self.plugins = ['none']
        if len(self.pmanager.getAllPlugins()) == 0:
            raise Exception("No Plugins Found!")
        for plugin in self.pmanager.getAllPlugins():
            plugin.threads = threads
            self.plugins.append(plugin.name)
            plugin.plugin_object.setname(plugin.name)
            print "Plugin found: {}".format(plugin.name)
        

    def run_module(self, module, job_data_orig, tar=False, 
                   all_data=False, reads=False, meta=False, 
                   overrides=True):
        """
        Keyword Arguments:
        module -- name of plugin
        job_data -- dict of job parameters
        tar -- return tar of all output, rather than module.OUTPUT file
        all_data -- return module.OUTPUT and list of all files in self.outdir
        reads -- include files if module.OUTPUT == 'reads'
          Not recommended for large read files.

        """
        job_data = job_data_orig
        # job_data = copy.deepcopy(job_data_orig)
        # # Pass back orig file descriptor
        # try:
        #     job_data['out_report'] = job_data_orig['out_report'] 
        # except:
        #     pass
        if not self.has_plugin(module):
            raise Exception("No plugin named {}".format(module))
        plugin = self.pmanager.getPluginByName(module)
        settings = plugin.details.items('Settings')
        plugin.plugin_object.update_settings(job_data)
        if meta:
            output = plugin.plugin_object(settings, job_data, self, meta=True)
        else:
            output = plugin.plugin_object(settings, job_data, self)
        log = plugin.plugin_object.out_module.name
        if tar:
            tarfile = plugin.plugin_object.tar_output(job_data['job_id'])
            return output, tarfile, [], log
        if all_data:
            if not reads and plugin.plugin_object.OUTPUT == 'reads':
                #Don't return all files from plugins that output reads 
                data = []
            else:
                data = plugin.plugin_object.get_all_output_files()
            return output, data, log
        return output, [], log

    def output_type(self, module):
        return self.pmanager.getPluginByName(module).plugin_object.OUTPUT

    def input_type(self, module):
        return self.pmanager.getPluginByName(module).plugin_object.INPUT

    def get_short_name(self, module):
        try:
            plugin = self.pmanager.getPluginByName(module)
            settings = plugin.details.items('Settings')
            for kv in settings:
                if kv[0] == 'short_name':
                    sn = kv[1]
                    break
            return sn
        except:
            return None


    def has_plugin(self, plugin):
        if not plugin.lower() in self.plugins:
            logging.error("{} plugin not found".format(plugin))
            return False
        return True

    def valid_modules(self, l):
        """ Return filtered list of available modules """
        return [m for m in l if not m.startswith('?') and self.has_plugin(m)]

    def validate_pipe(self, pipe):
        for stage in pipe:
            for word in stage.replace('+', ' ').split(' '):
                if not (word.startswith('?') or self.has_plugin(word)):
                    raise Exception('Invalid pipeline command')
                

    def split_pipe(self, l):
        """ Splits a multi-module string in to bins 
        Ex: 'kiki ?k=29 velvet' -> [[kiki, ?k=29], [velvet]]
        """
        bins = []
        for word in l:
            if not word.startswith('?'):
                bins.append([word])
            elif word.startswith('?'):
                bins[-1].append(word)
        return bins
            
    def parse_input(self, pipe):
        """
        Parses inital pipe and separates branching bins
        Ex: ['sga', '?p=True', 'kiki ?k=31 velvet', 'sspace']
        """
        stages = phelper.parse_branches(pipe)
        return stages

    def parse_pipe(self, pipe):
        """ Returns the pipeline(s)z of modules.
        Returns parameter overrides from string.
        e.g Input: [sga_ec 'kiki ?k=31 velvet ?ins=500' sspace]
        Output: [kiki, velvet, a5], [{k:31}, {ins:500}, {}]
        """

        # Parse param overrides
        overrides = []
        pipeline = []
        module_num = -1
        for group in pipe:
            for word in group.split('+'):
                if word.lower() == 'none':
                    pass
                elif not word.startswith('?') and self.has_plugin(word): # is module
                    module_num = module_num + 1
                    pipeline.append(word)
                    overrides.append({})

                elif word[1:-1].find('=') != -1: # is param
                    kv = word[1:].split('=')
                    overrides[module_num] = dict(overrides[module_num].items() +
                                                 dict([kv]).items())

        return pipeline, overrides
