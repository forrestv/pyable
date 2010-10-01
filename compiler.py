from __future__ import division

import ast
import random
import copy
import struct

import type_impl
import util

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
import corepy.arch.x86_64.platform as platform
from corepy.arch.x86_64.lib.memory import MemRef
from corepy.lib.extarray import extarray
from corepy.arch.x86_64.platform.linux.x86_64_exec import make_executable


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
        def _(bs):
            bs.code += isa.push(registers.rbp)
            bs.code += isa.mov(registers.rbp, registers.rsp)
            bs.code += isa.sub(registers.rsp, bs.flow.space * 32)
        # pop uses rsp
        # memory access uses rbp
        # we need old stack current memory access
        assert len(arg_types) <= len(self.t.args.args), [arg_types, self.t.args.args, self.name]
        pos = 16
        for i, (arg_type, t) in enumerate(reversed(zip(arg_types, self.t.args.args))):
            assert isinstance(t, ast.Name)
            assert isinstance(t.ctx, ast.Param)
            def _(bs, arg_type=arg_type, pos=pos):
                bs.flow.stack.append(arg_type)
                for i in reversed(xrange(arg_type.size)):
                    bs.code += isa.push(MemRef(registers.rbp, pos + i * 8))
            pos += 8 * arg_type.size
            this.append(ast.Assign(
                targets=[ast.Name(id=t.id, ctx=ast.Store())],
                value=_,
            ))
            # pop memref(registers.rbp, -x)
        @this.append
        def _(bs, pos=pos):
            bs.code += isa.mov(registers.rax, MemRef(registers.rbp, pos))
            bs.code += isa.mov(MemRef(registers.rbp, -8), registers.rax)
        for t, v in zip(self.t.args.args[::-1][:len(self.t.args.args)-len(arg_types)], self.t.args.defaults[::-1]):
            this.append(ast.Assign(
                targets=[ast.Name(id=t.id, ctx=ast.Store())],
                value=v,
            ))
        @this.append
        def _(bs):
            @bs.flow.try_stack.append
            def _(bs):
                type = bs.flow.stack.pop()
                
                if type.size >= 1:
                    bs.code += isa.pop(registers.r13)
                if type.size >= 2:
                    bs.code += isa.pop(registers.r14)
                if type.size >= 3:
                    assert False
                
                bs.code += isa.mov(registers.r12, ~type.id)
                
                #assert not bs.flow.stack, bs.flow.stack
                
                # leave
                bs.code += isa.mov(registers.rsp, registers.rbp)
                bs.code += isa.pop(registers.rbp)
                
                bs.code += isa.ret() # return address
                
                bs.this.append(None)
            @bs.flow.return_stack.append
            def _(bs):
                type = bs.flow.stack.pop()
                
                if type.size >= 1:
                    bs.code += isa.pop(registers.r13)
                if type.size >= 2:
                    bs.code += isa.pop(registers.r14)
                if type.size >= 3:
                    assert False
                
                bs.code += isa.mov(registers.r12, type.id)
                
                assert not bs.flow.stack, bs.flow.stack
                
                # leave
                bs.code += isa.mov(registers.rsp, registers.rbp)
                bs.code += isa.pop(registers.rbp)
                
                bs.code += isa.ret() # return address
                
                bs.this.append(None)
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
        self.allocd_locals = False
        self.class_stack = []
        self.try_stack = []
        self.return_stack = []
    
    def __repr__(self):
        return "Flow<%r>" % self.__dict__
    
    def __hash__(self):
        return hash(tuple(self.stack))
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
            self.vars[name] = len(self.vars) * 32
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
        r.allocd_locals = self.allocd_locals
        r.class_stack[:] = self.class_stack
        r.try_stack[:] = self.try_stack
        r.return_stack[:] = self.return_stack
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
    
    def finalise(self, desc):
        
        def check(a, b):
            if not isinstance(a, isa.push): return False
            if not isinstance(b, isa.pop): return False
            return a._operands[0] is b._operands[0]
        while True:
            old = self.code
            res = self.program.get_stream()
            for i in xrange(len(old)):
                if i != len(old) - 1 and check(old[i], old[i+1]):
                        pass
                elif i != 0 and check(old[i-1], old[i]):
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
        util.debug(self.program, desc)
        #return self.program.inst_addr()
        
        global data_pos
        data[data_pos:data_pos+len(self.program.render_code)] = self.program.render_code
        #print data.buffer_info()
        pos = data_pos
        res = data.buffer_info()[0] + data_pos
        data_pos += len(self.program.render_code)
        #if data_pos % 512:
        #    data_pos += 512 - data_pos % 512
        #print "BUFFER", data[:data_pos]
        data.references.append(self.program.render_code.references)
        self.program.render_code = OffsetListProxy(data, pos)
        return res

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

