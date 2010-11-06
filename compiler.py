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
    def __init__(self, scopes):
        # scopes is a list of types, actual data is passed in as a pointer to the values in the function
        self.produced = util.cdict(self.produce)
        self.scopes = scopes
    def call(self, arg_types=()):
        def _(bs):
            util.add_redirection(bs.code, lambda rdi: util.get_call(self.produced[arg_types]))
        return _
    def produce(self, arg_types):
        return translate(
            flow=Flow(self.scopes),
            desc="exec " + self.name + " " + repr(arg_types),
            this=[
                self.pre(arg_types),
                self.t.body,
                ast.Return(value=None),
                end,
            ],
        )

class Root(Executable):
    def __init__(self, scopes, t):
        Executable.__init__(self, scopes)
        assert isinstance(t, ast.FunctionDef)
        self.t = t
    def pre(self, arg_types):
        assert not arg_types
        bs.flow.scopes 

def Function(scopes, t):
    #if is_generator(t):
    #    return Generator(t)
    return NonGenerator(scopes, t)

class NonGenerator(Executable):
    def __init__(self, scopes, t):
        assert isinstance(t, ast.FunctionDef)
        self.t = t
        Executable.__init__(self, scopes)
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
            bs.code += isa.sub(registers.rsp, 100 * 32)
        # pop uses rsp
        # memory access uses rbp
        # we need old stack current memory access
        assert len(arg_types) <= len(self.t.args.args), [arg_types, self.t.args.args, self.name]
        assert len(arg_types) >= len(self.t.args.args) - len(self.t.args.defaults)
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
                
                bs.this.append(end)
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
                
                #assert not bs.flow.stack, bs.flow.stack
                
                # leave
                bs.code += isa.mov(registers.rsp, registers.rbp)
                bs.code += isa.pop(registers.rbp)
                
                bs.code += isa.ret() # return address
                
                bs.this.append(end)
        return this
    def load(self):
        def _(bs):
            assert self.scopes == [None]
            bs.code += isa.push(0)
            bs.flow.stack.append(type_impl.functions[self])
        return _
    def create(self):
        def _(bs):
            alloc_locals(bs)
            bs.this.append(type_impl.functions[self].create())
        return _

#class Generator(object):

class AnnotatedStack(object):
    def __init__(self):
        self.stack = []
    def __len__(self):
        return len(self.stack)
    def dup_other(self, other):
        self.stack = list(other.stack)
    def pop(self):
        return self.stack.pop()[0]
    def pop2(self):
        return self.stack.pop()
    def append(self, item):
        self.stack.append((item, None))
    def append2(self, item, ann):
        self.stack.append((item, ann))
    def extend(self, items):
        self.stack.extend((x, None) for x in items)
    def __eq__(self, other):
        return self.stack == other.stack
    def __hash__(self):
        return hash(tuple(self.stack))
    def __getitem__(self, index):
        if isinstance(index, slice):
            return [x[0] for x in self.stack[index]]
        else:
            return self.stack[index][0]

class StackScope(object):
    def __init__(self, names=()):
        self.names = names
        self._names_dict = {}
        for i, (name, type) in enumerate(self.names):
            self._names_dict[name] = (i, type)
    def __repr__(self):
        return "StackScope" + repr(self.names)
    def load_name(self, name):
        def _(bs):
            try:
                pos, type = self._names_dict[name]
            except KeyError:
                from objects.upperdict import Unset
                pos, type = 0, Unset
            
            for i in xrange(type.size):
                bs.code += isa.mov(registers.rax, MemRef(registers.rbp, -100 * 32 + pos * 32 + i * 8))
                bs.code += isa.push(registers.rax)
            bs.flow.stack.append(type)
        return _
    def store_name(self, name):
        def _(bs):
            assert bs.flow.scopes.pop() is self
            
            try:
                pos = self._names_dict[name][0]
            except KeyError:
                for i, (name2, type2) in enumerate(self.names + ((None, None),)):
                    if type2 is None:
                        pos = i
                        break
            
            type = bs.flow.stack.pop()
            for i in reversed(xrange(type.size)):
                bs.code += isa.pop(registers.rax)
                bs.code += isa.mov(MemRef(registers.rbp, - 100 * 32 + pos * 32 + i * 8), registers.rax)
            
            new_names = tuple((name, type) if i == pos else (name2, type2) for i, (name2, type2) in enumerate(self.names + ((None, None),)))
            while new_names[-1] == (None, None): new_names = new_names[:-1]
            bs.flow.scopes.append(stackscopes[new_names])
        return _
    def del_name(self, name):
        def _(bs):
            assert False
            assert bs.flow.scopes.pop() is self
            
        return _
