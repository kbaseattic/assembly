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
#import tarfile
import glob

import metadata as meta

from ConfigParser import SafeConfigParser

def get_default(key):
    """Get assemblers default value from config file."""
    return parser.get('assemblers', key)

def is_available(assembler):
    """ Check if ASSEMBLER is a valid/available assembler.
    """
    assemblers = ['kiki','velvet','a5']
    if assembler in assemblers:
        return True
    else:
        return False

def run(assembler, job_data):
    plugin = self.pmanager.getPluginByName(assembler)
    settings = plugin.details.items('Settings')
    return plugin.plugin_object(settings, job_data)
    

    # if len(os.listdir(datapath)) == 0:
    #     raise IOError #empty directory!
    # logging.info("Running assembler: %s" % assembler)
    # if assembler == 'kiki':
    #     result_tar = run_kiki(datapath, uid, bwa)
    # elif assembler == 'velvet':
    #     result_tar = run_velvet(datapath, uid, bwa)
    # elif assembler == 'a5':
    #     result_tar = run_a5(datapath, uid)
    # if result_tar is not None:
    #     return result_tar
    # else:
    #     raise IOError

def run_a5(datapath, uid):
    a5_exec = 'a5_pipeline.pl'
    raw_path = datapath + '/raw/'
    a5_data = datapath + '/a5/' + uid + '/'
    os.makedirs(a5_data)
    a5_prefix = a5_data + 'a5'
    args = [a5_exec,]
    valid_files = get_fastq(raw_path)
    if not valid_files:
        raise Exception('No valid input files')
    readfiles = []
    tmp_files = []
    for file in valid_files:
        readfile = raw_path + file
        print readfile
        args.append(readfile)
        readfiles.append(readfile)
    args.append(a5_prefix)
    print args
    print "Starting a5"
    p = subprocess.Popen(args)
    p.wait()

    results = a5_data + '*'
    rlist = glob.glob(results)
    #tmp_files += contigs
    logging.debug("Contigs: %s" % rlist)

    tar_file = tar_list(a5_data, rlist, 'a5_data.tar.gz')

    # Return location of finished data
    return tar_file


def run_kiki(datapath, uid, bwa):
    ki_exec = basepath + get_default('kiki.path')
    ki_exec += get_default('kiki.exec')
    threshold = 1000
    raw_path = datapath + '/raw/'
    kiki_data = datapath + '/kiki/' + uid + '/'
    os.makedirs(kiki_data)
    kiki_prefix = kiki_data + 'kiki'
    args = [ki_exec, '-k', '29', '-i']
    valid_files  = get_fasta(raw_path)
    valid_files += get_fastq(raw_path)

    if not valid_files:
        raise Exception('No valid input files')

    readfiles = []
    tmp_files = []

    for file in valid_files:
        readfile = raw_path + file
        print readfile
        args.append(readfile)
        readfiles.append(readfile)
    args.append('-o')
    args.append(kiki_prefix)
    #ki_data = raw_path + 'ki/'    
    print args
    print "Starting kiki"
    p = subprocess.Popen(args)
    p.wait()

    contigfile = kiki_data + '*.contig'
    contigs = glob.glob(contigfile)

    if not contigs:
        raise Exception("No contigs")
    tmp_files += contigs
    logging.debug("Contigs: %s" % contigs)

    if bwa:
        fa_contigs = []
        for contig in contigs:
            outfile = contig + '.kifa'
            tab_to_fasta(contig, outfile, threshold)
            fa_contigs.append(outfile)
            tmp_files.append(outfile)

        if len(fa_contigs) < 1:
            pass #TODO concat
        else:
            ref_contig = os.path.basename(fa_contigs[0])

        bwa_bam = run_bwa(kiki_data, ref_contig, readfiles, 'kiki')
        contigs.append(bwa_bam)
        #tmp_files.append(bwa_bam)

    tar_file = tar_list(kiki_data, contigs, 'ki_data.tar.gz')

    # Remove intermediate files
    contigfile = raw_path + '*.contig.*'
    #tmp_files += glob.glob(contigfile)

    # for temp in tmp_files:
    #     try:
    #         os.remove(temp)
    #         logging.info("Removed %s" % temp)
    #     except:
    #         logging.info("Could not remove %s" % temp)

    # Return location of finished data
    return tar_file


def run_velvet(datapath, uid, bwa):

    velvet_data = datapath 
    velvet_data += '/'
    velvet_data += uid
    velvet_data += '/'
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
    read_files = []



    # Find paired
    paired_reads = get_paired(get_fasta(raw_path))
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
            read_files.append(str(raw_path + paired_reads[i][0]))
            read_files.append(str(raw_path + paired_reads[i][1]))
    else:
        # TODO handle more than just fasta files
        valid_files = get_fasta(raw_path)
        valid_files += get_fastq(raw_path)

        if not valid_files:
            raise Exception('No valid input files')

        for file in valid_files:
            readfile = raw_path + file
            args.append(readfile)
            read_files.append(readfile)
    

    logging.info(args)
    p = subprocess.Popen(args)
    p.wait()

    args_g = [velvetg, velvet_data]
    logging.info(args_g)
    g = subprocess.Popen(args_g)
    g.wait()

    vfiles = [velvet_data + 'contigs.fa', velvet_data + 'stats.txt']
    for f in vfiles:
        if not os.path.exists(f):
            raise Exception('No contigs')

    #Run BWA if specified
    if bwa:
        vfiles.append(run_bwa(velvet_data, 'contigs.fa', read_files, 'velvet'))



    tar_file = tar_list(datapath, vfiles, 'velvet_data.tar.gz')
    return tar_file

def get_tar_name(job_id, suffix):
    name = 'job' + str(job_id)
    name += '_'
    name += suffix
    name += '.tar.gz'
    return name
    

def run_soapdenovo():
    return 2


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

def fasta_to_tab(fasta_file):
    pass




parser = SafeConfigParser()
parser.read('arast.conf')
basepath = get_default('basepath')
#metadata = meta.MetadataConnection(parser.get('meta','mongo.remote.host'))

