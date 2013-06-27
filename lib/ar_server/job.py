class ArastJob(dict):
    """
    store runtimes, scores, files
    pipeline data: name, modules, files, times, 
    """
    def __init__(self, *args):
        dict.__init__(self, *args)
        self.pipeline_data = {}

    def plot(self):
        pass

    def export(self):
        pass