stackscopes = util.cdict(StackScope)

class Flow(object):
    def __init__(self, scopes=None):
        if scopes is None:
            from objects.upperdict import UpperDict
            self.scopes = [None, UpperDict("root")]
        else:
            self.scopes = scopes + [StackScope()]
        self.stack = AnnotatedStack()
        self.ctrl_stack = []
        self.try_stack = []
        self.return_stack = []
        self.globals = set()
    
    def __repr__(self):
        return "Flow<%r>" % self.__dict__
    
    def __hash__(self):
        return hash(self.stack) ^ hash(tuple(self.scopes))
    
    def __eq__(self, other):
        if not isinstance(other, Flow):
            return False
        return self.__dict__ == other.__dict__
    
    def clone(self):
        r = Flow()
        r.scopes[:] = self.scopes
        r.stack.dup_other(self.stack)
        r.ctrl_stack[:] = self.ctrl_stack
        r.try_stack[:] = self.try_stack
        r.return_stack[:] = self.return_stack
        r.globals.update(self.globals)
        return r

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
        assert data_pos < len(data)
        #if data_pos % 512:
        #    data_pos += 512 - data_pos % 512
        #print "BUFFER", data[:data_pos]
        data.references.append(self.program.render_code.references)
        self.program.render_code = util.OffsetListProxy(data, pos)
        return res

data = extarray('B', '\xff'*1000000)
data.references = []
data_pos = 0
make_executable(*data.buffer_info())

def alloc_locals(bs):
    if not isinstance(bs.flow.scopes[-1], StackScope):
        return
    
    assert False, bs.flow.scopes
    
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

def get_module(name):
    if name == "ctypes":
        def _(bs):
            import myctypes
            bs.flow.stack.append(myctypes.CtypesModule)
        return _
    elif name == "__pyable__":
        def _(bs):
            import mypyable
            bs.flow.stack.append(mypyable.PyableModule)
        return _
    else:
        return ast.Call(func=ast.Name(id='__import__', ctx=ast.Load()), args=[ast.Str(s=name)], keywords=[], starargs=None, kwargs=None)

def flattened_contains_none(l):
    if l is None:
        return True
    if isinstance(l, list):
        return any(flattened_contains_none(x) for x in l)
    return False

