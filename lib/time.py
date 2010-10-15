import ctypes

libc = ctypes.CDLL("libc.so.6")

#libc.clock.restype = ctypes.c_longlong

def clock():
    return 1e-6 * libc.clock()

def sleep(seconds):
    libc.usleep(int(1000000 * seconds))

def time():
    b = ctypes.create_string_buffer(16)
    libc.gettimeofday(b, None)
    return b.int_at(0) + 1e-6 * (b.int_at(8) & 0xffffffff)

if __name__ == "__main__":
    def main():
        print time()  
        print clock()
        for i in xrange(100000000):
            continue
        print clock()
    main()
    for i in xrange(10):
        print time()
        sleep(1)
