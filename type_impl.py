from __future__ import division

import struct
import ctypes
import ast

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
from corepy.arch.x86_64.lib.memory import MemRef

import util
import compiler

id_to_type = {}

def number(inst):
    inst.id = len(id_to_type)
    assert inst.id not in id_to_type
    id_to_type[inst.id] = inst
    #print inst, inst.id
    return inst

class _Type(object):
    def copy(self):
        return self.__class__()
    def __repr__(self):
        return self.__class__.__name__
    #def getattr(self):
    #    return None
    def getattr_const_string(self, s):
        assert False, "%s has no attr '%s'" % (self, s)
    def call_const(self, c):
        return None
    def to_python(self, data):
        return self
Type = number(_Type())

class _IntAbsMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rdi)
            bs.code += isa.mov(registers.rax, registers.rdi)
            bs.code += isa.cqo()
            bs.code += isa.mov(registers.rax, registers.rdx)
            bs.code += isa.xor(registers.rax, registers.rdi)
            bs.code += isa.sub(registers.rax, registers.rdx)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Int)
        return _
IntAbsMeth = number(_IntAbsMeth())

class _IntNonzeroMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.flow.stack.append(Int)
        return _
IntNonzeroMeth = number(_IntNonzeroMeth())


class _IntStrMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            
            bs.code += isa.push(registers.rbp)
            bs.code += isa.mov(registers.rbp, registers.rsp)
            
            loop = bs.program.get_unique_label()
            
            bs.code += isa.mov(registers.r14, 0)
            
            bs.code += isa.cmp(registers.rax, 0)
            bs.code += isa.jge(loop)
            
            bs.code += isa.mov(registers.r14, 1)
            bs.code += isa.neg(registers.rax)
            
            bs.code += loop
            
            bs.code += isa.mov(registers.rdx, 0)
            bs.code += isa.mov(registers.rbx, 10)
            bs.code += isa.idiv(registers.rbx)
            bs.code += isa.add(registers.rdx, ord('0'))
            bs.code += isa.sub(registers.rsp, 1)
            bs.code += isa.mov(MemRef(registers.rsp, data_size=8), registers.dl)
            
            bs.code += isa.cmp(registers.rax, 0)
            bs.code += isa.jne(loop)
            
            skip = bs.program.get_unique_label()
            
            bs.code += isa.cmp(registers.r14, 0)
            bs.code += isa.je(skip)
            
            bs.code += isa.sub(registers.rsp, 1)
            bs.code += isa.mov(MemRef(registers.rsp, data_size=8), ord('-'))
            
            bs.code += skip
            
            bs.code += isa.mov(registers.r12, registers.rbp)
            bs.code += isa.sub(registers.r12, registers.rsp)
            bs.code += isa.push(registers.r12)
            bs.code += isa.add(registers.r12, 8)
            
            bs.code += isa.mov(registers.r13, registers.rsp)
            
            bs.code += isa.and_(registers.rsp, -16)
            
            bs.code += isa.mov(registers.rdi, registers.r12)
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.call(registers.rax)
            
            bs.code += isa.mov(registers.rdi, registers.rax)
            bs.code += isa.mov(registers.rsi, registers.r13)
            bs.code += isa.mov(registers.rdx, registers.r12)
            bs.code += isa.mov(registers.rax, ctypes.cast(ctypes.memmove, ctypes.c_void_p).value)	
            bs.code += isa.call(registers.rax)
            
            bs.code += isa.mov(registers.rsp, registers.rbp)
            bs.code += isa.pop(registers.rbp)
            
            bs.code += isa.push(registers.rax)
            
            bs.flow.stack.append(Str)
        return _
IntStrMeth = number(_IntStrMeth())

