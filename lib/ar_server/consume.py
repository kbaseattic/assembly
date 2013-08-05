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
import threading
import tarfile
import subprocess
#from yapsy.PluginManager import PluginManager
from plugins import ModuleManager
from job import ArastJob
from multiprocessing import current_process as proc
from traceback import format_tb, format_exc

import config
import assembly as asm
import metadata as meta
import shock 

from ConfigParser import SafeConfigParser

class ArastConsumer:
    def __init__(self, shockurl, arasturl, config, threads, queue):
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
        if queue:
            self.queue = queue
            print('Using queue:{}'.format(self.queue))
        else:
            self.queue = self.parser.get('rabbitmq','default_routing_key')
        self.min_free_space = float(self.parser.get('compute','min_free_space'))
        self.metadata = meta.MetadataConnection(config, arasturl)
        self.gc_lock = multiprocessing.Lock()
        #self.metadata.update_doc('active_nodes', 'server_name', socket.gethostname(),
         #                        'status', 'running')

    def garbage_collect(self, datapath, user, required_space):
        """ Monitor space of disk containing DATAPATH and delete files if necessary."""
        self.gc_lock.acquire()
        s = os.statvfs(datapath)
        free_space = float(s.f_bsize * s.f_bavail)
        logging.debug("Free space in bytes: %s" % free_space)
        logging.debug("Required space in bytes: %s" % required_space)
        while ((free_space - self.min_free_space) < required_space):
            #Delete old data
            dirs = os.listdir(os.path.join(datapath, user))
            times = []
            for dir in dirs:
                times.append(os.path.getmtime(os.path.join(datapath, user, dir)))
            if len(dirs) > 0:
                old_dir = os.path.join(datapath, user, dirs[times.index(min(times))])
                shutil.rmtree(old_dir, ignore_errors=True)
            else:
                logging.error("No more directories to remove")
                break
            logging.info("Space required.  %s removed." % old_dir)
            s = os.statvfs(datapath)
            free_space = float(s.f_bsize * s.f_bavail)
            logging.debug("Free space in bytes: %s" % free_space)
        self.gc_lock.release()


    def get_data(self, body):
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
        user = params['ARASTUSER']

        data_doc = self.metadata.get_doc_by_data_id(params['data_id'], params['ARASTUSER'])
        if data_doc:
            paired = data_doc['pair']
            single = data_doc['single']
            files = data_doc['filename']
            ids = data_doc['ids']
            token = params['oauth_token']
            try:
                ref = data_doc['reference']
            except:
                pass
        else:
            self.metadata.update_job(uid, 'status', 'Invalid Data ID')
            raise Exception('Data {} does not exist on Shock Server'.format(
                    params['data_id']))

        all_files = []
        if os.path.isdir(filepath):
            logging.info("Requested data exists on node")
            try:
                for l in paired:
                    filedict = {'type':'paired', 'files':[]}
                    for word in l:
                        if is_filename(word):
                            baseword = os.path.basename(word)
                            filedict['files'].append(
                                extract_file(os.path.join(filepath,  baseword)))
                        else:
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                    all_files.append(filedict)
            except:
                logging.info('No paired files submitted')

            try:
                for seqfiles in single:
                    for wordpath in seqfiles:
                        filedict = {'type':'single', 'files':[]}    
                        if is_filename(wordpath):
                            baseword = os.path.basename(wordpath)
                            filedict['files'].append(
                                extract_file(os.path.join(filepath, baseword)))
                        else:
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                        all_files.append(filedict)
            except:
                logging.info(format_tb(sys.exc_info()[2]))
                logging.info('No single files submitted!')
            
            try:
                for r in ref:
                    for wordpath in r:
                        filedict = {'type':'reference', 'files':[]}    
                        if is_filename(wordpath):
                            baseword = os.path.basename(wordpath)
                            filedict['files'].append(
                                extract_file(os.path.join(filepath, baseword)))
                        else:
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                        all_files.append(filedict)
            except:
                logging.info(format_tb(sys.exc_info()[2]))
                logging.info('No reference files submitted!')
            
    
            touch(datapath)

        else: # download data
            self.metadata.update_job(uid, 'status', 'Data transfer')
            os.makedirs(filepath)

            # Get required space and garbage collect
            try:
                req_space = 0
                for file_size in data_doc['file_sizes']:
                    req_space += file_size
                self.garbage_collect(self.datapath, user, req_space)
            except:
                pass 
            url = "http://%s" % (self.shockurl)

            try:
                for l in paired:
                    #FILEDICT contains a single read library's info
                    filedict = {'type':'paired', 'files':[]}
                    for word in l:
                        if is_filename(word):
                            baseword = os.path.basename(word)
                            filedict['files'].append(
                                self.download(url, user, token, ids[files.index(baseword)], filepath))
                        else:
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                    all_files.append(filedict)
            except:
                #logging.info(format_exc(sys.exc_info()))
                logging.info('No paired files submitted')

            try:
                for seqfiles in single:
                    for wordpath in seqfiles:
                        filedict = {'type':'single', 'files':[]}
                        # Parse user directories
                        try:
                            path, word = wordpath.rsplit('/', 1)
                            path += '/'
                        except:
                            word = wordpath
                            path = ''

                        if is_filename(word):
                            baseword = os.path.basename(word)
                            filedict['files'].append(
                                self.download(url, user, token, ids[files.index(baseword)], filepath))
                        else:
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                        all_files.append(filedict)
            except:
                logging.info(format_exc(sys.exc_info()))
                logging.info('No single end files submitted')

            try:
                for r in ref:
                    for wordpath in r:
                        filedict = {'type':'reference', 'files':[]}
                        # Parse user directories
                        try:
                            path, word = wordpath.rsplit('/', 1)
                            path += '/'
                        except:
                            word = wordpath
                            path = ''

                        if is_filename(word):
                            baseword = os.path.basename(word)
                            filedict['files'].append(
                                self.download(url, user, token, ids[files.index(baseword)], filepath))
                        else:
                            kv = word.split('=')
                            filedict[kv[0]] = kv[1]
                        all_files.append(filedict)
            except:
                #logging.info(format_exc(sys.exc_info()))
                logging.info('No single end files submitted')

        return datapath, all_files


    def compute(self, body):
        error = False
        params = json.loads(body)
        job_id = params['job_id']
        uid = params['_id']
        user = params['ARASTUSER']
        token = params['oauth_token']
        pipelines = params['pipeline']

        #support legacy arast client
        if len(pipelines) > 0:
            if type(pipelines[0]) is not list:
                pipelines = [pipelines]
                
        ### Download files (if necessary)
        datapath, all_files = self.get_data(body)
        rawpath = datapath + '/raw/'
        jobpath = os.path.join(datapath, str(job_id))
        try:
            os.makedirs(jobpath)
        except:
            raise Exception ('Data Error')

        ### Create job log
        self.out_report_name = '{}/{}_report.txt'.format(jobpath, str(job_id))
        self.out_report = open(self.out_report_name, 'w')

        ### Create data to pass to pipeline
        reads = []
        reference = []
        for fileset in all_files:
            if fileset['type'] == 'single' or fileset['type'] == 'paired':
                reads.append(fileset)
            elif fileset['type'] == 'reference':
                reference.append(fileset)
            else:
                raise Exception('fileset error')

        job_data = ArastJob({'job_id' : params['job_id'], 
                    'uid' : params['_id'],
                    'user' : params['ARASTUSER'],
                    'reads': reads,
                    'reference': reference,
                    'initial_reads': list(reads),
                    'raw_reads': copy.deepcopy(reads),
                    'processed_reads': list(reads),
                    'pipeline_data': {},
                    'datapath': datapath,
                    'out_report' : self.out_report})

        self.out_report.write("Arast Pipeline: Job {}\n".format(job_id))
        
        self.start_time = time.time()
        self.done_flag = threading.Event()
        timer_thread = UpdateTimer(self.metadata, 29, time.time(), uid, self.done_flag)
        timer_thread.start()
        
        download_ids = {}
        url = "http://%s" % (self.shockurl)
        url += '/node'
        try:
            include_all_data = params['all_data']
        except:
            include_all_data = False
        contigs = not include_all_data
        status = ''
        if pipelines:
            try:
                for p in pipelines:
                    self.pmanager.validate_pipe(p)

                result_files, summary= self.run_pipeline(pipelines, job_data, contigs_only=contigs)
                for f in result_files:
                    print f
                    fname = os.path.basename(f).split('.')[0]
                    res = self.upload(url, user, token, f)
                    download_ids[fname] = res['D']['id']

                status += "pipeline [success] "
                self.out_report.write("Pipeline completed successfully\n")
            except:
                traceback = format_exc(sys.exc_info())
                status = "[FAIL] {}".format(sys.exc_info()[1])
                print traceback
                self.out_report.write("ERROR TRACE:\n{}\n".
                                      format(format_tb(sys.exc_info()[2])))

        # Format report
        self.done_flag.set()
        new_report = open('{}.tmp'.format(self.out_report_name), 'w')
        try:
            with open(summary) as s:
                new_report.write(s.read())
        except:
            new_report.write('No Summary File Generated!\n\n\n')
        self.out_report.close()
        with open(self.out_report_name) as old:
            new_report.write(old.read())
        new_report.close()
        os.remove(self.out_report_name)
        shutil.move(new_report.name, self.out_report_name)
        res = self.upload(url, user, token, self.out_report_name)
        download_ids['report'] = res['D']['id']

        # Get location
        self.metadata.update_job(uid, 'result_data', download_ids)
        self.metadata.update_job(uid, 'status', status)


        print '=========== JOB COMPLETE ============'

    def update_time_record(self):
        elapsed_time = time.time() - self.start_time
        ftime = str(datetime.timedelta(seconds=int(elapsed_time)))
        self.metadata.update_job(uid, 'computation_time', ftime)

    def run_pipeline(self, pipes, job_data, contigs_only=True):
        """
        Runs all pipelines in list PIPES
        """
        all_pipes = []
        for p in pipes:
            all_pipes += self.pmanager.parse_input(p)
        logging.info('{} pipelines:'.format(len(all_pipes)))
        for p in all_pipes:
            print '->'.join(p)
        #include_reads = self.pmanager.output_type(pipeline[-1]) == 'reads'
        include_reads = False
        pipeline_num = 1
        all_files = []
        pipe_outputs = []
        logfiles = []
        ale_reports = {}
        final_contigs = []
        final_scaffolds = []
        output_types = []
        num_pipes = len(all_pipes)
        for pipe in all_pipes:
            #job_data = copy.deepcopy(job_data_global)
            #job_data['out_report'] = job_data_global['out_report'] 
            pipeline, overrides = self.pmanager.parse_pipe(pipe)
            job_data.add_pipeline(pipeline_num, pipeline)
            num_stages = len(pipeline)
            pipeline_stage = 1
            pipeline_results = []
            cur_outputs = []

            # Reset job data 
            job_data['reads'] = copy.deepcopy(job_data['raw_reads'])
            job_data['processed_reads'] = []
            print job_data

            self.out_report.write('\n{0} Pipeline {1}: {2} {0}\n'.format('='*15, pipeline_num, pipe))
            pipe_suffix = '' # filename code for indiv pipes
            pipe_start_time = time.time()
            pipe_alive = True

            # Store data record for pipeline

            for module_name in pipeline:
                if not pipe_alive:
                    self.out_report.write('\n{0} Module Failure, Killing Pipe {0}'.format(
                            'X'*10))
                    break
                module_code = '' # unique code for data reuse
                print '\n\n{0} Running module: {1} {2}'.format(
                    '='*20, module_name, '='*(35-len(module_name)))
                self.garbage_collect(self.datapath, job_data['user'], 2147483648) # 2GB

                ## PROGRESS CALCULATION
                pipes_complete = (pipeline_num - 1) / float(num_pipes)
                stage_complete = (pipeline_stage - 1) / float(num_stages)
                pct_segment = 1.0 / num_pipes
                stage_complete *= pct_segment
                total_complete = pipes_complete + stage_complete
                cur_state = 'Running: [{}%]'.format(int(total_complete * 100))
                self.metadata.update_job(job_data['uid'], 'status', cur_state)
                if module_name.lower() == 'none':
                    continue

                ## LOG REPORT For now, module code is 1st and last letter
                short_name = self.pmanager.get_short_name(module_name)
                if short_name:
                    #pipe_suffix += short_name.capitalize()
                    module_code += short_name.capitalize()
                else:
                    #pipe_suffix += module_name[0].upper() + module_name[-1]
                    module_code += module_name[0].upper() + module_name[-1]
                mod_overrides =  overrides[pipeline_stage - 1]
                for k in mod_overrides.keys():
                            #pipe_suffix += '_{}{}'.format(k[0], par[k])
                    module_code += '_{}{}'.format(k[0], mod_overrides[k])
                pipe_suffix += module_code
                self.out_report.write('PIPELINE {} -- STAGE {}: {}\n'.format(
                        pipeline_num, pipeline_stage, module_name))
                logging.debug('New job_data for stage {}: {}'.format(
                        pipeline_stage, job_data))
                job_data['params'] = overrides[pipeline_stage-1].items()
                module_start_time = time.time()
                ## RUN MODULE
                # Check if output data exists
                reuse_data = False
                enable_reuse = True # KILL SWITCH
                if enable_reuse:
                    for k, pipe in enumerate(pipe_outputs):
                        if reuse_data:
                            break
                        if not pipe:
                            continue
                        # Check that all previous pipes match
                        for i in range(pipeline_stage):
                            try:
                                if not pipe[i][0] == cur_outputs[i][0]:
                                    break
                            except:
                                pass
                            try:
                                if (pipe[i][0] == module_code and i == pipeline_stage - 1):
                                    #and overrides[i].items() == job_data['params']): #copy!
                                    print('Found previously computed data, reusing {}.'.format(
                                            module_code))
                                    output = [] + pipe[i][1]
                                    pfix = (k+1, i+1)
                                    alldata = [] + pipe[i][2]
                                    reuse_data = True
                                    job_data.get_pipeline(pipeline_num).get_module(
                                        pipeline_stage)['elapsed_time'] = time.time(
                                        job_data.get_pipeline(i).get_module(
                                                pipeline_stage)['elapsed_time'])
                                        
                                    break
                            except: # Previous pipes may be shorter
                                pass

                output_type = self.pmanager.output_type(module_name)

                if not reuse_data:
                    output, alldata, mod_log = self.pmanager.run_module(
                        module_name, job_data, all_data=True, reads=include_reads)
                    if not output:
                        pipe_alive = False
                        break
                    # Prefix outfiles with pipe stage, only assemblers
                    alldata = [asm.prefix_file_move(
                            file, "P{}_S{}_{}".format(pipeline_num, pipeline_stage, module_name)) 
                                for file in alldata]
                    module_elapsed_time = time.time() - module_start_time
                    job_data.get_pipeline(pipeline_num).get_module(
                        pipeline_stage)['elapsed_time'] = module_elapsed_time
                    if output_type == 'contigs': #Assume assembly contigs
                        pass
                    elif output_type == 'reads':
                        pass
                    if alldata: #If log was renamed
                        mod_log = asm.prefix_file(mod_log, "P{}_S{}_{}".format(
                                pipeline_num, pipeline_stage, module_name))

                if output_type == 'contigs' or output_type == 'scaffolds': #Assume assembly contigs
                    if reuse_data:
                        p_num, p_stage = pfix
                    else:
                        p_num, p_stage = pipeline_num, pipeline_stage

                    # If plugin returned scaffolds
                    if type(output) is tuple and len(output) == 2:
                        out_contigs = output[0]
                        out_scaffolds = output[1]
                        cur_scaffolds = [asm.prefix_file(
                                file, "P{}_S{}_{}".format(p_num, p_stage, module_name)) 
                                    for file in out_scaffolds]
                    else:
                        out_contigs = output
                    cur_contigs = [asm.prefix_file(
                            file, "P{}_S{}_{}".format(p_num, p_stage, module_name)) 
                                for file in out_contigs]
                        
                    #job_data['reads'] = asm.arast_reads(alldata)
                    job_data['contigs'] = cur_contigs
                    
                elif output_type == 'reads': #Assume preprocessing
                    if include_reads and reuse_data: # data was prefixed and moved
                        for d in output:
                            files = [asm.prefix_file(f, "P{}_S{}_{}".format(
                                        pipeline_num, pipeline_stage, module_name)) for f in d['files']]
                            d['files'] = files
                            d['short_reads'] = [] + files
                    job_data['reads'] = output
                    job_data['processed_reads'] = list(job_data['reads'])

                pipeline_results += alldata
                if pipeline_stage == num_stages: # Last stage, add contig for assessment
                    if output: #If a contig was produced
                        fcontigs = cur_contigs
                        rcontigs = [asm.rename_file_symlink(f, 'P{}_{}'.format(
                                    pipeline_num, pipe_suffix)) for f in fcontigs]
                        try:
                            rscaffolds = [asm.rename_file_symlink(f, 'P{}_{}_{}'.format(
                                        pipeline_num, pipe_suffix, 'scaff')) for f in cur_scaffolds]
                            if rscaffolds:
                                scaffold_data = {'files': rscaffolds, 'name': pipe_suffix}
                                final_scaffolds.append(scaffold_data)
                        except:
                            pass
                        contig_data = {'files': rcontigs, 'name': pipe_suffix, 'alignment_bam': []}
                        final_contigs.append(contig_data)
                        output_types.append(output_type)
                

                try:
                    logfiles.append(mod_log)
                except:
                    pass
                pipeline_stage += 1
                
                cur_outputs.append([module_code, output, alldata])
            pipe_elapsed_time = time.time() - pipe_start_time
            pipe_ftime = str(datetime.timedelta(seconds=int(pipe_elapsed_time)))
            job_data.get_pipeline(pipeline_num)['elapsed_time'] = pipe_elapsed_time

            if not output:
                self.out_report.write('ERROR: No contigs produced. See module log\n')
            else:

                ## Assessment
                #self.pmanager.run_module('reapr', job_data)
                #print job_data
                # TODO reapr break may be diff from final reapr align!
                # ale_out, _, _ = self.pmanager.run_module('ale', job_data)
                # if ale_out:
                #     job_data.get_pipeline(pipeline_num).import_ale(ale_out)
                #     ale_reports[pipe_suffix] = ale_out
                pipeline_datapath = '{}/{}/pipeline{}/'.format(job_data['datapath'], 
                                                               job_data['job_id'],
                                                               pipeline_num)
                try:
                    os.makedirs(pipeline_datapath)
                except:
                    logging.info("{} exists, skipping mkdir".format(pipeline_datapath))
                all_files.append(asm.tar_list(pipeline_datapath, pipeline_results, 
                                    'pipe{}_{}.tar.gz'.format(pipeline_num, pipe_suffix)))

            self.out_report.write('Pipeline {} total time: {}\n\n'.format(pipeline_num, pipe_ftime))
            job_data.get_pipeline(pipeline_num)['name'] = pipe_suffix
            pipe_outputs.append(cur_outputs)
            pipeline_num += 1

        job_data['final_contigs'] = final_contigs
        try:
            job_data['final_scaffolds'] = final_scaffolds
        except:
            job_data['final_scaffolds'] = []
        #mfiles,_,_ = self.pmanager.run_module('gam_ngs', job_data)
        # for m in mfiles:
        #     job_data['final_contigs'].append({'files':[m]})

        ## ANALYSIS: Quast
        job_data['contig_types'] = output_types
        job_data['params'] = [] #clear overrides from last stage
        quast_report, quast_tar, z1, q_log = self.pmanager.run_module('quast', job_data, 
                                                                      tar=True, meta=True)
        if job_data['final_scaffolds']:
            print 'Found scaffolds'
            print job_data['final_scaffolds']
            scaff_data = dict(job_data)
            scaff_data['final_contigs'] = job_data['final_scaffolds']
            scaff_report, scaff_tar, _, scaff_log = self.pmanager.run_module('quast', scaff_data, 
                                                                      tar=True, meta=True)
            scaffold_quast = True
        else:
            scaffold_quast = False

        logfiles.append(q_log)

        ## Add reference assessment
        # if job_data['reference']:
        #     ref_data = dict(job_data)
        #     ref_data['contigs'] = job_data['reference'][0]['files']
        #     ref_ale_out, _, _ = self.pmanager.run_module('ale', ref_data)
        #     if ref_ale_out:
        #         job_data.add_pipeline(-1, [])
        #         job_data.get_pipeline(-1).import_ale(ref_ale_out)
        #         job_data.get_pipeline(-1)['name'] = 'REF'
                
        job_data.import_quast(quast_report[0])
        
        ## Write out ALE scores
        # self.out_report.write("\n\n{0} ALE Reports {0}\n".format("="*10))
        # for suffix,report in ale_reports.items():
        #     try:
        #         f = open(report, 'r')
        #         score = f.readline()
        #         f.close()
        #         self.out_report.write("{}: {}\n".format(suffix, score))
        #     except:
        #         self.out_report.write("{}: Error\n".format(suffix))

        # for suffix,report in ale_reports.items():
        #     self.out_report.write("\n\n{0} ALE: {1}  {0}\n".format("="*10, suffix))
        #     try:
        #         with open(report) as infile:
        #             self.out_report.write(infile.read())
        #     except:
        #         self.out_report.write("Error writing log file")

        ## CONCAT MODULE LOG FILES
        self.out_report.write("\n\n{0} Begin Module Logs {0}\n".format("="*10))
        for log in logfiles:
            self.out_report.write("\n\n{0} Begin Module {0}\n".format("="*10))
            try:
                with open(log) as infile:
                    self.out_report.write(infile.read())
            except:
                self.out_report.write("Error writing log file")

        ## Format Returns
        ctg_analysis = quast_tar.rsplit('/', 1)[0] + '/{}_ctg_qst.tar.gz'.format(job_data['job_id'])
        summary = quast_report[0]
        os.rename(quast_tar, ctg_analysis)
        return_files = [ctg_analysis]
        # ale_plot = job_data.plot_ale()
        # if ale_plot:
        #     return_files.append(ale_plot)
        if scaffold_quast:
            scf_analysis = scaff_tar.rsplit('/', 1)[0] + '/{}_scf_qst.tar.gz'.format(job_data['job_id'])
            #summary = quast_report[0]
            os.rename(scaff_tar, scf_analysis)
            return_files.append(scf_analysis)

        contig_files = []
        for data in final_contigs + final_scaffolds:
            for f in data['files']:
                contig_files.append(os.path.realpath(f))

        return_files.append(asm.tar_list('{}/{}'.format(job_data['datapath'], job_data['job_id']),
                            contig_files, '{}_assemblies.tar.gz'.format(
                job_data['job_id'])))
        return return_files, summary


    def upload(self, url, user, token, file):
        files = {}
        files["file"] = (os.path.basename(file), open(file, 'rb'))
        logging.debug("Message sent to shock on upload: %s" % files)
        sclient = shock.Shock(url, user, token)
        res = sclient.curl_post_file(file)
        return res

    def download(self, url, user, token, node_id, outdir):
        sclient = shock.Shock(url, user, token)
        downloaded = sclient.curl_download_file(node_id, outdir=outdir)
        return extract_file(downloaded)

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
        try:
            self.compute(body)
        except:
            params = json.loads(body)
            print sys.exc_info()
            status = "[FAIL] {}".format(format_tb(sys.exc_info()[2]))
            print logging.error(status)
            self.metadata.update_job(params['job_id'], 'status', status)

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
    
