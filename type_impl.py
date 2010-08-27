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

@apply
class Type(object):
    def __init__(self):
        number(self)
    def __repr__(self):
        return self.__class__.__name__
    def const_getattr(self, s):
        f = getattr(self, "getattr_" + s, None)
        if f is None:
            assert False, "%s has no attr '%s'" % (self, s)
        def _(bs):
            assert bs.flow.stack.pop() is self
            f(bs)
        return _
    def call_const(self, c):
        return None
    def to_python(self, data):
        return self
_Type = Type.__class__

@apply
class IntAbsMeth(_Type):
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

@apply
class IntNonzeroMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.flow.stack.append(Bool)
        return _

@apply
class IntPosMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.flow.stack.append(Int)
        return _

@apply
class IntNegMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            bs.code += isa.neg(registers.rax)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Int)
        return _

@apply
class IntInvertMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            bs.code += isa.not_(registers.rax)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Int)
        return _

@apply
class IntStrMeth(_Type):
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

@apply
class IntAddMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert len(arg_types) == 1
        def _(bs):
            other_type = bs.flow.stack.pop()
            if other_type is not Int and other_type is not Bool:
                for i in xrange(other_type.size):
                    bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(NotImplementedType)
                return
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rbx)
            bs.code += isa.pop(registers.rax)
            bs.code += isa.add(registers.rax, registers.rbx)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Int)
        return _

@apply
class IntSubMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert len(arg_types) == 1
        def _(bs):
            other_type = bs.flow.stack.pop()
            if other_type is not Int and other_type is not Bool:
                for i in xrange(other_type.size):
                    bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(NotImplementedType)
                return
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rbx)
            bs.code += isa.pop(registers.rax)
            bs.code += isa.sub(registers.rax, registers.rbx)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Int)
        return _

@apply
class IntMulMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert len(arg_types) == 1
        def _(bs):
            other_type = bs.flow.stack.pop()
            if other_type is not Int and other_type is not Bool:
                for i in xrange(other_type.size):
                    bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(NotImplementedType)
                return
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rbx)
            bs.code += isa.pop(registers.rax)
            bs.code += isa.imul(registers.rax, registers.rbx)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Int)
        return _

@apply
class IntModMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert len(arg_types) == 1
        def _(bs):
            other_type = bs.flow.stack.pop()
            if other_type is not Int and other_type is not Bool:
                for i in xrange(other_type.size):
                    bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(NotImplementedType)
                return
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rbx)
            bs.code += isa.pop(registers.rax)
            bs.code += isa.mov(registers.rdx, 0)
            bs.code += isa.mov(registers.rax, registers.rax)
            bs.code += isa.idiv(registers.rbx)
            bs.code += isa.push(registers.rdx)
            bs.flow.stack.append(Int)
        return _

class _IntCmpMeths(_Type):
    size = 1
    insts = {
        'lt': isa.jl,
        'gt': isa.jg,
        'ge': isa.jge,
        'le': isa.jle,
        'ne': isa.jne,
        'eq': isa.je,
    }
    def __init__(self, op_name):
        _Type.__init__(self)
        self.inst = self.insts[op_name]
    def __call__(self, arg_types):
        assert arg_types == (Int,)
        def _(bs):
            assert bs.flow.stack.pop() is Int
            bs.code += isa.pop(registers.rbx)
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            
            bs.code += isa.cmp(registers.rax, registers.rbx)
            bs.code += isa.mov(registers.rax, 1)
            
            label = bs.program.get_unique_label()
            
            bs.code += self.inst(label)
            
            bs.code += isa.mov(registers.rax, 0)
            
            bs.code += label
            
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Bool)
        return _
IntCmpMeths = util.cdict(_IntCmpMeths)

