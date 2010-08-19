from __future__ import division

import ast
import random
import copy

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
        def _(bs):
            util.add_redirection(bs.code, lambda rdi: util.get_call(self.produced[arg_types]))
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

def Function(t):
    #if is_generator(t):
    #    return Generator(t)
    return NonGenerator(t)

class NonGenerator(Executable):
    def __init__(self, t):
        Executable.__init__(self)
        assert isinstance(t, ast.FunctionDef)
        self.t = t
        self.is_generator = is_generator(self.t)
    @property
    def name(self):
        return self.t.name
    def pre(self, arg_types):
        assert not self.t.args.vararg
        assert not self.t.args.kwarg
        this = []
        
        if self.is_generator:
            # store rsp, rip
            pass
        
        # isa.push(registers.rip)
        # isa.jmp(<here>)
        @this.append
        def _(bs):
            bs.code += isa.push(registers.rbp)
            bs.code += isa.mov(registers.rbp, registers.rsp)
            bs.code += isa.sub(registers.rsp, bs.flow.space * 8)
        # pop uses rsp
        # memory access uses rbp
        # we need old stack current memory access
        assert len(arg_types) <= len(self.t.args.args), [arg_types, self.t.args.args]
        for i, (arg_type, t) in enumerate(reversed(zip(arg_types, self.t.args.args))):
            assert isinstance(t, ast.Name)
            assert isinstance(t.ctx, ast.Param)
            def _(bs, arg_type=arg_type, i=i):
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

#class Generator(object):

class Flow(object):
    def __init__(self, executable):
        self.executable = executable
        self.space = 1000
        self.vars = {}
        #self.spaces = [0] * self.space
        self.var_type_impl = {}
        self.stack = []
        self.ctrl_stack = []
    
    def __repr__(self):
        return "Flow<%r>" % self.__dict__
    
    def __hash__(self):
        return 0
        return id(self.executable) ^ self.space ^ util.hash_dict(self.vars) ^ util.hash_dict(self.var_type_impl)
    def __eq__(self, other):
        if not isinstance(other, Flow):
            return False
        #if self.__dict__ == other.__dict__:
        #    print self, other, self.__dict__ == other.__dict__
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
        #r.spaces[:] = self.spaces
        r.var_type_impl.update(self.var_type_impl)
        r.stack[:] = self.stack
        r.ctrl_stack[:] = self.ctrl_stack
        return r

class FrozenFlow(object):
    def __hash__(self):
        v = 1361760622
        for item in self.dict.iteritems():
            pass
        return 
    def unfreeze(self):
        return Flow

def reverse_reference(t):
    t = copy.copy(t)
    if isinstance(t.ctx, ast.Load):
        t.ctx = ast.Store()
    elif isinstance(t.ctx, ast.Store):
        t.ctx = ast.Load()
    else:
        assert False, t.ctx
    return t

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

def _is_generator(x):
    if isinstance(x, ast.Yield):
        return True
    elif isinstance(x, list):
        return any(_is_generator(y) for y in x)
    elif isinstance(x, ast.FunctionDef):
        return False
    elif isinstance(x, ast.AST):
        return any(_is_generator(v) for k, v in ast.iter_fields(x))
    else:
        return False

def is_generator(x):
    assert isinstance(x, ast.FunctionDef)
    return _is_generator(x.body)

