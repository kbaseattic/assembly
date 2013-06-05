AssemblyRAST Plugin Specification
=================================

About
-----
This document specifies the format and structure of plugin modules to be used with AssemblyRAST.

Plugin Structure
----------------
Plugins are based on the Yapsy plugin framework.  Each plugin consists of two files::

  PLUGIN_NAME.py #plugin methods

  PLUGIN_NAME.yapsy-plugin #plugin config

Configuration File
------------------
The configuration file contains information required for the plugin framework, as well as addition custom defaults that can be set by the user.  The following is an example configuration file::

  #super_assembler.yapsy-plugin

  [Core]
  Name = kiki
  Module = kiki
  
  [Settings]
  short_name = ki
  executable = /usr/bin/ki
  filetypes = fasta,fa,fastq,fq
  k = 29
  contig_threshold = 1000
  
  [Documentation]
  Author = Chris Bun
  Version = 0.1
  Description = Kiki read assembler

The fields in the CORE section are required, and fields in SETTINGS are to be used by the plugin.

Plugin File
-----------
A plugin inherits the yapsy "IPlugin" class, as well as a "Base<TYPE>" class, depending on what the plugin type is.  In this example, we will use an assembler plugin and thus inherit "BaseAssembler."  Due to the heterogeneous nature of the tools input and output invocation formats, plugins may vary greatly within method bodies.  Assembler plugins require a run() function that takes in library dictionaries, and returns a list of contigs.::

    def run(self, reads):
        """
        Input: list of dicts contain file and read info
        Output: list of full paths to contig files.  File extensions should reflect
          the file type
          eg. return ['/data/contigs1.fa', '/data/contigs2.fa']
        """
        return contigs


Read Libraries (BaseAssembler)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The format of the READS dictionary is as follows::

  >print reads
  
  [{'type': 'paired, 'files': ['/data/reads1.fa', '/data/reads2.fa']},
   {'type': 'paired, 'files': ['/data/readsA.fa', '/data/readsB.fa']}]

Object Attributes
~~~~~~~~~~~~~~~~~
When a plugin is invoked, job data is passed in and available to the plugin.  The following is available::

  self.outpath # Directory where output files should be output
  self.out_report # File descriptor for global ARast job log file
  self.out_module # File descriptor for current plugin's log file

**Configuration Attributes**
All attributes defined in the configuration file are available.  For example, in the above configuration, a "k" field was specified.  In the plugin, we can use::

  my_k_value = self.k

Helper Functions
~~~~~~~~~~~~~~~~
The BasePlugin class offers some helper functions to infer necessary data::

  max_read_length, read_count = self.calculate_read_data()

Running Subprocesses
~~~~~~~~~~~~~~~~~~~~
Commandline arguments are to be placed in a python list, and invoked via the built-in 'arast_popen()' method, which is a wrapper over subprocess.Popen() that handles ARast-specific functionality.  

Example plugin
~~~~~~~~~~~~~~
The following is an example implementation of an assembler plugin::

  """
  super_assembler.py
  """
  import glob
  from plugins import BaseAssembler
  from yapsy.IPlugin import IPlugin

  class MySuperAssembler(BaseAssembler, IPlugin):
      def run(self, libs):
        cmd_args = [self.executable, 
	            '-k', self.k, 
		    '-o', self.outpath]

        ## Read sets are stored in separate Python dictionaries
        for library in libs['files']:
	  if library['type'] == 'single': 
	    se_list = library['files']
	    cmd_args.append('--single')
	    cmd_args += se_reads
	  elif library['type'] == 'paired':
	    pe_list = library[files]
	    cmd_args.append('--pair')
	    cmd_args += pe_list

        self.arast_popen(cmd_args)

	## Get list of results to return
	contigs = glob.glob(self.outpath + '/*.contig')
        return contigs

Overrides from client
~~~~~~~~~~~~~~~~~~~~~
Assembler-specific flags can be called from the client side.  For example, from the arast commandline, one can call::

  arast run -f reads.fa -p idba ?k=32

These are handled automatically by `arast_popen()`, but some assemblers have multiple steps in which flags should not be appended.  Call these particular executions with the `overrides=False` parameter::

  idba_cmd_merge = [self.bin_idba_ud, '--merge', file1, file2, merged_file]
  arast.popen(idba_cmd_merge, overrides=False)

  idba_cmd = [self.bin_idba_ud, '-r', merged_file, outbase, '--maxk', self.max_k]
  arast.popen(idba_cmd)