class _Int(_Type):
    size = 1
    def getattr_const_string(self, s):
        def _(bs):
            assert bs.flow.stack[-1] is self
            if s == "numerator":
                pass
            elif s == "denominator":
                bs.code += isa.pop(registers.rax)
                bs.code += isa.push(1)
            elif s == "real":
                pass
            elif s == "imag":
                bs.code += isa.pop(registers.rax)
                bs.code += isa.push(0)
            elif s == "__abs__":
                assert bs.flow.stack.pop() is self
                #bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(IntAbsMeth)
                # method needs to contain this and the pointer
            elif s == "__nonzero__":
                assert bs.flow.stack.pop() is self
                #bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(IntNonzeroMeth)
            elif s == "__str__":
                assert bs.flow.stack.pop() is self
                #bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(IntStrMeth)
            else:
                assert False, s
        return _
    def load_constant(self, value):
        assert isinstance(value, int)
        value = int(value)
        def _(bs):
            bs.code += isa.mov(registers.rax, value)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(self)
        return _
    def __neg__(self):
        def _(bs):
            bs.code += isa.pop(registers.rax)
            bs.code += isa.neg(registers.rax)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Int)
        return _
    
    def __add__(self, other):
        if isinstance(other, type(Int)):
            def _(bs):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.pop(registers.rax)
                bs.code += isa.add(registers.rax, registers.rbx)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
    __radd__ = __add__
    
    def __sub__(self, other):
        if isinstance(other, type(Int)):
            def _(bs):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.pop(registers.rax)
                bs.code += isa.sub(registers.rax, registers.rbx)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
    
    def __mul__(self, other):
        if isinstance(other, type(Int)):
            def _(bs):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.pop(registers.rax)
                bs.code += isa.imul(registers.rax, registers.rbx)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
    __rmul__ = __mul__
    
    def __div__(self, other):
        if isinstance(other, type(Int)):
            def _(bs):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.pop(registers.rax)
                bs.code += isa.mov(registers.rdx, 0)
                bs.code += isa.mov(registers.rax, registers.rax)
                bs.code += isa.idiv(registers.rbx)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
    
    def __floordiv__(self, other):
        if isinstance(other, type(Int)):
            def _(bs):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.pop(registers.rax)
                bs.code += isa.mov(registers.rdx, 0)
                bs.code += isa.mov(registers.rax, registers.rax)
                bs.code += isa.idiv(registers.rbx)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
    
    def __mod__(self, other):
        if isinstance(other, type(Int)):
            def _(bs):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.pop(registers.rax)
                bs.code += isa.mov(registers.rdx, 0)
                bs.code += isa.mov(registers.rax, registers.rax)
                bs.code += isa.idiv(registers.rbx)
                bs.code += isa.push(registers.rdx)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
    
    def __or__(self, other):
        if isinstance(other, type(Int)):
            def _(bs):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.pop(registers.rax)
                bs.code += isa.or_(registers.rax, registers.rbx)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
Int = number(_Int())

class _Float(_Type):
    size = 1
    def load_constant(self, value):
        assert isinstance(value, float)
        value = float(value)
        def _(bs):
            bs.code += isa.mov(registers.rax, struct.unpack("l", struct.pack("d", value))[0])
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(self)
        return _
    def __neg__(self):
        def _(bs):
            bs.code += isa.neg(registers.rax)
        return _
    def __add__(self, other, reverse=False):
        if isinstance(other, type(Float)):
            def _(bs):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.pop(registers.rax)
                bs.code += isa.push(registers.rax)
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp))
                bs.code += isa.mov(MemRef(registers.rsp), registers.rbx)
                bs.code += isa.movsd(registers.xmm1, MemRef(registers.rsp))
                bs.code += isa.addsd(registers.xmm0, registers.xmm1)
                bs.code += isa.movsd(MemRef(registers.rsp), registers.xmm0)
                bs.flow.stack.append(Float)
            return _
        elif isinstance(other, type(Int)):
            def _(bs):
                if not reverse:
                    bs.code += isa.pop(registers.rbx)
                bs.code += isa.pop(registers.rax)
                if reverse:
                    bs.code += isa.pop(registers.rbx)
                bs.code += isa.cvtsi2sd(registers.xmm1, registers.rbx)
                bs.code += isa.push(registers.rax)
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp))
                bs.code += isa.addsd(registers.xmm0, registers.xmm1)
                bs.code += isa.movsd(MemRef(registers.rsp), registers.xmm0)
                bs.flow.stack.append(Float)
            return _
        return NotImplemented
    __radd__ = lambda self, other: self.__add__(other, reverse=True)
