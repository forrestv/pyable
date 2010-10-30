from __future__ import division

import ctypes
import os
import traceback
import struct
import ast
import struct
import array
from corepy.lib.extarray import extarray
from corepy.arch.x86_64.platform.linux.x86_64_exec import make_executable

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
from corepy.arch.x86_64.lib.memory import MemRef
import corepy.arch.x86_64.platform as platform

DEBUG = 0

def debug(program, name):
    if DEBUG:
        print "start", name
        program.print_code(pro=True, epi=True, line_numbers=False)
        print "end", name

class Program(platform.Program):
    def __init__(self, *args, **kwargs):
        platform.Program.__init__(self, *args, **kwargs)
        self.references = []
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

def memoize(f):
    #return f
    cache = {}
    def _(*args):
        if args not in cache:
            cache[args] = f(*args)
        return cache[args]
    return _

class fake_int(long):
    def __lt__(self, other):
        # alters corepy.arch.x86_64.isa.x86_64_fields.x86ImmediateOperand.fits
        if other == 4294967296:
            return False
        return not self >= other

'''
def get_call(addr):
    program = BareProgram()
    code = program.get_stream()
    code += isa.mov(registers.rax, fake_int(addr))
    code += isa.call(registers.rax)
    program.add(code)
    program.cache_code()
    return program.render_code

def get_mov_rax(addr):
    program = BareProgram()
    code = program.get_stream()
    code += isa.mov(registers.rax, fake_int(addr))
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
'''

def get_jmp(addr):
    l = [72, 184]
    l.extend(struct.unpack("8B", struct.pack("l", addr)))
    l.extend([72, 255, 224])
    return array.array('B', l)

def get_call(addr):
    l = [72, 184]
    l.extend(struct.unpack("8B", struct.pack("l", addr)))
    l.extend([72, 255, 208])
    return array.array('B', l)

def get_mov_rax(addr):
    l = [72, 184]
    l.extend(struct.unpack("8B", struct.pack("l", addr)))
    return array.array('B', l)

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

class UpdatableMovRax(object):
    def __init__(self, caller_code, initial):
        self.value = initial
        
        self.caller_program = caller_code.prgm
        self.caller_start = caller_code.prgm.get_unique_label()
        self.caller_end = caller_code.prgm.get_unique_label()
        caller_code += self.caller_start
        self.inst = isa.mov(registers.rax, fake_int(self.value))
        caller_code += self.inst
        caller_code += self.caller_end
    
    def replace(self, data):
        self.inst.__dict__ = isa.mov(registers.rax, fake_int(data)).__dict__
        if self.caller_program.render_code is None:
            self.value = data
            return
        assert list(self.caller_program.render_code[self.caller_start.position:self.caller_end.position]) == \
            list(get_mov_rax(self.value))
        self.value = data
        self.caller_program.render_code[self.caller_start.position:self.caller_end.position] = get_mov_rax(self.value)

patch_len = len(get_jmp(0))

callback_type = ctypes.CFUNCTYPE(None, ctypes.c_int64)

def get_asm_glue_old(dest_addr):
    program = BareProgram()
    code = program.get_stream()
    code += isa.mov(registers.rax, fake_int(dest_addr))
    code += isa.push(registers.r12)
    code += isa.mov(registers.r12, registers.rsp)
    code += isa.and_(registers.rsp, -16)
    code += isa.call(registers.rax)
    code += isa.mov(registers.rsp, registers.r12)
    code += isa.pop(registers.r12)
    code += isa.pop(registers.rax)
    code += isa.sub(registers.rax, patch_len)
    code += isa.jmp(registers.rax)
    program.add(code)
    program.cache_code()
    return program.render_code

def get_asm_glue(dest):
    l = [72, 184]
    l.extend(struct.unpack("8B", struct.pack("l", ctypes.cast(dest, ctypes.c_void_p).value)))
    l.extend([73, 84, 73, 137, 228, 72, 131, 228, 240, 72, 255, 208, 76, 137, 228, 73, 92, 72, 88, 72, 131, 232, 13, 72, 255, 224])
    l = extarray('B', l)
    make_executable(*l.buffer_info())
    l.references.append(dest)
    return l

redirections = 0
triggered_redirections = 0

def add_redirection(caller_code, callback):
        global redirections
        redirections += 1
        
        @called_from_asm
        def glue(rdi):
            global triggered_redirections
            triggered_redirections += 1
            caller_program.render_code[caller_start.position:caller_end.position] = callback(rdi)
            caller_program.references.remove(code)
        
        code = get_asm_glue(callback_type(glue))
        
        caller_program = caller_code.prgm
        
        caller_start = caller_program.get_unique_label()
        caller_end = caller_program.get_unique_label()
        
        caller_code += caller_start
        caller_code += isa.mov(registers.rax, fake_int(code.buffer_info()[0]))
        caller_code += isa.call(registers.rax)
        caller_code += caller_end
        
        caller_program.references.append(code)

