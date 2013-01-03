import abc
import logging 
import os
import uuid

class BasePlugin(object):
    """ 
    job_data dictionary contains:
    - job_id
    - uid
    - reads: list of tuples eg. [('/data/unpaired.fa,), ('/data/1a.fa', '/data/1b.fa')]
    """
        
    def create_directories(self, job_data):
        datapath = job_data['datapath'] + '/' + str(job_data['job_id']) + '/' + self.name + '_' + str(uuid.uuid4())
        logging.info("Creating directory: {}".format(datapath))
        os.makedirs(datapath)
        return datapath

    def init_settings(self, settings):
        for kv in settings:
            setattr(self, kv[0], kv[1])

    def run_checks(self, settings, job_data):
        logging.info("Doing checks")
        #Check binary exists
        #Check data is valid
        pass

    def tar(self, files):
        pass

    def update_status(self):
        pass

    
class BaseAssembler(BasePlugin):
    def __call__(self, settings, job_data):
        self.run_checks(settings, job_data)
        logging.info("{} Settings: {}".format(self.name, settings))
        self.init_settings(settings)
        outpath = self.create_directories(job_data)
        valid_files = self.get_valid_reads(job_data)
        job_data['reads'] = valid_files
        data, tarfile, report = self.run(settings, job_data, outpath)

    def get_valid_reads(self, job_data):
        filetypes = self.filetypes.split(',')
        filetypes = ['.' + filetype for filetype in filetypes]
        valid_files = []
        for filetype in filetypes:
            for file in job_data['reads']:
                if file[0].find(filetype) != -1:
                    f1 = file[0]
                    try:
                        f2 = file[1]
                        files = (f1,f2)
                    except:
                        files = (f1,)
                    valid_files.append(files)
        return valid_files
