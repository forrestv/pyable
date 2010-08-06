import ast
import sys
import struct

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
import corepy.arch.x86_64.platform as platform
from corepy.arch.x86_64.lib.memory import MemRef
import corepy.lib.extarray as extarray
import corepy.lib.printer as printer
import corepy.arch.x86_64.lib.util as util

import util
from cdict import cdict

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
    if not isinstance(node, ast.AST):
        raise TypeError('expected AST, got %r' % node.__class__.__name__)
    return _format(node)

class Function(object):
    def __init__(self, space):
        self.space = space
        self.vars = {}
        self.var_types = {}
    def emit_start(self, code):
        code.add(isa.enter(self.space * 8, 0))
    def emit_end(self, code):
        code.add(isa.leave())
        code.add(isa.ret())
        #bs.code[enter_index] = isa.enter(len(bs.locs)*8, 0)
    def get_var_loc(self, name):
        try:
            return self.vars[name] - self.space
        except KeyError:
            if len(self.vars) == self.space:
                raise MemoryError
            self.vars[name] = len(self.vars)* 8
            return self.get_var_loc(name)
    def set_var_type(self, name, type):
        self.var_types[name] = type
    def get_var_type(self, name):
        return self.var_types[name]

class BlockStatus(object):
    def __init__(self, function=None):
        if function is None:
            function = Function(1000)
        self.function = function
        self.program = util.BareProgram()
        self.code = self.program.get_stream()
        self.stack = []
    
    def finalise(self):
        while False: #True:
            old = self.code
            res = self.program.get_stream()
            for i in xrange(len(old)):
                if i != len(old) - 1 and \
                    str(old[i]) == str(isa.push(registers.rax)) and \
                    str(old[i + 1]) == str(isa.pop(registers.rax)):
                        pass
                elif i != 0 and \
                    str(old[i - 1]) == str(isa.push(registers.rax)) and \
                    str(old[i]) == str(isa.pop(registers.rax)):
                        pass
                else:
                    res.add(old[i])
            if len(res) < len(old):
                if DEBUG:
                    print "DECREASE", len(res), len(old)
                    for i in xrange(10):
                        print
                    self.code.print_code()
                    for i in xrange(5):
                        print "------"
                    res.print_code()
                self.code = res
            else:
                break
        self.program.add(self.code)
        self.program.cache_code()
        #self.program.print_code()
        return self.program # return Block(self.program)

class Block(object):
    def __init__(self, program):
        self.program = program

class _Function(object):
    def __init__(self, t):
        self.t = t
        assert isinstance(self.t, ast.FunctionDef)
        self.addr = None
        self.program = None
    def _get_addr(self):
        if self.addr is None:
            self._render()
        return self.addr
    def add_call(self, code):
        if self.addr:
            code.add(isa.mov(registers.rax, util.fake_int(self.addr)))
            code.add(isa.call(registers.rax))
        else:
            util.Redirection(self._redir_callback)
    def redir_callback(self, redir):
        redir.replace(util.get_call(self._get_addr()))

functions = {}

class Int(object):
    def load_constant(self, value):
        assert isinstance(value, int)
        value = int(value)
        def _(bs, this):
            bs.code.add(isa.mov(registers.rax, value))
        return _
    def __neg__(self):
        def _(bs, this):
            bs.code.add(isa.neg(registers.rax))
        return _
    def __add__(self, other):
        if isinstance(other, Int):
            def _(bs, this):
                bs.code.add(isa.add(registers.rax, registers.rbx))
            return _
        return NotImplemented
    __radd__ = __add__

class Float(object):
    def load_constant(self, value):
        assert isinstance(value, float)
        value = float(value)
        def _(bs, this):
            bs.code.add(isa.mov(registers.rax, struct.unpack("l", struct.pack("d", value))[0]))
        return _
    def __neg__(self):
        def _(bs, this):
            bs.code.add(isa.neg(registers.rax))
        return _
    def __add__(self, other):
        if isinstance(other, Float):
            def _(bs, this):
                bs.code.add(isa.mov(registers.st0, registers.rax))
                bs.code.add(isa.mov(registers.st1, registers.rbx))
                bs.code.add(isa.fadd(registers.st0, registers.st1))
                bs.code.add(isa.mov(registers.rax, registers.st0))
            return _
        return NotImplemented
    __radd__ = __add__

class Tuple(object):
    def load_constant(self, ast):
        assert isinstance(ast)

class Object(object):
    pass

def memoize(f):
    def get(result=[]):
        if not result:
            result.append(f())
        return result[0]
    return get

