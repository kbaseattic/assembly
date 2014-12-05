#! /usr/bin/env python

"""Assembly execution drivers.

This module provides the default parameters and handling of
assembler-specific configurations.

Assembler defaults are set in the 'arast.conf' file

"""
import logging
import os
import re
import subprocess
import shutil
import glob
from contextlib import contextmanager

# import metadata as meta

from ConfigParser import SafeConfigParser

def get_default(key):
    """Get assemblers default value from config file."""
    return parser.get('assemblers', key)

def run(assembler, job_data):
    plugin = self.pmanager.getPluginByName(assembler)
    settings = plugin.details.items('Settings')
    return plugin.plugin_object(settings, job_data)

def get_tar_name(job_id, suffix):
    name = 'job' + str(job_id)
    name += '_'
    name += suffix
    name += '.tar.gz'
    return name
    
def tar(outpath, asm_data, tarname):
    print "Compressing"
    outfile = outpath + '/tar/'

    try:
        os.makedirs(outfile)
    except:
        pass

    outfile += tarname
    targs = ['tar', '-czvf', outfile, asm_data]
    t = subprocess.Popen(targs)
    t.wait()
    return outfile

def tar_directory(outpath, directory, tarname):
    outfile = outpath
    try:
        os.makedirs(outfile)
    except:
        pass

    outfile += tarname
    targs = ['tar', '-czvf', outfile, './']
    t = subprocess.Popen(targs, cwd=directory)
    t.wait()
    return outfile

def tar_list(outpath, file_list, tarname):
    """ Tars a file list. Attempts to find the highest common path"""
    common_path = os.path.commonprefix(file_list)
    outfile = outpath + '/tar/'
    try: os.makedirs(outfile)
    except: pass
    outfile += tarname
    targs = ['tar', '-czvf', outfile]
    targs += [os.path.relpath(path, common_path) for path in file_list]
    logging.debug("Tar command: %s: " % targs)
    t = subprocess.Popen(targs, cwd=common_path)
    t.wait()
    return outfile

def ls_recursive(path):
    """ Returns list of all files in a dir"""
    allfiles = []
    for root, sub_dirs, files in os.walk(path):
        for f in files:
            allfiles.append(os.path.join(root, f))
    return allfiles

def prefix_file_move(file, prefix):
    """ Adds prefix to file, returns new file name, moves file"""
    if os.path.isdir(file):
        return file
    f = '/' + str(prefix) + '__' + os.path.basename(file)
    newfile =  os.path.split(file)[0] + f
    os.rename(file, newfile)
    return newfile

def prefix_file(file, prefix):
    """ Adds prefix to file, returns new filename"""
    if os.path.isdir(file):
        return file
    f = '/' + str(prefix) + '__' + os.path.basename(file)
    newfile =  os.path.split(file)[0] + f
    return newfile

def rename_file_copy(filepath, newname):
    """ Renames the file, keeping the file extension, copies to new file name"""
    f = '/' + newname + '.' + os.path.basename(filepath).rsplit('.', 1)[1]
    newfile =  os.path.split(filepath)[0] + f
    shutil.copy(filepath, newfile)
    return newfile

def rename_file_symlink(filepath, newname):
    """ Renames the file, keeping the file extension, symlinks to new file name"""
    f = '/' + newname + '.' + os.path.basename(filepath).rsplit('.', 1)[1]
    newfile =  os.path.split(filepath)[0] + f
    os.symlink(filepath, newfile)
    return newfile
    

def get_fasta(directory):
    """ Return the list of Fasta files in DIRECTORY
    """
    files = os.listdir(directory)
    fasta_files = [file for file in files 
                   if re.search(r'\.fa$|\.fasta$', file, re.IGNORECASE) is not None]
    return fasta_files

def get_fastq(directory):
    """ Return the list of Fastq files in DIRECTORY
    """
    files = os.listdir(directory)
    fastq_files = [file for file in files 
                   if re.search(r'\.fq$|\.fastq$', file, re.IGNORECASE) is not None]
    return fastq_files
    
def get_quala(directory):
    """ Return the list of Quala files in DIRECTORY
    """
    files = os.listdir(directory)
    quala_files = [file for file in files 
                   if re.search(r'\.qa$|\.quala$', file, re.IGNORECASE) is not None]
    return fastq_files

def get_qual_encoding(file):
    f = open(file, 'r')
    while True:
        bline = f.readline()
        if bline.find('+') != -1: # Line before quality line
            line = f.readline()
            for c in line:
                if ord(c) > 74:
                    logging.info("Detected phred64 quality encoding")
                    return 'phred64'
                elif ord(c) < 64:
                    logging.info("Detected phred33 quality encoding")
                    return 'phred33'
        if len(bline) == 0: #EOF
            break
    return

def tab_to_fasta(tabbed_file, outfile, threshold):
    tabbed = open(tabbed_file, 'r')
    fasta = open(outfile, 'w')
    #prefixes = ['>_', ' len_', ' cov_', ' stdev_', ' GC_', '\n']
    prefixes = ['>_', ' len_', ' cov_', ' stdev_', ' GC_', ' seed_', '\n']
    for line in tabbed:
        l = line.split('\t')
        if int(l[1]) <= threshold:
            for i in range(len(l)):
                fasta.write(prefixes[i] + l[i])
    tabbed.close()
    fasta.close()


def arast_reads(filelist):
    """ Returns a list of files into the ARAST reads dict format """
    filedicts = []
    for f in filelist:
        filedicts.append({'type':'single', 'files':[f]})
    return filedicts


def curl_download_url(url, outdir=None, token=None):
    if outdir:
        try: os.makedirs(outdir)
        except OSError: pass
    else:
        outdir = os.getcwd()

    filename = os.path.basename(url)
    filename = re.sub(r'\?download', '', filename)
    filename = re.sub(r'[?&]', '_', filename)

    cmd = ['curl', '-k', '-o', filename, url ]
    if token:
        cmd += ['-H', '"Authorization: OAuth {}"'.format(token)]

    logging.info("curl cmd = {}".format(" ".join(cmd)))

    p = subprocess.Popen(cmd, cwd=outdir)
    p.wait()
    downloaded = os.path.join(outdir, os.path.basename(url))
    if os.path.exists(downloaded):
        print('File Downloaded:', downloaded)
        return downloaded



parser = SafeConfigParser()
#parser.read('arast.conf')
#basepath = get_default('basepath')
#metadata = meta.MetadataConnection(parser.get('meta','mongo.remote.host'))

###### Context Managers

@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass
