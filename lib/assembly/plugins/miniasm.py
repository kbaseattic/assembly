import logging
import os
import re
import utils
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

logger = logging.getLogger(__name__)

class MiniasmAssembler(BaseAssembler, IPlugin):
    new_version = True

    def run(self):
        """
        Build the command and run.
        Return list of contig file(s)

        MiniASM takes as input noisy long reads in .bax.h5 or .fasta files
        """
        fasta_reads = []

        for readset in self.data.readsets_single:
            if not readset.is_long_read():
                continue
            new_file = None
            filename = readset.files[0]
            basename = os.path.basename(filename)
            if re.search(r'\.fa$|\.fasta$', filename, re.IGNORECASE) is not None:
                fasta_reads.append(filename)
                continue
            elif re.search(r'\.fq$|\.fastq$', filename, re.IGNORECASE) is not None:
                # convert fastq to fasta using seqtk
                new_file = os.path.join(self.outpath, os.path.splitext(basename)[0] + '.fasta')
                cmd_string = '{} seq -A {} > {}'.format(self.seqtk, filename, new_file)
                self.arast_popen(cmd_string, cwd=self.outpath, shell=True)
            elif re.search(r'\.bax\.h5$|\.plx\.h5$', filename, re.IGNORECASE) is not None:
                # convert h5 to fasta using pls2fasta
                new_file = os.path.join(self.outpath, os.path.splitext(os.path.splitext(basename)[0])[0] + '.fasta')
                cmd_string = '{} {} {} -trimByRegion'.format(self.pls2fasta, filename, new_file)
                self.arast_popen(cmd_string, cwd=self.outpath, shell=True)
            if utils.is_non_zero_file(new_file):
                fasta_reads.append(new_file)
            else:
                logger.warning('Could not convert {} to {}'.format(basename, new_file))

        output = {}

        if not fasta_reads:
            logger.warn('No read file suitable for miniasm; miniasm only works on long reads.')
            return output

        # concatenate fasta files
        cmd_string = 'cat {} | gzip -1 >reads.fa.gz'.format(' '.join(fasta_reads))
        self.arast_popen(cmd_string, cwd=self.outpath, shell=True)

        # overlap
        cmd_string = '{} -Sw5 -L100 -m0 -t{} reads.fa.gz reads.fa.gz | gzip -1 > reads.paf.gz'.format(
            self.minimap, self.process_threads_allowed)
        self.arast_popen(cmd_string, cwd=self.outpath, shell=True)

        # layout
        cmd_string = '{} -f reads.fa.gz reads.paf.gz -c {} -s {} -o {} > reads.gfa'.format(
            self.executable, self.min_coverage, self.min_span, self.min_overlap)
        self.arast_popen(cmd_string, cwd=self.outpath, shell=True)

        cmd_string = '{} < reads.gfa > contigs.fa'.format(self.gfa2fasta)
        self.arast_popen(cmd_string, cwd=self.outpath, shell=True)

        contigs = os.path.join(self.outpath, 'contigs.fa')

        if utils.is_non_zero_file(contigs):
            output['contigs'] = [contigs]
        else:
            logger.warning('miniasm failed to produce contigs')

        return output
