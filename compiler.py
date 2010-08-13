from __future__ import division

import ast
import random

import type_impl
import util

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
import corepy.arch.x86_64.platform as platform
from corepy.arch.x86_64.lib.memory import MemRef


class Executable(object):
    def __init__(self):
        self.produced = util.cdict(self.produce)
    def __call__(self, arg_types=()):
        def _(bs, this):
            util.Redirection(bs.code, lambda caller: caller.replace(util.get_call(self.produced[arg_types])))
        return _
    def produce(self, arg_types):
        return translate(
            flow=Flow(self),
            desc="exec " + self.name + " " + repr(arg_types),
            this=[
                self.pre(arg_types),
                self.t.body,
                ast.Return(value=None),
                None,
            ],
        )


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
            bs.code += isa.or_(registers.rsp, 0xf) # adds at most 15
            bs.code += isa.sub(registers.rsp, bs.flow.space * 8)
        # pop uses rsp
        # memory access uses rbp
        # we need old stack current memory access
        assert len(arg_types) <= len(self.t.args.args), [arg_types, self.t.args.args]
        for i, (arg_type, t) in enumerate(reversed(zip(arg_types, self.t.args.args))):
            assert isinstance(t, ast.Name)
            assert isinstance(t.ctx, ast.Param)
            def _(bs, this, arg_type=arg_type, i=i):
                bs.flow.stack.append(arg_type)
                bs.code += isa.push(MemRef(registers.rbp, 16 + 8 * i))
            this.append(ast.Assign(
                targets=[ast.Name(id=t.id, ctx=ast.Store())],
                value=_,
            ))
            # pop memref(registers.rbp, -x)
        for t, v in zip(self.t.args.args[::-1][:len(self.t.args.args)-len(arg_types)], self.t.args.defaults[::-1]):
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
        self.space = 101
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
                if util.DEBUG and 0:
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

blocks = []

