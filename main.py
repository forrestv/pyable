import ast
import sys
import struct

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
import corepy.arch.x86_64.platform as platform
from corepy.arch.x86_64.lib.memory import MemRef

import util
import type_impl

class Executable(object):
    def __init__(self):
        self.produced = util.cdict(self.produce)
    def __call__(self, arg_types=()):
        def _(bs, this):
            util.Redirection(bs.code, lambda caller: caller.replace(util.get_call(self.produced[arg_types].inst_addr())))
        return _
    def produce(self, arg_types):
        bs = BlockStatus(Flow(self))
        compile(bs, [[
            self.pre(arg_types),
            self.t.body,
            ast.Return(value=None),
        ]])
        #print self.pre(arg_types)
        #print list(bs.code)
        p = bs.finalise()
        debug(p, "exec " + self.name + " " + repr(arg_types))
        return p
        #bs.code[enter_index] = isa.enter(len(bs.locs)*8, 0)

class Module(Executable):
    def __init__(self, t, name):
        Executable.__init__(self)
        assert isinstance(t, ast.Module)
        self.t = t
        self.name = name
    def pre(self, arg_types):
        assert not arg_types
        this = []
        @this.append
        def _(bs, this):
            bs.code += isa.push(registers.rbp)
            bs.code += isa.mov(registers.rbp, registers.rsp)
            bs.code += isa.sub(registers.rsp, bs.flow.space * 8)
        return this

class Function(Executable):
    def __init__(self, t):
        Executable.__init__(self)
        assert isinstance(t, ast.FunctionDef)
        self.t = t
    @property
    def name(self):
        return self.t.name
    def pre(self, arg_types):
        assert not self.t.args.vararg
        assert not self.t.args.kwarg
        this = []
        # isa.push(registers.rip)
        # isa.jmp(<here>)
        @this.append
        def _(bs, this):
            bs.code += isa.push(registers.rbp)
            bs.code += isa.mov(registers.rbp, registers.rsp)
            bs.code += isa.sub(registers.rsp, bs.flow.space * 8)
        # pop uses rsp
        # memory access uses rbp
        # we need old stack current memory access
        assert len(arg_types) <= len(self.t.args.args), [arg_types, self.t.args.args]
        for i, (arg_type, t) in enumerate(zip(arg_types, self.t.args.args)):
            assert isinstance(t, ast.Name)
            assert isinstance(t.ctx, ast.Param)
            def _(bs, this, arg_type=arg_type):
                bs.flow.stack.append(arg_type)
                bs.code += isa.push(MemRef(registers.rbp, 24 + 8 * i))
            this.append(ast.Assign(
                targets=[ast.Name(id=t.id, ctx=ast.Store())],
                value=_,
            ))
            # pop memref(registers.rbp, -x)
        for t, v in zip(self.t.args.args[::-1][:len(self.t.args.args)-len(arg_types)], self.t.args.defaults[::-1]):
            print t.id, v.n
            this.append(ast.Assign(
                targets=[ast.Name(id=t.id, ctx=ast.Store())],
                value=v,
            ))
        return this

# separate this into block info
#     program, code
# and persistant flow data
#     variable types, allocations

class Flow(object):
    def __init__(self, executable):
        self.executable = executable
        self.space = 1000
        self.vars = {}
        self.var_type_impl = {}
        self.stack = []
        self.ctrl_stack = []
    
    def __repr__(self):
        return "Flow<%r>" % self.__dict__
    
    def __hash__(self):
        return 0 # O(n) hack :(
        return hash(self.space) ^ hash(self.vars) ^ hash(self.var_type_impl)
    def __eq__(self, other):
        if not isinstance(other, Flow):
            return False
        return self.__dict__ == other.__dict__
        #if self.executable is not other.executable:
        #    return False
        #return (self.space, self.vars, self.var_type_impl, self.stack) == (other.space, other.vars, other.var_type_impl, other.stack)
    
    # refactor to get_var(type=None) (need set, del)
    def get_var_loc(self, name):
        try:
            return self.vars[name] - self.space
        except KeyError:
            if len(self.vars) == self.space:
                raise MemoryError # hehe
            self.vars[name] = len(self.vars) * 8
            return self.get_var_loc(name)
    def set_var_type(self, name, type):
        self.var_type_impl[name] = type
    def get_var_type(self, name):
        return self.var_type_impl[name]
    def clone(self):
        r = Flow(self.executable)
        r.space = self.space
        r.vars.update(self.vars)
        r.var_type_impl.update(self.var_type_impl)
        r.stack[:] = self.stack[:]
        r.ctrl_stack[:] = self.ctrl_stack[:]
        return r