Float = number(_Float())

class ProtoTuple(_Type):
    size = 1
    arg_types = None
    def __init__(self, arg_types):
        number(self)
        self.arg_types = arg_types
        self.arg_size = sum(x.size for x in self.arg_types)
    def __repr__(self):
        return "ProtoTuple%r" % (self.arg_types,)
    def load(self):
        def _(bs):
            for arg in self.arg_types[::-1]:
                assert bs.flow.stack.pop() is arg
            
            bs.code += isa.mov(registers.rdi, 8 * self.arg_size)
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.call(registers.rax)
            
            bs.code += isa.mov(registers.r12, registers.rax)
            
            bs.code += isa.mov(registers.rdi, registers.rax)
            bs.code += isa.mov(registers.rsi, registers.rsp)
            bs.code += isa.mov(registers.rdx, 8 * self.arg_size)
            bs.code += isa.mov(registers.rax, ctypes.cast(ctypes.memmove, ctypes.c_void_p).value)	
            bs.code += isa.call(registers.rax)
            
            bs.code += isa.push(registers.r12)
            bs.flow.stack.append(self)
        return _
    def to_python(self, data):
        assert len(data) == 8
        data = struct.unpack("q", data)
        return (0,)*len(self.arg_types)
    def getitem(self):
        def _(bs):
            assert bs.flow.stack.pop() is Int
            bs.code += isa.pop(registers.r13) # index
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.r12)
            
            #bs.code += isa.mul(registers.rbx, 8)
            #bs.code += isa.add(registers.rbx, 8)
            
            bs.code += isa.push(registers.r13)
            
            def _(value):
                def _(bs):
                    type = self.arg_types[value]
                    for i in xrange(type.size):
                        bs.code += isa.push(MemRef(registers.r12, self.arg_size * 8 - sum(x.size for x in self.arg_types[:value]) * 8 - 8))
                    bs.flow.stack.append(self.arg_types[value])
                return _
            util.unlift(bs, _, "ProtoTuple.getitem")
        return _
    def store(self):
        def _(bs):
            assert bs.flow.stack.pop() is self
            
            isa.pop(registers.rax)
            
            pos = 0
            for i, type in enumerate(self.arg_types):
                bs.flow.stack.append(type)
                for j in xrange(type.size):
                    bs.code += isa.push(MemRef(registers.rax, pos))
                    pos += 8
        return _

class Tuple2(_Type):
    size = 1
    def load(self, arg_types):
        arg_size = sum(x.size for x in arg_types)
        def _(bs):
            for arg in self.arg_types[::-1]:
                assert bs.flow.stack.pop() is arg
            
            # r12 = malloc(8 * (1 + len(arg_types) + arg_size))
            bs.code += isa.mov(registers.rdi, 8 * (1 + len(arg_types) + arg_size))
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.call(registers.rax)
            bs.code += isa.mov(registers.r12, registers.rax)
            
            bs.code += isa.mov(MemRef(registers.r12), len(arg_types))
            for i in xrange(len(arg_types)):
                bs.code += isa.mov(MemRef(registers.r12, 8 * (1 + i)),
                    8 * (1 + len(arg_types) + sum(x.size for x in self.arg_types[value+1:]))
                )
            
            bs.code += isa.mov(registers.rdi, registers.r12)
            bs.code += isa.add(registers.rdi, 8 * (1 + len(arg_types)))
            bs.code += isa.mov(registers.rsi, registers.rsp)
            bs.code += isa.mov(registers.rdx, 8 * arg_size)
            bs.code += isa.mov(registers.rax, ctypes.cast(ctypes.memmove, ctypes.c_void_p).value)	
            bs.code += isa.call(registers.rax)
            
            bs.code += isa.push(registers.r12)
            bs.flow.stack.append(self)
        return _

