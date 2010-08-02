class cdict(dict):
    def __init__(self, getter):
        dict.__init__(self)
        self.getter = getter
    def __missing__(self, item):
        self[item] = self.getter(item)
        return item