class BlockStatus(object):
    def __init__(self, flow):
        self.flow = flow
        
        self.program = util.BareProgram()
        self.code = self.program.get_stream()
    
    def finalise(self):
        while True:
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
                if DEBUG and 0:
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
        blocks.append(self.program)
        
        return self.program

def debug(program, name):
    if DEBUG:
        print "start", name
        program.print_code(pro=True, epi=True)
        print "end", name

def memoize(f):
    cache = {}
    def _(*args):
        if args not in cache:
            cache[args] = f(*args)
        return cache[args]
    return _

functions = []

def compile(bs, stack):
    while True:
        this = []
        if stack:
            t = stack.pop()
        else:
            t = None
        
        if t is None:
            return bs
        elif callable(t):
            t(bs, this)
        elif isinstance(t, list):
            assert not this
            this = t
        elif isinstance(t, ast.Module):
            assert False
        elif isinstance(t, ast.FunctionDef):
            def _(bs, this, t=t):
                key = len(functions)
                functions.append(Function(t))
                bs.code += isa.mov(registers.rax, key)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(type_impl.Function)
            # could be optimized
            this.append(ast.Assign(
                targets=[ast.Name(id=t.name, ctx=ast.Store())],
                value=_,
            ))
        elif isinstance(t, ast.AugAssign):
            this.append(ast.Assign(
                targets=[t.target],
                value=ast.BinOp(left=ast.Name(id=t.target.id, ctx=ast.Load()), op=t.op, right=t.value),
            ))
        elif isinstance(t, ast.Assign):
            this.append(t.value) # pushes 1
            @this.append
            def _(bs, this, t=t):
                bs.code += isa.pop(registers.rax)
                rax_type = bs.flow.stack.pop()
                for target in t.targets:
                    assert isinstance(target.ctx, ast.Store)
                    
                    @this.append
                    def _(bs, this):
                        bs.code += isa.push(registers.rax)
                        bs.flow.stack.append(rax_type)
                        bs.code += isa.push(registers.rax)
                        bs.flow.stack.append(rax_type)
                    
                    this.append(target)
                    
                    @this.append
                    def _(bs, this):
                        bs.code += isa.pop(registers.rax)
                        rax_type = bs.flow.stack.pop()
        elif isinstance(t, ast.Expr):
            this.append(t.value)
            @this.append
            def _(bs, this, t=t):
                bs.code += isa.pop(registers.rax)
                rax_type = bs.flow.stack.pop()
        elif isinstance(t, ast.Num):
            if isinstance(t.n, float):
                o = type_impl.Float
            elif isinstance(t.n, int):
                o = type_impl.Int
            else:
                assert False, t.n
            this.append(o.load_constant(t.n))
            @this.append
            def _(bs, this, o=o):
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(o)
        elif isinstance(t, ast.Name):
            if isinstance(t.ctx, ast.Load):
                bs.code += isa.mov(registers.rax, MemRef(registers.rbp, bs.flow.get_var_loc(t.id)))
                rax_type = bs.flow.get_var_type(t.id)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(rax_type)
            elif isinstance(t.ctx, ast.Store):
                bs.code += isa.pop(registers.rax)
                rax_type = bs.flow.stack.pop()
                bs.code += isa.mov(MemRef(registers.rbp, bs.flow.get_var_loc(t.id)), registers.rax)
                bs.flow.set_var_type(t.id, rax_type)
            else:
                assert False, t.ctx
        elif isinstance(t, ast.If):
            @memoize
            def make_b(flow, t=t):
                bs = BlockStatus(flow.clone())
                compile(bs, [[
                    t.body,
                    lambda bs, this: util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_c(bs.flow)))),
                ]])
                p = bs.finalise()
                debug(p, "if_b")
                return p.inst_addr()
            
            @memoize
            def make_c(flow, stack=stack):
                bs = BlockStatus(flow.clone())
                compile(bs, stack)
                p = bs.finalise()
                debug(p, "if_c")
                return p.inst_addr()
            
            this.append(t.test)
            @this.append
            def _(bs, this):
                bs.code += isa.pop(registers.rax)
                rax_type = bs.flow.stack.pop()
                assert isinstance(rax_type, type(type_impl.Int)), rax_type
                bs.code += isa.test(registers.rax, registers.rax)
                skip = bs.program.get_unique_label()
                bs.code += isa.jz(skip)
                util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_b(bs.flow))))
                bs.code += skip
                util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_c(bs.flow))))
            this.append(None)
        elif isinstance(t, ast.While):
            @memoize
            def make_a(flow, t=t):
                def _(bs, this):
                    bs.code += isa.pop(registers.rax)
                    rax_type = bs.flow.stack.pop()
                    bs.code += isa.test(registers.rax, registers.rax)
                    skip = bs.program.get_unique_label()
                    bs.code += isa.jz(skip)
                    util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_b(bs.flow))))
                    bs.code += skip
                    util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_c(bs.flow))))
                bs = BlockStatus(flow.clone())
                compile(bs, [[t.test, _]])
                p = bs.finalise()
                debug(p, "while_a")
                return p.inst_addr()
            
            @memoize
            def make_b(flow, t=t):
                bs = BlockStatus(flow.clone())
                compile(bs, [[
                    t.body,
                    lambda bs, this: util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_a(bs.flow)))),
                ]])
                p = bs.finalise()
                debug(p, "while_b")
                return p.inst_addr()
            
            @memoize
            def make_c(flow, stack=stack):
                bs = BlockStatus(flow.clone())
                removed = bs.flow.ctrl_stack.pop()
                assert removed is mine
                compile(bs, stack)
                p = bs.finalise()
                debug(p, "while_c")
                return p.inst_addr()
            
            bs.flow.ctrl_stack.append((
                lambda bs, this: util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_a(bs.flow)))), # continue
                lambda bs, this: util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_c(bs.flow)))), # break
            ))
            mine = bs.flow.ctrl_stack[-1]
            util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_a(bs.flow))))
            this.append(None)
        elif isinstance(t, ast.Compare):
            assert len(t.ops) == 1 and len(t.comparators) == 1
            this.append(t.left)
            this.append(t.comparators[0])
            @this.append
            def _(bs, this, t=t):
                op = t.ops[0]
                bs.code += isa.pop(registers.rax)
                rax_type = bs.flow.stack.pop()
                bs.code += isa.pop(registers.rbx)
                rbx_type = bs.flow.stack.pop()
                bs.code += isa.cmp(registers.rbx, registers.rax)
                bs.code += isa.mov(registers.rax, 0)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(type_impl.Int)
                label = bs.program.get_unique_label()
                if isinstance(op, ast.Lt):
                    bs.code += isa.jge(label)
                elif isinstance(op, ast.Gt):
                    bs.code += isa.jle(label)
                elif isinstance(op, ast.LtE):
                    bs.code += isa.jg(label)
                elif isinstance(op, ast.GtE):
                    bs.code += isa.jl(label)
                elif isinstance(op, ast.Eq):
                    bs.code += isa.jne(label)
                elif isinstance(op, ast.NotEq):
                    bs.code += isa.je(label)
                else:
                    assert False, op
                bs.code += isa.pop(registers.rax)
                rax_type = bs.flow.stack.pop()
                bs.code += isa.mov(registers.rax, 1)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(type_impl.Int)
                bs.code += label
        elif isinstance(t, ast.Print):
            assert t.dest is None
            for value in t.values:
                this.append(value)
                @this.append
                def _(bs, this,value=value):
                    bs.code += isa.pop(registers.rdi)
                    rdi_type = bs.flow.stack.pop()
                    if isinstance(rdi_type, type(type_impl.Int)):
                        bs.code += isa.mov(registers.rax, util.print_int64_addr)
                    elif isinstance(rdi_type, type(type_impl.Float)):
                        bs.code += isa.mov(registers.rax, util.print_double_addr)
                    else:
                        bs.code += isa.mov(registers.rax, util.print_string_addr)
                    bs.code += isa.call(registers.rax)
            if t.nl:
                @this.append
                def _(bs, this):
                    bs.code += isa.mov(registers.rax, util.print_nl_addr)
                    bs.code += isa.call(registers.rax)
        elif isinstance(t, ast.UnaryOp):
            this.append(t.operand)
            @this.append
            def _(bs, this, t=t):
                bs.code += isa.pop(registers.rax)
                rax_type = bs.flow.stack.pop()
                if isinstance(rax_type, type(type_impl.Int)) and isinstance(t.op, ast.USub):
                    bs.code += isa.neg(registers.rax)
                else:
                    assert False, t.op
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(rax_type)
        elif isinstance(t, ast.BinOp):
            this.append(t.left)
            this.append(t.right)
            @this.append
            def _(bs, this, t=t):
                bs.code += isa.pop(registers.rbx)
                rbx_type = bs.flow.stack.pop().copy()
                bs.code += isa.pop(registers.rdi)
                rdi_type = bs.flow.stack.pop().copy()
                
                rdi_type.register = registers.rdi
                rbx_type.register = registers.rbx
                
                if isinstance(t.op, ast.Add): r = (rdi_type + rbx_type)
                elif isinstance(t.op, ast.Sub): r = (rdi_type - rbx_type)
                elif isinstance(t.op, ast.Mult): r = (rdi_type * rbx_type)
                elif isinstance(t.op, ast.Div): r = (rdi_type / rbx_type)
                elif isinstance(t.op, ast.FloorDiv): r = (rdi_type // rbx_type)
                elif isinstance(t.op, ast.Mod): r = (rdi_type % rbx_type)
                else: assert False, t.op
                
                this.append(r)
        elif isinstance(t, ast.Call):
            assert not t.keywords
            assert not t.starargs
            assert not t.kwargs
            
            for arg in t.args:
                this.append(arg)
            
            this.append(t.func)
            
            @memoize
            def make_c(flow, stack=stack, t=t):
                bs = BlockStatus(flow.clone())
                this = []
                @this.append
                def _(bs, this):
                    bs.code += isa.pop(registers.rax)
                    assert bs.flow.stack.pop() is type_impl.Function
                    for arg in t.args:
                        bs.code += isa.pop(registers.rax)
                        bs.flow.stack.pop() # XXX
                    bs.code += isa.push(registers.r12)
                    #bs.flow.stack.append(type_impl.id_to_type[registers.r13])
                    bs.flow.stack.append(type_impl.Int)
                compile(bs, stack + [this])
                p = bs.finalise()
                debug(p, "call_c")
                return p.inst_addr()
            
            def make_thingy(flow, data, types):
                if DEBUG:
                    print "call_thingy", data
                
                bs = BlockStatus(flow.clone())
                
                good = bs.program.get_unique_label()
                
                bs.code += isa.cmp(MemRef(registers.rsp), data)
                bs.code += isa.je(good)
                bs.code += isa.mov(registers.rdi, MemRef(registers.rsp))
                util.Redirection(bs.code, lambda caller, data: caller.replace(util.get_jmp(make_thingy(bs.flow, data, types))), True)
                bs.code += good
                compile(bs, [[
                    functions[data](types),
                    lambda bs, this: util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_c(bs.flow)))),
                ]])
                
                p = bs.finalise()
                debug(p, "call_thingy")
                return p.inst_addr()
            
            @this.append
            def _(bs, this, t=t):
                assert bs.flow.stack[-1] is type_impl.Function
                types = tuple(bs.flow.stack[-2 - i] for i, a in enumerate(t.args))
                bs.code += isa.mov(registers.rdi, MemRef(registers.rsp))
                util.Redirection(bs.code, lambda caller, data: caller.replace(util.get_jmp(make_thingy(bs.flow, data, types))), True)
            this.append(None)
        elif isinstance(t, ast.Tuple):
            if isinstance(t.ctx, ast.Load):
                this.extend(t.elts)
                
                @this.append
                def _(bs, this, t=t):
                    bs.code += isa.mov(registers.rdi, 8*len(t.elts))
                    bs.code += isa.mov(registers.rax, util.malloc_addr)
                    bs.code += isa.call(registers.rax)
                    
                    for i, elt in reversed(list(enumerate(t.elts))):
                        bs.code += isa.pop(MemRef(registers.rax, 8*i))
                        type = bs.flow.stack.pop()
                    
                    bs.code += isa.push(registers.rax)
                    bs.flow.stack.append(type_impl.Tuple)
            elif isinstance(t.ctx, ast.Store):
                isa.pop(registers.rax)
                rax_type = bs.flow.stack.pop()
                
                for i, elt in reversed(list(enumerate(t.elts))):
                    bs.code += isa.push(MemRef(registers.rax, 8*i))
                    bs.flow.stack.append(type_impl.Int) # XXX
                
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
                    rax_type = bs.flow.stack.pop()
                    assert rax_type is type_impl.Tuple, (rax_type, type_impl.Tuple)
                    
                    bs.code += isa.push(MemRef(registers.rax, 8 * t.slice.value.n))
                    bs.flow.stack.append(type_impl.Int) # XXX
            elif isinstance(t.ctx, ast.Store):
                assert False
                bs.code += isa.pop(registers.rax)
                rax_type = bs.flow.stack.pop()
                bs.code += isa.mov(MemRef(registers.rbp, bs.flow.get_var_loc(t.id)), registers.rax)
            else:
                assert False, t.ctx
        elif isinstance(t, ast.Continue):
            this.append(bs.flow.ctrl_stack[-1][0])
        elif isinstance(t, ast.Break):
            this.append(bs.flow.ctrl_stack[-1][1])
        elif isinstance(t, ast.Str):
            this.append(type_impl.Str.load_constant(t.s))
        elif isinstance(t, ast.Return):
            if t.value is None:
                this.append(ast.Num(n=1001))
            else:
                this.append(t.value)
            @this.append
            def _(bs, this):
                bs.code += isa.pop(registers.r12)
                rax_type = bs.flow.stack.pop()
                
                bs.code += isa.mov(registers.r13, rax_type.id)
                
                # leave
                bs.code += isa.mov(registers.rsp, registers.rbp)
                bs.code += isa.pop(registers.rbp)
                
                assert not bs.flow.stack, bs.flow.stack
                
                bs.code += isa.ret() # return address
            
            this.append(None)
        elif isinstance(t, ast.Pass):
            pass # haha
        else:
            assert False, t
        stack.extend(reversed(this))

if sys.argv[1] == "--debug":
    DEBUG = 1
    sys.argv[1:] = sys.argv[2:]
else:
    DEBUG = 0

tree = ast.parse(open(sys.argv[1]).read())

if DEBUG:
    print util.dump(tree)

blocks = []

def make_root():
    bs = BlockStatus(Flow(None))
    compile(bs, [[
        main_module(),
        lambda bs, this: bs.code.add(isa.ret()),
    ]])
    p = bs.finalise()
    debug(p, "make_root")
    return p

main_module = Module(tree, "__main__")

def caller():
    p = util.Program()
    code = p.get_stream()
    util.Redirection(code, lambda caller: caller.replace(util.get_call(make_root().inst_addr())))
    p.add(code)
    p.cache_code()
    debug(p, "caller")
    return p
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
