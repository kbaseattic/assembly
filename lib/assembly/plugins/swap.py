import os
from plugins import BaseAssembler
from yapsy.IPlugin import IPlugin

class SwapAssembler(BaseAssembler, IPlugin):
    def run(self, reads):
        ## Swap only supports a single FastA file.
        # Convert Fastq files
        fasta_files = []
        for f in self.get_files(reads):
                if f.endswith('.fq') or f.endswith('.fastq'):  #Convert
                    in_fasta = f.rpartition('.')[0] + '.fasta'
                    self.arast_popen([self.fastq_to_fasta, '-i', f, '-o', in_fasta])
                    if not os.path.getsize(in_fasta):
                        raise Exception('Error converting to FastQ')
                    fasta_files.append(in_fasta)
                else:
                    fasta_files.append(f)

        # Concatenate multiple files
        if len(fasta_files) == 1:
            reads_file = fasta_files[0]
        else:
            reads_file = os.path.join(self.outpath, 'reads.fa')
            with open(reads_file, 'w') as outfile:
                for fa in fasta_files:
                    with open(fa) as reads:
                        for line in reads:
                            outfile.write(line)

        ## Run assembly
        self.arast_popen(['mpirun', '-n', self.process_threads_allowed, 
                          self.executable, '-k', self.k,'-o', 
                          self.outpath + 'swap', '-i', reads_file])
        contig = os.path.join(self.outpath, 'swap', 'CEContig.fasta')
        if os.path.exists(contig):
            return [contig]
        else:
            return []


