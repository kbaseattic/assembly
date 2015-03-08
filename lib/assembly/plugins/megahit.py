import logging
import os
import subprocess
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin
import multiprocessing

logger = logging.getLogger(__name__)

class MegahitAssembler(BaseAssembler, IPlugin):
    def run(self):
        """
        Prepare command
        Launch command
        Yield result

        A megahit command looks like this:

        ./megahit -m 500000000000 --cpu-only -l 300 -o megahit-test-2015-01-23-2 \
            --input-cmd "zcat SRS150404/*.fastq.gz" \
            --k-min 21 --k-max 99 --k-step 10 \
            --min-count 2 \
            --num-cpu-threads 32 \
        | tee Log

        The --k-* parameters can be ommited. --min-count is valued at 2 by default too.

        """

        command = []
        command += [self.executable, "--cpu-only"]
        command += ['--num-cpu-threads', self.process_threads_allowed]
        command += ['-l', '512']

        # The metahit vendor recommends using 90% to 95% of the memory available.
        system_memory = self.get_system_memory()
        process_threads_allowed = int(self.process_threads_allowed)
        total_threads = self.get_total_thread_count()

        available_memory = system_memory / total_threads * process_threads_allowed

        command += ['-m', str(available_memory)]
        command += ['--input-cmd']

        # quotes are not required because the argument will be passed to arast_popen,
        # which will pass it to subprocess.Popen
        command += ["cat " + " ".join(self.data.readfiles) + ""]

        # TODO self.Name does not exist although the key Name is defined
        # in the configuration file.
        command += ['-o', os.path.join(self.outpath, "megahit")]

        # logging covered by arast_popen
        # logger.info("Command line: {}".format(" ".join(command)))
        self.arast_popen(command)

        contigs = os.path.join(self.outpath, 'megahit', 'final.contigs.fa')

        return {'contigs': contigs}

    # TODO: this should be moved elsewhere
    # because other classes may need this.
    def get_system_memory(self):
        # TODO: This could us psutil instead

        with open('/proc/meminfo') as my_file:
            for line in my_file:
                tokens = line.split()
                if len(tokens) == 3:
                    [entry, value, units] = tokens

                    if entry == "MemTotal:":
                        return int(value) * 1024

        # If the amount is unknown, return 4 GiB.
        return 4 * 1024 * 1024 * 1024

    def get_total_thread_count(self):
        return multiprocessing.cpu_count()