def extract_file(filename):
    """ Decompress files if necessary """
    filepath = os.path.dirname(filename)
    supported = ['tar.gz', 'tar.bz2', 'bz2', 'gz', 'lz', 
                 'rar', 'tar', 'tgz','zip']
    for ext in supported:
        if filename.endswith(ext):
            extracted_file = filename[:filename.index(ext)-1]
            if os.path.exists(extracted_file): # Check extracted already
                return extracted_file
            logging.debug("Extracting %s" % filename)
            p = subprocess.Popen(['unp', filename], 
                                 cwd=filepath, stderr=subprocess.STDOUT)
            p.wait()
            if os.path.exists(extracted_file):
                return extracted_file
            else:
                print "{} does not exist!".format(extracted_file)
                raise Exception('Archive structure error')
    logging.debug("Could not extract %s" % filename)
    return filename            

def is_filename(word):
    return word.find('.') != -1 and word.find('=') == -1

def list_io_basenames(job_data):
    """ Lists filenames in JOB_DATA dict """
    basenames = []
    for d in job_data['reads']:
        for f in d['files']:
            basenames.append(os.path.basename(f))
    return basenames

class UpdateTimer(threading.Thread):
    """ Thread for updating time in the mongodb record (for arast stat). """
    def __init__(self, meta_obj, update_interval, start_time, uid, done_flag):
        self.meta = meta_obj
        self.interval = update_interval
        self.uid = uid
        self.start_time = start_time
        self.done_flag = done_flag
        threading.Thread.__init__(self)

    def run(self):
        while True:
            if self.done_flag.is_set():
                print 'Stopping Timer Thread'
                return
            elapsed_time = time.time() - self.start_time
            ftime = str(datetime.timedelta(seconds=int(elapsed_time)))
            self.meta.update_job(self.uid, 'computation_time', ftime)
            time.sleep(self.interval)
