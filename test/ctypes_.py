import ctypes

ctypes.CDLL("libc.so.6").putchar(104)
ctypes.CDLL("libc.so.6").putchar(10)