@apply
class IntFloorDivMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert len(arg_types) == 1
        def _(bs):
            other_type = bs.flow.stack.pop()
            if other_type is not Int and other_type is not Bool:
                for i in xrange(other_type.size):
                    bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(NotImplementedType)
                return
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rbx)
            bs.code += isa.pop(registers.rax)
            bs.code += isa.mov(registers.rdx, 0)
            bs.code += isa.mov(registers.rax, registers.rax)
            bs.code += isa.idiv(registers.rbx)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Int)
        return _

@apply
class Int(_Type):
    size = 1
    def getattr_numerator(self, bs):
        bs.flow.stack.append(Int)
    def getattr_denominator(self, bs):
        bs.code += isa.pop(registers.rax)
        bs.code += isa.push(1)
        bs.flow.stack.append(Int)
    def getattr_real(self, bs):
        bs.flow.stack.append(Int)
    def getattr_imag(self, bs):
        bs.code += isa.pop(registers.rax)
        bs.code += isa.push(0)
        bs.flow.stack.append(Int)
    def getattr___abs__(self, bs):
        bs.flow.stack.append(IntAbsMeth)
    def getattr___nonzero__(self, bs):
        bs.flow.stack.append(IntNonzeroMeth)
    def getattr___str__(self, bs):
        bs.flow.stack.append(IntStrMeth)
    def getattr___neg__(self, bs):
        bs.flow.stack.append(IntNegMeth)
    def getattr___pos__(self, bs):
        bs.flow.stack.append(IntPosMeth)
    def getattr___invert__(self, bs):
        bs.flow.stack.append(IntInvertMeth)
    def getattr___add__(self, bs):
        bs.flow.stack.append(IntAddMeth)
    def getattr___sub__(self, bs):
        bs.flow.stack.append(IntSubMeth)
    def getattr___mul__(self, bs):
        bs.flow.stack.append(IntMulMeth)
    def getattr___div__(self, bs):
        bs.flow.stack.append(IntFloorDivMeth) # fixme
    def getattr___floordiv__(self, bs):
        bs.flow.stack.append(IntFloorDivMeth)
    def getattr___mod__(self, bs):
        bs.flow.stack.append(IntModMeth)
    def getattr___gt__(self, bs): bs.flow.stack.append(IntCmpMeths['gt'])
    def getattr___lt__(self, bs): bs.flow.stack.append(IntCmpMeths['lt'])
    def getattr___ge__(self, bs): bs.flow.stack.append(IntCmpMeths['ge'])
    def getattr___le__(self, bs): bs.flow.stack.append(IntCmpMeths['le'])
    def getattr___eq__(self, bs): bs.flow.stack.append(IntCmpMeths['eq'])
    def getattr___ne__(self, bs): bs.flow.stack.append(IntCmpMeths['ne'])
    
    def load_constant(self, value):
        assert isinstance(value, int)
        value = int(value)
        def _(bs):
            bs.code += isa.mov(registers.rax, value)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(self)
        return _
_Int = Int.__class__

@apply
class BoolStrMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            false = bs.program.get_unique_label()
            bs.code += isa.pop(registers.rax)
            bs.code += isa.cmp(registers.rax, 0)
            bs.code += isa.mov(registers.rax, ctypes.cast(strings['False'], ctypes.c_void_p).value)
            bs.code += isa.je(false)
            bs.code += isa.mov(registers.rax, ctypes.cast(strings['True'], ctypes.c_void_p).value)
            bs.code += false
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Str)
        return _

@apply
class Bool(_Int):
    load = None
    load_constant = None
    def load_false(self):
        def _(bs):
            bs.code += isa.mov(registers.rax, 0)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(self)
        return _
    def load_true(self):
        def _(bs):
            bs.code += isa.mov(registers.rax, 1)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(self)
        return _
    def getattr___str__(self, bs):
        bs.flow.stack.append(BoolStrMeth)

@apply
class FloatStrMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp))
            bs.code += isa.pop(registers.rdi)
            
            bs.code += isa.push(registers.rbp)
            bs.code += isa.mov(registers.rbp, registers.rsp)
            
            bs.code += isa.and_(registers.rsp, -16)
            bs.code += isa.sub(registers.rsp, 64)
            
            bs.code += isa.lea(registers.rdi, MemRef(registers.rbp, -32, data_size=None))
            bs.code += isa.mov(registers.rsi, ctypes.cast(raw_strings["%.12g\0"], ctypes.c_void_p).value)
            bs.code += isa.mov(registers.al, 1)
            bs.code += isa.mov(registers.r15, util.sprintf_addr)
            bs.code += isa.call(registers.r15)
            bs.code += isa.mov(registers.r12, registers.rax)
            
            loop = bs.program.get_unique_label()
            skip = bs.program.get_unique_label()
            add = bs.program.get_unique_label()
            
            bs.code += isa.lea(registers.rax, MemRef(registers.rbp, -32, data_size=None))
            
            bs.code += loop
            
            bs.code += isa.cmp(MemRef(registers.rax, data_size=8), 0)
            bs.code += isa.je(add)
            bs.code += isa.cmp(MemRef(registers.rax, data_size=8), ord('.'))
            bs.code += isa.je(skip)
            bs.code += isa.inc(registers.rax)
            bs.code += isa.jmp(loop)
            
            bs.code += add
            
            bs.code += isa.mov(MemRef(registers.rax, 0, data_size=8), ord('.'))
            bs.code += isa.mov(MemRef(registers.rax, 1, data_size=8), ord('0'))
            bs.code += isa.add(registers.r12, 2)
            
            bs.code += skip
            
            bs.code += isa.mov(MemRef(registers.rbp, -32 - 8), registers.r12)
            bs.code += isa.add(registers.r12, 8)
            
            bs.code += isa.mov(registers.rdi, registers.r12)
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.call(registers.rax)
            
            bs.code += isa.mov(registers.rdi, registers.rax)
            bs.code += isa.lea(registers.rsi, MemRef(registers.rbp, -32 - 8, data_size=None))
            bs.code += isa.mov(registers.rdx, registers.r12)
            bs.code += isa.mov(registers.rax, ctypes.cast(ctypes.memmove, ctypes.c_void_p).value)	
            bs.code += isa.call(registers.rax)
            
            bs.code += isa.mov(registers.rsp, registers.rbp)
            bs.code += isa.pop(registers.rbp)
            
            bs.code += isa.push(registers.rax)
            
            bs.flow.stack.append(Str)
        return _

@apply
class Float(_Type):
    size = 1
    def load_constant(self, value):
        assert isinstance(value, float)
        value = float(value)
        def _(bs):
            bs.code += isa.mov(registers.rax, struct.unpack("l", struct.pack("d", value))[0])
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(self)
        return _
    def const_getattr(self, s):
        def _(bs):
            assert bs.flow.stack[-1] is self
            if s == "__str__":
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(FloatStrMeth)
            else:
                assert False, s
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

class _TupleGetitemMeth(_Type):
    size = 1
    def __init__(self, arg_types):
        self.arg_types = arg_types
        self.arg_size = sum(x.size for x in self.arg_types)
    def __call__(self, arg_types):
        assert arg_types == (Int,)
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

tuplegetitemmeths = util.cdict(_TupleGetitemMeth)

class ProtoTuple(_Type):
    size = 1
    arg_types = None
    def __init__(self, arg_types):
        _Type.__init__(self)
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
    def getattr___getitem__(self, bs): bs.flow.stack.append(tuplegetitemmeths[self.arg_types])
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
        _Type.__init__(self)
        self.name = name
        self.bases = bases
        self.dict = dict
        self.attrs = {}
        self.attr_setters = {}
        self.attrs2 = {}
        self.attr_setters2 = {}
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
            def handler(new_func, new_func2):
                self.attrs[attr] = new_func
                for umr in self.attr_setters.get(attr, []):
                    umr.replace(new_func)
                self.attrs2[attr] = new_func2
                for umr in self.attr_setters2.get(attr, []):
                    umr.replace(new_func2)
            handler_cfunc = ctypes.CFUNCTYPE(None, ctypes.c_int64, ctypes.c_int64)(handler)
            self.cfuncs.append(handler_cfunc)
            bs.code += isa.pop(registers.rsi)
            bs.code += isa.pop(registers.rdi)
            bs.code += isa.mov(registers.r12, registers.rsp)
            bs.code += isa.and_(registers.rsp, -16)
            bs.code += isa.mov(registers.rax, ctypes.cast(handler_cfunc, ctypes.c_void_p).value)
            bs.code += isa.call(registers.rax)
            bs.code += isa.mov(registers.rsp, registers.r12)
        return _

@apply
class Scope(object):
    slots = []
    
    def create(self):
        def _(bs):
            assert not bs.flow.allocd_locals
            
            new_slots = self.get_slots(bs.flow.var_type_impl)
            if new_slots in self.slots:
                new_id = self.slots.index(new_slots)
            else:
                new_id = len(self.slots)
                self.slots.append(new_slots)
            
            new_size = sum(x.size for x, _ in new_slots.itervalues())
            
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.mov(registers.rdi, 8 * new_size)
            bs.code += isa.call(registers.rax)
            bs.code += isa.mov(registers.r15, registers.rax) # r15 = pointer to new slots data
            
            for attr_, (type_, pos_) in new_slots.iteritems():
                old_pos_ = bs.flow.get_var_loc(attr_)
                for i in xrange(type_.size):
                    bs.code += isa.mov(registers.rax, MemRef(registers.rbp, loc + i * 8))
                    bs.code += isa.mov(MemRef(registers.r15, 8 * (pos_ + i)), registers.rax)
            
            bs.code += isa.mov(registers.rdi, 8 * 3)
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.call(registers.rax)
            
            bs.code += isa.mov(MemRef(registers.rax), new_id)
            bs.code += isa.mov(MemRef(registers.rax, 8), registers.r15)
            bs.code += isa.mov(registers.rbx, MemRef(registers.rbp, -8)) # get parent
            bs.code += isa.mov(MemRef(registers.rax, 16), registers.rbx) # parent
            
            bs.code += isa.mov(MemRef(registers.rbp, -8), registers.rax)
        return _
    def set_global(self, attr):
        def _(bs):
            bs.code += isa.mov(registers.r12, MemRef(registers.rbp, -8)) # scope object
            bs.code += isa.push(MemRef(registers.r12)) # slot id
            
            def store_in(slot_id):
                def _(bs):
                    slots = self.slots[slot_id]
                    if attr not in slots or slots[attr][0] is not type:
                        var_types = self.get_var_types(slots)
                        var_types[attr] = None
                        new_slots = self.get_slots(var_types)
                        if new_slots in self.slots:
                            new_id = self.slots.index(new_slots)
                        else:
                            new_id = len(self.slots)
                            self.slots.append(new_slots)
                        
                        #print slots, new_slots, slot_id, new_id
                        
                        #old_size = sum(x.size for x, _ in slots.itervalues())
                        new_size = sum(x.size for x, _ in new_slots.itervalues())
                        
                        bs.code += isa.mov(registers.r14, MemRef(registers.r12, 8)) # r14 = pointer to old slots data
                        
                        bs.code += isa.mov(registers.rax, util.malloc_addr)
                        bs.code += isa.mov(registers.rdi, 8 * new_size)
                        bs.code += isa.call(registers.rax)
                        bs.code += isa.mov(registers.r15, registers.rax) # r15 = pointer to new slots data
                        
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
                return _
            util.unlift(bs, store_in, "Scope.set_global")
        return _
    def set_name(self, attr):
        def _(bs):
            bs.code += isa.mov(registers.r12, MemRef(registers.rbp, -8)) # scope object
            bs.code += isa.push(MemRef(registers.r12)) # slot id
            
            def store_in(slot_id):
                def _(bs):
                    slots = self.slots[slot_id]
                    type = bs.flow.stack.pop()
                    assert type is not None
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
                        new_size = sum(x.size for x, _ in new_slots.itervalues() if x is not None)
                        
                        bs.code += isa.mov(registers.r14, MemRef(registers.r12, 8)) # r14 = pointer to old slots data
                        
                        bs.code += isa.mov(registers.rax, util.malloc_addr)
                        bs.code += isa.mov(registers.rdi, 8 * new_size)
                        bs.code += isa.call(registers.rax)
                        bs.code += isa.mov(registers.r15, registers.rax) # r15 = pointer to new slots data
                        
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
                    
                    bs.code += isa.mov(registers.r14, MemRef(registers.r12, 8))
                    for i in xrange(type.size):
                        bs.code += isa.pop(MemRef(registers.r14, 8 * (slots[attr][1] + i)))
                return _
            util.unlift(bs, store_in, "Scope.set_name")
        return _
    def get_name(self, attr):
        def _(bs):
            bs.code += isa.mov(registers.r12, MemRef(registers.rbp, -8)) # scope object
            bs.code += isa.cmp(registers.r12, 0)
            bs.code += isa.push(-1)
            skip = bs.program.get_unique_label()
            bs.code += isa.je(skip)
            bs.code += isa.pop(registers.rax)
            bs.code += isa.push(MemRef(registers.r12)) # slot id
            bs.code += skip
            
            def load_in(slot_id):
                if slot_id == -1: assert False, attr + " not found"
                def _(bs):
                    slots = self.slots[slot_id]
                    
                    try:
                        type, pos = slots[attr]
                        if type is None: raise KeyError
                    except KeyError:
                        bs.code += isa.mov(registers.r12, MemRef(registers.r12, 16)) # scope object
                        bs.code += isa.cmp(registers.r12, 0)
                        bs.code += isa.push(-1)
                        skip = bs.program.get_unique_label()
                        bs.code += isa.je(skip)
                        bs.code += isa.pop(registers.rax)
                        bs.code += isa.push(MemRef(registers.r12)) # slot id
                        bs.code += skip
                        util.unlift(bs, load_in, "Scope.get_name")
                    else:
                        bs.code += isa.mov(registers.r14, MemRef(registers.r12, 8))
                        for i in reversed(xrange(type.size)):
                            bs.code += isa.push(MemRef(registers.r14, 8 * (pos + i)))
                        bs.flow.stack.append(type)
                return _
            util.unlift(bs, load_in, "Scope.get_name")
        return _
    def del_name(self, attr):
        def _(bs):
            assert bs.flow.stack.pop() is self
        return _
    def get_slots(self, var_types):
        pos = 0
        res = {}
        for name, type in sorted(var_types.iteritems()):
            res[name] = (type, pos)
            pos += type.size if type is not None else 0
        return res
    def get_var_types(self, slots):
        res = {}
        for name, (type, pos) in slots.iteritems():
            res[name] = type
        return res

class ProtoInstance(_Type):
    size = 1
    def __init__(self, type):
        _Type.__init__(self)
        self.type = type
        self.slots = [{}]
    def __repr__(self):
        return "ProtoInstance(%s)" % (self.type,)
    def new(self, arg_types):
        def _(bs):
            bs.code += isa.mov(registers.rdi, 8 * 2)
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.call(registers.rax)
            bs.code += isa.mov(registers.r12, registers.rax)
            
            bs.code += isa.mov(MemRef(registers.r12), 0)
            bs.code += isa.mov(MemRef(registers.r12, 8), 0)
            
            bs.code += isa.push(registers.r12)
            bs.flow.stack.append(self)
            
            self.type.attr_setters.setdefault('__init__', []).append(util.UpdatableMovRax(bs.code, self.type.attrs.get('__init__', say_functions[self.type.name, '__init__'])))
            bs.code += isa.push(registers.rax)
            self.type.attr_setters2.setdefault('__init__', []).append(util.UpdatableMovRax(bs.code, self.type.attrs2.get('__init__', say_functions[self.type.name, '__init__'])))
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Function)
            
            bs.code += isa.push(registers.r12)
            bs.flow.stack.append(self)
            
            arg_size = sum(x.size for x in arg_types)
            for i in xrange(arg_size):
                bs.code += isa.push(MemRef(registers.rsp, 8*arg_size))
            bs.flow.stack.extend(arg_types)

            bs.this.append(bs.flow.stack[-2 - len(arg_types)]((self,) + arg_types))
            
            @bs.this.append
            def _(bs, arg_types=arg_types):
                # discard __init__ result
                type = bs.flow.stack.pop()
                for i in xrange(type.size):
                    bs.code += isa.pop(registers.rax)
                
                assert bs.flow.stack.pop() is self
                
                bs.code += isa.pop(registers.r12)
                
                for arg_type in arg_types[::-1]:
                    assert bs.flow.stack.pop() is arg_type
                    for i in xrange(arg_type.size):
                        bs.code += isa.pop(registers.rax)
                
                assert bs.flow.stack[-1] is self.type, bs.flow.stack[-1]
                bs.flow.stack.pop()
                
                bs.code += isa.push(registers.r12)
                bs.flow.stack.append(self)
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
                        
                        bs.code += isa.mov(registers.r14, MemRef(registers.r12, 8)) # r14 = pointer to old slots data
                        
                        bs.code += isa.mov(registers.rax, util.malloc_addr)
                        bs.code += isa.mov(registers.rdi, 8 * new_size)
                        bs.code += isa.call(registers.rax)
                        bs.code += isa.mov(registers.r15, registers.rax) # r15 = pointer to new slots data
                        
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
                    
                    bs.code += isa.mov(registers.r14, MemRef(registers.r12, 8))
                    for i in xrange(type.size):
                        bs.code += isa.pop(MemRef(registers.r14, 8 * (slots[attr][1] + i)))
                return _
            util.unlift(bs, _, "ProtoInstance.setattr_const_string")
        return _
    def const_getattr(self, attr):
        if attr == '__class__':
            def _(bs):
                assert bs.flow.stack.pop() is self
                for i in xrange(self.size):
                    bs.code += isa.pop(registers.rax)
                assert self.type.size == 0
                bs.flow.stack.append(self.type)
            return _
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
                        self.type.attr_setters.setdefault(attr, []).append(util.UpdatableMovRax(bs.code, self.type.attrs.get(attr, say_functions[self.type.name, attr])))
                        bs.code += isa.push(registers.rax)
                        self.type.attr_setters2.setdefault(attr, []).append(util.UpdatableMovRax(bs.code, self.type.attrs2.get(attr, say_functions[self.type.name, attr])))
                        bs.code += isa.push(registers.rax)
                        bs.flow.stack.append(Function)
                        
                        assert bs.flow.stack[-1] is Function
                        
                        bs.code += isa.push(registers.r12)
                        bs.flow.stack.append(self)
                        
                        bs.this.append(methods[self].load())
                return _
            util.unlift(bs, _, "ProtoInstance.const_getattr")
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

# store slot in bs.flow.stack once we know it ... though it can change in functions and (undetectibly) other threads .. D:
# i hate threads

protoinstances = util.cdict(ProtoInstance)

raw_strings = util.cdict(lambda s: ctypes.create_string_buffer(s))
strings = util.cdict(lambda s: ctypes.create_string_buffer(struct.pack("L", len(s)) + s))

@apply
class StrStrMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.flow.stack.append(Str)
        return _

@apply
class StrGetitemMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        #assert not arg_types
        assert arg_types == (Int,)
        def _(bs):
            assert bs.flow.stack.pop() is Int
            bs.code += isa.pop(registers.r13)
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.r12)
            
            bs.code += isa.add(registers.r12, 8)
            bs.code += isa.shl(registers.r13, 3)
            bs.code += isa.add(registers.r12, registers.r13)
            bs.code += isa.mov(registers.r13, MemRef(registers.r12))
            
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.mov(registers.rdi, 8 * 2)
            bs.code += isa.call(registers.rax)
            
            bs.code += isa.mov(MemRef(registers.rax), 1)
            bs.code += isa.mov(MemRef(registers.rax, 8), registers.r13)
            
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Str)
        return _

@apply
class StrOrdMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            
            bs.code += isa.add(registers.rax, 8)
            bs.code += isa.mov(registers.rax, MemRef(registers.r12))
            
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Int)
        return _

