import asmtypes
import wasp
import os
from Bio import SeqIO

####### Decorators
def wasp_contigs(func):
    """Take a wasp link, run functions on contigs """
    def func_on_contigs(*wasplinks):
        contigs = []
        for w in wasplinks:
            contigs += w['default_output'].files
        newlink = wasp.WaspLink()
        output = func(contigs)
        if type(output) is int:
            return output
        newlink['default_output'] = asmtypes.set_factory('contigs', [output])
        return newlink
    return func_on_contigs

##### FileSet Functions #####
## sorting/filtering


###### Raw data Functions
@wasp_contigs
def best_contig(contigs):
    return contigs[0]

@wasp_contigs
def n50(contigs):
    ''' https://code.google.com/p/biopyscripts '''
    contig = contigs[0]
    contigsLength = []
    sum = 0
    for seq_record in SeqIO.parse(open(contig), "fasta"):
        sum += len(seq_record.seq)
        contigsLength.append(len(seq_record.seq))

    teoN50 = sum / 2.0     
    contigsLength.sort()   
    contigsLength.reverse()    

    #checking N50
    testSum = 0
    N50 = 0
    for con in contigsLength:
        testSum += con
        if teoN50 < testSum:
            N50 = con
            break
    print 'N50 of {}: {}'.format(os.path.basename(contig), N50)
    return N50

####### Wasp expressions





