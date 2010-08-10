import ctypes
import ctypes.util

libc = ctypes.CDLL(ctypes.util.find_library("c"))

def abs(x):
    if x < 0:
        return -x
    return x

def all(iterable):
    for element in iterable:
        if not element:
            return False
    return True

def any(iterable):
    for element in iterable:
        if element:
            return True
    return False

def bin(x):
    result = []
    while x:
        result.append(x & 1)
        x >>= 1
    result.append('0b')
    return ''.join(reversed(result))

class bool(int):
    def __new__(x=None):
        return True if x else False

_chrs = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x20\x21\x22\x23\x24\x25\x26\x27\x28\x29\x2a\x2b\x2c\x2d\x2e\x2f\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x3a\x3b\x3c\x3d\x3e\x3f\x40\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f\x60\x61\x62\x63\x64\x65\x66\x67\x68\x69\x6a\x6b\x6c\x6d\x6e\x6f\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79\x7a\x7b\x7c\x7d\x7e\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff"

def chr(i):
    return _chrs[i]

def classmethod(function):
    pass

def cmp(x, y):
    pass

def compile(source, filename, mode, flags=0, dont_inherit=0):
    pass

def complex(real=0., imag=0.):
    pass

def delattr(object, name):
    pass

class dict(object):
    pass

_no_arg = object()
def dir(object=_no_arg):
    if object is _no_arg:
        pass
    pass

def divmod(a, b):
    pass

def enumerate(sequence, start=0):
    for item in sequence:
        yield start, item
        start += 1

def eval(expression, , globals=None, locals=None):
    pass

def execfile(filename, globals=None, locals=None):
    pass

class file(object):
    def __init__(self, name, mode='r', bufzise=None):
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

def filter(function, iterable):
    for element in iterable:
        if (function is not None and function(element)) or (function is None and element):
            yield element

class float(object):
    pass

def format(value, format_spec=None):
    pass

class frozenset(object):
    def __init__(self, iterable=None):
        pass

def getattr(object, name, default=_no_arg):
    pass

def globals():
    pass

def hasattr(object, name):
    pass

def hash(object):
    return object.__hash__()

def help(object=_no_arg):
    pass

def hex(x):
    pass

def id(x):
    pass

def input(prompt=None):
    pass

class int(object):
    pass

def isinstance(object, classinfo):
    return issubclass(type(object), classinfo)

def issubclass(class_, classinfo):
    # mod check
    pass

def iter(o, sentinel):
    pass

def open(name, mode='r', buffering=None):
    return file(name, mode, buffering)

class list(object):
    def __init__(self, elements=None):
        self._length = 0
        self._allocated = 0
        self._pointer = 0
        if elements is not None:
            for element in elements:
                self.append(element)
    def append(self, element):
        if self._length + 1 > self._allocated:
            self._allocated = self._allocated * 2 + 1
            self._pointer = libc.realloc(self._pointer, self._allocated * 16)
        ctypes.write(self._pointer + self._length * 16, type(element))
        ctypes.write(self._pointer + self._length * 16 + 8, element)
    def __getitem__(self, element):
        return 

def range(start, end=None, step=1):
    assert step
    if end is None:
        end = start
        start = 0
    result = []
    i = start
    while (i < end and step > 0) or (i > end and step < 0):
        result.append(i)
        i += step
    return result

def xrange(start, end=None, step=1):
    assert step
    if end is None:
        end = start
        start = 0
    i = start
    while (i < end and step > 0) or (i > end and step < 0):
        yield i
        i += step

if __name__ == "__main__":
    import random
    
    # range
    for i in xrange(1000):
        a = random.randrange(-1000, 1000)
        assert range(a) == oldrange(a)

    for i in xrange(1000):
        a = random.randrange(-1000, 1000)
        b = random.randrange(-1000, 1000)
        assert range(a, b) == oldrange(a, b)

    for i in xrange(1000):
        a = random.randrange(-1000, 1000)
        b = random.randrange(-1000, 1000)
        c = random.randrange(-1000, 1000)
        while c == 0:
            c = random.randrange(-1000, 1000)
        assert range(a, b, c) == oldrange(a, b, c)
    
    # file
    f = open(__file__)
    l = f.read(10)
    assert len(l) == 10, l
    while True:
        l = f.read(10)
        if len(l) < 10:
            break
    f = open(__file__)
    print f.read()
