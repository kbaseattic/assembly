import asmtypes
import wasp

####### Decorators
def wasp_contigs(func):
    """Take a wasp link, run functions on contigs """
    def func_on_contigs(*wasplinks):
        contigs = []
        for w in wasplinks:
            contigs += w['default_output'].files
        newlink = wasp.WaspLink()
        newlink['default_output'] = asmtypes.set_factory('contigs', [func(contigs)])
        return newlink
    return func_on_contigs


###### Raw data Functions
@wasp_contigs
def best_contig(contigs):
    return contigs[0]

def n50(contigs):
    return 42

####### Wasp expressions





