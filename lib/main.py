
import ctypes
#import ctypes.util

#libc = ctypes.CDLL(ctypes.util.find_library("c"))
libc = ctypes.CDLL("libc.so.6")

class object():
    def __init__(self):
        pass
    def __repr__(self):
        return "<" + self.__class__.__name__ + " object>"
        #return "<%s object>" % (self.__class__.__name__,)
    def __str__(self):
        return self.__repr__()

def abs(x):
    return x.__abs__()

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
    x = int(x)
    result = []
    while True:
        result.append('1' if x & 1 else '0')
        x >>= 1
        if not x:
            break
    result.append('0b')
    return ''.join(reversed(result))

#class bool(int):
#    def __new__(x=None):
#        return True if x else False

def chr(i):
    return "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x20\x21\x22\x23\x24\x25\x26\x27\x28\x29\x2a\x2b\x2c\x2d\x2e\x2f\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x3a\x3b\x3c\x3d\x3e\x3f\x40\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f\x60\x61\x62\x63\x64\x65\x66\x67\x68\x69\x6a\x6b\x6c\x6d\x6e\x6f\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79\x7a\x7b\x7c\x7d\x7e\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff"[i]

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

#_no_arg = object()
def dir(object=_no_arg):
    if object is _no_arg:
        pass
    pass

def divmod(a, b):
    # needs to do both
    res = a.__divmod__(b)
    if res is NotImplemented:
        res = b.__rdivmod__(a)
        if res is NotImplemented:
            raise NotImplementedError
    return res

def enumerate(sequence, start=0):
    for item in sequence:
        yield start, item
        start += 1

def eval(expression, globals=None, locals=None):
    pass

def execfile(filename, globals=None, locals=None):
    pass

class file(object):
    def __init__(self, name, mode='r', bufsize=None):
        self.name = name
        if name == "<stdin>":
            self._file = libc.stdin
        elif name == "<stdout>":
            self._file = libc.stdout
        elif name == "<stderr>":
            self._file = libc.stderr
        else:
            self._file = libc.fopen(name, mode)
            if not self._file:
                assert False, "could not open file!"
    def read(self, size=None):
        if size is None:
            size = 1000000
        res = ctypes.create_string_buffer(size)
        actual = libc.fread(res, 1, size, self._file)
        return res.raw[:actual]
        #print "AHH", size
        #if size is None:
        #    l = []
        #    while True:
        #        l.append(self.read(2**16))
        #        if len(l[-1]) < 2**16:
        #            break
        #    return ''.join(l)
        #print "c"
        #res = ctypes.create_string_buffer(size)
        #print "d"
        #actual = libc.fread(res, 1, size, self._file)
        #print "b"
        #return res.raw[:actual]
    def readline(self):
        def _():
            while True:
                c = self.read(1)
                if not c:
                    return
                yield c
                if c == "\n":
                    return
        return ''.join(_())

    def write(self, data):
        libc.fwrite(self._file, 1, len(data), data)

def filter(function, iterable):
    if function is None:
        for element in iterable:
            if element:
                yield element
    else:
        for element in iterable:
            if function(element):
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

class module(object):
    pass

def __import__(name):
    exec open(a).read()

class listiterator(object):
    def __init__(self, parent):
        self.parent = parent
        self.pos = 0
    def __iter__(self):
        return self
    def __length_hint__(self):
        return len(self.parent)
    def next(self):
        if self.pos >= len(self.parent):
            raise StopIteration()
        res = self.parent[self.pos]
        self.pos += 1
        return res

def map(f, iterable):
    res = []
    i = 0
    j = iterable.__len__()
    while i < j:
        res.append(f(iterable[i]))
        i += 1
    return res

def chr(i):
    return "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x20\x21\x22\x23\x24\x25\x26\x27\x28\x29\x2a\x2b\x2c\x2d\x2e\x2f\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x3a\x3b\x3c\x3d\x3e\x3f\x40\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f\x60\x61\x62\x63\x64\x65\x66\x67\x68\x69\x6a\x6b\x6c\x6d\x6e\x6f\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79\x7a\x7b\x7c\x7d\x7e\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff"[i]

def ord(i):
    return i.__ord__()


class list(object):
    def __init__(self, iterable=None):
        self._used = 0
        self._allocated = 0
        if iterable is not None:
            for item in iterable:
                self.append(item)
    def __len__(self):
        return self._used
    def __iter__(self):
        return listiterator(self)
    def _grow(self):
        new_allocated = self._allocated * 2 + 1
        import _pyable
        new_store = _pyable.raw(4 * new_allocated)
        if self._used:
            new_store.copy_from(self._store, 4 * self._used)
        self._allocated = new_allocated
        self._store = new_store
    def append(self, item):
        if self._used + 1 > self._allocated:
             self._grow()
        self._store.store_object(4 * self._used, item)
        self._used += 1
        return self
    def __getitem__(self, index):
        if index < 0:
            index += self._used
        if index >= self._used:
            return None
        return self._store.load_object(4 * index)
    def __setitem__(self, index, item):
        if index < 0:
            index += self._used
        if index >= self._used:
            return None
        self._store.store_object(4 * index, item)
    def pop(self, index=-1):
        if index < 0:
            index += self._used
        if index < 0 or index >= self._used:
            return None
        res = self._store.load_object(4 * index)
        i = 4 * index
        while i + 4 < 4 * self._used:
            self._store[i] = self._store[i + 4]
            t += 1
        self._used -= 1
        return res
    def __mul__(self, other):
        new = self.__class__()
        i = 0
        while i < other:
            j = 0
            while j < self._used:
                new.append(self[j])
                j += 1
            i += 1
        return new
import _pyable
_pyable.set_list_impl(list)

def len(o):
    return o.__len__()

def eval(s):
    return _pyable.eval(s)

stdin = open("<stdin>")

class Exception(object):
    pass

class StopIteration(Exception):
    pass
_pyable.set_StopIteration_impl(StopIteration)

def input():
    return eval(raw_input())

def raw_input():
    return stdin.readline()

if len(_pyable.args):
    a = _pyable.args[0]
    try:
        exec open(a).read()
    except Exception, e:
        print "error! D:", e
else:
    while True:
        exec raw_input()

if 0:
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


