import ctypes
import os
import traceback
import struct
import ast

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
import corepy.arch.x86_64.platform as platform

class Program(platform.Program):
    def __init__(self, *args, **kwargs):
        platform.Program.__init__(self, *args, **kwargs)
        self.references = set()
    def cache_code(self):
        platform.Program.cache_code(self)
        self.render_code.references = self.references # shared, not copied

class BareProgram(Program):
    def _synthesize_prologue(self):
        self._prologue = []
    def _synthesize_epilogue(self):
        self._epilogue = []

class cdict(dict):
    def __init__(self, getter):
        dict.__init__(self)
        self.getter = getter
    def __missing__(self, item):
        self[item] = value = self.getter(item)
        return value

class fake_int(long):
    def __lt__(self, other):
        # alters corepy.arch.x86_64.isa.x86_64_fields.x86ImmediateOperand.fits
        if other == 4294967296:
            return False
        return not self >= other

def get_call(addr):
    program = BareProgram()
    code = program.get_stream()
    code += isa.mov(registers.rax, fake_int(addr))
    code += isa.call(registers.rax)
    program.add(code)
    program.cache_code()
    return program.render_code

def get_jmp(addr):
    program = BareProgram()
    code = program.get_stream()
    code += isa.mov(registers.rax, fake_int(addr))
    code += isa.jmp(registers.rax)
    program.add(code)
    program.cache_code()
    return program.render_code

delayed = []
def execute_delayed():
    for func in delayed:
        func()
    delayed[:] = []
def add_delayed(func):
    delayed.append(func)

def called_from_asm(func):
    def f(*args, **kwargs):
        try:
            execute_delayed()
            return func(*args, **kwargs)
        except:
            traceback.print_exc()
            os._exit(0)
    return f

class Redirection(object):
    """
    Inserts instructions into 'caller_code' that do:
    
    while True:
        callback(<Redirection object>)
    
    while frobulating rax.
    
    Offers a 'replace' method that replaces this with other code,
    which must be a specific length. It is usually replaced with
    a call or jmp from get_call and get_jmp.
    """
    
    def __init__(self, caller_code, callback, take_arg=False):
        self.callback2 = callback
        self.take_arg = take_arg
        
        self.callback_cfunc = ctypes.CFUNCTYPE(ctypes.c_uint64, ctypes.c_uint64)(self.callback)
        callback_addr = ctypes.cast(self.callback_cfunc, ctypes.c_void_p).value
        
        # we could hook on caller_program.compile and build this when the caller is compiled
        # then we wouldn't have to fiddle with returning the jmp address
        # but then we'd have to replace the reference in caller_program
        # i suppose we could use Redirection.replace for that if we cleared the del junk out
        self._program = BareProgram()
        code = self._program.get_stream()
        code += isa.mov(registers.rax, fake_int(callback_addr))
        code += isa.call(registers.rax)
        code += isa.jmp(registers.rax)
        self._program.add(code)
        self._program.cache_code()
        
        self.caller_program = caller_code.prgm
        self.caller_start = caller_code.prgm.get_unique_label()
        self.caller_end = caller_code.prgm.get_unique_label()
        caller_code += self.caller_start
        caller_code += isa.mov(registers.rax, fake_int(self._program.inst_addr()))
        caller_code += isa.jmp(registers.rax)
        caller_code += self.caller_end
        
        self.caller_program.references.add(self)
    
    @called_from_asm
    def callback(self, data):
        if self.take_arg:
            self.callback2(self, data)
        else:
            self.callback2(self)
        if hasattr(self, "jmp_addr"):
            return self.jmp_addr
        return self.caller_program.inst_addr() + self.caller_start.position
    
    def replace(self, data):
        assert list(self.caller_program.render_code[self.caller_start.position:self.caller_end.position]) == \
            list(get_jmp(self._program.inst_addr()))
        self.caller_program.render_code[self.caller_start.position:self.caller_end.position] = data
        self.caller_program.references.remove(self)
        self.jmp_addr = self.caller_program.inst_addr() + self.caller_start.position
        del self.caller_program, self.caller_start, self.caller_end
        del self._program, self.callback_cfunc, self.callback2

@called_from_asm
def print_int64(i):
    print i,
print_int64_cfunc = ctypes.CFUNCTYPE(None, ctypes.c_int64)(print_int64)
print_int64_addr = ctypes.cast(print_int64_cfunc, ctypes.c_void_p).value


@called_from_asm
def print_double(i):
    print struct.unpack("d", struct.pack("l", i))[0],
print_double_cfunc = ctypes.CFUNCTYPE(None, ctypes.c_int64)(print_double)
print_double_addr = ctypes.cast(print_double_cfunc, ctypes.c_void_p).value

@called_from_asm
def print_string(i):
    length, = struct.unpack("l", ctypes.string_at(i, 8))
    print ctypes.string_at(i+8, length),
print_string_cfunc = ctypes.CFUNCTYPE(None, ctypes.c_int64)(print_string)
print_string_addr = ctypes.cast(print_string_cfunc, ctypes.c_void_p).value

@called_from_asm
def print_nl():
    print
print_nl_cfunc = ctypes.CFUNCTYPE(None)(print_nl)
print_nl_addr = ctypes.cast(print_nl_cfunc, ctypes.c_void_p).value

malloc_addr = ctypes.cast(ctypes.CDLL("libc.so.6").malloc, ctypes.c_void_p).value
realloc_addr = ctypes.cast(ctypes.CDLL("libc.so.6").realloc, ctypes.c_void_p).value

def dump(node, annotate_fields=True, include_attributes=False):
    """
    Return a formatted dump of the tree in *node*.  This is mainly useful for
    debugging purposes.  The returned string will show the names and the values
    for fields.  This makes the code impossible to evaluate, so if evaluation is
    wanted *annotate_fields* must be set to False.  Attributes such as line
    numbers and column offsets are not dumped by default.  If this is wanted,
    *include_attributes* can be set to True.
    """
    def _format(node,indent=4):
        if isinstance(node, ast.AST):
            fields = [(a, _format(b, indent+4)) for a, b in ast.iter_fields(node)]
            rv = node.__class__.__name__ + '(\n'
            for field in fields:
                rv += ' '*indent + '%s=%s,\n' % field
            if include_attributes and node._attributes:
                rv += fields and ', ' or ' '
                rv += ', '.join('%s=%s' % (a, _format(getattr(node, a), indent+4))
                    for a in node._attributes)
            return rv + ' '*indent + ')'
        elif isinstance(node, list):
            return '[\n%s%s\n%s]' % (' '*indent,(',\n'+' '*indent).join(_format(x, indent+4) for x in node), ' '*indent)
        return repr(node)
    return _format(node)

if __name__ == "__main__":
    ran = False
    
    def q():
        global ran
        ran = True
        print "q called!"
    cfunc = ctypes.CFUNCTYPE(None)(q)
    addr = ctypes.cast(cfunc, ctypes.c_void_p).value
    
    def f(a):
        a.replace(get_call(addr))
    
    program = Program()
    code = program.get_stream()
    code += isa.mov(registers.rdi, 42)
    code += isa.mov(registers.rax, print_int64_addr)
    code += isa.call(registers.rax)
    Redirection(code, f)
    code += isa.mov(registers.rdi, 43)
    code += isa.mov(registers.rax, print_int64_addr)
    code += isa.call(registers.rax)
    program.add(code)
    
    processor = platform.Processor()
    processor.execute(program)
    
    assert ran
    
    print "done"
