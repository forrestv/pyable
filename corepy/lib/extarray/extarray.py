import array

class extarray(array.array):
    def __init__(self, *args, **kwargs):
        array.array.__init__(self)
        self.references = []

class extbuffer(object):
    pass
