import ctypes

func_type = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong)

_SC_PAGESIZE = 30
PROT_READ = 1
PROT_WRITE = 2
PROT_EXECUTE = 4

libc = ctypes.CDLL("libc.so.6")
libc.mprotect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
libc.sysconf.restype = ctypes.c_long

class Error(Exception):
    pass

class ExecParams(object):
    p1 = p2 = p3 = p4 = p5 = p6 = 0

def make_executable(addr, size):
    pagesize = libc.sysconf(_SC_PAGESIZE)
    if pagesize <= 0:
        raise Error()
    gap = addr % pagesize
    if libc.mprotect(addr - gap, size + gap, PROT_READ | PROT_WRITE | PROT_EXECUTE):
        raise Error()

def execute_int(addr, params):
    return ctypes.cast(addr, func_type)(params.p1, params.p2, params.p3, params.p4, params.p5, params.p6)
