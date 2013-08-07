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

import metadata as meta

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
    outfile = outpath + '/tar/'

    try:
        os.makedirs(outfile)
    except:
        pass

    outfile += tarname
    targs = ['tar', '-czvf', outfile]
    for file in file_list:
        f = './' + os.path.basename(file)
        targs.append('-C')
        targs.append(os.path.split(file)[0])
        targs.append(f)
    
    logging.debug("Tar command: %s: " % targs)
    t = subprocess.Popen(targs)
    t.wait()
    return outfile

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

def read_config():
    pass

def run_bwa(data_dir, ref_name, read_files, prefix):
    """ Ex: run_bwa(velvet_data, 'contigs.fa', reads_list, 'velvet') """
    bwa_exec = 'bwa'
    samtools_exec = 'samtools'
    tmp_files = []

    ref_file = data_dir + ref_name

    # Run the index on reference
    bwa_args = [bwa_exec, 'index']
    bwa_args.append(ref_file)
    logging.info(bwa_args)
    p_index = subprocess.Popen(bwa_args)
    p_index.wait()

    # Align reads to reference
    bwa_args = [bwa_exec, 'aln']
    bwa_args.append(ref_file)

    if len(read_files) > 1:
        # Concatenate read files
        reads = data_dir + 'reads.fa'
        destination = open(reads,'wb')
        for rf in read_files:
            logging.info("Concatenating read file: %s", rf)
            shutil.copyfileobj(open(rf,'rb'), destination)
        destination.close()
        tmp_files.append(reads)
    else:
        reads = read_files[0]
    bwa_args.append(reads)
    

    aln_out = data_dir + prefix
    aln_out += '_aln.sai'
    aln_outbuffer = open(aln_out, 'wb')
    tmp_files.append(aln_out)
    bwa_args.append(aln_out)
    logging.info(bwa_args)
    p_aln = subprocess.Popen(bwa_args, stdout=aln_outbuffer)
    p_aln.wait()
    aln_outbuffer.close()

    # Create Sam file
    #bwa samse $ref $dir/aln-$refX$reads.sai $reads > $dir/aln-$refX$reads.sam
    bwa_args = [bwa_exec, 'samse', ref_file, aln_out, reads]
    sam_out = data_dir + prefix
    sam_out += '_aln.sam'
    sam_outbuffer = open(sam_out, 'wb')
    tmp_files.append(sam_out)
    bwa_args.append(sam_out)
    logging.info(bwa_args)
    p_sam = subprocess.Popen(bwa_args, stdout=sam_outbuffer)
    p_sam.wait()
    sam_outbuffer.close()

    # Create bam file
    # samtools view -S -b -o $dir/aln-$refX$reads.bam $dir/aln-$refX$reads.sam
    samtools_args = [samtools_exec, 'view', '-S', '-b', '-o']
    bam_out = data_dir + prefix
    bam_out += '_aln.bam'
    bam_outbuffer = open(bam_out, 'wb')
    samtools_args.append(bam_out)
    samtools_args.append(sam_out)

    logging.info(samtools_args)
    p_bam = subprocess.Popen(samtools_args, stdout=bam_outbuffer)
    p_bam.wait()
    bam_outbuffer.close()

    for temp in tmp_files:
        try:
            os.remove(temp)
        except:
            logging.info("Could not remove %s" % temp)

    return bam_out

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


parser = SafeConfigParser()
#parser.read('arast.conf')
#basepath = get_default('basepath')
#metadata = meta.MetadataConnection(parser.get('meta','mongo.remote.host'))

