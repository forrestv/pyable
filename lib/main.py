import ctypes
import __pyable__
#import ctypes.util

#libc = ctypes.CDLL(ctypes.util.find_library("c"))
libc = ctypes.CDLL("libc.so.6")

class object():
    def __init__(self):
        pass
    def __len__(self):
        raise TypeError("object of type '" + self.__class__.__name__ + "' has no len()!")
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
    if i < 0 or i >= 256:
        raise ValueError("chr() arg not in range(256)")
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
        self._file = libc.fopen(name, mode)
        if not self._file:
            raise IOError("could not open " + name)
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
        #def _():
        #    while True:
        #        c = self.read(1)
        #        if not c:
        #            return
        #        yield c
        #        if c == "\n":
        #            return
        #return ''.join(_())
        r = ""
        while True:
            c = libc.fgetc(self._file)
            if c > 1000000:
                return r
            c = chr(c)
            r += c
            if c == '\n':
                return r

    def write(self, data):
        libc.fwrite(data, 1, len(data), self._file)
    def flush(self):
        libc.fflush(self._file)

class file_from_fileno(file):
    def __init__(self, fileno, name, mode):
        self.name = name
        self._file = libc.fdopen(fileno, mode)
        if not self._file:
            assert False, "could not open file!"

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

def repr(object):
    return object.__repr__()

def str(object):
    return object.__str__()

def hex(x):
    return object.__hex__()

def id(x):
    pass

def input(prompt=None):
    pass

def int(object):
    return object.__int__()

def isinstance(object, classinfo):
    return issubclass(type(object), classinfo)

def issubclass(class_, classinfo):
    # mod check
    pass

def iter(o, sentinel):
    return o.__iter__()

def open(name, mode='r', buffering=None):
    return file(name, mode, buffering)

def range(start, end=None, step=1):
    assert step != 0, "range step != 0"
    if end is None:
        end = start
        start = 0
    result = []
    i = start
    while (i < end and step > 0) or (i > end and step < 0):
        result.append(i)
        i += step
    return result

class rangeiterator(object):
    pass

class rangeiteratordown(rangeiterator):
    def __init__(self, start, end, step):
        assert step < 0
        self.pos = start
        self.end = end
        self.step = step
    def __iter__(self):
        return self
    def __length_hint__(self):
        if self.end >= self.pos:
            return 0
        return (self.pos - self.end - 1)//-self.step + 1
    def next(self):
        old = self.pos
        if old <= self.end:
            raise StopIteration()
        self.pos = old + self.step
        return old

class rangeiteratorup(rangeiterator):
    def __init__(self, start, end, step):
        assert step > 0
        self.pos = start
        self.end = end
        self.step = step
    def __iter__(self):
        return self
    def __length_hint__(self):
        if self.end <= self.pos:
            return 0
        return (self.end - self.pos - 1)//self.step + 1
    def next(self):
        old = self.pos
        if old >= self.end:
            raise StopIteration()
        self.pos = old + self.step
        return old

class xrange(object):
    def __init__(self, start, end=None, step=1):
        assert step != 0, "xrange step != 0"
        if end is None:
            end = start
            start = 0
        self.start = start
        self.end = end
        self.step = step
    def __iter__(self):
        if self.step > 0:
            return rangeiteratorup(self.start, self.end, self.step)
        else:
            return rangeiteratordown(self.start, self.end, self.step)

#def xrange(start, end=None, step=1):
#    assert step != 0, "xrange step != 0"
#    if end is None:
#        end = start
#        start = 0
#    i = start
#    while (i < end and step > 0) or (i > end and step < 0):
#        yield i
#        i += step

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
    for item in iterable:
        res.append(f(item))
    return res

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
        new_store = __pyable__.raw(4 * new_allocated)
        if self._used:
            new_store.copy_from(self._store, 4 * self._used)
        self._allocated = new_allocated
        self._store = new_store
    def append(self, item):
        if self._used + 1 > self._allocated:
             self._grow()
        self._store.store_object(4 * self._used, item)
        self._used += 1
    def __getitem__(self, index):
        try:
            index.real
        except:
            return self*1
        if index < 0:
            index += self._used
        if index < 0 or index >= self._used:
            raise IndexError()
        return self._store.load_object(4 * index)
    def __setitem__(self, index, item):
        if index < 0:
            index += self._used
        if index < 0 or index >= self._used:
            raise IndexError()
        self._store.store_object(4 * index, item)
    def pop(self, index=-1):
        if index < 0:
            index += self._used
        if index < 0 or index >= self._used:
            raise IndexError()
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
    def __repr__(self):
        r = '['
        first = True
        for item in self:
            if not first:
                r += ', '
            r += item.__repr__()
            first = False
        r += ']'
        return r
    def __add__(self, other):
        res = []
        for item in self:
            res.append(item)
        for item in other:
            res.append(item)
        return res
    def __contains__(self, other):
        for item in self:
            if item == other:
                return True
        return False
__pyable__.set_list_impl(list)

