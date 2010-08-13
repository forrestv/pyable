import ctypes

c = ctypes.CDLL("libc.so.6")

c.putchar(104)
c.putchar(10)