class ProtoObject(_Type):
    '''maybe ProtoObject should be singleton with size=1'''
    size = 0
    def __init__(self, name, bases, dict):
        number(self)
        self.name = name
        self.bases = bases
        self.dict = dict
        self.attrs = {}
        self.attr_setters = {}
        self.cfuncs = []
    def __call__(self, arg_types):
        def _(bs):
            assert bs.flow.stack[-1 - len(arg_types)] is self
            bs.this.append(protoinstances[self].new(arg_types))
        return _
    def setattr_const_string(self, attr):
        def _(bs):
            assert bs.flow.stack.pop() is self
            type = bs.flow.stack.pop()
            assert type is Function
            def handler(new_func):
                self.attrs[attr] = new_func
                for umr in self.attr_setters.get(attr, []):
                    umr.replace(new_func)
            handler_cfunc = ctypes.CFUNCTYPE(None, ctypes.c_int64)(handler)
            self.cfuncs.append(handler_cfunc)
            bs.code += isa.pop(registers.rdi)
            bs.code += isa.mov(registers.r12, registers.rsp)
            bs.code += isa.and_(registers.rsp, -16)
            bs.code += isa.mov(registers.rax, ctypes.cast(handler_cfunc, ctypes.c_void_p).value)
            bs.code += isa.call(registers.rax)
            bs.code += isa.mov(registers.rsp, registers.r12)
        return _

