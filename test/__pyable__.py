old_type = type
type = lambda n, b, d: old_type(n, () if b is None else b, {} if d is None else d)

type_number = None

import random

raw = lambda n: list(random.randrange(-2**63, 2**63) for i in xrange(n))

class raw(list):
    def __init__(self, length):
        for i in xrange(length):
            self.append(random.randrange(-2**63, 2**63))
            #self.append(None)
    def store_object(self, index, item):
        self[index] = item
    def load_object(self, index):
        return self[index]
    def copy_from(self, other, length):
        assert len(self) >= length
        assert len(other) >= length
        self[:length] = other

def set_list_impl(x):
    pass