def translate(desc, flow, stack=None, this=None):
    #print "translate", desc, flow, stack, this
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
        bs.this = []
        
        if t is None:
            p = bs.finalise()
            util.debug(p, desc)
            return p.inst_addr()
        elif callable(t):
            t(bs)
        elif isinstance(t, list):
            assert not bs.this
            bs.this = t
        elif isinstance(t, ast.Module):
            assert False
        elif isinstance(t, ast.Lambda):
            key = len(type_impl.functions)
            type_impl.functions.append(Function(ast.FunctionDef(
                name="<lambda>",
                args=t.args,
                body=ast.Return(t.body),
                decorator_list=[],
            )))
            bs.code += isa.mov(registers.rax, key)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(type_impl.Function)
        elif isinstance(t, ast.FunctionDef):
            def _(bs, t=t):
                key = len(type_impl.functions)
                type_impl.functions.append(Function(t))
                bs.code += isa.mov(registers.rax, key)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(type_impl.Function)
            # could be optimized
            bs.this.append(ast.Assign(
                targets=[ast.Name(id=t.name, ctx=ast.Store())],
                value=_,
            ))
        elif isinstance(t, ast.AugAssign):
            bs.this.append(ast.Assign(
                targets=[t.target],
                value=ast.BinOp(left=reverse_reference(t.target), op=t.op, right=t.value),
            ))
        elif isinstance(t, ast.Assign):
            bs.this.append(t.value)
            
            if len(t.targets) > 1:
                @bs.this.append
                def _(bs, t=t):
                    for target in t.targets:
                        assert isinstance(target.ctx, ast.Store)
                        
                        @bs.this.append
                        def _(bs):
                            type = bs.flow.stack[-1]
                            
                            for i in xrange(type.size):
                                bs.code += isa.push(MemRef(registers.rsp, 8*type.size - 8))
                            
                            bs.flow.stack.append(type)
                        
                        bs.this.append(target)
                    
                    @bs.this.append
                    def _(bs):
                        type = bs.flow.stack.pop()
                        for i in xrange(type.size):
                            bs.code += isa.pop(registers.rax)
            else:
                bs.this.append(t.targets[0])
        elif isinstance(t, ast.Expr):
            bs.this.append(t.value)
            @bs.this.append
            def _(bs, t=t):
                type = bs.flow.stack.pop()
                for i in xrange(type.size):
                    bs.code += isa.pop(registers.rax)
        elif isinstance(t, ast.Num):
            if isinstance(t.n, float):
                o = type_impl.Float
            elif isinstance(t.n, int):
                o = type_impl.Int
            else:
                assert False, t.n
            bs.this.append(o.load_constant(t.n))
        elif isinstance(t, ast.Name):
            if isinstance(t.ctx, ast.Load):
                if t.id == 'None':
                    bs.this.append(type_impl.NoneType.load())
                else:
                    try:
                        type, loc = bs.flow.get_var_type(t.id), bs.flow.get_var_loc(t.id)
                    except KeyError:
                        # scope scope scope scope scope scope scope snope testing testing one two three
                        pass
                        raise
                        bs.code += isa.push(0)
                        bs.flow.stack.append(type_impl.Function)
                    else:
                        for i in xrange(type.size):
                            bs.code += isa.mov(registers.rax, MemRef(registers.rbp, loc + i * 8))
                            bs.code += isa.push(registers.rax)
                        bs.flow.stack.append(type)
            elif isinstance(t.ctx, ast.Store):
                assert t.id != 'None'
                type = bs.flow.stack.pop()
                bs.flow.set_var_type(t.id, type)
                for i in reversed(xrange(type.size)):
                    bs.code += isa.pop(registers.rax)
                    bs.code += isa.mov(MemRef(registers.rbp, bs.flow.get_var_loc(t.id) + i * 8), registers.rax)
            else:
                assert False, t.ctx
        elif isinstance(t, ast.If) or isinstance(t, ast.IfExp):
            # instead of memoize, avoid jumps with a jump from new to midway through original if flow is the same
            
            @util.memoize
            def make_post(flow, stack=list(bs.call_stack)):
                return translate("if_post", flow, stack=stack)
            
            #@util.memoize
            def make_orelse(flow, t=t, make_post=make_post):
                return translate("if_orelse", flow, this=[
                    t.orelse,
                    lambda bs: util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_post(bs.flow))),
                    None,
                ])
            
            #@util.memoize
            def make_body(flow, t=t, make_post=make_post):
                return translate("if_body", flow, this=[
                    t.body,
                    lambda bs: util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_post(bs.flow))),
                    None,
                ])
            
            bs.this.append(t.test)
            @bs.this.append
            def _(bs, t=t):
                type = bs.flow.stack.pop()
                assert type is type_impl.Int, type
                bs.code += isa.pop(registers.rax)
                bs.code += isa.test(registers.rax, registers.rax)
                skip = bs.program.get_unique_label()
                bs.code += isa.jz(skip)
                util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_body(bs.flow)))
                bs.code += skip
                util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_orelse(bs.flow)))
            bs.this.append(None)
        elif isinstance(t, ast.While):
            @util.memoize
            def make_a(flow, t=t):
                def _(bs):
                    bs.code += isa.pop(registers.rax)
                    rax_type = bs.flow.stack.pop()
                    bs.code += isa.test(registers.rax, registers.rax)
                    skip = bs.program.get_unique_label()
                    bs.code += isa.jz(skip)
                    util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_b(bs.flow)))
                    bs.code += skip
                    util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_c(bs.flow)))
                
                return translate("while_a", flow, this=[
                    t.test,
                    _,
                    None,
                ])
            
            @util.memoize
            def make_b(flow, t=t):
                return translate("while_b", flow, this=[
                    t.body,
                    lambda bs: util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_a(bs.flow))),
                    None,
                ])
            
            number = random.randrange(1000)
            
            @util.memoize
            def make_c(flow, stack=list(bs.call_stack), number=number):
                def _(bs):
                    removed = bs.flow.ctrl_stack.pop()
                    assert removed[2] == number
                return translate("while_c", flow, stack=stack, this=[
                    _,
                ])
            
            bs.flow.ctrl_stack.append([
                lambda bs, flow=bs.flow, make_a=make_a: util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_a(flow))), # continue
                lambda bs, flow=bs.flow, make_c=make_c: util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_c(flow))), # break
                number, # used for sanity check while avoiding circular reference
            ])
            
            bs.this.append(bs.flow.ctrl_stack[-1][0]) # continue
            bs.this.append(None)
        elif isinstance(t, ast.Compare):
            assert len(t.ops) == 1 and len(t.comparators) == 1
            bs.this.append(t.left)
            bs.this.append(t.comparators[0])
            op = t.ops[0]
            if isinstance(op, ast.Is) or isinstance(op, ast.IsNot):
                @bs.this.append
                def _(bs, op=op):
                    regs = [registers.rbx, registers.rcx, registers.rdx, registers.rdi, registers.rsi, registers.r9]
                    
                    right_registers = []
                    left_registers = []
                    
                    right_type = bs.flow.stack.pop()
                    for i in xrange(right_type.size):
                        reg = regs.pop(0)
                        bs.code += isa.pop(reg)
                        right_registers.append(reg)
                    left_type = bs.flow.stack.pop()
                    for i in xrange(left_type.size):
                        reg = regs.pop(0)
                        bs.code += isa.pop(reg)
                        left_registers.append(reg)
                    
                    if right_type is not left_type:
                        bs.code += isa.push(0 if isinstance(op, ast.Is) else 1)
                    else:
                        bs.code += isa.mov(registers.rax, 1 if isinstance(op, ast.Is) else 0)
                        bs.code += isa.mov(registers.r15, 0 if isinstance(op, ast.Is) else 1)
                        for reg_r, reg_l in zip(right_registers, left_registers):
                            bs.code += isa.cmp(reg_r, reg_l)
                            bs.code += isa.cmovne(registers.rax, registers.r15)
                        bs.code += isa.push(registers.rax)
                    bs.flow.stack.append(type_impl.Int)
            else:
                @bs.this.append
                def _(bs, t=t):
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
                bs.this.append(value)
                @bs.this.append
                def _(bs, value=value):
                    type = bs.flow.stack.pop()
                    
                    if type is type_impl.Int:
                        bs.code += isa.pop(registers.rdi)
                        bs.code += isa.mov(registers.rax, util.print_int64_addr)
                    elif type is type_impl.Float:
                        bs.code += isa.pop(registers.rdi)
                        bs.code += isa.mov(registers.rax, util.print_double_addr)
                    elif type is type_impl.Str:
                        bs.code += isa.pop(registers.rdi)
                        bs.code += isa.mov(registers.rax, util.print_string_addr)
                    elif type is type_impl.NoneType:
                        type_impl.Str.load_constant("None")(bs)
                        assert bs.flow.stack.pop() is type_impl.Str
                        bs.code += isa.pop(registers.rax)
                        bs.code += isa.mov(registers.rdi, registers.rax)
                        bs.code += isa.mov(registers.rax, util.print_string_addr)
                    else:
                        assert False, rdi_type
                    bs.code += isa.mov(registers.r12, registers.rsp)
                    bs.code += isa.and_(registers.rsp, -16)
                    bs.code += isa.call(registers.rax)
                    bs.code += isa.mov(registers.rsp, registers.r12)
            if t.nl:
                @bs.this.append
                def _(bs):
                    bs.code += isa.mov(registers.rax, util.print_nl_addr)
                    bs.code += isa.mov(registers.r12, registers.rsp)
                    bs.code += isa.and_(registers.rsp, -16)
                    bs.code += isa.call(registers.rax)
                    bs.code += isa.mov(registers.rsp, registers.r12)
        elif isinstance(t, ast.UnaryOp):
            bs.this.append(t.operand)
            @bs.this.append
            def _(bs, t=t):
                type = bs.flow.stack.pop()
                if isinstance(t.op, ast.USub): r = -type
                else: assert False, t.op
                bs.this.append(r)
        elif isinstance(t, ast.BinOp):
            bs.this.append(t.left)
            bs.this.append(t.right)
            @bs.this.append
            def _(bs, t=t):
                right_type = bs.flow.stack.pop()
                left_type = bs.flow.stack.pop()
                
                if isinstance(t.op, ast.Add): r = left_type + right_type
                elif isinstance(t.op, ast.Sub): r = left_type - right_type
                elif isinstance(t.op, ast.Mult): r = left_type * right_type
                elif isinstance(t.op, ast.Div): r = left_type / right_type
                elif isinstance(t.op, ast.FloorDiv): r = left_type // right_type
                elif isinstance(t.op, ast.Mod): r = left_type % right_type
                elif isinstance(t.op, ast.Pow): r = left_type ** right_type
                elif isinstance(t.op, ast.BitAnd): r = left_type & right_type
                elif isinstance(t.op, ast.BitOr): r = left_type | right_type
                elif isinstance(t.op, ast.BitXor): r = left_type ^ right_type
                elif isinstance(t.op, ast.LShift): r = left_type << right_type
                elif isinstance(t.op, ast.RShift): r = left_type >> right_type
                else: assert False, t.op
                
                bs.this.append(r)
        elif isinstance(t, ast.BoolOp):
            @util.memoize
            def make_post(flow, stack=list(bs.call_stack)):
                return translate("boolop_post", flow, stack=stack)
            
            for value in t.values[:-1]:
                bs.this.append(value)
                @bs.this.append
                def _(bs):
                    type = bs.flow.stack[-1]
                    for i in xrange(type.size):
                        bs.code += isa.push(MemRef(registers.rsp, 8 * (type.size - 1))) # check this!
                    bs.flow.stack.append(type)
                    def _(bs):
                        assert bs.flow.stack[-1] is bs.flow.stack[-2] is type
                    bs.this.append(
                        ast.Call(
                            func=ast.Attribute(
                                value=_,
                                attr='__nonzero__',
                                ctx=ast.Load(),
                                ),
                            args=[],
                            keywords=[],
                            starargs=None,
                            kwargs=None,
                            ),
                        )
                @bs.this.append
                def _(bs, t=t, make_post=make_post):
                    assert bs.flow.stack.pop() is type_impl.Int
                    bs.code += isa.pop(registers.rax)
                    skip = bs.program.get_unique_label()
                    bs.code += isa.test(registers.rax, registers.rax)
                    if isinstance(t.op, ast.And):
                        bs.code += isa.jnz(skip)
                    elif isinstance(t.op, ast.Or):
                        bs.code += isa.jz(skip)
                    else:
                        assert False
                    util.add_redirection(bs.code, lambda rdi, flow=bs.flow.clone(): util.get_jmp(make_post(flow)))
                    bs.code += skip
                    type = bs.flow.stack.pop()
                    for i in xrange(type.size):
                        bs.code += isa.pop(registers.rax)
            
            bs.this.append(t.values[-1])
            # these next two can be eliminated at the cost of branching
            bs.this.append(lambda bs, make_post=make_post: util.add_redirection(bs.code, lambda rdi, flow=bs.flow.clone(): util.get_jmp(make_post(flow))))
            bs.this.append(None)
        elif isinstance(t, ast.Call):
            assert not t.keywords
            assert not t.starargs
            assert not t.kwargs
            
            bs.this.append(t.func)
            
            @bs.this.append
            def _(bs, t=t):
                if len(t.args) == 1 and isinstance(t.args[0], (ast.Num, ast.Str)):
                    c = bs.flow.stack[-1].call_const(t.args[0])
                    if c is not None:
                        bs.this.append(c)
                        return
                
                bs.this.extend(t.args)
                
                @bs.this.append
                def _(bs, t=t):
                    arg_types = tuple(bs.flow.stack[-1 - i] for i, a in enumerate(t.args))[::-1]
                    bs.this.append(bs.flow.stack[-1 - len(t.args)](arg_types))
            
        elif isinstance(t, ast.Tuple):
            if isinstance(t.ctx, ast.Load):
                bs.this.extend(t.elts)
                
                @bs.this.append
                def _(bs, t=t):
                    arg_types = tuple(bs.flow.stack[-1 - i] for i, a in enumerate(t.elts))[::-1]
                    bs.this.append(type_impl.ProtoTuple(arg_types).load())
            elif isinstance(t.ctx, ast.Store):
                type = bs.flow.stack[-1]
                
                bs.this.append(type.store())
                
                for elt in t.elts:
                    assert isinstance(elt, ast.Name)
                    assert isinstance(elt.ctx, ast.Store), elt.ctx
                bs.this.extend(t.elts)
            else:
                assert False, t.ctx
        elif isinstance(t, ast.Subscript):
            if isinstance(t.ctx, ast.Load):
                assert isinstance(t.slice, ast.Index)
                bs.this.append(t.value)
                
                bs.this.append(t.slice.value)
                
                @bs.this.append
                def _(bs, t=t):
                    bs.this.append(bs.flow.stack[-2].getitem())
            elif isinstance(t.ctx, ast.Store):
                assert isinstance(t.slice, ast.Index)
                bs.this.append(t.value)
                
                bs.this.append(t.slice.value)
                
                @bs.this.append
                def _(bs, t=t):
                    bs.this.append(bs.flow.stack[-2].setitem())
            else:
                assert False, t.ctx
        elif isinstance(t, ast.Continue):
            if not bs.flow.ctrl_stack[-1][0]:
                raise SyntaxError
            bs.this.append(bs.flow.ctrl_stack[-1][0])
        elif isinstance(t, ast.Break):
            if not bs.flow.ctrl_stack[-1][1]:
                raise SyntaxError
            bs.this.append(bs.flow.ctrl_stack[-1][1])
        elif isinstance(t, ast.Str):
            bs.this.append(type_impl.Str.load_constant(t.s))
        elif isinstance(t, ast.Return):
            if t.value is None:
                bs.this.append(ast.Name(id='None', ctx=ast.Load()))
            else:
                bs.this.append(t.value)
            @bs.this.append
            def _(bs):
                type = bs.flow.stack.pop()
                
                if type.size >= 1:
                    bs.code += isa.pop(registers.r13)
                if type.size >= 2:
                    bs.code += isa.pop(registers.r14)
                if type.size >= 3:
                    assert False
                
                bs.code += isa.mov(registers.r12, type.id)
                
                # leave
                bs.code += isa.mov(registers.rsp, registers.rbp)
                bs.code += isa.pop(registers.rbp)
                
                assert not bs.flow.stack, bs.flow.stack
                
                bs.code += isa.ret() # return address
            
            bs.this.append(None)
        elif isinstance(t, ast.Pass):
            pass # haha
        elif isinstance(t, ast.Assert):
            skip = bs.program.get_unique_label()
            bs.this.append(t.test)
            @bs.this.append
            def _(bs, t=t, skip=skip):
                assert bs.flow.stack.pop() is type_impl.Int
                bs.code += isa.pop(registers.rax)
                bs.code += isa.test(registers.rax, registers.rax)
                bs.code += isa.jnz(skip)
            # we're assuming print doesn't split this block
            bs.this.append(ast.Print(dest=None, values=[ast.Str(t.msg.s if t.msg is not None else "assert error")], nl=True))
            @bs.this.append
            def _(bs, skip=skip):
                bs.code += isa.ud2()
                bs.code += skip
        elif isinstance(t, ast.List):
            assert isinstance(t.ctx, ast.Load)
            import mypyable
            def _gettype(bs):
                bs.flow.stack.append(mypyable.list_impl)
                assert mypyable.list_impl.size == 0
            bs.this.append(
                ast.Call(
                    func=_gettype,
                    args=[],
                    keywords=[],
                    starargs=None,
                    kwargs=None,
                    ),
                )
            for e in t.elts:
                def _(bs):
                    assert bs.flow.stack[-1] is type_impl.protoinstances[mypyable.list_impl]
                bs.this.append(
                    ast.Call(
                        func=ast.Attribute(
                            value=_,
                            attr='append',
                            ctx=ast.Load(),
                            ),
                        args=[e],
                        keywords=[],
                        starargs=None,
                        kwargs=None,
                        ),
                    )
        elif isinstance(t, ast.Import):
            for name in t.names:
                assert isinstance(name, ast.alias)
                if name.name == "ctypes":
                    def _(bs):
                        import myctypes
                        bs.flow.stack.append(myctypes.CtypesModule)
                    bs.this.append(ast.Assign(
                        targets=[ast.Name(id=name.name if name.asname is None else name.asname, ctx=ast.Store())],
                        value=_
                    ))
                    continue
                if name.name == "_pyable":
                    def _(bs):
                        import mypyable
                        bs.flow.stack.append(mypyable.PyableModule)
                    bs.this.append(ast.Assign(
                        targets=[ast.Name(id=name.name if name.asname is None else name.asname, ctx=ast.Store())],
                        value=_
                    ))
                    continue
                bs.this.append(ast.Assign(
                    targets=[ast.Name(id=name.name if name.asname is None else name.asname, ctx=ast.Store())],
                    value=ast.Call(func=ast.Name(id='__import__', ctx=ast.Load()), args=[ast.Str(s=name.name)], keywords=[], starargs=None, kwargs=None)
                ))
        elif isinstance(t, ast.Attribute):
            if isinstance(t.ctx, ast.Load):
                bs.this.append(t.value)
                @bs.this.append
                def _(bs, t=t):
                    bs.this.append(bs.flow.stack[-1].getattr_const_string(t.attr))
            elif isinstance(t.ctx, ast.Store):
                bs.this.append(t.value)
                @bs.this.append
                def _(bs, t=t):
                    bs.this.append(bs.flow.stack[-1].setattr_const_string(t.attr))
            elif isinstance(t.ctx, ast.Del):
                bs.this.append(t.value)
                @bs.this.append
                def _(bs, t=t):
                    bs.this.append(bs.flow.stack[-1].delattr_const_string(t.attr))
            else:
                assert False
        elif isinstance(t, ast.ClassDef):
            #bs.flow.class_stack
            t.name
            t.bases
            t.body
            t.decorator_list
        elif isinstance(t, ast.Delete):
            for target in t.targets:
                assert isinstance(target.ctx, ast.Del)
                bs.this.append(target)
        else:
            assert False, t
        bs.call_stack.extend(reversed(bs.this))

type_impl.functions.append(Function(ast.FunctionDef(
    name="null_func",
    args=ast.arguments(
        args=[],
        vararg=None,
        kwarg=None,
        defaults=[],
    ),
    body=[],
    decorator_list=[],
)))
