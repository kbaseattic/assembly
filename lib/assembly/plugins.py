import abc
import copy
import logging
import itertools
import os
import uuid
import sys
import time
import datetime
import signal
import subprocess
import re
import multiprocessing
import signal
from yapsy.PluginManager import PluginManager
from yapsy.IPluginLocator import IPluginLocator
from threading  import Thread
from Queue import Queue, Empty
import ConfigParser
import traceback

import assembly
import asmtypes
import pipe as phelper
import wasp


logger = logging.getLogger(__name__)


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

    def base_call(self, settings, job_data, manager, strict=False):
        """ Plugin wrapper """
        ### This might be a recursive call, backup Plugin object attrs
        ### !!! This won't work in parallel
        try:
            backup = self._save()
            logger.info('Previous instance found, backing up.')
        except AttributeError: pass

        ### Compatibility
        self.init_settings(settings, job_data, manager)
        output = self.wasp_run()
        self.out_module.close()

        #### If this was an internal plugin run, restore outer plugin logfile
        try:
            self._restore(backup)
            logger.info('Restored Plugin Object self attributes')
        except UnboundLocalError: pass
        output['input_data'] = self.data.readfiles
        return output

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

        shell = kwargs.get('shell', False)
        if not shell:
            cmd_string = human_readable_command(cmd_args)
        else:
            cmd_string = cmd_args
        if cmd_args[0].find('..') != -1 and not shell:
            raise Exception("Plugin Config not updated: {}".format(cmd_args[0]))

        self.out_module.write("Command: {}\n".format(cmd_string))
        try:
            self.out_report.write('Command: {}\n'.format(cmd_string))
        except Exception as e:
            logger.error('Could not write to report: {} -- {}'.format(cmd_string, e))
        m_start_time = time.time()
        logger.info("Command line: {}".format(cmd_string if shell else " ".join(cmd_args)))
        try:
            env_copy = os.environ.copy()
            env_copy['OMP_NUM_THREADS'] = self.process_threads_allowed
            p = subprocess.Popen(cmd_args, env=env_copy,
                                 # cwd=self.outpath,              # weird: adding cwd causes tagdust to fail
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 preexec_fn=os.setsid, **kwargs)

            ## Module Logging Thread
            q = Queue()
            t = Thread(target=handle_output, args=(p.stdout, q))
            t.daemon = True # thread dies with the program
            t.start()

            ## Poll for kill requests
            while p.poll() is None:
                if self.killed():
                    os.killpg(p.pid, signal.SIGTERM)
                    raise asmtypes.ArastUserInterrupt('Terminated by user')

                ## Flush STDOUT to logs
                while True:
                    try:  line = q.get_nowait() # or q.get(timeout=.1)
                    except Empty:
                        break
                    else: # got line
                        logger.debug(line.strip())
                        self.is_urgent_output(line)
                        self.out_module.write(line)
                time.sleep(5)

            p.wait()

            #Flush again
            while True:
                try:  line = q.get_nowait() # or q.get(timeout=.1)
                except Empty:
                    break
                else: # got line
                    logger.debug(line.strip())
                    self.is_urgent_output(line)
                    self.out_module.write(line)

            if p.returncode != 0:
                logger.warn('Process failed with exit code: {}'.format(p.returncode))

        except subprocess.CalledProcessError as e:
            logger.warn('Process Failed.\nExit Code: {}\nOutput:{}\n'.format(e.returncode, e.output))

        m_elapsed_time = time.time() - m_start_time
        m_ftime = str(datetime.timedelta(seconds=int(m_elapsed_time)))
        try:
            self.out_report.write('Command: {}\n'.format(m_ftime))
        except Exception as e:
            logger.error('Could not write to report: {} -- {}'.format(cmd_string, e))

    def is_urgent_output(self, line):
        """
        Plugins should override this if functionality depends on stdout.
        Should return False if no action should be taken.
        Returning a non-zero value will terminate the process and return
        the value to the plugin instance.

        This is for use cases where tools provide feedback to STDOUT which
        could be used to debug / iterate over itself in a smart way.
        """
        pass

    def killed(self):
        """ Check the kill queue to see if job should be killed """

        my_user = self.job_data['user']
        my_jobid = self.job_data['job_id']

        popped = False
        self.pmanager.kill_list_lock.acquire()
        try:
            kl = self.pmanager.kill_list
            for i,kr in enumerate(kl):
                if my_user == kr['user'] and str(my_jobid) == kr['job_id']:
                    kl.pop(i)
                    popped = True
        except:
            logger.error("Unexpected error in removing executed job to be killed from kill_list")
            raise
        finally:
            self.pmanager.kill_list_lock.release()

        return popped


    def create_directories(self, job_data):
        datapath = (job_data['datapath'] + '/' + str(job_data['job_id']) +
                    '/' + self.name + '_' + str(uuid.uuid4())) + '/'
        logger.info("Creating directory: {}".format(datapath))

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
        self.outpath = self.create_directories(job_data)
        self.pmanager = manager
        self.threads = 1
        self.process_cores = multiprocessing.cpu_count()
        self.arast_threads = int(manager.threads)
        self.process_threads_allowed = str(self.process_cores / self.arast_threads)
        self.job_data = job_data
        self.tools = {'ins_from_sam': os.path.join(self.pmanager.module_bin_path, 'getinsertsize.py')}
        self.out_report = job_data['out_report'] #Job log file
        self.out_module = open(os.path.join(self.outpath, '{}.out'.format(self.name)), 'w')
        job_data['logfiles'].append(self.out_module.name)
        for kv in settings:
            ## set absolute paths
            abs = os.path.abspath(kv[1])
            if os.path.exists(abs) or os.path.isfile(abs):
                setattr(self, kv[0], abs)
            else:
                setattr(self, kv[0], kv[1])

        #### Set custom parameters
        self.extra_params = []
        for kv in job_data['params']:
            if not hasattr(self, kv[0]):
                self.extra_params.append(kv)
            setattr(self, kv[0], kv[1])

        #### Initialize Internal Wasp Engine ####
        plugin_data = copy.deepcopy(job_data)
        out_internal = open('{}.{}'.format(self.out_module.name, self.name), 'w')
        plugin_data['out_report'] = self.out_report
        self.plugin_engine = wasp.WaspEngine(self.pmanager, plugin_data)
        #### Get default outputs of last module and pass on persistent data
        job_data['wasp_chain']['outpath'] = self.outpath
        if job_data['wasp_chain']['link']:
            all_sets = []
            for link in job_data['wasp_chain']['link']:
                if not link:
                    continue
                if isinstance(link['default_output'], asmtypes.FileSet):
                    all_sets.append(link['default_output']) # Single FileSet
                elif type(link['default_output']) is list:
                    all_sets += [fileset for fileset in link['default_output']]
                elif not link['default_output']:
                    raise Exception('"{}" stage failed to produce any output.'.format(link['module']))
                else:
                    raise Exception('Wasp Link Error')
            self.data = asmtypes.FileSetContainer(all_sets)
        else:
            self.data = job_data.wasp_data()
        self.initial_data = job_data['initial_data']

    def _save(self):
        attrs = ['outpath', 'job_data', 'out_report', 'out_module', 'data']
        saved = {'repr': self.__repr__()}
        for attr in attrs:
            saved[attr] = getattr(self, attr)
        return saved

    def _restore(self, data):
        assert self.__repr__() == data['repr']
        attrs = ['outpath', 'job_data', 'out_report', 'out_module', 'data']
        for attr in attrs:
            setattr(self, attr, data[attr])

    def linuxRam(self):
        """Returns the RAM of a linux system"""
        totalMemory = os.popen("free -m").readlines()[1].split()[1]
        return int(totalMemory)

    def get_all_output_files(self):
        """ Returns list of all files created after run. """
        allfiles = []
        for root, sub_dirs, files in os.walk(self.outpath):
            for f in files:
                allfiles.append(os.path.join(root, f))
        return allfiles

    def run_checks(self, settings, job_data):
        logger.info("Doing checks")
        # TODO Check binary exists
        # TODO Check data is valid
        pass

    def get_insert_info(self, libs):
        """ Returns a list of tuples for initial read insert and stdev info
        eg [(100, 20), (500, 50), ()]"""
        libs_info = []
        for lib in libs:
            if (lib['type'] == 'paired'):
                try:
                    ins_sd = (lib['insert'], lib['stdev'])
                except:
                    ins_sd = ()
            elif lib['type'] == 'single':
                ins_sd = ()
            libs_info.append(ins_sd)
        return libs_info

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
        logger.info('Estimating insert size')
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
        exp = '(bwa (contigs {}) (paired {} {}))'.format(contig_file, reads[0], reads[1])
        samfile = self.plugin_engine.run_expression(exp).files[0]
        if os.path.getsize(samfile) == 0:
            logger.error('Error estimating insert length')
            raise Exception('estimate ins failed')
        cmd_args = [self.tools['ins_from_sam'], samfile]
        results = subprocess.check_output(cmd_args)
        insert_size = int(float(re.split('\s|,', results)[9]))
        stdev = int(float(re.split('\=|\s', results)[-2]))
        logger.info('Estimated Insert Length: {}'.format(insert_size))
        return insert_size, stdev

    def calculate_genome_size(self, fasta):
        s = open(fasta).read()
        s = re.sub(r'>[^\n\r]*', '', s)
        s = re.sub(r'\s+', '', s)
        return len(s)