end = object()
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
    
    if flattened_contains_none(bs.call_stack):
        raise TypeError()
    
    bs.desc = util.dump(bs.call_stack)
    
    while True:
        t = bs.call_stack.pop()
        class a(list):
            def append(self, i):
                if i is None:
                    raise TypeError()
                list.append(self, i)
        bs.this = a()
        #if util.DEBUG:
        #    print
        #    print bs.call_stack
        #    print util.dump(t)
        
        #print util.dump(t)
        #print t
        
        if t is end:
            return bs.finalise(desc)
        elif callable(t):
            v = t(bs)
            #assert v is None, (t, v) # some lambdas break this
            #print
            #print bs.flow.stack, bs.this, bs.call_stack, bs.desc
            #print
        elif isinstance(t, list):
            assert not bs.this
            bs.this = t
        elif isinstance(t, ast.Module):
            assert False
        elif isinstance(t, ast.Lambda):
            Function(list(bs.flow.scopes), ast.FunctionDef(
                name="<lambda>",
                args=t.args,
                body=ast.Return(t.body),
                decorator_list=[],
            )).create()(bs)
        elif isinstance(t, ast.FunctionDef):
            bs.this.append(ast.Assign(
                targets=[ast.Name(id=t.name, ctx=ast.Store())],
                value=Function(list(bs.flow.scopes), t).create(),
            ))
        elif isinstance(t, ast.AugAssign):
            bs.this.append(ast.Assign(
                targets=[t.target],
                value=ast.BinOp(left=reverse_reference(t.target), op=t.op, right=t.value),
            ))
        elif isinstance(t, ast.Assign):
            bs.this.append(t.value)

            for i, target in enumerate(t.targets):
                assert isinstance(target.ctx, ast.Store)
                
                if i != len(t.targets) - 1: # if not last
                    bs.this.append(util.dup)
                
                bs.this.append(target)
        elif isinstance(t, ast.Expr):
            # XXX handle __doc__ here? also _ and printing for REPL
            bs.this.append(t.value)
            bs.this.append(util.discard)
        elif isinstance(t, ast.Num):
            if isinstance(t.n, float):
                bs.this.append(type_impl.Float.load_constant(t.n))
            elif isinstance(t.n, int):
                bs.this.append(type_impl.Int.load_constant(t.n))
            else:
                assert False, t.n
        elif isinstance(t, ast.Name):
            if isinstance(t.ctx, ast.Load):
                if t.id == 'None':
                    bs.this.append(type_impl.NoneType.load())
                elif t.id == 'True':
                    bs.this.append(type_impl.Bool.load_true())
                elif t.id == 'False':
                    bs.this.append(type_impl.Bool.load_false())
                else:
                    def get_name(name, mro):
                        def _(bs):
                            #print name, mro
                            #print
                            if mro[-1] is None:
                                import mypyable
                                if mypyable.NameError_impl is None:
                                    bs.this.append(ast.Raise(ast.Str(s=name + " is not set!"), None, None))
                                    return
                                #print name
                                #for a in bs.flow.scopes: print a
                                #print
                                bs.this.append(ast.Raise(
                                    type=ast.Call(
                                        func=mypyable.NameError_impl.load,
                                        args=[ast.Str(s=name)],
                                        keywords=[],
                                        starargs=None,
                                        kwargs=None,
                                        ),
                                    inst=None,
                                    tback=None,
                                ))
                            else:
                                bs.this.append(mro[-1].load_name(name))
                                @bs.this.append
                                def _(bs):
                                    from objects.upperdict import Unset
                                    if bs.flow.stack[-1] is Unset:
                                        bs.flow.stack.pop()
                                        bs.this.append(get_name(name, mro[:-1]))
                        return _
                    bs.this.append(get_name(t.id, bs.flow.scopes))
            elif isinstance(t.ctx, ast.Store):
                assert t.id not in ('None', 'True', 'False')
                # XXX
                if t.id in bs.flow.globals:
                    bs.this.append(bs.flow.scopes[-2].store_name(t.id))
                else:
                    bs.this.append(bs.flow.scopes[-1].store_name(t.id))
            else:
                assert False, t.ctx
        elif isinstance(t, ast.Global):
            for name in t.names:
                assert name not in ('None', 'True', 'False')
                bs.flow.globals.add(name)
        elif isinstance(t, ast.If) or isinstance(t, ast.IfExp):
            # instead of memoize, avoid jumps with a jump from new to midway through original if flow is the same
            
            @util.memoize
            def make_post(flow, stack=list(bs.call_stack)):
                return translate("if_post", flow, stack=stack)
            
            @util.memoize
            def make_orelse(flow, t=t, make_post=make_post):
                return translate("if_orelse", flow, this=[
                    t.orelse,
                    lambda bs: util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_post(bs.flow))),
                    end,
                ])
            
            @util.memoize
            def make_body(flow, t=t, make_post=make_post):
                return translate("if_body", flow, this=[
                    t.body,
                    lambda bs: util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_post(bs.flow))),
                    end,
                ])
            bs.this.append(t.test)
            @bs.this.append
            def _(bs):
                if bs.flow.stack[-1] not in (type_impl.Int, type_impl.Bool):
                    bs.this.append(
                        ast.Call(
                            func=ast.Attribute(
                                value=lambda bs: None,
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
                type, hint = bs.flow.stack.pop2()
                assert type is type_impl.Int or type is type_impl.Bool, type
                if hint is not None and True:
                    bs.flow.stack.append(type)
                    util.discard(bs)
                    #print "HINTED HERE", hint
                    if hint:
                        bs.this.append(t.body)
                    else:
                        bs.this.append(t.orelse)
                    return
                bs.code += isa.pop(registers.rax)
                bs.code += isa.test(registers.rax, registers.rax)
                skip = bs.program.get_unique_label()
                bs.code += isa.jz(skip)
                def check(x, y):
                    assert x, y
                util.add_redirection(bs.code, lambda rdi: (check(hint is None or hint, (0, type, hint)), util.get_jmp(make_body(bs.flow)))[1])
                bs.code += skip
                util.add_redirection(bs.code, lambda rdi: (check(hint is None or not hint, (1, type, hint)), util.get_jmp(make_orelse(bs.flow)))[1])
                bs.this.append(end)
        elif isinstance(t, ast.While):
            @util.memoize
            def make_a(flow, t=t):
                def _(bs):
                    type, hint = bs.flow.stack.pop2()
                    assert type is type_impl.Int or type is type_impl.Bool
                    bs.code += isa.pop(registers.rax)
                    bs.code += isa.cmp(registers.rax, 0)
                    skip = bs.program.get_unique_label()
                    bs.code += isa.je(skip)
                    util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_b(bs.flow)))
                    bs.code += skip
                    util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_c(bs.flow)))
                
                def _2(bs):
                    if bs.flow.stack[-1] not in (type_impl.Int, type_impl.Bool):
                        bs.this.append(
                            ast.Call(
                                func=ast.Attribute(
                                    value=lambda bs: None,
                                    attr='__nonzero__',
                                    ctx=ast.Load(),
                                    ),
                                args=[],
                                keywords=[],
                                starargs=None,
                                kwargs=None,
                                ),
                            )
                return translate("while_a", flow, this=[
                    t.test,
                    _2,
                    _,
                    end,
                ])
            
            @util.memoize
            def make_b(flow, t=t):
                return translate("while_b", flow, this=[
                    t.body,
                    lambda bs: util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_a(bs.flow))),
                    end,
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
                lambda bs, flow=bs.flow, make_a=make_a: (util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_a(flow))), bs.this.append(end)), # continue
                lambda bs, flow=bs.flow, make_c=make_c: (util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_c(flow))), bs.this.append(end)), # break
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
                        bs.flow.stack.append2(type_impl.Bool, not isinstance(op, ast.Is))
                    else:
                        if right_type.size:
                            bs.code += isa.mov(registers.rax, 1 if isinstance(op, ast.Is) else 0)
                            bs.code += isa.mov(registers.r15, 0 if isinstance(op, ast.Is) else 1)
                            for reg_r, reg_l in zip(right_registers, left_registers):
                                bs.code += isa.cmp(reg_r, reg_l)
                                bs.code += isa.cmovne(registers.rax, registers.r15)
                            bs.code += isa.push(registers.rax)
                            bs.flow.stack.append(type_impl.Bool)
                        else:
                            bs.code += isa.push(1 if isinstance(op, ast.Is) else 0)
                            bs.flow.stack.append2(type_impl.Bool, isinstance(op, ast.Is))
            else:
                if isinstance(op, ast.Lt): r = "lt"
                elif isinstance(op, ast.LtE): r = "le"
                elif isinstance(op, ast.Eq): r = "eq"
                elif isinstance(op, ast.NotEq): r = "ne"
                elif isinstance(op, ast.Gt): r = "gt"
                elif isinstance(op, ast.GtE): r = "ge" 
                elif isinstance(op, ast.In): r = "contains" 
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
                            value=t.comparators[0] if isinstance(op, ast.In) else t.left,
                            attr='__%s__' % r,
                            ctx=ast.Load(),
                            ),
                        args=[t.left if isinstance(op, ast.In) else t.comparators[0]],
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
            if 1:
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
            else:
                import mypyable
                bs.this.append(t.dest if t.dest is not None else ast.Attribute(
                    value=mypyable.SysModule_impl.load(),
                    attr="stdout",
                    ctx=ast.Load(),
                ))
                for i, value in enumerate(t.values):
                    if i:
                        bs.this.append(ast.Expr(ast.Call(
                            func=ast.Attribute(
                                value=util.dup,
                                attr="write",
                                ctx=ast.Load(),
                                ),
                            args=[ast.Str(s=" ")],
                            keywords=[],
                            starargs=None,
                            kwargs=None,
                        )))
                    bs.this.append(ast.Expr(ast.Call(
                        func=ast.Attribute(
                            value=util.dup,
                            attr="write",
                            ctx=ast.Load(),
                            ),
                        args=[ast.Call(
                            func=ast.Attribute(
                                value=value,
                                attr='__str__',
                                ctx=ast.Load(),
                                ),
                            args=[],
                            keywords=[],
                            starargs=None,
                            kwargs=None,
                            )],
                        keywords=[],
                        starargs=None,
                        kwargs=None,
                    )))
                if t.nl:
                    bs.this.append(ast.Expr(ast.Call(
                        func=ast.Attribute(
                            value=util.dup,
                            attr="write",
                            ctx=ast.Load(),
                            ),
                        args=[ast.Str(s="\n")],
                        keywords=[],
                        starargs=None,
                        kwargs=None,
                    )))
                bs.this.append(util.discard)
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
                    bs.code += isa.xor(registers.rax, 1)
                    bs.code += isa.push(registers.rax)
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
                #if util.DEBUG:
                #    print "XXX", bs, t, r
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
                #@bs.this.append
                #def _(bs):
                #    #type = bs.flow.stack[-1]
                #    #for i in xrange(type.size):
                #    #    bs.code += isa.push(MemRef(registers.rsp, 8 * (type.size - 1))) # check this!
                #    #bs.flow.stack.append(type)
                #    util.dup(bs)
                #    def _(bs):
                #        assert bs.flow.stack[-1] is bs.flow.stack[-2] is type
                bs.this.append(value)
                bs.this.append(
                    ast.Call(
                        func=ast.Attribute(
                            value=util.dup,
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
                    util.discard(bs)
            
            bs.this.append(t.values[-1])
            # these next two can be eliminated at the cost of branching
            bs.this.append(lambda bs, make_post=make_post: util.add_redirection(bs.code, lambda rdi, flow=bs.flow.clone(): util.get_jmp(make_post(flow))))
            bs.this.append(end)
        elif isinstance(t, ast.Call):
            assert not t.keywords
            assert not t.starargs
            assert not t.kwargs
            
            bs.this.append(t.func)
            
            @bs.this.append
            def _(bs, t=t):
                bs.this.extend(t.args)
                
                @bs.this.append
                def _(bs, t=t):
                    arg_types = tuple(bs.flow.stack[-1 - i] for i, a in enumerate(t.args))[::-1]
                    bs.this.append(bs.flow.stack[-1 - len(t.args)].call(arg_types))
            
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
                bs.this.append(ast.Call(
                    func=ast.Attribute(value=t.value, attr='__getitem__', ctx=ast.Load()),
                    args=[t.slice],
                    keywords=[],
                    starargs=None,
                    kwargs=None,
                ))
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
                
                bs.this.append(util.discard)
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
                #print bs.flow.stack.stack
                bs.flow.return_stack.pop()(bs)
        elif isinstance(t, ast.Raise):
            assert t.tback is None
            if t.inst is not None:
                bs.this.append(ast.Call(
                    func=t.type,
                    args=[t.inst],
                    keywords=[],
                    starargs=None,
                    kwargs=None,
                ))
            else:
                bs.this.append(t.type)
                @bs.this.append
                def _(bs):
                    assert not isinstance(bs.flow.stack[-1], type_impl.ProtoObject) # should call
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
            if isinstance(t.ctx, ast.Load):
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
                if t.elts:
                    bs.this.append(ast.Attribute(
                        value=util.dup,
                        attr='append',
                        ctx=ast.Load(),
                        ),
                    )
                    for e in t.elts:
                        bs.this.append(ast.Expr(
                            ast.Call(
                                func=util.dup,
                                args=[e],
                                keywords=[],
                                starargs=None,
                                kwargs=None,
                                ),
                            ))
                    bs.this.append(util.discard)
            elif isinstance(t.ctx, ast.Store):
                assert isinstance(t.ctx, ast.Store)
                bs.this.append(
                    ast.Call(
                        func=ast.Attribute(
                            value=lambda bs: None,
                            attr='__iter__',
                            ctx=ast.Load(),
                            ),
                        args=[],
                        keywords=[],
                        starargs=None,
                        kwargs=None,
                        ),
                    )
                for e in t.elts:
                    bs.this.append(
                        ast.Assign(
                            targets=[e],
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
                bs.this.append(util.discard)
            else:
                assert False, t.ctx
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
            if t.keys:
                bs.this.append(
                    ast.Attribute(
                        value=util.dup,
                        attr='__setitem__',
                        ctx=ast.Load(),
                        ),
                )
                for k, v in zip(t.keys, t.values):
                    bs.this.append(ast.Expr(
                        ast.Call(
                            func=util.dup,
                            args=[k, v],
                            keywords=[],
                            starargs=None,
                            kwargs=None,
                            ),
                        ))
                bs.this.append(util.discard)
        elif isinstance(t, ast.Import):
            for name in t.names:
                assert isinstance(name, ast.alias)
                bs.this.append(ast.Assign(
                    targets=[ast.Name(id=name.name if name.asname is None else name.asname, ctx=ast.Store())],
                    value=get_module(name.name),
                ))
        elif isinstance(t, ast.ImportFrom):
            assert t.level == 0
            bs.this.append(get_module(t.module))
            for i, name in enumerate(t.names):
                assert isinstance(name, ast.alias)
                if name.name == '*':
                    bs.this.append(ast.Attribute(
                        value=lambda bs, t=t: None if i == len(t.names) - 1 else util.dup,
                        attr="__dict__",
                        ctx=ast.Load(),
                        ),
                    )
                    @bs.this.append
                    def _(bs):
                        type = bs.flow.stack.pop()
                        from objects.upperdict import UpperDictType
                        assert isinstance(type, UpperDictType), type
                        bs.flow.scopes.append(type.dict)
                else:
                    bs.this.append(ast.Assign(
                        targets=[ast.Name(id=name.name if name.asname is None else name.asname, ctx=ast.Store())],
                        value=ast.Attribute(
                            value=lambda bs, t=t: None if i == len(t.names) - 1 else util.dup,
                            attr=name.name,
                            ctx=ast.Load(),
                            ),
                    ))
        elif isinstance(t, ast.Attribute):
            if isinstance(t.ctx, ast.Load):
                bs.this.append(t.value)
                @bs.this.append
                def _(bs, t=t):
                    #print list(bs.flow.stack), bs.flow.scopes
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
            
            bs.this.append(ast.Call(
                func=mypyable.Type.load(),
                args=[type_impl.Str.load_constant(t.name), ast.Tuple(elts=t.bases, ctx=ast.Load()), type_impl.NoneType.load()],
                keywords=[],
                starargs=None,
                kwargs=None,
            ))
            
            bs.this.append(ast.Assign(
                targets=[ast.Name(id=t.name, ctx=ast.Store())],
                value=util.dup,
            ))
            
            bs.this.append(ast.Attribute(
                value=lambda bs: None,
                attr="__dict__",
                ctx=ast.Load(),
            ))
            
            @bs.this.append
            def _(bs):
                type = bs.flow.stack.pop()
                assert type.size == 0
                assert type.dict is not None
                bs.flow.scopes.append(type.dict)
            
            bs.this.append(t.body)
            
            @bs.this.append
            def _(bs):
                bs.flow.scopes.pop()
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
                #print list(bs.flow.stack)
                util.rev3(bs)
                assert bs.flow.stack.pop() is type_impl.Str # body
                def exec_it(i):
                    def _(bs):
                        s = type_impl.Str.to_python(struct.pack("l", i))
                        try:
                            tree = ast.parse(s, "<string>")
                        except SyntaxError, e:
                            import mypyable
                            util.discard2(bs)
                            bs.this.append(ast.Raise(
                                type=ast.Call(
                                    func=mypyable.SyntaxError_impl.load,
                                    args=[ast.Str(s=s)],
                                    keywords=[],
                                    starargs=None,
                                    kwargs=None,
                                    ),
                                inst=None,
                                tback=None,
                            ))
                        else:
                            old_scopes = list(bs.flow.scopes)
                            from objects.upperdict import UpperDictType
                            assert isinstance(tree, ast.Module)
                            globals_type = bs.flow.stack.pop()
                            if isinstance(globals_type, UpperDictType):
                                assert globals_type.dict is not None, globals_type
                                bs.flow.scopes.append(globals_type.dict)
                                bs.flow.scopes[:] = [None, globals_type.dict]
                            elif globals_type is type_impl.NoneType:
                                pass
                            else:
                                assert False, globals_type
                            locals_type = bs.flow.stack.pop()
                            if locals_type is type_impl.DictProxy:
                                assert locals_type.size == 1
                                                                
                                alloc_locals(bs) # HACK, we should instead put this in the scope linked list
                                
                                assert False
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
                            elif isinstance(locals_type, UpperDictType):
                                bs.flow.scopes.append(locals_type.dict)
                            elif locals_type is type_impl.NoneType:
                                pass
                            else:
                                assert False
                            bs.this.append(tree.body)
                            if locals_type is type_impl.DictProxy:
                                @bs.this.append
                                def _(bs):
                                    bs.code += isa.mov(registers.r12, MemRef(registers.rbp, -8))
                                    
                                    #bs.code += isa.mov(registers.rdi, registers.r12)
                                    #bs.code += isa.mov(registers.rax, util.free_addr)
                                    #bs.code += isa.call(registers.rax)
                                    
                                    bs.code += isa.mov(registers.rax, MemRef(registers.r12, 16))
                                    bs.code += isa.mov(MemRef(registers.rbp, -8), registers.rax)
                            elif isinstance(locals_type, UpperDictType):
                                @bs.this.append
                                def _(bs, locals_type=locals_type):
                                    assert bs.flow.scopes.pop() is locals_type.dict
                            if isinstance(globals_type, UpperDictType):
                                @bs.this.append
                                def _(bs, globals_type=globals_type):
                                    assert bs.flow.scopes == [None, globals_type.dict]
                                    bs.flow.scopes[:] = old_scopes
                    return _
                util.unlift_noncached(bs, exec_it, "exec")
        elif isinstance(t, ast.TryFinally):
            @bs.flow.try_stack.append
            def _(bs, call_stack=list(bs.call_stack), flow=bs.flow.clone(), t=t):
                bs.call_stack[:] = call_stack
                bs.flow.ctrl_stack[:] = flow.ctrl_stack
                assert bs.flow.return_stack == flow.ctrl_stack
                assert bs.flow.try_stack == flow.try_stack
                
                util.lower(bs, len(bs.flow.stack) - (len(flow.stack) + 1))
                
                bs.this = []
                bs.this.append(t.finalbody)
                @bs.this.append
                def _(bs):
                    bs.flow.try_stack.pop()(bs)
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
                        if catch_type is None or catch_type.isinstance(exc_type):
                            bs.call_stack[:] = call_stack
                            bs.flow.ctrl_stack[:] = flow.ctrl_stack
                            assert bs.flow.return_stack == flow.return_stack
                            assert bs.flow.try_stack == flow.try_stack
                            
                            #print bs.flow.stack, flow.stack
                            #for i in xrange(len(bs.flow.stack) - len(flow.stack)):
                            #    print i
                            #    util.rem1(bs)
                            
                            util.lower(bs, len(bs.flow.stack) - (len(flow.stack) + 1))
                            
                            bs.this = []
                            
                            if handler.name is None:
                                util.discard(bs)
                            else:
                                bs.this.append(handler.name)
                            
                            bs.this.append(handler.body)
                @bs.this.append
                def _(bs):
                    bs.flow.try_stack.pop()(bs)
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
                    util.discard(bs)
                    #bs.flow.return_stack.pop()
                    removed = bs.flow.ctrl_stack.pop()
                    assert removed[2] == number
                return translate("while_c", flow, stack=stack, this=[
                    _,
                    t.orelse,
                ])
            
            @util.memoize
            def make_c(flow, stack=list(bs.call_stack), number=number):
                def _(bs):
                    util.discard(bs)
                    #bs.flow.return_stack.pop()
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
                            util.discard(bs) # pop StopIteration
                            @bs.this.append
                            def _(bs):
                                util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_c_normal(bs.flow)))
                            bs.this.append(end)
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
                        bs.this.append(end)
                
                return translate("while_a", flow, this=[
                    _,
                    end,
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
            #@bs.flow.return_stack.append
            #def for_returner(bs):
            #    # pop iterator
            #    util.rem1(bs)
            #    bs.flow.return_stack.pop()(bs)
            @bs.this.append
            def _(bs, make_a=make_a, make_c=make_c, number=number):
                bs.flow.ctrl_stack.append([
                    lambda bs: (util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_a(bs.flow))), bs.this.append(end)), # continue
                    lambda bs: (util.add_redirection(bs.code, lambda rdi: util.get_jmp(make_c(bs.flow))), bs.this.append(end)), # break
                    number, # used for sanity check while avoiding circular reference
                ])
                bs.flow.ctrl_stack[-1][0](bs) # continue
        else:
            assert False, util.dump(t)
        bs.call_stack.extend(reversed(bs.this))
