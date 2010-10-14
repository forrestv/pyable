import ctypes

libc = ctypes.CDLL("libc.so.6")

#libc.clock.restype = ctypes.c_longlong

def clock():
    return libc.clock()/1000000.

if __name__ == "__main__":
  def main():
    print clock()
    for i in xrange(100000000): continue
    print clock()
  main()