class ProtoInstance(_Type):
    size = 1
    def __init__(self, type):
        self.type = type
        self.slots = [{}]
        number(self)
    def __repr__(self):
        return "ProtoInstance(%s)" % (self.type,)
    def new(self, arg_types):
        def _(bs):
            assert bs.flow.stack.pop() is self.type
            
            bs.code += isa.mov(registers.rdi, 8 * 2)
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.call(registers.rax)
            bs.code += isa.mov(registers.r12, registers.rax)
            
            bs.code += isa.mov(MemRef(registers.r12), 0)
            bs.code += isa.mov(MemRef(registers.r12, 8), 0)
            
            bs.code += isa.push(registers.r12)
            bs.flow.stack.append(self)
            
            #assert bs.flow.stack[-1 - len(arg_types)] is self.type
            #bs.code += isa.mov(MemRef(registers.rsp, sum(x.size for x in arg_types)), registers.rax)
            #bs.flow.stack[-1 - len(arg_types
            #bs.code += bs.pop(registers.rax)
            assert not arg_types
            
            self.type.attr_setters.setdefault('__init__', []).append(util.UpdatableMovRax(bs.code, self.type.attrs.get('__init__', 0)))
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Function)
            
            bs.code += isa.push(registers.r12)
            bs.flow.stack.append(self)
            
            bs.this.append(bs.flow.stack[-2]((self,)))
            
            @bs.this.append
            def _(bs):
                type = bs.flow.stack.pop()
                for i in xrange(type.size):
                    bs.code += isa.pop(registers.rax)
        return _
    def setattr_const_string(self, attr):
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.r12)
            bs.code += isa.push(MemRef(registers.r12)) # slot id
            def _(value):
                def _(bs):
                    slots = self.slots[value]
                    type = bs.flow.stack.pop()
                    if attr not in slots or slots[attr][0] is not type:
                        var_types = self.get_var_types(slots)
                        var_types[attr] = type
                        new_slots = self.get_slots(var_types)
                        if new_slots in self.slots:
                            new_id = self.slots.index(new_slots)
                        else:
                            new_id = len(self.slots)
                            self.slots.append(new_slots)
                        
                        #old_size = sum(x.size for x, _ in slots.itervalues())
                        new_size = sum(x.size for x, _ in new_slots.itervalues())
                        
                        
                        bs.code += bs.program.get_label("AAA")
                        
                        bs.code += isa.mov(registers.r14, MemRef(registers.r12, 8)) # r14 = pointer to old slots data
                        
                        bs.code += isa.mov(registers.rax, util.malloc_addr)
                        bs.code += isa.mov(registers.rdi, 8 * new_size)
                        bs.code += isa.call(registers.rax)
                        bs.code += isa.mov(registers.r15, registers.rax) # r15 = pointer to new slots data
                        
                        #bs.code += isa.ud2()
                        
                        bs.code += bs.program.get_label("BBB")
                        
                        # move variables organized as slots in *r14 to as organized in new_slots in *r15
                        for attr_, (type_, pos_) in new_slots.iteritems():
                            if attr_ == attr:
                                continue
                            assert slots[attr_][0] is type_
                            old_pos_ = slots[attr_][1]
                            for i in xrange(type_.size):
                                bs.code += isa.mov(registers.rax, MemRef(registers.r14, 8 * (old_pos_ + i)))
                                bs.code += isa.mov(MemRef(registers.r15, 8 * (pos_ + i)), registers.rax)
                        
                        # free old slots holder
                        bs.code += isa.mov(registers.rax, util.free_addr)
                        bs.code += isa.mov(registers.rdi, registers.r14)
                        bs.code += isa.call(registers.rax)
                        
                        # change reference and id on object
                        bs.code += isa.mov(MemRef(registers.r12), new_id)
                        bs.code += isa.mov(MemRef(registers.r12, 8), registers.r15)
                        
                        slots = new_slots
                    
                    bs.code += bs.program.get_label("CCC")
                    
                    bs.code += isa.mov(registers.r14, MemRef(registers.r12, 8))
                    for i in xrange(type.size):
                        bs.code += isa.pop(MemRef(registers.r14, 8 * (slots[attr][1] + i)))
                        
                    bs.code += bs.program.get_label("DDD")
                return _
            util.unlift(bs, _, "ProtoInstance.setattr_const_string")
        return _
    def getattr_const_string(self, attr):
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.r12)
            bs.code += isa.push(MemRef(registers.r12)) # slot id
            def _(value):
                def _(bs):
                    slots = self.slots[value]
                    if attr in slots:
                        type, pos = slots[attr]
                        bs.code += isa.mov(registers.r14, MemRef(registers.r12, 8))
                        for i in xrange(type.size):
                            bs.code += isa.push(MemRef(registers.r14, 8 * (pos + i)))
                        bs.flow.stack.append(type)
                    else:
                        self.type.attr_setters.setdefault(attr, []).append(util.UpdatableMovRax(bs.code, self.type.attrs.get(attr, 0)))
                        bs.code += isa.push(registers.rax)
                        bs.flow.stack.append(Function)
                        
                        assert bs.flow.stack[-1] is Function
                        
                        bs.code += isa.push(registers.r12)
                        bs.flow.stack.append(self)
                        
                        bs.this.append(methods[self].load())
                return _
            util.unlift(bs, _, "ProtoInstance.getattr_const_string")
        return _
    def delattr_const_string(self, attr):
        def _(bs):
            assert bs.flow.stack.pop() is self
        return _
    def get_slots(self, var_types):
        pos = 0
        res = {}
        for name, type in sorted(var_types.iteritems()):
            res[name] = (type, pos)
            pos += type.size
        return res
    def get_var_types(self, slots):
        res = {}
        for name, (type, pos) in slots.iteritems():
            res[name] = type
        return res
    def getitem(self):
        def _(bs):
            #   self, index
            # swap
            #   index, self
            # getattr(-1, "__getitem__")
            #   index, __getitem__ method
            # swap
            #   __getitem__ method, index
            # call
            #   result
            
            def swap(bs):
                regs = [registers.rbx, registers.rcx, registers.rdx, registers.rdi, registers.rsi, registers.r9]
                
                def pop():
                    res = []
                    type = bs.flow.stack.pop()
                    for i in xrange(type.size):
                        reg = regs.pop()
                        bs.code += isa.pop(reg)
                        res.append(reg)
                    return type, res
                def push((type, regs)):
                    assert type.size == len(regs)
                    for reg in reversed(regs):
                        bs.code += isa.push(reg)
                    bs.flow.stack.append(type)
                
                a = pop()
                b = pop()
                push(a)
                push(b)
            
            bs.this.append(swap)
            
            def _(bs):
                assert bs.flow.stack[-1] is self
            bs.this.append(ast.Attribute(value=_, attr='__getitem__', ctx=ast.Load()))
            
            bs.this.append(swap)
            
            def _(bs):
                pass
            bs.this.append(ast.Call(func=_, args=[_], keywords=[], starargs=None, kwargs=None))
        return _

