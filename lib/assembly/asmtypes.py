import os
import uuid

### arast ###
import client
import assembly


#### Single Files #####
class FileInfo(dict):
    def __init__(self, filename=None, shock_url=None, shock_id=None, name=None,
                 create_time=None, metadata=None, direct_url=None, keep_name=False, *args):
        dict.__init__(self, *args)
        if filename:
            assert os.path.exists(filename)
            filesize = os.path.getsize(filename)
            fname = os.path.basename(filename)
        else:
            filesize = None
            fname = None
        self.update({'direct_url': direct_url,
                     'shock_url': shock_url,
                     'shock_id' : shock_id,
                     'filesize': filesize,
                     'filename': fname,
                     'local_file': filename,
                     'keep_name': keep_name,
                     'create_time': create_time,
                     'metadata': metadata})
        self.id = uuid.uuid4()

    # def fetch_file(self, outdir=None):
    #     """ If file has a direct_url, download the file"""
    #     downloaded = assembly.curl_download_url(self.direct_url, outdir=outdir)
    #     self.update({'filesize': os.path.getsize(downloaded),
    #                  'filename': os.path.basename(self.direct_url),
    #                  'local_file': downloaded})

##### Set of Files ######
class FileSet(dict):
    def __init__(self, set_type, file_infos,
                 **kwargs):
        dict.__init__(self)
        self.update({'type': set_type,
                     'file_infos': [],
                     'tags': []})
        self.update(kwargs)
        self.id = uuid.uuid4()
        if type(file_infos) is list:
            for f in file_infos:
                self['file_infos'].append(f)
        else:
            self['file_infos'] = [file_infos]

    @property
    def files(self):
        """ Returns file paths of all files in set"""
        return [f['local_file'] for f in self['file_infos']]

    @property
    def shock_nodes(self):
        return [fi['shock_id'] for fi in self['file_infos']]

    @property
    def name(self):
        return self.get('name')

    @property
    def type(self):
        return self.get('type')

    def add_tag(self, tag):
        if not tag in self['tags']:
            self['tags'].append(tag)

    def update_files(self, files):
        self['file_infos'] = [FileInfo(f) for f in files]

    def update_fileinfo(self, fileinfos):
        self['file_infos'] = fileinfos


class ReadSet(FileSet):
    def __init__(self, set_type, file_infos,  **kwargs):
        self['insert'] = None
        self['stdev'] = None
        FileSet.__init__(self, set_type, file_infos, **kwargs)
        self.__dict__.update(kwargs)
        self['type'] = set_type

    @property
    def insert(self):
        return self['insert']

    @property
    def stdev(self):
        return self['stdev']

    def is_long_read(self):
        return 'long_read' in self['tags']


class ContigSet(FileSet):
    def __init__(self, set_type, file_infos,  **kwargs):
        FileSet.__init__(self, set_type, file_infos, **kwargs)
        self.__dict__.update(kwargs)

class ScaffoldSet(FileSet):
    def __init__(self, set_type, file_infos,  **kwargs):
        FileSet.__init__(self, set_type, file_infos, **kwargs)
        self.__dict__.update(kwargs)

class ReferenceSet(FileSet):
    def __init__(self, set_type, file_infos,  **kwargs):
        FileSet.__init__(self, set_type, file_infos, **kwargs)
        self.__dict__.update(kwargs)
        assert len(file_infos) < 2

def set_factory(set_type, file_infos, keep_name=False, **kwargs):
    """
    Creates a particular FileSet (e.g ReadSet) depending on set_type.
    file_infos is a list of filepaths, FileInfos, or a FileSet.
    If file_infos is a FileSet, it will convert it to the correct class
    according to set_type.
    """

    if isinstance(file_infos, FileSet):
        file_infos = file_infos['file_infos']
    elif type(file_infos) is not list:
        file_infos = [file_infos]
    for i,f in enumerate(file_infos):
        if type(f) is not FileInfo and os.path.exists(f):
            file_infos[i] = FileInfo(f, keep_name=keep_name)

    if set_type in ['paired', 'single']:
        return ReadSet(set_type, file_infos, **kwargs)
    elif set_type == 'contigs':
        return ContigSet(set_type, file_infos, **kwargs)
    elif set_type == 'scaffolds':
        return ScaffoldSet(set_type, file_infos, **kwargs)
    elif set_type == 'reference':
        return ReferenceSet(set_type, file_infos, **kwargs)
    else:
        return FileSet(set_type, file_infos, **kwargs)


#### All Filesets #####
class FileSetContainer(dict):
    def __init__(self, filesets=None):
        self.filesets = filesets if filesets else []

    def find_type(self, set_type):
        return [fileset for fileset in self.filesets if fileset['type'] == set_type]

    def find(self, id):
        for fileset in self.filesets:
            if fileset.id == id: return fileset

    def find_and_update(self, id, newdict):
        self.find(id).update(newdict)

    def __repr__(self):
        return str(self.filesets)

    def __str__(self):
        return str(self.filesets)

    @property
    def readsets(self):
        """ Returns a list of all ReadSet objects"""
        return [fileset for fileset in self.filesets if type(fileset) is ReadSet]

    @property
    def readsets_paired(self):
        """ Returns a list of all paired-end  ReadSet objects"""
        return [readset for readset in self.readsets if readset['type'] == 'paired']

    @property
    def readsets_single(self):
        """ Returns a list of all single-end  ReadSet objects"""
        return [readset for readset in self.readsets if readset['type'] == 'single']

    @property
    def readfiles(self):
        return [readfile for readset in self.readsets for readfile in readset.files]

    @property
    def readfiles_paired(self):
        return [readfile for readset in self.readsets_paired for readfile in readset.files]

    @property
    def readfiles_single(self):
        return [readfile for readset in self.readsets_single for readfile in readset.files]

    @property
    def contigsets(self):
        """ Returns a list of all ContigSet objects"""
        return [fileset for fileset in self.filesets if type(fileset) is ContigSet]

    @property
    def contigfiles(self):
        return [contigfile for contigset in self.contigsets for contigfile in contigset.files]

    @property
    def scaffoldsets(self):
        """ Returns a list of all ScaffoldSet objects"""
        return [fileset for fileset in self.filesets if type(fileset) is ScaffoldSet]

    @property
    def scaffoldfiles(self):
        return [scaffoldfile for scaffoldset in self.scaffoldsets for scaffoldfile in scaffoldset.files]

    @property
    def referencesets(self):
        """ Returns a list of all ReferenceSet objects"""
        return [fileset for fileset in self.filesets if type(fileset) is ReferenceSet]

    @property
    def referencefiles(self):
        return [referencefile for referenceset in self.referencesets for referencefile in referenceset.files]

    @property
    def bamfiles(self):
        pass


def filepaths(filesets):
    """ Return a list of filepaths from list of FileSets """
    filepaths = []
    for fs in filesets:
        filepaths += fs.files
    return filepaths



######## ARAST EXCEPTIONS #########

class ArastUserInterrupt(BaseException):
    pass

class ArastDataInputError(Exception):
    pass

class ArastDataOutputError(Exception):
    pass

class ArastClientRequestError(Exception):
    pass
