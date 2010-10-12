import ctypes

libc = ctypes.CDLL("libc.so.6")

#libc.clock.restype = ctypes.c_longlong

def clock():
    return libc.clock()/1000000.

if __name__ == "__main__":
    print clock()
    for i in xrange(10000000): continue
    print clock()