def translate(desc, flow, stack=None, this=None):
    bs = BlockStatus(flow.clone())    
    
    new_stack = []
    if stack is not None:
        new_stack.extend(stack)
    if this is not None:
        new_stack.append(this)
    bs.call_stack = new_stack
    del this, new_stack
    
    while True:
        t = bs.call_stack.pop()
        this = []
        
        if t is None:
            p = bs.finalise()
            util.debug(p, desc)
            return p.inst_addr()
        elif callable(t):
            t(bs, this)
        elif isinstance(t, list):
            assert not this
            this = t
        elif isinstance(t, ast.Module):
            assert False
        elif isinstance(t, ast.FunctionDef):
            def _(bs, this, t=t):
                key = len(type_impl.functions)
                type_impl.functions.append(Function(t))
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
                if t.id == 'None':
                    this.append(type_impl.NoneType.load())
                else:
                    pos = bs.flow
                    bs.code += isa.mov(registers.rax, MemRef(registers.rbp, bs.flow.get_var_loc(t.id)))
                    rax_type = bs.flow.get_var_type(t.id)
                    bs.code += isa.push(registers.rax)
                    bs.flow.stack.append(rax_type)
            elif isinstance(t.ctx, ast.Store):
                assert t.id != 'None'
                bs.code += isa.pop(registers.rax)
                rax_type = bs.flow.stack.pop()
                bs.code += isa.mov(MemRef(registers.rbp, bs.flow.get_var_loc(t.id)), registers.rax)
                bs.flow.set_var_type(t.id, rax_type)
            else:
                assert False, t.ctx
        elif isinstance(t, ast.If):
            @util.memoize
            def make_b(flow, t=t):
                return translate("if_b", flow, this=[
                    t.body,
                    lambda bs, this: util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_c(bs.flow)))),
                    None,
                ])
            
            @util.memoize
            def make_c(flow, stack=list(bs.call_stack)):
                return translate("if_c", flow, stack=stack)
            
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
            @util.memoize
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
                
                return translate("while_a", flow, this=[
                    t.test,
                    _,
                    None,
                ])
            
            @util.memoize
            def make_b(flow, t=t):
                return translate("while_b", flow, this=[
                    t.body,
                    lambda bs, this: util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_a(bs.flow)))),
                    None,
                ])
            
            number = random.randrange(1000)
            
            @util.memoize
            def make_c(flow, stack=list(bs.call_stack), number=number):
                def _(bs, this):
                    removed = bs.flow.ctrl_stack.pop()
                    assert removed[2] == number
                return translate("while_c", flow, stack=stack, this=[
                    _,
                ])
            
            bs.flow.ctrl_stack.append([
                lambda bs, this, flow=bs.flow, make_a=make_a: util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_a(flow)))), # continue
                lambda bs, this, flow=bs.flow, make_c=make_c: util.Redirection(bs.code, lambda caller: caller.replace(util.get_jmp(make_c(flow)))), # break
                number, # used for sanity check while avoiding circular reference
            ])
            
            this.append(bs.flow.ctrl_stack[-1][0]) # continue
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
                elif isinstance(op, ast.Is): # XXX
                    bs.code += isa.jne(label)
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
                    elif isinstance(rdi_type, type(type_impl.Str)):
                        bs.code += isa.mov(registers.rax, util.print_string_addr)
                    elif isinstance(rdi_type, type(type_impl.NoneType)):
                        type_impl.Str.load_constant("None")(bs, this)
                        assert bs.flow.stack.pop() is type_impl.Str
                        bs.code += isa.mov(registers.rdi, registers.rax)
                        bs.code += isa.mov(registers.rax, util.print_string_addr)
                    else:
                        assert False, rdi_type
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
                right_type = bs.flow.stack.pop()
                left_type = bs.flow.stack.pop()
                
                if isinstance(t.op, ast.Add): r = (left_type + right_type)
                elif isinstance(t.op, ast.Sub): r = (left_type - right_type)
                elif isinstance(t.op, ast.Mult): r = (left_type * right_type)
                elif isinstance(t.op, ast.Div): r = (left_type / right_type)
                elif isinstance(t.op, ast.FloorDiv): r = (left_type // right_type)
                elif isinstance(t.op, ast.Mod): r = (left_type % right_type)
                elif isinstance(t.op, ast.BitOr): r = (left_type | right_type)
                else: assert False, t.op
                
                this.append(r)
        elif isinstance(t, ast.Call):
            assert not t.keywords
            assert not t.starargs
            assert not t.kwargs
            
            this.append(t.func)
            
            @this.append
            def _(bs, this, t=t):
                if len(t.args) == 1 and isinstance(t.args[0], (ast.Num, ast.Str)):
                    c = bs.flow.stack[-1].call_const(t.args[0])
                    if c is not None:
                        this.append(c)
                        return
                
                for arg in t.args:
                    this.append(arg)
                
                @this.append
                def _(bs, this, t=t):
                    this.append(bs.flow.stack[-1 - len(t.args)](tuple(bs.flow.stack[-1 - i] for i, a in enumerate(t.args))))
            
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
                this.append(ast.Name(id='None', ctx=ast.Load()))
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
        elif isinstance(t, ast.Assert):
            this.append(t.test)
            @this.append
            def _(bs, this, t=t):
                assert bs.flow.stack.pop() is type_impl.Int
                bs.code += isa.pop(registers.rax)
                bs.code += isa.test(registers.rax, registers.rax)
                skip = bs.program.get_unique_label()
                bs.code += isa.jnz(skip)
            # we're assuming print doesn't split this block
            this.append(ast.Print(dest=None, values=[ast.Str(t.msg.s if t.msg is not None else "assert error")], nl=True))
            @this.append
            def _(bs, this):
                bs.code += isa.ud2()
                bs.code += skip
        elif isinstance(t, ast.List):
            assert isinstance(t.ctx, ast.Load)
            this.append(type_impl.List.load())
            for e in t.elts:
                this.append(e)
                @this.append
                def _(bs, this):
                    bs.code += isa.pop(registers.rax)
                    rax_type = bs.stack.pop()
                    bs.code += isa.pop(registers.rdi)
                    rdi_type = bs.stack.pop()
                    bs.code += isa.push(registers.rdi)
                    bs.stack.append(rdi_type)
                    bs.code += isa.push(registers.rdi)
                    bs.stack.append(rdi_type)
                    bs.code += isa.push(registers.rax)
                    bs.stack.append(rax_type)
                this.append(type_impl.List.append())
        elif isinstance(t, ast.Import):
            for name in t.names:
                assert isinstance(name, ast.alias)
                if name.name == "ctypes":
                    def _(bs, this):
                        import myctypes
                        bs.code += isa.push(0)
                        bs.flow.stack.append(myctypes.CtypesModule)
                    this.append(ast.Assign(
                        targets=[ast.Name(id=name.name if name.asname is None else name.asname, ctx=ast.Store())],
                        value=_
                    ))
                    continue
                this.append(ast.Assign(
                    targets=[ast.Name(id=name.name if name.asname is None else name.asname, ctx=ast.Store())],
                    value=ast.Call(func=ast.Name(id='__import__', ctx=ast.Load()), args=[ast.Str(s=name.name)], keywords=[], starargs=None, kwargs=None)
                ))
        elif isinstance(t, ast.Attribute):
            if isinstance(t.ctx, ast.Load):
                this.append(t.value)
                @this.append
                def _(bs, this, t=t):
                    this.append(bs.flow.stack[-1].getattr_const_string(t.attr))
            elif isinstance(t.ctx, ast.Store):
                assert False
            else:
                assert False
        else:
            assert False, t
        bs.call_stack.extend(reversed(this))