# store slot in bs.flow.stack once we know it ... though it can change in functions and (undetectibly) other threads .. D:
# i hate threads

protoinstances = util.cdict(ProtoInstance)

strings = util.cdict(lambda s: ctypes.create_string_buffer(struct.pack("L", len(s)) + s))

class _StrStrMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.flow.stack.append(Str)
        return _
StrStrMeth = number(_StrStrMeth())

class _Str(_Type):
    size = 1
    def load_constant(self, s):
        assert isinstance(s, str)
        def _(bs):
            bs.code += isa.mov(registers.rax, ctypes.cast(strings[s], ctypes.c_void_p).value)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Str)
        return _
    def to_python(self, data):
        i, = struct.unpack("q", data)
        length, = struct.unpack("l", ctypes.string_at(i, 8))
        return ctypes.string_at(i+8, length)
    def getattr_const_string(self, s):
        def _(bs):
            assert bs.flow.stack[-1] is self
            if s == "__str__":
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(StrStrMeth)
            else:
                assert False, s
        return _
Str = number(_Str())

functions = []

class _Function(_Type):
    size = 1
    def __call__(self, arg_types):
        def _(bs):
            assert bs.flow.stack[-1 - len(arg_types)] is self
            bs.code += isa.push(MemRef(registers.rsp, 8*len(arg_types)))
            
            def _(value):
                def _(bs):
                    bs.this.append(functions[value](arg_types))
                    @bs.this.append
                    def _(bs):
                        for arg_type in arg_types[::-1]:
                            type = bs.flow.stack.pop()
                            assert type is arg_type, (type, arg_type)
                            for i in xrange(arg_type.size):
                                bs.code += isa.pop(registers.rax)
                        assert bs.flow.stack.pop() is self
                        bs.code += isa.pop(registers.rax)
                        bs.code += isa.push(registers.r12) # unlift return type
                        def _(value):
                            def _(bs):
                                bs.flow.stack.append(id_to_type[value])
                                if bs.flow.stack[-1].size >= 1:
                                    bs.code += isa.push(registers.r13)
                                if bs.flow.stack[-1].size >= 2:
                                    bs.code += isa.push(registers.r14)
                                if bs.flow.stack[-1].size >= 3:
                                    assert False
                            return _
                        util.unlift(bs, _, "_Function.__call__ (inner)")
                return _
            util.unlift(bs, _, "_Function.__call__")
        return _
Function = number(_Function())

class _Method(_Type):
    def __init__(self, self_type):
        self.self_type = self_type
        self.size = Function.size + self.self_type.size
    def load(self):
        def _(bs):
            assert bs.flow.stack.pop() is self.self_type
            assert bs.flow.stack.pop() is Function
            
            bs.flow.stack.append(self)
        return _
    def __call__(self, arg_types):
        def _(bs):
            assert bs.flow.stack.pop(-1 - len(arg_types)) is self
            bs.flow.stack.insert(-1 - len(arg_types), self.self_type)
            bs.flow.stack.insert(-1 - len(arg_types), Function)
            bs.this.append(Function((self.self_type,) + arg_types))
        return _

methods = util.cdict(_Method)

class _NoneStrMeth(_Type):
    size = 0
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.this.append(Str.load_constant('None'))
        return _
NoneStrMeth = number(_NoneStrMeth())

class _NoneType(_Type):
    size = 0
    def load(self):
        def _(bs):
            bs.flow.stack.append(NoneType)
        return _
    def to_python(self, data):
        assert not data
    def getattr_const_string(self, s):
        def _(bs):
            assert bs.flow.stack[-1] is self
            if s == "__str__":
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(NoneStrMeth)
            else:
                assert False, s
        return _
NoneType = number(_NoneType())
