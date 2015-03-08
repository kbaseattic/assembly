import logging
import os

import asmtypes
import wasp
from Bio import SeqIO


logger = logging.getLogger(__name__)


####### Decorators
def wasp_contigs_wrapped(func):
    """Take a wasp link, run functions on contigs, return a new wasp link """
    def func_on_contigs(*wasplinks):
        contigs = []
        for w in wasplinks:
            contigs += w['default_output'].files
        newlink = wasp.WaspLink()
        output = func(contigs)
        newlink['default_output'] = asmtypes.set_factory('contigs', [output])
        return newlink
    return func_on_contigs

def wasp_contigs(func):
    """Take a wasp link, run functions on contigs """
    def func_on_contigs(*wasplinks):
        contigs = []
        for w in wasplinks:
            contigs += w['default_output'].files
        return func(contigs)
    return func_on_contigs

def wasp_filesets(func):
    """Take a wasp link, run functions on filesets """
    def func_on_contigs(*wasplinks):
        try: return func([w['default_output'].files for w in wasplinks])
        except AttributeError:
            return func([fset for w in wasplinks for fset in w['default_output']])
    return func_on_contigs


##### FileSet Functions #####
## sorting/filtering


###### Raw data Functions
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
    logger.info('N50 of {}: {}'.format(os.path.basename(contig), N50))
    return N50

def arast_score(*wasplinks):
    return n50(*wasplinks)

####### Wasp expressions
@wasp_filesets
def has_paired(readsets):
    for r in readsets:
        if r.type == 'paired':
            return True
    return False