class dict(object):
    def __init__(self):
        self._len = 0
        self._table = [[], [], [], []]
    def __len__(self):
        return self._len
    def __iter__(self):
        return dictiterator(self)
    def _grow(self):
        new_table = []
        for i in xrange(len(self._table) * 2):
            new_table.append([])
        
        new_allocated = self._allocated * 2 + 1
        new_store = __pyable__.raw(4 * new_allocated)
        if self._used:
            new_store.copy_from(self._store, 4 * self._used)
        self._allocated = new_allocated
        self._store = new_store
    def __getitem__(self, index):
        h = index.__hash__()
        l = self._table[h % self._table.__len__()]
        for i in xrange(len(l)):
            if l[i][0] == index:
                return l[i][1]
        raise KeyError()
    def __setitem__(self, index, item):
        h = index.__hash__()
        l = self._table[h % self._table.__len__()]
        for i in xrange(len(l)):
            if l[i][0] == index:
                l[i] = (index, item)
                break
        else:
            l.append((index, item))
    def __contains__(self, index):
        h = index.__hash__()
        l = self._table[h % self._table.__len__()]
        for i in xrange(len(l)):
            if l[i][0] == index:
                return True
        return False
__pyable__.set_dict_impl(dict)

def len(o):
    return o.__len__()

def eval(s):
    exec "return " + s
    #return __pyable__.eval(s)

type = __pyable__.type

class BaseException(object):
    pass

class Exception(BaseException):
    def __init__(self, message=None):
        self.message = message
    def __repr__(self):
        if self.message is None:
            return self.__class__.__name__ + "()"
        else:
            return self.__class__.__name__ + "(" + repr(self.message) + ")"

class StopIteration(Exception):
    pass
__pyable__.set_StopIteration_impl(StopIteration)

class StandardError(Exception):
    pass

class TypeError(StandardError):
    pass
__pyable__.set_TypeError_impl(TypeError)

class SyntaxError(StandardError):
    pass
__pyable__.set_SyntaxError_impl(SyntaxError)

class ImportError(StandardError):
    pass

class ValueError(StandardError):
    pass

class EOFError(StandardError):
    pass

class AssertionError(Exception):
    pass
__pyable__.set_AssertionError_impl(AssertionError)

class AttributeError(Exception):
    pass
__pyable__.set_AttributeError_impl(AttributeError)

class NameError(Exception):
    pass
__pyable__.set_NameError_impl(NameError)

class KeyError(Exception):
    pass

class IndexError(Exception):
    pass

class EnvironmentError(Exception):
    pass

class IOError(EnvironmentError):
    pass


class module(object):
    __pyable__inline__ = True
    def __init__(self, name):
        self.__name__ = name
    def __repr__(self):
        return "<module '" + self.__name__ + "'>"

sys = module('sys')
sys.modules = {}
sys.modules['sys'] = sys
sys.stdin = file_from_fileno(0, '<stdin>', 'r')
sys.stdout = file_from_fileno(1, '<stdout>', 'w')
sys.stderr = file_from_fileno(2, '<stderr>', 'w')
sys.argv = __pyable__.args
sys.path = []
sys.path.append("lib/")
sys.path.append("/usr/lib/python2.6/")
sys.path.append("test/")
sys.builtin_module_names = ['posix'] # keep os happy
__pyable__.set_SysModule_impl(sys)

def __import__(name):
    if name in sys.modules:
        return sys.modules[name]
    for path in sys.path:
        try:
            f = open(path + name + ".py")
        except IOError:
            continue
        f = f.read()
        r = module(name)
        sys.modules[name] = r
        r.__doc__ = None
        r.__package__ = None
        exec f in __pyable__.top_scope, r.__dict__
        return r
    else:
        raise ImportError(name)
    assert False

def input():
    return eval(raw_input())

def raw_input(prompt=None):
    if prompt is not None:
        sys.stdout.write(prompt)
        sys.stdout.flush()
    r = sys.stdin.readline()
    if not r:
        raise EOFError()
    return r

class property(object):
    __pyable__inline__ = True
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.__doc__ = doc

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self         
        if self.fget is None:
            raise AttributeError, "unreadable attribute"
        return self.fget(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError, "can't set attribute"
        self.fset(obj, value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError, "can't delete attribute"
        self.fdel(obj)
    
    def getter(self, fget):
        self.fget = fget
        return self
    
    def setter(self, fset):
        self.fset = fset
        return self
    
    def deleter(self, fdel):
        self.fdel = fdel
        return self

class complex(object):
    __slots__ = {
        "real": "const",
        "imag": "const",
    }
    def __init__(real, imag):
        self.real = real
        self.imag = imag

r = module("__main__")
sys.modules["__main__"] = r
r.__doc__ = None
r.__package__ = None
if len(sys.argv):
    try:
        exec open(sys.argv[0]).read() in __pyable__.top_scope, r.__dict__
    except Exception, e:
        print "error:", e
else:
    print "pyAble SVN"
    print "Be careful!"
    while True:
        try:
            _line = raw_input(">>> ")
            if _line == "":
                print
                break
            exec _line in __pyable__.top_scope, r.__dict__
        except Exception, e:
            try:
                print "error:", e
            except:
                print "exception caught printing exception! here be dragons!"
