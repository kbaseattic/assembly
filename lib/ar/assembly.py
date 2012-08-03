"""
Assembly execution library
"""
import os
import subprocess

## Available Assemblers ##
assemblers = [
{
        'name' : 'Kiki',
        'aliases' : ['kiki', 'ki'],
        'command' : 'kiki'
},
{
        'name' : 'Velvet',
        'aliases' : ['velvet',],
        'command' : 'velvet'
},
{
        'name' : 'SOAPdenovo',
        'aliases' : ['soap'],
        'command' : 'soapdenovo'
}
]

velvet_defaults = {
    'output_dir' : 'auto',
    'hash_length' : '31,45,2',
    'file_type' : '-fasta'
}


def is_available(assembler):
    """ Check if ASSEMBLER is a valid/available assembler
    """
    return True

def run(assembler, datapath):
    if is_available(assembler):
        if assembler == 'kiki':
            print "Starting kiki"
            run_kiki(datapath)
        elif assembler == 'velvet':
    
            run_velvet(datapath)

def run_kiki():


    # Return location of finished data
    return 2


def run_velvet(datapath):
    velvet_data = datapath 
    velvet_data += '/velvet/'
    os.makedirs(velvet_data)

    # Set up parameters
    hash = velvet_defaults['hash_length']
    file_type = velvet_defaults['file_type']

    # Run velvet
    print "Starting velvet"
    args = ['/usr/bin/velveth',
            velvet_data,
            hash,
            file_type]
    raw_path = datapath + '/raw/'
    for file in os.listdir(raw_path):
        readfile = raw_path + file
        args.append(readfile)
    p = subprocess.Popen(args)

def run_soapdenovo():
    return 2
