import ctypes

libc = ctypes.CDLL("libc.so.6")

class ExecParams(object):
    p1 = p2 = p3 = p4 = p5 = p6 = 0

libc.mprotect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]

class Error(Exception):
    pass

def make_executable(addr, size):
    if libc.mprotect(addr, size, 0x7):
        raise Error()

func_type = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong)

def execute_int(addr, params):
    return ctypes.cast(addr, func_type)(params.p1, params.p2, params.p3, params.p4, params.p5, params.p6)
