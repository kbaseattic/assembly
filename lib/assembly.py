#! /usr/bin/env python

"""Assembly execution drivers.

This module provides the default parameters and handling of
assembler-specific configurations.

Assembler defaults are set in the 'arast.conf' file

"""
import logging
import metadata
import os
import re
import subprocess
import tarfile

from ConfigParser import SafeConfigParser

def get_default(key):
    """Get assemblers default value from config file."""
    return parser.get('assemblers', key)

def is_available(assembler):
    """ Check if ASSEMBLER is a valid/available assembler
    """
    return True

def run(assembler, datapath, job_id):
    logging.info("Running assembler: %s" % assembler)
    logging.warning("Not changing job status until port forwarding issue resolved")
    #metadata.update_job(job_id, 'status', 'running')
    result_tar = 'NO_TAR'
    if is_available(assembler):
        if assembler == 'kiki':
            run_kiki(datapath)
        elif assembler == 'velvet':
            result_tar = run_velvet(datapath)
    #metadata.update_job(job_id, 'status', 'complete')
    return result_tar

def run_kiki():

    # Return location of finished data
    return 2


def run_velvet(datapath):
    velvet_data = datapath 
    velvet_data += '/velvet/'
    os.makedirs(velvet_data)

    # Set up parameters
    velveth = basepath + get_default('velvet.path')
    velvetg = velveth
    velveth += get_default('velvet.exec_h')
    velvetg += get_default('velvet.exec_g')
    hash = get_default('velvet.hash_length')
    file_type = get_default('velvet.file_type')

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
    

    logging.info(args)
    p = subprocess.Popen(args)
    p.wait()

    args_g = [velvetg, velvet_data]
    logging.info(args_g)
    g = subprocess.Popen(args_g)
    g.wait()

    tarfile = tar(datapath, velvet_data, 'velvet_data.tar.gz')
    return tarfile

def run_soapdenovo():
    return 2


def tar(outpath, asm_data, tarname):
    print "Compressing"
    outfile = outpath + '/tar/'
    os.makedirs(outfile)
    outfile += tarname
    targs = ['tar', '-czvf', outfile, asm_data]
    t = subprocess.Popen(targs)
    t.wait()
    return outfile

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
    

parser = SafeConfigParser()
parser.read('arast.conf')
basepath = get_default('basepath')
