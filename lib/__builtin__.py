import ctypes
import ctypes.util

libc = ctypes.CDLL(ctypes.util.find_library("c"))

class file(object):
    def __init__(self, name, mode='r', buffering=None):
        self._file = libc.fopen(name, mode)
    def read(self, size=None):
        if size is None:
            l = []
            while True:
                l.append(self.read(2**16))
                if len(l[-1]) < 2**16:
                    break
            return ''.join(l)
        res = ctypes.create_string_buffer(size)
        actual = libc.fread(res, 1, size, self._file)
        return res.raw[:actual]

def open(name, mode='r', buffering=None):
    return file(name, mode, buffering)

if __name__ == "__main__":
    f = open(__file__)
    l = f.read(10)
    assert len(l) == 10, l
    while True:
        l = f.read(10)
        if len(l) < 10:
            break
    f = open(__file__)
    print f.read()