data = extarray('B', '\xff'*100000000)
data.references = []
data_pos = 0
make_executable(*data.buffer_info())

def alloc_locals(bs):
    if bs.flow.allocd_locals:
        return
    
    # needs to convert!
    
    type_impl.Scope.create()(bs)
    
    @bs.this.append
    def _(bs):
        bs.flow.allocd_locals = True

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
        if util.DEBUG:
            print
            print bs.call_stack
            print util.dump(t)
        
        if t is None:
            return bs.finalise(desc)
        elif callable(t):
            t(bs)
        elif isinstance(t, list):
            assert not bs.this
            bs.this = t
        elif isinstance(t, ast.Module):
            assert False
        elif isinstance(t, ast.Lambda):
            alloc_locals(bs)
            key = len(type_impl.functions)
            type_impl.functions.append(Function(ast.FunctionDef(
                name="<lambda>",
                args=t.args,
                body=ast.Return(t.body),
                decorator_list=[],
            )))
            bs.code += isa.mov(registers.rax, key)
            bs.code += isa.push(registers.rax)
            bs.code += isa.mov(registers.rax, MemRef(registers.rbp, -8))
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(type_impl.Function)
        elif isinstance(t, ast.FunctionDef):
            alloc_locals(bs)
            def _(bs, t=t):
                key = len(type_impl.functions)
                type_impl.functions.append(Function(t))
                bs.code += isa.mov(registers.rax, key)
                bs.code += isa.push(registers.rax)
                bs.code += isa.mov(registers.rax, MemRef(registers.rbp, -8))
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
                        def _(bs, target=target):
                            type = bs.flow.stack[-1]
                            
                            for i in xrange(type.size):
                                bs.code += isa.push(MemRef(registers.rsp, 8*type.size - 8))
                            
                            bs.flow.stack.append(type)
                            
                            if bs.flow.class_stack:
                                assert False
                            
                            bs.this.append(target)
                    
                    @bs.this.append
                    def _(bs):
                        type = bs.flow.stack.pop()
                        for i in xrange(type.size):
                            bs.code += isa.pop(registers.rax)
            else:
                target = t.targets[0]
                if bs.flow.class_stack:
                    assert isinstance(target, ast.Name)
                    assert len(bs.flow.class_stack) == 1
                    target = ast.Attribute(
                        value=ast.Name(
                            id=bs.flow.class_stack[0],
                            ctx=ast.Load(),
                            ),
                        attr=target.id,
                        ctx=ast.Store(),
                        )
                bs.this.append(target)
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
                elif t.id == 'True':
                    bs.this.append(type_impl.Bool.load_true())
                elif t.id == 'False':
                    bs.this.append(type_impl.Bool.load_false())
                else:
                    try:
                        if bs.flow.allocd_locals: raise KeyError
                        type = bs.flow.get_var_type(t.id)
                        if type is None: raise KeyError
                        loc = bs.flow.get_var_loc(t.id)
                    except KeyError:
                        bs.this.append(type_impl.Scope.get_name(t.id))
                    else:
                        for i in xrange(type.size):
                            bs.code += isa.mov(registers.rax, MemRef(registers.rbp, loc + i * 8))
                            bs.code += isa.push(registers.rax)
                        bs.flow.stack.append(type)
            elif isinstance(t.ctx, ast.Store):
                assert t.id != 'None'
                assert t.id != 'True'
                assert t.id != 'False'
                if bs.flow.allocd_locals or bs.flow.var_type_impl.get(t.id, "") is None:
                    bs.this.append(type_impl.Scope.set_name(t.id))
                else:
                    type = bs.flow.stack.pop()
                    bs.flow.set_var_type(t.id, type)
                    for i in reversed(xrange(type.size)):
                        bs.code += isa.pop(registers.rax)
                        bs.code += isa.mov(MemRef(registers.rbp, bs.flow.get_var_loc(t.id) + i * 8), registers.rax)
            else:
                assert False, t.ctx
        elif isinstance(t, ast.Global):
            for name in t.names:
                assert name != 'None'
                assert name != 'True'
                assert name != 'False'
                if bs.flow.allocd_locals:
                    bs.this.append(type_impl.Scope.set_global(name))
                else:
                    bs.flow.set_var_type(name, None)
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
            
            bs.this.append(
                ast.Call(
                    func=ast.Attribute(
                        value=t.test,
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
            def _(bs, t=t, make_orelse=make_orelse, make_body=make_body):
                type = bs.flow.stack.pop()
                assert type is type_impl.Int or type is type_impl.Bool, type
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
                    type = bs.flow.stack.pop()
                    assert type is type_impl.Int or type is type_impl.Bool
                    bs.code += isa.pop(registers.rax)
                    bs.code += isa.cmp(registers.rax, 0)
                    skip = bs.program.get_unique_label()
                    bs.code += isa.je(skip)
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
                lambda bs, flow=bs.flow, make_a=make_a: (util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_a(flow))), bs.this.append(None)), # continue
                lambda bs, flow=bs.flow, make_c=make_c: (util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_c(flow))), bs.this.append(None)), # break
                number, # used for sanity check while avoiding circular reference
            ])
            
            bs.this.append(bs.flow.ctrl_stack[-1][0]) # continue
        elif isinstance(t, ast.Compare):
            assert len(t.ops) == 1 and len(t.comparators) == 1
            op = t.ops[0]
            if isinstance(op, ast.Is) or isinstance(op, ast.IsNot):
                bs.this.append(t.left)
                bs.this.append(t.comparators[0])
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
                if isinstance(op, ast.Lt): r = "lt"
                elif isinstance(op, ast.LtE): r = "le"
                elif isinstance(op, ast.Eq): r = "eq"
                elif isinstance(op, ast.NotEq): r = "ne"
                elif isinstance(op, ast.Gt): r = "gt"
                elif isinstance(op, ast.GtE): r = "ge" 
                else: assert False, op
                
                #bs.this.append(t.left)
                #bs.this.append(t.right)
                
                #@bs.this.append
                #def _(bs):
                #    regs = list(good_regs)
                #    right = pop(regs)
                #    left = pop(regs)
                #    push(left)
                #    push(right)
                
                bs.this.append(
                    ast.Call(
                        func=ast.Attribute(
                            value=t.left,
                            attr='__%s__' % r,
                            ctx=ast.Load(),
                            ),
                        args=[t.comparators[0]],
                        keywords=[],
                        starargs=None,
                        kwargs=None,
                        ),
                    )
                '''
                @bs.this.append
                def _(bs, t=t):
                    op = t.ops[0]
                    bs.code += isa.pop(registers.rax)
                    rax_type = bs.flow.stack.pop()
                    assert rax_type is type_impl.Int
                    bs.code += isa.pop(registers.rbx)
                    rbx_type = bs.flow.stack.pop()
                    assert rbx_type is type_impl.Int
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
                '''
        elif isinstance(t, ast.Print):
            assert t.dest is None
            for value in t.values:
                bs.this.append(
                    ast.Call(
                        func=ast.Attribute(
                            value=value,
                            attr='__str__',
                            ctx=ast.Load(),
                            ),
                        args=[],
                        keywords=[],
                        starargs=None,
                        kwargs=None,
                        ),
                    )
                @bs.this.append
                def _(bs):
                    type = bs.flow.stack.pop()
                    
                    assert type is type_impl.Str
                    
                    bs.code += isa.pop(registers.rdi)
                    bs.code += isa.mov(registers.rax, util.print_string_addr)
                    
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
            if isinstance(t.op, ast.USub): r ="neg"
            elif isinstance(t.op, ast.UAdd): r = "pos"
            # abs
            elif isinstance(t.op, ast.Invert): r = "invert"
            
            elif isinstance(t.op, ast.Not): r = "nonzero"
            
            else: assert False, t.op
            
            bs.this.append(
                ast.Call(
                    func=ast.Attribute(
                        value=t.operand,
                        attr='__%s__' % r,
                        ctx=ast.Load(),
                        ),
                    args=[],
                    keywords=[],
                    starargs=None,
                    kwargs=None,
                    ),
                )
            
            if isinstance(t.op, ast.Not):
                @bs.this.append
                def _(bs):
                    assert bs.flow.stack[-1] is type_impl.Bool
                    true = bs.program.get_unique_label()
                    end = bs.program.get_unique_label()
                    bs.code += isa.pop(registers.rax)
                    bs.code += isa.cmp(registers.rax, 0)
                    bs.code += isa.je(true)
                    bs.code += isa.push(0)
                    bs.code += isa.jmp(end)
                    bs.code += true
                    bs.code += isa.push(1)
                    bs.code += end
        elif isinstance(t, ast.BinOp):
            if isinstance(t.op, ast.Add): r = "add"
            elif isinstance(t.op, ast.Sub): r = "sub"
            elif isinstance(t.op, ast.Mult): r = "mul"
            elif isinstance(t.op, ast.FloorDiv): r = "floordiv"
            elif isinstance(t.op, ast.Mod): r = "mod"
            # divmod
            elif isinstance(t.op, ast.Pow): r = "pow"
            elif isinstance(t.op, ast.LShift): r = "lshift"
            elif isinstance(t.op, ast.RShift): r = "rshift"
            elif isinstance(t.op, ast.BitAnd): r = "and"
            elif isinstance(t.op, ast.BitXor): r = "xor"
            elif isinstance(t.op, ast.BitOr): r = "or"
            
            elif isinstance(t.op, ast.Div): r = "div"
            # truediv
            
            else: assert False, t.op
            
            #bs.this.append(t.left)
            #bs.this.append(t.right)
            
            #@bs.this.append
            #def _(bs):
            #    regs = list(good_regs)
            #    right = pop(regs)
            #    left = pop(regs)
            #    push(left)
            #    push(right)
            
            bs.this.append(
                ast.Call(
                    func=ast.Attribute(
                        value=t.left,
                        attr='__%s__' % r,
                        ctx=ast.Load(),
                        ),
                    args=[t.right],
                    keywords=[],
                    starargs=None,
                    kwargs=None,
                    ),
                )
            
            @bs.this.append
            def _(bs, t=t, r=r):
                if util.DEBUG:
                    print "XXX", bs, t, r
                # XXX should cache left/right
                result_type = bs.flow.stack[-1]
                if result_type is type_impl.NotImplementedType:
                    bs.flow.stack.pop()
                    bs.this.append(
                        ast.Call(
                            func=ast.Attribute(
                                value=t.right,
                                attr='__r%s__' % r,
                                ctx=ast.Load(),
                                ),
                            args=[t.left],
                            keywords=[],
                            starargs=None,
                            kwargs=None,
                            ),
                        )
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
                    assert bs.flow.stack.pop() in (type_impl.Int, type_impl.Bool)
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
                    bs.this.append(type_impl.prototuples[arg_types].load())
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
                bs.this.append(t.value)
                
                bs.this.append(t.slice)
                
                #   self, index
                # swap
                #   index, self
                # getattr(-1, "__getitem__")
                #   index, __getitem__ method
                # swap
                #   __getitem__ method, index
                # call
                #   result
                
                def _(bs):
                    pass
                
                bs.this.append(util.swap)
                
                bs.this.append(ast.Attribute(value=_, attr='__getitem__', ctx=ast.Load()))
                
                bs.this.append(util.swap)
                
                bs.this.append(ast.Call(func=_, args=[_], keywords=[], starargs=None, kwargs=None, name="sub"))
            elif isinstance(t.ctx, ast.Store):
                bs.this.append(t.value)
                
                bs.this.append(t.slice.value)
                
                #   item, self, index
                # swap
                #   item, index, self
                # getattr(-1, "__getitem__")
                #   item, index, __getitem__ method
                # rev3
                #   __setitem__ method, index, item
                # call
                #   result
                
                bs.this.append(util.swap)
                
                def _(bs):
                    pass
                
                bs.this.append(ast.Attribute(value=_, attr='__setitem__', ctx=ast.Load()))
                
                bs.this.append(util.rev3)
                
                bs.this.append(ast.Call(func=_, args=[_, _], keywords=[], starargs=None, kwargs=None, name="store"))
                
                @bs.this.append
                def _(bs):
                    type = bs.flow.stack.pop()
                    for i in xrange(type.size):
                        bs.code += isa.pop(registers.rax)
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
                bs.flow.return_stack.pop()(bs)
        elif isinstance(t, ast.Raise):
            assert t.inst is None
            assert t.tback is None
            bs.this.append(t.type)
            @bs.this.append
            def _(bs):
                bs.flow.try_stack.pop()(bs)
        elif isinstance(t, ast.Pass):
            pass # haha
        elif isinstance(t, ast.Assert):
            import mypyable
            bs.this.append(ast.If(
                test=ast.UnaryOp(
                    op=ast.Not(),
                    operand=t.test,
                    ),
                body=ast.Raise(
                    type=ast.Call(
                        func=mypyable.AssertionError_impl.load,
                        args=[t.msg] if t.msg is not None else [],
                        keywords=[],
                        starargs=None,
                        kwargs=None,
                        ),
                    inst=None,
                    tback=None,
                    ),
                orelse=[],
                ))
        elif isinstance(t, ast.List):
            assert isinstance(t.ctx, ast.Load)
            import mypyable
            def _gettype(bs):
                assert mypyable.list_impl is not None, "lists haven't been bootstrapped"
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
                bs.this.append(ast.Expr(
                    ast.Call(
                        func=ast.Attribute(
                            value=util.dup,
                            attr='append',
                            ctx=ast.Load(),
                            ),
                        args=[e],
                        keywords=[],
                        starargs=None,
                        kwargs=None,
                        ),
                    ))
        elif isinstance(t, ast.Dict):
            import mypyable
            def _gettype(bs):
                assert mypyable.dict_impl is not None, "dicts haven't been bootstrapped"
                bs.flow.stack.append(mypyable.dict_impl)
                assert mypyable.dict_impl.size == 0
            bs.this.append(
                ast.Call(
                    func=_gettype,
                    args=[],
                    keywords=[],
                    starargs=None,
                    kwargs=None,
                    ),
                )
            for k, v in zip(t.keys, t.values):
                bs.this.append(ast.Expr(
                    ast.Call(
                        func=ast.Attribute(
                            value=util.dup,
                            attr='__setitem__',
                            ctx=ast.Load(),
                            ),
                        args=[k, v],
                        keywords=[],
                        starargs=None,
                        kwargs=None,
                        ),
                    ))
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
        elif isinstance(t, ast.ImportFrom):
            assert t.level == 0
            for name in t.names:
                assert isinstance(name, ast.alias)
                if name.name:
                    pass
        elif isinstance(t, ast.Attribute):
            if isinstance(t.ctx, ast.Load):
                bs.this.append(t.value)
                @bs.this.append
                def _(bs, t=t):
                    bs.this.append(bs.flow.stack[-1].const_getattr(t.attr))
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
            assert not t.decorator_list
            
            import mypyable
            
            bs.this.append(ast.Assign(
                targets=[ast.Name(id=t.name, ctx=ast.Store())],
                value=ast.Call(
                    func=mypyable.Type.load(),
                    args=[type_impl.Str.load_constant(t.name), ast.Tuple(elts=t.bases, ctx=ast.Load()), type_impl.NoneType.load()],
                    keywords=[],
                    starargs=None,
                    kwargs=None,
                    ),
            ))
            
            @bs.this.append
            def _(bs, t=t):
                bs.flow.class_stack.append(t.name)
            
            bs.this.append(t.body)
            
            @bs.this.append
            def _(bs, t=t):
                assert bs.flow.class_stack.pop() == t.name
        elif isinstance(t, ast.Delete):
            for target in t.targets:
                assert isinstance(target.ctx, ast.Del)
                bs.this.append(target)
        elif isinstance(t, ast.Index):
            bs.this.append(t.value)
            #assert Fal
        elif isinstance(t, ast.Slice):
            bs.this.append(t.lower if t.lower is not None else type_impl.NoneType.load())
            bs.this.append(t.upper if t.upper is not None else type_impl.NoneType.load())
            bs.this.append(t.step if t.step is not None else type_impl.NoneType.load())
            @bs.this.append
            def _(bs):
                type_impl.protoslices[tuple(bs.flow.stack[-3:])].load()(bs)
        elif isinstance(t, ast.Exec):
            bs.this.append(t.body)
            bs.this.append(t.globals if t.globals else type_impl.NoneType.load())
            bs.this.append(t.locals if t.locals else type_impl.NoneType.load())
            @bs.this.append
            def _(bs):
                util.rev3(bs)
                assert bs.flow.stack.pop() is type_impl.Str # body
                def exec_it(i):
                    def _(bs):
                        s = type_impl.Str.to_python(struct.pack("l", i))
                        try:
                            tree = ast.parse(s, "<string>")
                        except SyntaxError, e:
                            import mypyable
                            bs.this.append(ast.Raise(
                                type=ast.Call(
                                    func=mypyable.SyntaxError_impl.load,
                                    args=[],
                                    keywords=[],
                                    starargs=None,
                                    kwargs=None,
                                    ),
                                inst=None,
                                tback=None,
                            ))
                        else:
                            assert isinstance(tree, ast.Module)
                            assert bs.flow.stack.pop() is type_impl.NoneType # globals
                            locals_type = bs.flow.stack.pop()
                            if locals_type is type_impl.DictProxy:
                                assert locals_type.size == 1
                                                                
                                alloc_locals(bs) # HACK, we should instead put this in the scope linked list
                                
                                bs.code += isa.pop(registers.r12)
                                
                                bs.code += isa.mov(registers.rdi, 8 * 4)
                                bs.code += isa.mov(registers.rax, util.malloc_addr)
                                bs.code += isa.call(registers.rax)
                                
                                bs.code += isa.mov(MemRef(registers.rax), 0) # type
                                bs.code += isa.mov(MemRef(registers.rax, 8), registers.r12) # object
                                bs.code += isa.mov(registers.rbx, MemRef(registers.rbp, -8)) # get parent
                                bs.code += isa.mov(MemRef(registers.rax, 16), registers.rbx) # parent
                                bs.code += isa.mov(registers.rbx, -1)
                                bs.code += isa.mov(MemRef(registers.rax, 24), registers.rbx) # bitfield
                                
                                bs.code += isa.mov(MemRef(registers.rbp, -8), registers.rax)
                            elif locals_type is type_impl.NoneType:
                                pass
                            else:
                                assert False
                            bs.this.append(tree.body)
                            if locals_type is type_impl.DictProxy:
                                @bs.this.append
                                def _(bs):
                                    bs.code += isa.mov(registers.rax, MemRef(registers.rbp, -8))
                                    bs.code += isa.mov(registers.rax, MemRef(registers.rax, 16))
                                    bs.code += isa.mov(MemRef(registers.rbp, -8), registers.rax)
                    return _
                util.unlift_noncached(bs, exec_it, "exec")
        elif isinstance(t, ast.TryFinally):
            @bs.flow.try_stack.append
            def _(bs, call_stack=list(bs.call_stack), flow=bs.flow.clone(), t=t):
                # HACK, i don't want to think about the things this breaks
                bs.call_stack[:] = call_stack
                bs.flow.ctrl_stack[:] = flow.ctrl_stack
                assert bs.flow.try_stack == flow.try_stack
                
                bs.this = []
                bs.this.append(t.finalbody)
            bs.this.append(t.body)
            @bs.this.append
            def _(bs, t=t):
                bs.flow.try_stack.pop()
            bs.this.append(t.finalbody)
        elif isinstance(t, ast.TryExcept):
            @bs.flow.try_stack.append
            def _(bs, t=t, call_stack=list(bs.call_stack), flow=bs.flow.clone()):
                for handler in t.handlers:
                    assert isinstance(handler, ast.ExceptHandler)
                    if handler.type is not None:
                        bs.this.append(handler.type)
                    @bs.this.append
                    def _(bs, handler=handler):
                        if handler.type is None:
                            catch_type = None
                        else:
                            catch_type = bs.flow.stack.pop()
                            for i in xrange(catch_type.size):
                                bs.code += isa.pop(registers.rax)
                        exc_type = bs.flow.stack[-1]
                        if catch_type.isinstance(exc_type) or catch_type is None:
                            # HACK, i don't want to think about the things this breaks
                            bs.call_stack[:] = call_stack
                            bs.flow.ctrl_stack[:] = flow.ctrl_stack
                            assert bs.flow.try_stack == flow.try_stack
                            
                            #print bs.flow.stack, flow.stack
                            #for i in xrange(len(bs.flow.stack) - len(flow.stack)):
                            #    print i
                            #    util.rem1(bs)
                            
                            bs.this = []
                            
                            if handler.name is None:
                                bs.flow.stack.pop()
                                for i in xrange(exc_type.size):
                                    bs.code += isa.pop(registers.rax)
                            else:
                                bs.this.append(handler.name)
                            
                            bs.this.append(handler.body)
            bs.this.append(t.body)
            @bs.this.append
            def _(bs):
                bs.flow.try_stack.pop()
            bs.this.append(t.orelse)
        elif isinstance(t, ast.For):
            number = random.randrange(1000)
            
            @util.memoize
            def make_c_normal(flow, stack=list(bs.call_stack), number=number, t=t):
                def _(bs):
                    type = bs.flow.stack.pop()
                    for i in xrange(type.size):
                        bs.code += isa.pop(registers.rax)
                    bs.flow.return_stack.pop()
                    removed = bs.flow.ctrl_stack.pop()
                    assert removed[2] == number
                return translate("while_c", flow, stack=stack, this=[
                    _,
                    t.orelse,
                ])
            
            @util.memoize
            def make_c(flow, stack=list(bs.call_stack), number=number):
                def _(bs):
                    type = bs.flow.stack.pop()
                    for i in xrange(type.size):
                        bs.code += isa.pop(registers.rax)
                    bs.flow.return_stack.pop()
                    removed = bs.flow.ctrl_stack.pop()
                    assert removed[2] == number
                return translate("while_c", flow, stack=stack, this=[
                    _,
                ])
            
            @util.memoize
            def make_a(flow, t=t, make_c_normal=make_c_normal):
                def _(bs):
                    @bs.flow.try_stack.append
                    def _(bs):
                        import mypyable
                        if mypyable.StopIteration_impl.isinstance(bs.flow.stack[-1]):
                            # pop StopIteration
                            type = bs.flow.stack.pop()
                            for i in xrange(type.size):
                                bs.code += isa.pop(registers.rax)
                            @bs.this.append
                            def _(bs):
                                util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_c_normal(bs.flow)))
                            bs.this.append(None)
                        else:
                            util.rem1(bs)
                            bs.flow.try_stack.pop()(bs)
                    bs.this.append(
                        ast.Assign(
                            targets=[t.target],
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=util.dup,
                                    attr='next',
                                    ctx=ast.Load(),
                                    ),
                                args=[],
                                keywords=[],
                                starargs=None,
                                kwargs=None,
                                ),
                            )
                        )
                    @bs.this.append
                    def _(bs):
                        bs.flow.try_stack.pop()
                    bs.this.append(t.body)
                    @bs.this.append
                    def _(bs):
                        util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_a(bs.flow)))
                        bs.this.append(None)
                
                return translate("while_a", flow, this=[
                    _,
                    None,
                ])
            
            bs.this.append(
                ast.Call(
                    func=ast.Attribute(
                        value=t.iter,
                        attr='__iter__',
                        ctx=ast.Load(),
                        ),
                    args=[],
                    keywords=[],
                    starargs=None,
                    kwargs=None,
                    ),
                )
            @bs.flow.return_stack.append
            def for_returner(bs):
                # pop iterator
                util.rem1(bs)
                bs.flow.return_stack.pop()(bs)
            @bs.this.append
            def _(bs, make_a=make_a, make_c=make_c, number=number):
                bs.flow.ctrl_stack.append([
                    lambda bs: (util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_a(bs.flow))), bs.this.append(None)), # continue
                    lambda bs: (util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_c(bs.flow))), bs.this.append(None)), # break
                    number, # used for sanity check while avoiding circular reference
                ])
                bs.flow.ctrl_stack[-1][0](bs) # continue
        else:
            assert False, util.dump(t)
        bs.call_stack.extend(reversed(bs.this))
