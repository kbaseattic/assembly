class FileInfo(dict):
    def __init__(self, filename, shock_url=None, shock_id=None, name=None,
                 filesize=None, create_time=None, metadata=None, *args):
        dict.__init__(self, *args)
        self.update({'shock_url': shock_url,
                     'shock_id' : shock_id,
                     'filesize': filesize,
                     'filename': filename,
                     'create_time': create_time,
                     'metadata': metadata})

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

