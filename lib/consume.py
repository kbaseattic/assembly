"""
Consumes a job from the queue
"""

import copy
import logging
import pika
import sys
import json
import requests
import os
import shutil
import time
import datetime 
import socket
import multiprocessing
import tarfile
import subprocess
#from yapsy.PluginManager import PluginManager
from plugins import ModuleManager
from multiprocessing import current_process as proc
from traceback import format_tb, format_exc

import config
import assembly as asm
import metadata as meta
import shock 

from ConfigParser import SafeConfigParser

class ArastConsumer:
    def __init__(self, shockurl, arasturl, config, threads):
        self.parser = SafeConfigParser()
        self.parser.read(config)
        # Load plugins
        self.pmanager = ModuleManager(threads)

    # Set up environment
        self.shockurl = shockurl
        self.arasturl = arasturl
        self.shockuser = self.parser.get('shock','admin_user')
        self.shockpass = self.parser.get('shock','admin_pass')
        self.datapath = self.parser.get('compute','datapath')
        self.queue = self.parser.get('rabbitmq','default_routing_key')
        self.min_free_space = float(self.parser.get('compute','min_free_space'))
        self.metadata = meta.MetadataConnection(config, arasturl)
        self.gc_lock = multiprocessing.Lock()
        
        #self.metadata.update_doc('active_nodes', 'server_name', socket.gethostname(),
         #                        'status', 'running')

    def garbage_collect(self, datapath, required_space):
        """ Monitor space of disk containing DATAPATH and delete files if necessary."""
        self.gc_lock.acquire()
        s = os.statvfs(datapath)
        free_space = float(s.f_bsize * s.f_bavail)
        logging.debug("Free space in bytes: %s" % free_space)
        logging.debug("Required space in bytes: %s" % required_space)
        while ((free_space - self.min_free_space) < required_space):
            #Delete old data
            dirs = os.listdir(datapath)
            times = []
            for dir in dirs:
                times.append(os.path.getmtime(datapath + dir))
            if len(dirs) > 0:
                old_dir = datapath + dirs[times.index(min(times))]
                shutil.rmtree(old_dir, ignore_errors=True)
            else:
                logging.error("No more directories to remove")
                break
            logging.info("Space required.  %s removed." % old_dir)
            s = os.statvfs(datapath)
            free_space = float(s.f_bsize * s.f_bavail)
            logging.debug("Free space in bytes: %s" % free_space)
        self.gc_lock.release()

    # def get_data(self, body):
    #     """Get data from cache or Shock server."""
    #     params = json.loads(body)

    #     filename = self.datapath
    #     filename += str(params['data_id'])
    #     datapath = filename
    #     all_files = []
    #     if os.path.isdir(datapath):
    #         logging.info("Requested data exists on node")
    #         touch(datapath)
    #     else:
    #         uid = params['_id']
    #         self.metadata.update_job(uid, 'status', 'Data transfer')
    #         data_doc = self.metadata.get_doc_by_data_id(params['data_id'])
    #         if data_doc:
    #             files = data_doc['filename']
    #             ids = data_doc['ids']
    #             job_id = params['job_id']
    #             uid = params['_id']
    #             filename += "/raw/"
    #             os.makedirs(filename)

    #             # Get required space and garbage collect
    #             try:
    #                 req_space = 0
    #                 for file_size in data_doc['file_sizes']:
    #                     req_space += file_size
    #                 self.garbage_collect(self.datapath, req_space)
    #             except:
    #                 pass 

    #             url = "http://%s" % (self.shockurl)
    #             for i in range(len(files)):
    #                 file = files[i]
    #                 id = ids[i]
    #                 temp_url = url
    #                 temp_url += "/node/%s" % (id)
    #                 temp_url += "?download" 
    #                 r = self.get(temp_url)
    #                 cur_file = filename
    #                 cur_file += file
    #                 with open(cur_file, "wb") as code:
    #                     code.write(r.content)
    #                 all_files.append(cur_file)
    #         else:
    #             datapath = None
    #     return datapath, all_files

    def get_data2(self, body):
        """Get data from cache or Shock server."""
        params = json.loads(body)
        #filepath = self.datapath + str(params['data_id'])
        filepath = os.path.join(self.datapath, params['ARASTUSER'],
                                str(params['data_id']))
        datapath = filepath
        filepath += "/raw/"
        all_files = []

        uid = params['_id']
        job_id = params['job_id']

        data_doc = self.metadata.get_doc_by_data_id(params['data_id'], params['ARASTUSER'])
        if data_doc:
            paired = data_doc['pair']
            single = data_doc['single']
            files = data_doc['filename']
            ids = data_doc['ids']
            token = params['oauth_token']
        else:
            raise Exception('Data {} does not exist on Shock Server'.format(
                    params['data_id']))

        all_files = []
        if os.path.isdir(datapath):
            logging.info("Requested data exists on node")
            try:
                for l in paired:
                    filedict = {'type':'paired', 'files':[]}
                    for word in l:
                        if is_filename(word):
                            filedict['files'].append(
                                os.path.join(filepath,  word))
                        else:
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                    all_files.append(filedict)
            except:
                logging.info('No paired files submitted')

            try:
                for l in single:
                    filedict = {'type':'single', 'files':[]}
                    for word in l:
                        if is_filename(word):
                            filedict['files'].append(
                                os.path.join(filepath, word))
                        else:
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                    all_files.append(filedict)
            except:
                logging.info(format_tb(sys.exc_info()[2]))
                logging.info('No single files submitted!')
            print all_files
            touch(datapath)

        else: # download data
            self.metadata.update_job(uid, 'status', 'Data transfer')
            os.makedirs(filepath)

            # Get required space and garbage collect
            try:
                req_space = 0
                for file_size in data_doc['file_sizes']:
                    req_space += file_size
                self.garbage_collect(self.datapath, req_space)
            except:
                pass 

            url = "http://%s" % (self.shockurl)

            try:
                for l in paired:
                    filedict = {'type':'paired', 'files':[]}
                    for word in l:
                        if is_filename(word):
                            baseword = os.path.basename(word)
                            filedict['files'].append(
                                shock.curl_download_file(url, ids[files.index(baseword)], token, outdir=filepath))
                        else:
                            print word
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                    all_files.append(filedict)
            except:
                logging.info(format_exc(sys.exc_info()))
                logging.info('No paired files submitted')

            try:
                for l in single:
                    filedict = {'type':'single', 'files':[]}
                    
                    for wordpath in l:
                        # Parse user directories
                        try:
                            path, word = wordpath.rsplit('/', 1)
                            path += '/'
                        except:
                            word = wordpath
                            path = ''

                        if is_filename(word):
                            filedict['files'].append(
                                shock.curl_download_file(url, ids[files.index(word)], token, outdir=filepath))
                            #shock.download(url, ids[files.index(word)], filepath + '/' + path))
                        else:
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                    all_files.append(filedict)
            except:
                logging.info(format_tb(sys.exc_info()[2]))

                logging.info('No single end files submitted')

        return datapath, all_files



    def compute(self, body):
        error = False
        params = json.loads(body)

        # Download files (if necessary)
        datapath, all_files = self.get_data2(body)
        rawpath = datapath + '/raw/'

        #extract_files(rawpath)
        if not datapath:
            error = True
            logging.error("Data does not exist!")
        
        job_id = params['job_id']
        uid = params['_id']
        user = params['ARASTUSER']
        token = params['oauth_token']

        jobpath = os.path.join(datapath, str(job_id))
        os.makedirs(jobpath
)
        # Create job log
        self.out_report_name = '{}/{}_report.txt'.format(jobpath, str(job_id))
        self.out_report = open(self.out_report_name, 'w')

        job_data = {'job_id' : params['job_id'], 
                    'uid' : params['_id'],
                    'reads': all_files,
                    'datapath': datapath,
                    'out_report' : self.out_report}
        self.out_report.write("Arast Pipeline: Job {}\n".format(job_id))

        try:
            pipeline = params['pipeline']
        except:
            pipeline = False

        start_time = time.time()
        download_ids = {}

        if error:
            self.metadata.update_job(uid, 'status', 'Datapath error')

        url = "http://%s" % (self.shockurl)
        url += '/node'

        # Run individual modules
        status = 'complete:'
        # if params['assemblers']:
        #     assemblers, overrides = parse_params(params['assemblers'])
        #     for idx, a in enumerate(assemblers):
        #         #for a in params['assemblers']:
        #         self.garbage_collect(self.datapath, 0)
        #         self.metadata.update_job(uid, 'status', "running: %s" % a)
        #         job_data['params'] = overrides[idx].items()
        #         try:
        #             result_tar = self.pmanager.run_module(a, job_data, tar=True)
        #             res = self.upload(url, result_tar)
        #             # Get location
        #             download_ids[a] = res['D']['id']
        #             status += "{} [success] ".format(a)
        #             self.out_report.write("ERROR TRACE:\n{}\n".
        #                                   format(format_tb(sys.exc_info()[2])))

        #         except Exception as e:
        #             status += "%s [failed:%s] " % (a, e)
        #             self.out_report.write("ERROR TRACE:\n{}\n".
        #                                   format(format_tb(sys.exc_info()[2])))

        #         except:
        #             status += "%s [failed:%s %s] " % (a, str(sys.exc_info()),
        #                                                   format_tb(sys.exc_info()[2]))
        #             logging.info("%s failed to finish" % a)
        #             self.out_report.write("ERROR TRACE:\n{}\n".
        #                                   format(format_tb(sys.exc_info()[2])))

        if pipeline:
            try:
                self.pmanager.validate_pipe(pipeline)
                result_tar, quast  = self.run_pipeline(pipeline, job_data)
                #res = self.upload(url, result_tar)
                res = self.upload(url, user, token, result_tar)
                download_ids['pipeline'] = res['D']['id']

                #res = self.upload(url, quast)
                res = self.upload(url, user, token, quast)
                download_ids['quast'] = res['D']['id']

                status += "pipeline [success] "
                self.out_report.write("Pipeline completed successfully\n")
            except:
                traceback = format_exc(sys.exc_info())
                status = "[FAIL] {}".format(sys.exc_info()[1])
                print traceback
                self.out_report.write("ERROR TRACE:\n{}\n".
                                      format(format_tb(sys.exc_info()[2])))


        elapsed_time = time.time() - start_time
        ftime = str(datetime.timedelta(seconds=int(elapsed_time)))

        self.out_report.close()
        #res = self.upload(url, self.out_report_name)
        res = self.upload(url, user, token, self.out_report_name)
        # Get location
        download_ids['report'] = res['D']['id']

        self.metadata.update_job(uid, 'result_data', download_ids)
        self.metadata.update_job(uid, 'status', status)
        self.metadata.update_job(uid, 'computation_time', ftime)

        print '=========== JOB COMPLETE ============'

    def run_pipeline(self, pipes, job_data_global):
        """
        Runs all pipelines in list PIPES
        """
        all_pipes = self.pmanager.parse_input(pipes)
        #include_reads = self.pmanager.output_type(pipeline[-1]) == 'reads'
        include_reads = False
        pipeline_num = 1
        all_files = []
        pipe_outputs = []
        final_contigs = []
        for pipe in all_pipes:
            try:
                job_data = copy.deepcopy(job_data_global)
                job_data['out_report'] = job_data_global['out_report'] 
                pipeline, overrides = self.pmanager.parse_pipe(pipe)
                num_stages = len(pipeline)
                pipeline_stage = 1
                pipeline_results = []
                cur_outputs = []
                self.out_report.write('Pipeline {}: {}\n'.format(pipeline_num, pipe))
                pipe_suffix = '' # filename code for indiv pipes
                for module_name in pipeline:
                    print '\n\n{0} Running module: {1} {2}'.format(
                        '='*20, module_name, '='*(35-len(module_name)))
                    if module_name.lower() == 'none':
                        continue
                    ## For now, module code is 1st and last letter
                    pipe_suffix += module_name[0].upper() + module_name[-1]

                    self.out_report.write('\n{0} PIPELINE {1} -- STAGE {2}: {3} {4}\n'.format(
                            '='*10, pipeline_num, pipeline_stage, 
                            module_name, '='*(25-len(module_name))))
                    self.out_report.write('Input file(s): {}\n'.format(list_io_basenames(job_data)))
                    logging.debug('New job_data for stage {}: {}'.format(
                            pipeline_stage, job_data))
                    job_data['params'] = overrides[pipeline_stage-1].items()

                    #### Run module
                    # Check if output data exists
                    reuse_data = False
                    for pipe in pipe_outputs:
                        if reuse_data:
                            break
                        for i in range(pipeline_stage):
                            try:
                                if not pipe[i][0] == cur_outputs[i][0]:
                                    break
                            except:
                                pass
                            if pipe[i][0] == module_name and i == pipeline_stage - 1: #copy!
                                logging.info('Found previously computed data, reusing.')
                                output = [] + pipe[i][1]
                                alldata = [] + pipe[i][2]
                                reuse_data = True
                                break

                    if not reuse_data:
                        output, alldata = self.pmanager.run_module(module_name, job_data, all_data=True,
                                                                   reads=include_reads)

                        # Prefix outfiles with pipe stage
                        alldata = [asm.prefix_file_move(
                                file, "P{}_S{}_{}".format(pipeline_num, pipeline_stage, module_name)) 
                                    for file in alldata]

                    output_type = self.pmanager.output_type(module_name)
                    if output_type == 'contigs': #Assume assembly contigs
                        job_data['reads'] = asm.arast_reads(alldata)

                    elif output_type == 'reads': #Assume preprocessing
                        if include_reads and reuse_data: # data was prefixed and moved
                            for d in output:
                                files = [asm.prefix_file(f, "P{}_S{}_{}".format(
                                            pipeline_num, pipeline_stage, module_name)) for f in d['files']]
                                d['files'] = files
                                d['short_reads'] = [] + files

                        job_data['reads'] = output
                    pipeline_results += alldata
                    if pipeline_stage == num_stages: # Last stage, add contig for assessment
                        fcontigs = [asm.prefix_file(
                                file, "P{}_S{}_{}".format(pipeline_num, pipeline_stage, module_name)) 
                                    for file in output]
                        rcontigs = [asm.rename_file_copy(f, 'P{}_{}'.format(
                                    pipeline_num, pipe_suffix)) for f in fcontigs]
                        final_contigs += rcontigs
                    pipeline_stage += 1
                    cur_outputs.append([module_name, output, alldata])
            except:
                traceback = format_exc(sys.exc_info())
                self.out_report.write('Pipeline Failed {}\n'.format(traceback))

            pipe_outputs.append(cur_outputs)
            pipeline_datapath = '{}/{}/pipeline{}/'.format(job_data['datapath'], job_data['job_id'],
                                                           pipeline_num)

            try:
                os.makedirs(pipeline_datapath)
            except:
                logging.info("{} exists, skipping mkdir".format(pipeline_datapath))
            all_files.append(asm.tar_list(pipeline_datapath, pipeline_results, 
                                'pipe{}_{}.tar.gz'.format(pipeline_num, pipe_suffix)))
            pipeline_num += 1

        # Quast
        job_data['final_contigs'] = final_contigs
        quast_tar = self.pmanager.run_module('quast', job_data, tar=True)
        quast_ret = quast_tar.rsplit('/', 1)[0] + '/report.tar.gz'
        os.rename(quast_tar, quast_ret)

        if len(all_files) == 1:
            return asm.tar_list('{}/{}'.format(job_data['datapath'], job_data['job_id']),
                                [all_files[0]],'pipeline_{}.tar.gz'.format(job_data['job_id'])), quast_ret
            
        return asm.tar_list('{}/{}'.format(job_data['datapath'], job_data['job_id']),
                        all_files,'pipelines_{}.tar.gz'.format(job_data['job_id'])), quast_ret
    

    def upload(self, url, user, token, file):
        files = {}
        files["file"] = (os.path.basename(file), open(file, 'rb'))
        logging.debug("Message sent to shock on upload: %s" % files)
        sclient = shock.Shock(url, user, token)
        res = sclient.curl_post_file(file)
        #res = self.post(url, files)
        print res
        return res

    # TODO move this to shock.py
    def post(self, url, files):
            r = None
            r = requests.post(url, auth=(self.shockuser, self.shockpass), files=files)

            res = json.loads(r.text)
            return res

    def get(self, url):     
        r = None
        r = requests.get(url, auth=(self.shockuser, self.shockpass))       
            #res = json.loads(r.text)
        return r

    def fetch_job(self):
        connection = pika.BlockingConnection(pika.ConnectionParameters(
                host = self.arasturl))
        channel = connection.channel()
        channel.basic_qos(prefetch_count=1)
        result = channel.queue_declare(queue=self.queue,
                                       exclusive=False,
                                       auto_delete=False,
                                       durable=True)

        logging.basicConfig(format=("%(asctime)s %s %(levelname)-8s %(message)s",proc().name))
        print proc().name, ' [*] Fetching job...'

        channel.basic_consume(self.callback,
                              queue=self.queue,
                              no_ack=True) #change?

        channel.start_consuming()

    def callback(self, ch, method, properties, body):
        print " [*] %r:%r" % (method.routing_key, body)
        self.compute(body)

    def start(self):
        self.fetch_job()


