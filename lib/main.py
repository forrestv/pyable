import ctypes
#import ctypes.util

#libc = ctypes.CDLL(ctypes.util.find_library("c"))
libc = ctypes.CDLL("libc.so.6")

class file(object):
    def __init__(self, a):
        print "a", a, a.__len__()


a = "afff"
print "a", a, a.__len__()
file(a)