class _StrCmpMeth(_Type):
    size = 1
    def __init__(self, op_name):
        _Type.__init__(self)
        self.op_name = op_name
    def __call__(self, arg_types):
        assert arg_types == (Str,)
        def _(bs):
            assert bs.flow.stack.pop() is Str
            bs.code += isa.pop(registers.rbx)
            
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            
            end = bs.program.get_unique_label()
            
            bs.code += isa.mov(registers.rdx, MemRef(registers.rax))
            
            if self.op_name in ('eq', 'ne'):
                bs.code += isa.mov(registers.rcx, 0 if self.op_name == 'eq' else 1)
            
            bs.code += isa.cmp(registers.rdx, MemRef(registers.rbx))
            
            if self.op_name in ('eq', 'ne'):
                bs.code += isa.jne(end)
            
            skip = bs.program.get_unique_label()
            bs.code += isa.jle(skip)
            bs.code += isa.mov(registers.rdx, MemRef(registers.rbx))
            bs.code += skip
            
            # rdx is length
            # r11 is pos
            
            bs.code += isa.mov(registers.r11, 0)
            bs.code += isa.add(registers.rax, 8)
            bs.code += isa.add(registers.rbx, 8)
            
            loop = bs.program.get_unique_label()
            bs.code += loop
            
            bs.code += isa.cmp(registers.r11, registers.rdx)
            bs.code += isa.mov(registers.rcx, 1 if self.op_name in ('eq', 'ge', 'le') else 0) # they're equal
            bs.code += isa.je(end)
            bs.code += isa.mov(registers.r12, MemRef(registers.rbx))
            bs.code += isa.cmp(MemRef(registers.rax), registers.r12)
            
            if self.op_name in ('eq',):
                bs.code += isa.mov(registers.rcx, 0)
                bs.code += isa.jne(end)
            if self.op_name in ('lt','le','gt','ge'):
                bs.code += isa.mov(registers.rcx, 1 if self.op_name in ('le','lt') else 0)
                bs.code += isa.jl(end)
            
            bs.code += isa.mov(registers.rcx, 1 if self.op_name in ('le','lt','ne') else 0)
            bs.code += isa.jl(end)
            bs.code += isa.mov(registers.rcx, 1 if self.op_name in ('ge','gt','ne') else 0)
            bs.code += isa.jg(end)
            
            bs.code += isa.jne(end)
            
            bs.code += isa.inc(registers.rax)
            bs.code += isa.inc(registers.rbx)
            bs.code += isa.inc(registers.r11)
            bs.code += isa.jmp(loop)
            
            bs.code += end
            
            bs.code += isa.push(registers.rcx)
            bs.flow.stack.append(Bool)
        return _