class BaseAssembler(BasePlugin):
    """
    An assembler plugin should implement a run() function

    """
    # Default behavior for run()
    INPUT = 'reads'
    OUTPUT = 'contigs'

    def wasp_run(self):
        return self.run()

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

    def wasp_run(self):
        return self.run()

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
    A preprocessing plugin should return a list of processed reads.
    For multiple libraries, return a list of list of reads.

    """
    # Default behavior for run()
    INPUT = 'reads'
    OUTPUT = 'reads'

    def wasp_run(self):
        #### Save and restore insert data, handle extra output
        orig_sets = copy.deepcopy(self.data.readsets)
        output = self.run()
        if output['reads']:
            if type(output['reads'][0]) is list:  ## Multiple Libraries
                for i, readset in enumerate(output['reads']):
                    orig_sets[i].update_files(readset)
                    orig_sets[i]['name'] = '{}_reads'.format(self.name)
            else:
                orig_sets[0].update_files(output['reads'])
                orig_sets[0]['name'] = '{}_reads'.format(self.name)
        else: return
        readsets = orig_sets
        try:
            for extra in output['extra']:
                readsets.append(asmtypes.set_factory('single', extra,
                                                     name='{}_single'.format(self.name)))
        except Exception as e:
            logger.warn('Wasp handles extra output: {}'.format(e))
        return {'reads': readsets}

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

class BaseAnalyzer(BasePlugin):
    """
    Sequence analysis plugin.  Input should be a list of library dicts

    """
    # Default behavior for run()
    INPUT = 'reads'
    OUTPUT = 'report'

    def wasp_run(self):
        return self.run()

    # Must implement run() method
    @abc.abstractmethod
    def run(self, libraries):
        return


class BasePostprocessor(BasePlugin):
    """
    A postprocessing plugin should implement a run() function

    """
    # Default behavior for run()
    INPUT = 'contigs, reads'
    OUTPUT = 'contigs'

    def wasp_run(self):
        return self.run()

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
    INPUT = 'contigs', 'scaffolds'
    OUTPUT = 'report'

    def wasp_run(self):
        return self.run()

    # Must implement run() method
    @abc.abstractmethod
    def run(self, contigs, reads):
        """
        Return reports

        """
        return

class BaseMetaAssembler(BasePlugin):
    # Default behavior for run()
    INPUT = 'contigs'
    OUTPUT = 'contigs'

    def wasp_run(self):
        return self.run()

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
    INPUT = ['contigs', 'reads']
    OUTPUT = 'alignment'

    def wasp_run(self):
        return self.run()

    # Must implement run() method
    @abc.abstractmethod
    def run(self, contigs, reads, merged_pair=False):
        """
        Return SAM file

        """
        return


class ModuleManager():
    def __init__(self, threads, kill_list, kill_list_lock, job_list, binpath, modulebin):
        self.threads = threads
        self.kill_list = kill_list
        self.kill_list_lock = kill_list_lock
        self.job_list = job_list # Running jobs
        self.binpath = binpath
        self.module_bin_path = modulebin

        self.root_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', '..'))
        self.plugin_path = os.path.join(self.root_path, "lib", "assembly", "plugins")

        self.pmanager = PluginManager()
        locator = self.pmanager.getPluginLocator()
        locator.setPluginInfoExtension('asm-plugin')
        self.pmanager.setPluginPlaces([ self.plugin_path ])
        self.pmanager.collectPlugins()
        self.pmanager.locatePlugins()
        self.plugins = ['none']
        num_plugins = len(self.pmanager.getAllPlugins())
        if  num_plugins == 0:
            raise Exception("No Plugins Found!")

        plugins = []
        self.executables = {}
        for plugin in self.pmanager.getAllPlugins():
            plugin.threads = threads
            self.plugins.append(plugin.name)
            plugin.plugin_object.setname(plugin.name)
            ## Check for installed binaries
            try:
                version = plugin.details.get('Documentation', 'Version')
                executables = plugin.details.items('Executables')
                full_execs = [(k, self.get_executable_path(v)) for k,v in executables]
                for binary in full_execs:
                    if not os.path.exists(binary[1]):
                        if float(version) < 1:
                            logger.warn('Third-party binary does not exist for beta plugin: {} (v{}) -- {}'.format(plugin.name, version, binary[1]))
                        else:
                            raise Exception('ERROR: Third-party binary does not exist for beta plugin: {} (v{}) -- {}'.format(plugin.name, version, binary[1]))
                self.executables[plugin.name] = full_execs
            except ConfigParser.NoSectionError: pass
            plugins.append(plugin.name)
        logger.info("Plugins found [{}]: {}".format(num_plugins, sorted(plugins)))


    def run_proc(self, module, wlink, job_data, parameters):
        """ Run module adapter for wasp interpreter
        To support the Job_data mechanism, injects wlink
        """
        if not self.has_plugin(module):
            raise Exception("No plugin named {}".format(module))
        plugin = self.pmanager.getPluginByName(module)

        config_settings = plugin.details.items('Settings')
        config_settings = update_settings(config_settings, parameters)

        try:
            settings = {k:v for k,v in self.executables[module]}
            for k,v in config_settings: ## Don't override
                if not k in settings:
                    settings[k] = v
            settings = settings.items()
        except:
            # settings = config_settings
            raise Exception("Plugin Config not updated: {}!".format(module))

        #### Check input/output type compatibility
        if wlink['link']:
            for link in wlink['link']:
                if not link:
                    continue
                if link['module']:
                    try:
                        assert (self.output_type(link['module']) == self.input_type(module) or
                                self.output_type(link['module']) in self.input_type(module))
                    except AssertionError:
                        raise Exception('{} and {} have mismatched input/output types'.format(module, link['module']))
        #### Run
        job_data['wasp_chain'] = wlink
        output = plugin.plugin_object.base_call(settings, job_data, self)
        ot = self.output_type(module)
        wlink.insert_output(output, ot,
                            plugin.name)
        if not wlink.output:
            raise Exception('"{}" module failed to produce {}'.format(module, ot))

        ### Store any output values in job_data
        data = {'module': module,
                'module_output': output}
        job_data['plugin_output'].append(data)

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

    def get_executable(self, module):
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

    def verify_file(self, filename):
        if not os.path.exists(filename):
            raise Exception("File not found: %s" % filename)

    def get_executable_path(self, filename, verify=False):
        guess1 = os.path.join(self.module_bin_path, filename)
        guess2 = os.path.join(self.binpath, filename)
        fullname = guess1 if os.path.exists(guess1) else guess2
        if verify: verify_file(fullname)
        return fullname

    def has_plugin(self, plugin):
        if not plugin.lower() in self.plugins:
            logger.error("{} plugin not found".format(plugin))
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

##### Helper Functions ######
def handle_output(out, q):
    for line in iter(out.readline, b''):
        q.put(line)
    out.close()

def update_settings(settings, new_dict):
    """
    Overwrite any new settings passed in
    """
    updated = []
    for tup in settings:
        if tup[0] in new_dict:
            updated.append((tup[0], str(new_dict[tup[0]])))
        else:
            updated.append(tup)
    return updated

def human_readable_command(cmd_args):
    cmd_human = []
    for w in cmd_args:
        if ' ' in w:
            sub_args = w.split()
            sub_cmd = ' '.join([path_base(x) for x in sub_args])
            cmd_human.append('"' + sub_cmd + '"')
        else:
            cmd_human.append(path_base(w))
    return ' '.join(cmd_human)

def path_base(path):
    if path.endswith('/'):
        return os.path.basename(path[:-1])
    else:
        return os.path.basename(path)