def compile(bs, stack):
    while True:
        this = []
        if stack:
            t = stack.pop()
        else:
            t = None
        
        if t is None:
            if DEBUG:
                bs.code.print_code()
            return bs
        elif callable(t):
            t(bs, this)
        elif isinstance(t, list):
            assert not this
            this = t
        elif isinstance(t, ast.Module):
            bs.function.emit_start(bs.code)
            this.append(t.body)
            this.append(lambda bs, this: bs.function.emit_end(bs.code))
        elif isinstance(t, ast.FunctionDef):
            functions[t.name] = Function(t)
        elif isinstance(t, ast.AugAssign):
            this.append(ast.Assign(
                targets=[t.target],
                value=ast.BinOp(left=ast.Name(id=t.target.id, ctx=ast.Load()), op=t.op, right=t.value),
            ))
        elif isinstance(t, ast.Assign):
            this.append(t.value) # pushes 1
            @this.append
            def _(bs, this, t=t):
                bs.code.add(isa.pop(registers.rax))
                rax_type = bs.stack.pop()
                for target in t.targets:
                    assert isinstance(target.ctx, ast.Store)
                    
                    @this.append
                    def _(bs, this):
                        bs.code.add(isa.push(registers.rax))
                        bs.stack.append(rax_type)
                        bs.code.add(isa.push(registers.rax))
                        bs.stack.append(rax_type)
                    
                    this.append(target)
                    
                    @this.append
                    def _(bs, this):
                        bs.code.add(isa.pop(registers.rax))
                        rax_type = bs.stack.pop()
        elif isinstance(t, ast.Expr):
            this.append(t.value)
            @this.append
            def _(bs, this, t=t):
                bs.code.add(isa.pop(registers.rax))
                rax_type = bs.stack.pop()
        elif isinstance(t, ast.Num):
            if isinstance(t.n, float):
                o = Float()
            elif isinstance(t.n, int):
                o = Int()
            else:
                assert False, t.n
            this.append(o.load_constant(t.n))
            @this.append
            def _(bs, this, o=o):
                bs.code.add(isa.push(registers.rax))
                bs.stack.append(o)
        elif isinstance(t, ast.Name):
            if isinstance(t.ctx, ast.Load):
                bs.code.add(isa.mov(registers.rax, MemRef(registers.rbp, bs.function.get_var_loc(t.id))))
                rax_type = bs.function.get_var_type(t.id)
                bs.code.add(isa.push(registers.rax))
                bs.stack.append(rax_type)
            elif isinstance(t.ctx, ast.Store):
                bs.code.add(isa.pop(registers.rax))
                rax_type = bs.stack.pop()
                bs.code.add(isa.mov(MemRef(registers.rbp, bs.function.get_var_loc(t.id)), registers.rax))
                bs.function.set_var_type(t.id, rax_type)
            else:
                assert False, t.ctx
        elif isinstance(t, ast.If):
            a_bs = bs
            
            @memoize
            def make_b(t=t, a_bs=a_bs):
                bs = BlockStatus(a_bs.function)
                compile(bs, [[
                    t.body,
                    lambda bs, this: util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_c()))),
                ]])
                p = bs.finalise()
                blocks.append(p)
                if DEBUG:
                    print "if_b", hex(p.inst_addr())
                    p.print_code()
                return p.inst_addr()
            
            @memoize
            def make_c(t=t, stack=stack):
                bs = BlockStatus(a_bs.function)
                compile(bs, stack)
                p = bs.finalise()
                blocks.append(p)
                if DEBUG:
                    print "if_c", hex(p.inst_addr())
                    p.print_code()
                return p.inst_addr()
            
            
            this.append(t.test)
            @this.append
            def _(bs, this):
                bs.code.add(isa.pop(registers.rax))
                rax_type = bs.stack.pop()
                assert isinstance(rax_type, Int), (rax_type, Int)
                bs.code.add(isa.test(registers.rax, registers.rax))
                skip = bs.program.get_unique_label()
                bs.code.add(isa.jz(skip))
                util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_b())))
                bs.code.add(skip)
                util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_c())))
            this.append(None)
        elif isinstance(t, ast.While):
            @memoize
            def make_a(t=t, a_bs=bs):
                if DEBUG:
                    print "make_a"
                def _(bs, this):
                    bs.code.add(isa.pop(registers.rax))
                    rax_type = bs.stack.pop()
                    bs.code.add(isa.test(registers.rax, registers.rax))
                    skip = bs.program.get_unique_label()
                    bs.code.add(isa.jz(skip))
                    util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_b())))
                    bs.code.add(skip)
                    util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_c())))
                bs = BlockStatus(a_bs.function)
                compile(bs, [[t.test, _]])
                p = bs.finalise()
                blocks.append(p)
                if DEBUG:
                    p.print_code()
                return p.inst_addr()
            
            @memoize
            def make_b(t=t, a_bs=bs):
                if DEBUG:
                    print "make_b while"
                bs = BlockStatus(a_bs.function)
                compile(bs, [[
                    t.body,
                    lambda bs, this: util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_a()))),
                ]])
                p = bs.finalise()
                blocks.append(p)
                if DEBUG:
                    print "addr", hex(p.inst_addr())
                    p.print_code(hex=True)
                return p.inst_addr()
            
            @memoize
            def make_c(t=t, stack=stack, a_bs=bs):
                bs = BlockStatus(a_bs.function)
                compile(bs, stack)
                p = bs.finalise()
                blocks.append(p)
                if DEBUG:
                    print "if_c", hex(p.inst_addr())
                    p.print_code()
                return p.inst_addr()
            
            util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_a())))
            this.append(None)
        elif isinstance(t, ast.Compare):
            assert len(t.ops) == 1 and len(t.comparators) == 1
            this.append(t.left)
            this.append(t.comparators[0])
            @this.append
            def _(bs, this, t=t):
                op = t.ops[0]
                bs.code.add(isa.pop(registers.rax))
                rax_type = bs.stack.pop()
                bs.code.add(isa.pop(registers.rbx))
                rbx_type = bs.stack.pop()
                bs.code.add(isa.cmp(registers.rbx, registers.rax))
                bs.code.add(isa.mov(registers.rax, 0))
                bs.code.add(isa.push(registers.rax))
                bs.stack.append(Int())
                label = bs.program.get_unique_label()
                if isinstance(op, ast.Lt):
                    bs.code.add(isa.jge(label))
                elif isinstance(op, ast.Gt):
                    bs.code.add(isa.jle(label))
                elif isinstance(op, ast.LtE):
                    bs.code.add(isa.jg(label))
                elif isinstance(op, ast.GtE):
                    bs.code.add(isa.jl(label))
                elif isinstance(op, ast.Eq):
                    bs.code.add(isa.jne(label))
                elif isinstance(op, ast.NotEq):
                    bs.code.add(isa.je(label))
                else:
                    assert False, op
                bs.code.add(isa.pop(registers.rax))
                rax_type = bs.stack.pop()
                bs.code.add(isa.mov(registers.rax, 1))
                bs.code.add(isa.push(registers.rax))
                bs.stack.append(Int())
                bs.code.add(label)
        elif isinstance(t, ast.Print):
            assert t.dest is None
            for value in t.values:
                this.append(value)
                @this.append
                def _(bs, this):
                    bs.code.add(isa.pop(registers.rdi))
                    rdi_type = bs.stack.pop()
                    #assert isinstance(rdi_type, Int), "can only print ints"
                    bs.code.add(isa.mov(registers.rax, util.print_int64_addr))
                    bs.code.add(isa.call(registers.rax))
            if t.nl:
                @this.append
                def _(bs, this):
                    bs.code.add(isa.mov(registers.rax, util.print_nl_addr))
                    bs.code.add(isa.call(registers.rax))
        elif isinstance(t, ast.UnaryOp):
            this.append(t.operand)
            @this.append
            def _(bs, this, t=t):
                bs.code.add(isa.pop(registers.rax))
                rax_type = bs.stack.pop()
                if isinstance(rax_type, Int) and isinstance(t.op, ast.USub):
                    bs.code.add(isa.neg(registers.rax))
                else:
                    assert False, t.op
                bs.code.add(isa.push(registers.rax))
                bs.stack.append(rax_type)
        elif isinstance(t, ast.BinOp):
            this.append(t.right)
            this.append(t.left)
            @this.append
            def _(bs, this, t=t):
                bs.code.add(isa.pop(registers.rax))
                rax_type = bs.stack.pop()
                bs.code.add(isa.pop(registers.rbx))
                rbx_type = bs.stack.pop()
                if 1:
                    if isinstance(t.op, ast.Add):
                        bs.code.add(isa.add(registers.rax, registers.rbx))
                    elif isinstance(t.op, ast.Sub):
                        bs.code.add(isa.sub(registers.rax, registers.rbx))
                    elif isinstance(t.op, ast.Mult):
                        bs.code.add(isa.imul(registers.rax, registers.rbx))
                    elif isinstance(t.op, ast.Div):
                        bs.code.add(isa.mov(registers.rdx, 0))
                        bs.code.add(isa.idiv(registers.rbx))
                    elif isinstance(t.op, ast.FloorDiv):
                        bs.code.add(isa.mov(registers.rdx, 0))
                        bs.code.add(isa.idiv(registers.rbx))
                    elif isinstance(t.op, ast.Mod):
                        bs.code.add(isa.mov(registers.rdx, 0))
                        bs.code.add(isa.idiv(registers.rbx))
                        bs.code.add(isa.mov(registers.rax, registers.rdx))
                    else:
                        assert False, t.op
                else:
                    if isinstance(t.op, ast.Add): r = (rax_type + rbx_type)
                    elif isinstance(t.op, ast.Sub): r = (rax_type - rbx_type)
                    elif isinstance(t.op, ast.Mult): r = (rax_type - rbx_type)
                    elif isinstance(t.op, ast.Div): r = (rax_type / rbx_type)
                    elif isinstance(t.op, ast.FloorDiv): r = (rax_type // rbx_type)
                    elif isinstance(t.op, ast.Mult): r = (rax_type % rbx_type)
                    else: assert False
                    this.append(r)
                @this.append
                def _(bs, this):
                    bs.code.add(isa.push(registers.rax))
                    bs.stack.append(rax_type)
        elif isinstance(t, ast.Call) and 0:
            assert not t.keywords
            assert not t.starargs
            assert not t.kwargs
            for arg in t.args:
                bs = compile(bs, arg)
            regs = [registers.rdi, registers.rsi, registers.rdx, registers.rcx][:len(t.args)]
            for arg in t.args:
                bs.code.add(isa.pop(regs.pop()))
                rax_type = bs.stack.pop() # XXX not rax
            functions[t.func.id].add_call(bs.code)
            bs.code.add(isa.push(registers.rax))
            bs.stack.append(rax_type)
        elif isinstance(t, ast.Tuple):
            if isinstance(t.ctx, ast.Load):
                this.extend(t.elts)
                
                @this.append
                def _(bs, this, t=t):
                    bs.code.add(isa.mov(registers.rdi, 8*len(t.elts)))
                    bs.code.add(isa.mov(registers.rax, util.malloc_addr))
                    bs.code.add(isa.call(registers.rax))
                    
                    for i, elt in reversed(list(enumerate(t.elts))):
                        bs.code.add(isa.pop(MemRef(registers.rax, 8*i)))
                    
                    bs.code.add(isa.push(registers.rax))
                    bs.stack.append(Tuple())
            elif isinstance(t.ctx, ast.Store):
                isa.pop(registers.rax)
                rax_type = bs.stack.pop()
                
                for i, elt in reversed(list(enumerate(t.elts))):
                    bs.code.add(isa.push(MemRef(registers.rax, 8*i)))
                    bs.stack.append(Int) # XXX
                
                for elt in t.elts:
                    assert isinstance(elt, ast.Name)
                    assert isinstance(elt.ctx, ast.Store), elt.ctx
                this.extend(t.elts)
            else:
                assert False, t.ctx
        elif isinstance(t, ast.Subscript):
            if isinstance(t.ctx, ast.Load):
                this.append(t.value)
                
                @this.append
                def _(bs, this, t=t):                
                    isa.pop(registers.rax)
                    rax_type = bs.stack.pop()
                    
                    bs.code.add(isa.push(MemRef(registers.rax, 8 * t.slice.value.n)))
            elif isinstance(t.ctx, ast.Store):
                assert False
                bs.code.add(isa.pop(registers.rax))
                rax_type = bs.stack.pop()
                bs.code.add(isa.mov(MemRef(registers.rbp, bs.function.get_var_loc(t.id)), registers.rax))
            else:
                assert False, t.ctx
        else:
            assert False, t
        stack.extend(reversed(this))


def add_root(tree):
    def make_root(tree):
        program = platform.Program()
        locs = {}
        code = program.get_stream()
        compile(tree, code, locs)
        program.add(code)
        program.cache_code()
        return program
    refs[1]


prerefs = {}
refs = cdict(lambda k: prerefs.pop(k)())
if sys.argv[1] == "--debug":
    DEBUG = 1
    sys.argv[1:] = sys.argv[2:]
else:
    DEBUG = 0
tree = ast.parse(open(sys.argv[1]).read())

#print tree
#print dump(tree)
#fadf
#add_parents(tree)
#print tree.parent
if DEBUG:
    print dump(tree)
blocks = []
def make_root(redir):
    bs = BlockStatus()
    r = compile(bs, [tree])
    p = bs.finalise()
    blocks.append(p)
    #p.print_code(pro=True, epi=True)
    if DEBUG:
        print "make_root"
        p.print_code()
    redir.replace(util.get_call(p.inst_addr()))

def caller():
    program = util.Program()
    code = program.get_stream()
    util.Redirection(code, make_root)
    program.add(code)
    program.cache_code()
    return program
caller = caller()

processor = platform.Processor()
if DEBUG:
    import time
    print "STARTING"
    start = time.time()
ret = processor.execute(caller, mode='int')
if DEBUG:
    end = time.time()
    print "END", ret, end-start