def get_redirection(callback):
    program = BareProgram()
    code = program.get_stream()
    add_redirection(code, callback)
    program.add(code)
    program.cache_code()
    return program

def post():
    if DEBUG:
        print "redirection stats:", triggered_redirections, "/", redirections

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
    import type_impl
    print type_impl.Str.to_python(struct.pack("l", i)),
print_string_cfunc = ctypes.CFUNCTYPE(None, ctypes.c_int64)(print_string)
print_string_addr = ctypes.cast(print_string_cfunc, ctypes.c_void_p).value

@called_from_asm
def print_nl():
    print
print_nl_cfunc = ctypes.CFUNCTYPE(None)(print_nl)
print_nl_addr = ctypes.cast(print_nl_cfunc, ctypes.c_void_p).value

malloc_addr = ctypes.cast(ctypes.CDLL("libc.so.6").malloc, ctypes.c_void_p).value
free_addr = ctypes.cast(ctypes.CDLL("libc.so.6").free, ctypes.c_void_p).value
realloc_addr = ctypes.cast(ctypes.CDLL("libc.so.6").realloc, ctypes.c_void_p).value
sprintf_addr = ctypes.cast(ctypes.CDLL("libc.so.6").sprintf, ctypes.c_void_p).value
memcmp_addr = ctypes.cast(ctypes.CDLL("libc.so.6").memcmp, ctypes.c_void_p).value

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

def unlift(bs, func, desc):
    #print desc
    #print func
    #flows = []
    @memoize
    def make_post(flow):
        #print flows
        #if flows:
        #    print flow, flows[-1]
        #    print flow == flows[-1]
        #    print flow.__dict__ == flows[-1].__dict__
        #flows.append(flow)
        return compiler.translate("unlift_post " + desc, flow, stack=list(bs.call_stack))
    def make_thingy(flow, data):
        #print "thingy", id(flows), desc, data
        def _(bs):
            good = bs.program.get_unique_label()
            
            bs.code += isa.mov(registers.rax, data) # check if could be combined into cmp
            bs.code += isa.cmp(MemRef(registers.rsp), registers.rax)
            bs.code += isa.je(good)
            bs.code += isa.mov(registers.rdi, MemRef(registers.rsp))
            add_redirection(bs.code, lambda rdi, flow=bs.flow.clone(): get_jmp(make_thingy(flow, rdi)))
            bs.code += good
            
            bs.code += isa.pop(registers.rax)
            bs.this.append(func(data))
        
        return compiler.translate("unlift_thingy " + desc, flow, this=[
            _,
            lambda bs: add_redirection(bs.code, lambda rdi, flow=bs.flow.clone(): get_jmp(make_post(flow))),
            compiler.end,
        ])
    bs.code += isa.mov(registers.rdi, MemRef(registers.rsp))
    add_redirection(bs.code, lambda rdi, flow=bs.flow.clone(): get_jmp(make_thingy(flow, rdi)))
    bs.this.append(compiler.end)

def unlift_noncached(bs, func, desc):
    #print desc
    @memoize
    def make_post(flow):
        return compiler.translate("unlift_post " + desc, flow, stack=list(bs.call_stack))
    
    def make_thingy(flow, data):
        return compiler.translate("unlift_thingy " + desc, flow, this=[
            func(data),
            lambda bs: add_redirection(bs.code, lambda rdi, flow=bs.flow.clone(): get_jmp(make_post(flow))),
            compiler.end,
        ])
    
    @called_from_asm
    def glue(rdi, flow=bs.flow.clone()):
        return make_thingy(flow, rdi)
    
    code = ctypes.CFUNCTYPE(ctypes.c_int64, ctypes.c_int64)(glue)
    
    bs.code += isa.pop(registers.rdi)
    bs.code += isa.mov(registers.rax, ctypes.cast(code, ctypes.c_void_p).value)
    bs.code += isa.mov(registers.r12, registers.rsp)
    bs.code += isa.and_(registers.rsp, -16)
    bs.code += isa.call(registers.rax)
    bs.code += isa.mov(registers.rsp, registers.r12)
    bs.code += isa.jmp(registers.rax)
    bs.this.append(compiler.end)
    
    bs.program.references.append(code)

def hash_dict(d):
    v = 4310987423
    for item in d.iteritems():
        v ^= hash(item)
    return v

import compiler

def read_top(bs, regs):
    res = []
    type = bs.flow.stack[-1]
    for i in xrange(type.size):
        reg = regs.pop()
        bs.code += isa.mov(reg, MemRef(registers.rsp, 8*i))
        res.append(reg)
    return type, res
def pop(bs, regs):
    res = []
    type = bs.flow.stack.pop()
    for i in xrange(type.size):
        reg = regs.pop()
        bs.code += isa.pop(reg)
        res.append(reg)
    return type, res
