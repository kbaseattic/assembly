"""
Assembly execution library
"""
import os
import subprocess
import tarfile
import re

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

velvet_cfg = {
    'bin_h' : '/usr/bin/velveth',
    'bin_g' : '/usr/bin/velvetg',
    'output_dir' : 'auto',
    'hash_length' : '29',
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
    velveth = velvet_cfg['bin_h']
    hash = velvet_cfg['hash_length']
    file_type = velvet_cfg['file_type']

    # Run velvet
    print "Starting velvet"
    args = [velveth,
            velvet_data,
            hash,
            file_type]
    raw_path = datapath + '/raw/'
    paired_reads = get_paired(get_fasta(raw_path))

    # Found paired
    if len(paired_reads) > 0:
        print "Found paired ends"
        print paired_reads
        pair_str = '-shortPaired'
        args.append(pair_str)
        args.append(str(raw_path + paired_reads[0][0]))
        args.append(str(raw_path + paired_reads[0][1]))
        for i in range(1,len(paired_reads)):
            flag = pair_str + str(i+1)
            args.append(flag)
            args.append(str(raw_path + paired_reads[i][0]))
            args.append(str(raw_path + paired_reads[i][1]))

    else:
        for file in os.listdir(raw_path):
            readfile = raw_path + file
            args.append(readfile)
    
    print ("Running subprocess")
    print args
    p = subprocess.Popen(args)
    p.wait()
    tar(datapath, velvet_data, 'velvet_data.tar.gz')

def run_soapdenovo():
    return 2


def tar(outpath, asm_data, tarname):
    print "Compressing"
    outfile = outpath + '/tar/'
    os.makedirs(outfile)
    outfile += tarname
    targs = ['tar', '-czvf', outfile, asm_data]
    subprocess.Popen(targs)

def get_paired(directory):
    """ Return a list of tuples of paired reads from directory or list
    """
    if type(directory) == 'str':
        files = os.listdir(directory)
    else:
        files = directory

    paired_re = re.compile('.A.|_1.')
    paired_files = []
    for file in files:
        m = re.search(paired_re, file)
        if m is not None:
            # Found first paired, look for second
            file2 = ''
            if m.group(0) == '.A.':
                file2 = re.sub('.A.', '.B.', file)
            elif m.group(0) == '_1.':
                file2 = re.sub('_1.', '_2.', file)
            if file2 in files:
                pair = [file, file2]
                paired_files.append(pair)
    return paired_files

def get_fasta(directory):
    """ Return the list of Fasta files in DIRECTORY
    """
    files = os.listdir(directory)
    fasta_files = [file for file in files if re.search(r'.fa$|.fasta$', file) is not None]
    return fasta_files
    