class _StrCmpMeth(_Type):
    size = 1
    def __init__(self, op_name):
        _Type.__init__(self)
        self.op_name = op_name
    def __call__(self, arg_types):
        assert arg_types == (Str,)
        def _(bs):
            assert bs.flow.stack.pop() is Str
            bs.code += isa.pop(registers.rdi)
            
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rsi)
            
            end = bs.program.get_unique_label()
            
            bs.code += isa.mov(registers.rcx, MemRef(registers.rsi))
            bs.code += isa.cmp(registers.rcx, MemRef(registers.rdi))
            if self.op_name in ('eq', 'ne'):
                bs.code += isa.mov(registers.rax, 0 if self.op_name == 'eq' else 1)
                bs.code += isa.jne(end)
            bs.code += isa.cmova(registers.rcx, MemRef(registers.rdi))
            
            bs.code += isa.mov(registers.r12, 0)
            bs.code += {
                'ne': isa.setne,
                'eq': isa.sete,
                'lt': isa.setb,
                'le': isa.setbe,
                'gt': isa.seta,
                'ge': isa.setae,
            }[self.op_name](registers.r12b)
            
            bs.code += isa.add(registers.rdi, 8)
            bs.code += isa.add(registers.rsi, 8)
            
            bs.code += isa.cmp(registers.rax, registers.rax)
            
            bs.code += isa.repz()
            bs.code += isa.cmpsb()
            
            bs.code += isa.mov(registers.rax, 1 if self.op_name in ('le','lt','ne') else 0) # less
            bs.code += isa.jl(end)
            bs.code += isa.mov(registers.rax, 1 if self.op_name in ('ge','gt','ne') else 0) # greater
            bs.code += isa.jg(end)
            
            bs.code += isa.mov(registers.rax, registers.r12)
            bs.code += end
            
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Bool)
        return _

StrCmpMeths = util.cdict(_StrCmpMeth)

@apply
class Str(_Type):
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
    
    def getattr___str__(self, bs): bs.flow.stack.append(StrStrMeth)
    def getattr___getitem__(self, bs): bs.flow.stack.append(StrGetitemMeth)
    def getattr___ord__(self, bs): bs.flow.stack.append(StrOrdMeth)
    def getattr___gt__(self, bs): bs.flow.stack.append(StrCmpMeths['gt'])
    def getattr___lt__(self, bs): bs.flow.stack.append(StrCmpMeths['lt'])
    def getattr___ge__(self, bs): bs.flow.stack.append(StrCmpMeths['ge'])
    def getattr___le__(self, bs): bs.flow.stack.append(StrCmpMeths['le'])
    def getattr___eq__(self, bs): bs.flow.stack.append(StrCmpMeths['eq'])
    def getattr___ne__(self, bs): bs.flow.stack.append(StrCmpMeths['ne'])

functions = []


def _get_func_say(x):
    functions.append("i can't find " + str(x))
    return len(functions) - 1

say_functions = util.cdict(_get_func_say)

@apply
class Function(_Type):
    size = 2
    def __call__(self, arg_types):
        def _(bs):
            assert bs.flow.stack[-1 - len(arg_types)] is self, bs.flow.stack[-1 - len(arg_types)]
            arg_size = sum(x.size for x in arg_types)
            bs.code += isa.push(MemRef(registers.rsp, 8*arg_size + 8))
            #bs.code += isa.mov(registers.rax, MemRef(registers.rsp, 8*arg_size - 8))
            
            def _(value):
                def _(bs):
                    if isinstance(functions[value], str):
                        assert False, functions[value]
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
            for arg in arg_types[::-1]:
                assert bs.flow.stack.pop() is arg
            assert bs.flow.stack.pop() is self
            bs.flow.stack.append(Function)
            bs.flow.stack.append(self.self_type)
            for arg in arg_types:
                bs.flow.stack.append(arg)
            bs.this.append(Function((self.self_type,) + arg_types))
        return _

methods = util.cdict(_Method)

@apply
class NoneStrMeth(_Type):
    size = 0
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.this.append(Str.load_constant('None'))
        return _

@apply
class NoneType(_Type):
    size = 0
    def load(self):
        def _(bs):
            bs.flow.stack.append(NoneType)
        return _
    def to_python(self, data):
        assert not data
    def const_getattr(self, s):
        def _(bs):
            assert bs.flow.stack[-1] is self
            if s == "__str__":
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(NoneStrMeth)
            else:
                assert False, s
        return _