def push(bs, (type, regs)):
    assert type.size == len(regs)
    for reg in reversed(regs):
        bs.code += isa.push(reg)
    bs.flow.stack.append(type)

good_regs = [registers.rbx, registers.rcx, registers.rdx, registers.rdi, registers.rsi, registers.r9]

def swap(bs):
    regs = list(good_regs)
    a = pop(bs, regs)
    b = pop(bs, regs)
    push(bs, a)
    push(bs, b)

def rev3(bs):
    regs = list(good_regs)
    a = pop(bs, regs)
    b = pop(bs, regs)
    c = pop(bs, regs)
    push(bs, a)
    push(bs, b)
    push(bs, c)

def rem1(bs):
    regs = list(good_regs)
    a = pop(bs, regs)
    pop(bs, regs)
    push(bs, a)

def rem2(bs):
    regs = list(good_regs)
    a = pop(bs, regs)
    pop(bs, regs)
    pop(bs, regs)
    push(bs, a)

def dup(bs):
    regs = list(good_regs)
    a = read_top(bs, regs)
    push(bs, a)

def lower(bs, n):
    regs = list(good_regs)
    a = pop(bs, regs)
    d = 0
    for i in xrange(n):
        t = bs.flow.stack.pop()
        d += t.size
    if d:
        bs.code += isa.add(registers.rsp, 8*d)
    push(bs, a)

def discard(bs):
    type = bs.flow.stack.pop()
    if type.size:
        bs.code += isa.add(registers.rsp, 8*type.size)

def discard2(bs):
    type = bs.flow.stack.pop()
    type1 = bs.flow.stack.pop()
    if type.size + type1.size:
        bs.code += isa.add(registers.rsp, 8*(type.size+type1.size))

class WatchedValue(object):
    def __init__(self, value):
        self.value = value
        self.watchers = []
    def get_and_watch(self, watcher):
        self.watchers.append(watcher)
        return self.value
    def watch_now(self, watcher):
        self.watchers.append(watcher)
        watcher(self.value)
    def set(self, new):
        assert self.value is not new
        self.value = new
        for watcher in self.watchers:
            watcher(new)

def branch_on_watched(bs, watched, func): # should have an argument on whether to merge like unlift does (unlift versions should be merged too)
    flow = bs.flow.clone()
    call_stack = list(bs.call_stack)
    branches = {} # value -> string
    def watcher(new_value):
        if not branches:
            branches[value] = bs.program.render_code[label.position:label.position + patch_len]
        if new_value in branches:
            data = branches[value]
        else:
            prgm = get_redirection(lambda rdi:  get_jmp(compiler.translate("branch_on_watched", flow, stack=call_stack, this=func(new_value))))
            data = prgm.render_code
            prgm.render_code = OffsetListProxy(bs.program.render_code, label.position)
            branches[value] = data
        bs.program.render_code[label.position:label.position + patch_len] = data
    value = watched.get_and_watch(watcher)
    label = bs.program.get_unique_label()
    bs.code += label
    # remove later
    for i in xrange(patch_len):
        bs.code += isa.nop()
    func(value)(bs)

def arg_check(bs, args, should):
    if map(id, args) == map(id, should): return False
    import mypyable
    bs.this.append(ast.Raise(
        type=ast.Call(
            func=mypyable.TypeError_impl.load,
            args=[ast.Str(s="expected %r, got %r" % (should, args))],
            keywords=[],
            starargs=None,
            kwargs=None,
            ),
        inst=None,
        tback=None,
        ),
    )
    return True


class OffsetListProxy(object):
    def __init__(self, source, offset):
        self.source = source
        self.offset = offset
    def __setitem__(self, item, value):
        if isinstance(item, slice):
            item = slice(item.start + self.offset, item.stop+self.offset, item.step)
        else:
            item += self.offset
        self.source.__setitem__(item, value)
    def __getitem__(self, item):
        if isinstance(item, slice):
            item = slice(item.start + self.offset, item.stop+self.offset, item.step)
        else:
            item += self.offset
        return self.source.__getitem__(item)


if __name__ == "__main__":
    print repr(get_jmp(0))
    print repr(get_call(0))
    print repr(get_mov_rax(0))
    print repr(get_asm_glue_old(0))
    blocks = []
    count = 10000
    def go(i=0):
        program = BareProgram()
        code = program.get_stream()
        if i == count:
            code += isa.ret()
        else:
            add_redirection(code, lambda rdi: get_jmp(go(i + 1)))
        program.add(code)
        program.cache_code()
        blocks.append(program)
        return program.inst_addr()
    program = Program()
    code = program.get_stream()
    add_redirection(code, lambda rdi: get_call(go()))
    program.add(code)
    
    processor = platform.Processor()
    import time
    
    
    start = time.time()
    processor.execute(program)
    end = time.time()
    
    print (end - start)/count*1000, "ms per"
    print count/(end-start), "hz"
