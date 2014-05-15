import os

#### Single Files #####
class FileInfo(dict):
    def __init__(self, filename, shock_url=None, shock_id=None, name=None,
                 filesize=None, create_time=None, metadata=None, *args):
        dict.__init__(self, *args)
        self.update({'shock_url': shock_url,
                     'shock_id' : shock_id,
                     'filesize': filesize,
                     'filename': os.path.basename(filename),
                     'local_file': filename,
                     'create_time': create_time,
                     'metadata': metadata})




##### Set of Files ######
class FileSet(dict):
    def __init__(self, set_type, file_infos, 
                 **kwargs):
        dict.__init__(self, **kwargs)
        self.update({'type': set_type,
                     'file_infos': []})
        if type(file_infos) is list:
            for f in file_infos:
                self['file_infos'].append(f)
        else:
            self['file_infos'] = [file_infos]

    @property
    def files(self):
        """ Returns file paths of all files in set"""
        return [f['local_file'] for f in self['file_infos']]


class ReadSet(FileSet):
    def __init__(self, set_type, file_infos,  **kwargs):
        FileSet.__init__(self, set_type, file_infos, **kwargs)
        self.__dict__.update(kwargs)

    @property
    def insert_len(self):
        return self.insert or None

def set_factory(set_type, file_infos, **kwargs):
    if set_type in ['paired', 'single']:
        return ReadSet(set_type, file_infos, **kwargs)
    else:
        return FileSet(set_type, file_infos, **kwargs)


#### All Filesets #####
class FileSetContainer(dict):
    def __init__(self, filesets=None):
        self.filesets = filesets if filesets else []

    @property
    def readsets(self):
        return [fileset for fileset in self.filesets if type(fileset) is ReadSet]

    @property
    def readsets_paired(self):
        return [readset for readset in self.readsets if readset['type'] == 'paired']

    @property
    def readsets_single(self):
        return [readset for readset in self.readsets if readset['type'] == 'single']
    
    @property
    def contigs(self):
        pass

    @property
    def reference(self):
        pass

    @property
    def bamfiles(self):
        pass


def filepaths(filesets):
    """ Return a list of filepaths from list of FileSets """
    filepaths = []
    for fs in filesets:
        filepaths += fs.files
    return filepaths

