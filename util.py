import ctypes
import sys
import traceback

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
import corepy.arch.x86_64.platform as platform
#import corepy.arch.x86_64.fields as fields

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

class fake_int(long):
    def __lt__(self, other):
        # alters corepy.arch.x86_64.isa.x86_64_fields.x86ImmediateOperand.fits
        if other == 4294967296:
            return False
        return not self >= other

def get_call(addr):
    program = BareProgram()
    code = program.get_stream()
    code.add(isa.mov(registers.rax, fake_int(addr)))
    code.add(isa.call(registers.rax))
    program.add(code)
    program.cache_code()
    return program.render_code

def get_jmp(addr):
    program = BareProgram()
    code = program.get_stream()
    code.add(isa.mov(registers.rax, fake_int(addr)))
    code.add(isa.jmp(registers.rax))
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
            sys.exit()
    return f

class Redirection(object):
    """
    Inserts instructions into 'caller_code' that do:
    
    while True:
        callback(<Redirection object>)
    
    and frobulate rax.
    
    Offers a 'replace' method that replaces this with other code,
    which must be a specific length. It is usually replaced with a call or jmp
    from get_call and get_jmp.
    """
    
    def __init__(self, caller_code, callback):
        self.callback2 = callback
        
        self.callback_cfunc = ctypes.CFUNCTYPE(ctypes.c_uint64)(self.callback)
        callback_addr = ctypes.cast(self.callback_cfunc, ctypes.c_void_p).value
        
        # we could hook on caller_program.compile and build this when the caller is compiled
        # then we wouldn't have to fiddle with returning the jmp address
        # but then we'd have to replace the reference in caller_program
        # i suppose we could use Redirection.replace for that if we cleared the del junk out
        self._program = BareProgram()
        code = self._program.get_stream()
        code.add(isa.mov(registers.rax, fake_int(callback_addr)))
        code.add(isa.call(registers.rax))
        code.add(isa.jmp(registers.rax))
        self._program.add(code)
        self._program.cache_code()
        
        self.caller_program = caller_code.prgm
        self.caller_start = caller_code.prgm.get_unique_label()
        self.caller_end = caller_code.prgm.get_unique_label()
        caller_code.add(self.caller_start)
        caller_code.add(isa.mov(registers.rax, fake_int(self._program.inst_addr())))
        caller_code.add(isa.jmp(registers.rax))
        caller_code.add(self.caller_end)
        
        self.caller_program.references.add(self)
    
    @called_from_asm
    def callback(self):
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
    print i
print_int64_cfunc = ctypes.CFUNCTYPE(None, ctypes.c_int64)(print_int64)
print_int64_addr = ctypes.cast(print_int64_cfunc, ctypes.c_void_p).value

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
    code.add(isa.mov(registers.rdi, 42))
    code.add(isa.mov(registers.rax, print_int64_addr))
    code.add(isa.call(registers.rax))
    Redirection(code, f)
    code.add(isa.mov(registers.rdi, 43))
    code.add(isa.mov(registers.rax, print_int64_addr))
    code.add(isa.call(registers.rax))
    program.add(code)
    
    processor = platform.Processor()
    processor.execute(program)
    
    assert ran
    
    print "done"
