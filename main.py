#import array
#import code as code_mod
import ctypes
import random
import sys
#import time
import traceback
import itertools

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
import corepy.arch.x86_64.platform as platform
from corepy.arch.x86_64.lib.memory import MemRef
import corepy.lib.extarray as extarray
import corepy.arch.x86_64.lib.util as util

import cdict

# main_wrapper
    # normal calling convention
    # calls as of yet unmade main func
# redir
    # custom calling convention
    # calls ctypes python compile function, with argument of random id
    # python func replaces jump to redir with jump/call to a new BLOCK
    # python func returns addr to jump to (which is where the new jump/call to BLOCK is)

# BLOCK
    # one entry point (start)
    # 0 or more middle conditional exit points
    # one unconditional exit point (end) - either jmp or ret

# call compile_wraper - 10 bytes
# ->
# jmp X - 10 bytes
# call X - 10 bytes

# restrictions
# rax used to jump from compile, so lost when an uncompiled block is called/jumped to
# everything else is free for all :D


class Program(platform.Program):
  def _synthesize_prologue(self):
    self._prologue = []
  def _synthesize_epilogue(self):
    self._epilogue = []


def print_int(i):
    print i
print_int_cfunc = ctypes.CFUNCTYPE(None, ctypes.c_int64)(print_int)
print_int_addr = ctypes.cast(print_int_cfunc, ctypes.c_void_p).value

blocks = {}
class Block(object):
    def __init__(self, render_code, referenced_render_codes):
        self.render_code = render_code
        self.referenced_render_codes = referenced_render_codes

def compile_main():
    #def compile_sub
    
    program = Program()
    code = program.get_stream()
    

def gen(body):
    print "gen"
    #return body()
    if body is compile_main:
        body = 0
    #else:
    #    a
    program = Program()
    code = program.get_stream()
    #code.add(isa.enter(0, 0))
    #code.add(isa.leave())
    #code.add(isa.ret())
    if body < 1000:
        Redirection(code, body + 1)
        code.add(isa.ret())
    else:
        code.add(isa.mov(registers.rdi, 45))
        code.add(isa.mov(registers.rax, print_int_addr))
        code.add(isa.call(registers.rax))
        code.add(isa.ret())
    program.add(code)
    program.cache_code()
    compiled_blocks.append(program.render_code)
    return get_call(program.inst_addr())


compiled_blocks = []
def get_call(addr):
    program = Program()
    code = program.get_stream()
    code.add(isa.mov(registers.rax, addr))
    code.add(isa.call(registers.rax))
    program.add(code)
    program.cache_code()
    return program.render_code
def get_jmp(addr):
    program = Program()
    code = program.get_stream()
    code.add(isa.mov(registers.rax, addr))
    code.add(isa.jmp(registers.rax))
    program.add(code)
    program.cache_code()
    return program.render_code
def compile(redir_id):
    try:
        for x in redirs_to_free:
            del redirs[x.id]
        redirs_to_free[:] = []
        redir = redirs[redir_id]
        data = gen(redir.body)
        return redir.replace_callee(data)
    except:
        traceback.print_exc(5)
        sys.exit()
compile_cfunc = ctypes.CFUNCTYPE(ctypes.c_uint64, ctypes.c_uint64)(compile)
compile_addr = ctypes.cast(compile_cfunc, ctypes.c_void_p).value

class Block(object):
    def __init__(self, ref):
        self.compiled = False
    def compile(self):
        assert not self.compiled
        self.compiled = True
        self.program = compile(ref)
        for type, redir in self.redirs:
            maker = get_jmp if type == 'jmp' else get_call
            redir.replace_callee(type(
        return self.render_code.
    def add_jmp(self, code):
        redir = Redirection(code, self.compile)
        self.redirs.append((get_jmp, redir))
    def add_call(self, code):
        redir = Redirection(code, self.compile)
        self.redirs.append((get_call, redir))
blocks = cdict.cdict(Block)

redir_id_generator = itertools.count()

class Redirection(object):
    def __init__(self, callee_code, body):
        self.id = redir_id_generator.next()
        redirs[self.id] = self
        self.body = body
        
        self._program = Program()
        code = self._program.get_stream()
        
        #code.add(isa.push(registers.rdi))
        code.add(isa.mov(registers.rdi, self.id))
        code.add(isa.mov(registers.rax, compile_addr))
        code.add(isa.call(registers.rax)) # sets rax
        #code.add(isa.pop(registers.rdi))
        code.add(isa.jmp(registers.rax))
        
        self._program.add(code)
        self._program.cache_code()
        
        label = callee_code.prgm.get_label(str(random.randrange(2**64)))
        callee_code.add(label)
        callee_code.add(isa.mov(registers.rax, self._program.inst_addr()))
        callee_code.add(isa.jmp(registers.rax))
        self.callee_program = callee_code.prgm
        self.callee_label = label
    def replace_callee(self, data):
        assert list(self.callee_program.render_code[self.callee_label.position:self.callee_label.position + 10]) == list(get_jmp(self._program.inst_addr()))
        self.callee_program.render_code[self.callee_label.position:self.callee_label.position + 10] = data
        jump_to = self.callee_program.inst_addr() + self.callee_label.position
        del self.callee_program, self.callee_label
        redirs_to_free.append(self)
        return jump_to
redirs = {}
redirs_to_free = [] # used because a redir's program is used when python returns to asm, so it can be freed the next time python is called into



#import newjit
#tree = newjit.convert_tree(newjit.read_tree(open(sys.argv[1])))

def caller():
    program = platform.Program()
    code = program.get_stream()
    blocks[tree].add_call(code)
    program.add(code)
    program.cache_code()
    return program
caller = caller()

processor = platform.Processor()
import time
print "STARTING"
start = time.time()
ret = processor.execute(caller, mode='int')
end = time.time()
print "END", ret, end-start