### Helper functions ###
def touch(path):
    now = time.time()
    try:
        # assume it's there
        os.utime(path, (now, now))
    except os.error:
        # if it isn't, try creating the directory,
        # a file with that name
        os.makedirs(os.path.dirname(path))
        open(path, "w").close()
        os.utime(path, (now, now))
    
def extract_files(datapath):
    """ Decompress files if necessary """
    files = os.listdir(datapath)
    logging.debug("Looking for files to extract in %s" % files)
    for tfile in [datapath + f for f in files]:
        if tarfile.is_tarfile(tfile):
            logging.debug("Extracting %s" % tfile)
            tarfile.open(tfile, 'r').extractall(datapath)
            os.remove(tfile)
        elif tfile.endswith('.bz2'):
            logging.debug("Extracting %s" % tfile)
            p = subprocess.Popen(['bunzip2', tfile])
            p.wait()

            
def parse_params(pipe):
    """ Returns the parameter overrides from string.
    e.g Input: [kiki ?k=31 velvet ?ins=500 a5]
    Output: [kiki, velvet, a5], [{k:31}, {ins:500}, {}]
    """
    # Parse param overrides
    overrides = []
    pipeline = []
    for word in pipe:
        module_num = -1
        if not word.startswith('?'): # is module
            pipeline.append(word)
            module_num += 1
            overrides.append({})
            
        elif word[1:-1].find('=') != -1: # is param
            kv = word[1:].split('=')
            overrides[module_num] = dict(overrides[module_num].items() +
                                         dict([kv]).items())
    return pipeline, overrides


def parse_reads(params):
    """
    Get file pairings from list.
    E.g Input: [
        Output: [('1a.fa,1b.fa), ('interleaved.fa',), 'unpaired.fa']
        [{'type':'paired','files': [pair1,pair2],'ins':300', 'exp_cov': None},
         {'type':'single', 'files': [file], 'ins': None, 'exp_cov': }

    """
    # Look in pair key
    #for pair in 


    # Look in single key

    

    files = []
    for word in filestring:
        if word[1:-1].find('=') != -1: # is paired
            kv = word.split('=')
    pass


def is_filename(word):
    return word.find('.') != -1 and word.find('=') == -1

def list_io_basenames(job_data):
    basenames = []
    for d in job_data['reads']:
        for f in d['files']:
            basenames.append(os.path.basename(f))
    return basenames
