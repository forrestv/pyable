from __future__ import division

import struct
import ctypes
import ast
import random

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
    assert inst.size <= 4

#@apply
class _Type(object):
    def __init__(self):
        number(self)
    def __repr__(self):
        return self.__class__.__name__
    def const_getattr(self, s):
        def not_found(bs):
            import mypyable
            bs.this.append(ast.Raise(
                type=ast.Call(
                    func=mypyable.AttributeError_impl.load,
                    args=[ast.Str(s=s)],
                    keywords=[],
                    starargs=None,
                    kwargs=None,
                    ),
                inst=None,
                tback=None,
                ),
            )
        f = getattr(self, "getattr_" + s, not_found)
        def _(bs):
            assert bs.flow.stack.pop() is self
            f(bs)
        return _
    def call_const(self, c):
        return None
    def to_python(self, data):
        return self
#_Type = Type.__class__

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
            
            
            # add small string test/create here
            # fix other str producing functions to add NUL at end
            
            
            
            bs.code += isa.push(registers.r12)
            bs.code += isa.add(registers.r12, 9)
            
            bs.code += isa.mov(registers.r13, registers.rsp)
            
            bs.code += isa.and_(registers.rsp, -16)
            
            bs.code += isa.mov(registers.rdi, registers.r12)
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.call(registers.rax)
            
            bs.code += isa.mov(MemRef(registers.rax, 1, registers.r12), 0)
            
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
            assert bs.flow.stack.pop() is self
            if other_type is not Int and other_type is not Bool:
                for i in xrange(other_type.size):
                    bs.code += isa.pop(registers.rax)
                bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(NotImplementedType)
                return
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
            assert bs.flow.stack.pop() is self
            if other_type is not Int and other_type is not Bool:
                for i in xrange(other_type.size):
                    bs.code += isa.pop(registers.rax)
                bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(NotImplementedType)
                return
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
            assert bs.flow.stack.pop() is self
            if other_type is not Int and other_type is not Bool:
                for i in xrange(other_type.size):
                    bs.code += isa.pop(registers.rax)
                bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(NotImplementedType)
                return
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
            assert bs.flow.stack.pop() is self
            if other_type is not Int and other_type is not Bool:
                for i in xrange(other_type.size):
                    bs.code += isa.pop(registers.rax)
                bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(NotImplementedType)
                return
            bs.code += isa.pop(registers.rbx)
            bs.code += isa.pop(registers.rax)
            bs.code += isa.mov(registers.rdx, 0)
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
            bs.code += isa.mov(registers.rcx, 1)
            
            label = bs.program.get_unique_label()
            
            bs.code += self.inst(label)
            
            bs.code += isa.mov(registers.rcx, 0)
            
            bs.code += label
            
            bs.code += isa.push(registers.rcx)
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
            assert bs.flow.stack.pop() is self
            if other_type is not Int and other_type is not Bool:
                for i in xrange(other_type.size):
                    bs.code += isa.pop(registers.rax)
                bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(NotImplementedType)
                return
            bs.code += isa.pop(registers.rbx)
            bs.code += isa.pop(registers.rax)
            bs.code += isa.mov(registers.rdx, 0)
            bs.code += isa.mov(registers.rax, registers.rax)
            bs.code += isa.idiv(registers.rbx)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Int)
        return _

@apply
class IntPowMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert len(arg_types) == 1
        def _(bs):
            other_type = bs.flow.stack.pop()
            assert bs.flow.stack.pop() is self
            if other_type is not Int and other_type is not Bool:
                for i in xrange(other_type.size):
                    bs.code += isa.pop(registers.rax)
                bs.code += isa.pop(registers.rax)
                bs.flow.stack.append(NotImplementedType)
                return
            loop = bs.program.get_unique_label()
            end = bs.program.get_unique_label()
            
            bs.code += isa.pop(registers.rbx) # exponent
            bs.code += isa.pop(registers.rax) # base
            bs.code += isa.mov(registers.rdx, 1)
            bs.code += isa.sub(registers.rbx, 0)
            bs.code += loop
            bs.code += isa.jz(end)
            bs.code += isa.imul(registers.rdx, registers.rax)
            bs.code += isa.sub(registers.rbx, 1)
            bs.code += isa.jmp(loop)
            bs.code += end
            bs.code += isa.push(registers.rdx)
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
    def getattr___repr__(self, bs):
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
    def getattr___pow__(self, bs):
        bs.flow.stack.append(IntPowMeth)
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
            bs.code += isa.mov(registers.rax, util.fake_int(value))
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(self)
        return _
    def to_python(self, data):
        i, = struct.unpack("l", data)
        return i
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
            
            
            # add small string test/alloc here
            
            
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
class FloatAddMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert arg_types in [(Int,), (Float,)]
        def _(bs):
            other = bs.flow.stack.pop()
            assert bs.flow.stack.pop() is self
            if isinstance(other, type(Float)):
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp, 8))
                bs.code += isa.movsd(registers.xmm1, MemRef(registers.rsp))
                bs.code += isa.pop(registers.rax)
            elif isinstance(other, type(Int)):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.cvtsi2sd(registers.xmm1, registers.rbx)
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp))
            else:
                assert False, other
            bs.code += isa.addsd(registers.xmm0, registers.xmm1)
            bs.code += isa.movsd(MemRef(registers.rsp), registers.xmm0)
            bs.flow.stack.append(Float)
        return _

@apply
class FloatNegMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            bs.code += isa.mov(registers.rbx, -9223372036854775808)
            bs.code += isa.xor(registers.rax, registers.rbx)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Float)
        return _

@apply
class FloatSubMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert arg_types in [(Int,), (Float,)]
        def _(bs):
            other = bs.flow.stack.pop()
            assert bs.flow.stack.pop() is self
            if isinstance(other, type(Float)):
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp, 8))
                bs.code += isa.movsd(registers.xmm1, MemRef(registers.rsp))
                bs.code += isa.pop(registers.rax)
            elif isinstance(other, type(Int)):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.cvtsi2sd(registers.xmm1, registers.rbx)
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp))
            else:
                assert False, other
            bs.code += isa.subsd(registers.xmm0, registers.xmm1)
            bs.code += isa.movsd(MemRef(registers.rsp), registers.xmm0)
            bs.flow.stack.append(Float)
        return _

@apply
class FloatRSubMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert arg_types in [(Int,), (Float,)]
        def _(bs):
            other = bs.flow.stack.pop()
            assert bs.flow.stack.pop() is self
            if isinstance(other, type(Float)):
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp, 8))
                bs.code += isa.movsd(registers.xmm1, MemRef(registers.rsp))
                bs.code += isa.pop(registers.rax)
            elif isinstance(other, type(Int)):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.cvtsi2sd(registers.xmm1, registers.rbx)
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp))
            else:
                assert False, other
            bs.code += isa.subsd(registers.xmm1, registers.xmm0)
            bs.code += isa.movsd(MemRef(registers.rsp), registers.xmm1)
            bs.flow.stack.append(Float)
        return _

@apply
class FloatMulMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert arg_types in [(Int,), (Float,)]
        def _(bs):
            other = bs.flow.stack.pop()
            assert bs.flow.stack.pop() is self
            if isinstance(other, type(Float)):
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp, 8))
                bs.code += isa.movsd(registers.xmm1, MemRef(registers.rsp))
                bs.code += isa.pop(registers.rax)
            elif isinstance(other, type(Int)):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.cvtsi2sd(registers.xmm1, registers.rbx)
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp))
            else:
                assert False, other
            bs.code += isa.mulsd(registers.xmm0, registers.xmm1)
            bs.code += isa.movsd(MemRef(registers.rsp), registers.xmm0)
            bs.flow.stack.append(Float)
        return _

@apply
class FloatDivMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert arg_types in [(Int,), (Float,)]
        def _(bs):
            other = bs.flow.stack.pop()
            assert bs.flow.stack.pop() is self
            if isinstance(other, type(Float)):
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp, 8))
                bs.code += isa.movsd(registers.xmm1, MemRef(registers.rsp))
                bs.code += isa.pop(registers.rax)
            elif isinstance(other, type(Int)):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.cvtsi2sd(registers.xmm1, registers.rbx)
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp))
            else:
                assert False, other
            bs.code += isa.divsd(registers.xmm0, registers.xmm1)
            bs.code += isa.movsd(MemRef(registers.rsp), registers.xmm0)
            bs.flow.stack.append(Float)
        return _

@apply
class FloatRDivMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert arg_types in [(Int,), (Float,)]
        def _(bs):
            other = bs.flow.stack.pop()
            assert bs.flow.stack.pop() is self
            if isinstance(other, type(Float)):
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp, 8))
                bs.code += isa.movsd(registers.xmm1, MemRef(registers.rsp))
                bs.code += isa.pop(registers.rax)
            elif isinstance(other, type(Int)):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.cvtsi2sd(registers.xmm1, registers.rbx)
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp))
            else:
                assert False, other
            bs.code += isa.divsd(registers.xmm1, registers.xmm0)
            bs.code += isa.movsd(MemRef(registers.rsp), registers.xmm1)
            bs.flow.stack.append(Float)
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
    def getattr___str__(self, bs): bs.flow.stack.append(FloatStrMeth)
    def getattr___neg__(self, bs): bs.flow.stack.append(FloatNegMeth)
    
    def getattr___add__(self, bs): bs.flow.stack.append(FloatAddMeth)
    def getattr___radd__(self, bs): bs.flow.stack.append(FloatAddMeth)
    
    def getattr___sub__(self, bs): bs.flow.stack.append(FloatSubMeth)
    def getattr___rsub__(self, bs): bs.flow.stack.append(FloatRSubMeth)
    
    def getattr___mul__(self, bs): bs.flow.stack.append(FloatMulMeth)
    def getattr___rmul__(self, bs): bs.flow.stack.append(FloatMulMeth)
    
    def getattr___div__(self, bs): bs.flow.stack.append(FloatDivMeth)
    def getattr___rdiv__(self, bs): bs.flow.stack.append(FloatRDivMeth)

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
        data, = struct.unpack("q", data)
        data = ctypes.string_at(data, self.arg_size*8)
        pos = self.arg_size
        res = []
        for item in self.arg_types:
            pos -= item.size
            res.append(item.to_python(data[pos:pos+item.size]))
        return tuple(res)
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

prototuples = util.cdict(ProtoTuple)

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
        self.bases = list(bases)
        #print bases
        self.dict = dict
        self.attrs = {}
        self.attr_setters = {}
        self.cfuncs = []
        import C3
        self.mro = C3.merge([[self]] + [x.mro for x in self.bases] + [self.bases])
    def __repr__(self):
        return self.name
        return "ProtoObject" + repr((self.name, self.bases, self.dict))
    def __call__(self, arg_types):
        def _(bs):
            assert bs.flow.stack[-1 - len(arg_types)] is self
            bs.this.append(protoinstances[self].new(arg_types))
        return _
    def issubclass(self, other):
        return self in other.mro
    def isinstance(self, other):
        return self in other.type.mro
    def setattr_const_string(self, attr):
        def _(bs):
            assert bs.flow.stack.pop() is self
            type = bs.flow.stack.pop()
            assert type is Function
            def handler(new_func, new_func2):
                r = new_func, new_func2
                self.attrs[attr] = r
                for umr in self.attr_setters.get(attr, []):
                    umr(r)
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
    def getattr___name__(self, bs):
        bs.this.append(Str.load_constant(self.name))
    def load(self, bs):
        bs.flow.stack.append(self)

name_bits = util.cdict(lambda name: 1 << random.randrange(64))

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
            
            bits = 0
            
            for attr_, (type_, pos_) in new_slots.iteritems():
                old_pos_ = bs.flow.get_var_loc(attr_)
                for i in xrange(type_.size):
                    bs.code += isa.mov(registers.rax, MemRef(registers.rbp, old_pos_ + i * 8))
                    bs.code += isa.mov(MemRef(registers.r15, 8 * (pos_ + i)), registers.rax)
                bits |= name_bits[attr_]
            
            bs.code += isa.mov(registers.rdi, 8 * 4)
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.call(registers.rax)
            
            bs.code += isa.mov(MemRef(registers.rax), new_id)
            bs.code += isa.mov(MemRef(registers.rax, 8), registers.r15)
            bs.code += isa.mov(registers.rbx, MemRef(registers.rbp, -8)) # get parent
            bs.code += isa.mov(MemRef(registers.rax, 16), registers.rbx) # parent
            bs.code += isa.mov(registers.rbx, bits)
            bs.code += isa.mov(MemRef(registers.rax, 24), registers.rbx) # parent
            
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
                        # can't do this, but maybe there is some way
                        # bs.code += isa.and_(MemRef(registers.r12, 24), ~name_bits[attr])
                        
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
                        bs.code += isa.mov(registers.rax, name_bits[attr])
                        bs.code += isa.or_(MemRef(registers.r12, 24), registers.rax)
                        
                        slots = new_slots
                    
                    bs.code += isa.mov(registers.r14, MemRef(registers.r12, 8))
                    for i in xrange(type.size):
                        bs.code += isa.pop(MemRef(registers.r14, 8 * (slots[attr][1] + i)))
                return _
            util.unlift(bs, store_in, "Scope.set_name")
        return _
    def get_name(self, attr):
        bits = name_bits[attr]
        def _(bs):
            bs.code += isa.mov(registers.r12, MemRef(registers.rbp, -8)) # scope object
            loop = bs.program.get_unique_label()
            bs.code += loop
            bs.code += isa.cmp(registers.r12, 0)
            bs.code += isa.mov(registers.rax, -1)
            skip = bs.program.get_unique_label()
            bs.code += isa.je(skip)
            bs.code += isa.mov(registers.rax, name_bits[attr])
            bs.code += isa.test(MemRef(registers.r12, 24), registers.rax)
            bs.code += isa.mov(registers.rax, MemRef(registers.r12)) # slot id
            bs.code += isa.jnz(skip)
            bs.code += isa.mov(registers.r12, MemRef(registers.r12, 16))
            bs.code += isa.jmp(loop)
            bs.code += skip
            bs.code += isa.push(registers.rax) # slot id
            
            
            def load_in(slot_id):
                def _(bs):
                    if slot_id == -1:
                        print attr, "not found XXX"
                        import mypyable
                        bs.this.append(ast.Raise(
                            type=ast.Call(
                                func=mypyable.NameError_impl.load,
                                args=[],
                                keywords=[],
                                starargs=None,
                                kwargs=None,
                                ),
                            inst=None,
                            tback=None,
                        ))
                        return
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
            bs.code += isa.mov(registers.rdi, 8 * 3)
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.call(registers.rax)
            bs.code += isa.mov(registers.r12, registers.rax)
            
            bs.code += isa.mov(MemRef(registers.r12), 0)
            bs.code += isa.mov(MemRef(registers.r12, 8), 0)
            bs.code += isa.mov(MemRef(registers.r12, 16), 0)
            
            bs.code += isa.push(registers.r12)
            bs.flow.stack.append(self)
            
            func1 = util.UpdatableMovRax(bs.code, 0)
            bs.code += isa.push(registers.rax)
            func2 = util.UpdatableMovRax(bs.code, 0)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Function)
            
            def func_changed(*args):
                for i in self.type.mro:
                    if '__init__' in i.attrs:
                        new = i.attrs['__init__']
                        break
                else:
                    new = (say_functions[self.type.name, '__init__'], 0)
                func1.replace(new[0])
                func2.replace(new[1])
            
            for i in self.type.mro:
                i.attr_setters.setdefault('__init__', []).append(func_changed)
            
            func_changed()
            
            bs.code += isa.push(registers.r12)
            bs.flow.stack.append(self)
            
            arg_size = sum(x.size for x in arg_types)
            for i in xrange(arg_size):
                bs.code += isa.push(MemRef(registers.rsp, 8*arg_size+8+8+8))
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
        assert attr != '__class__'
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
                        bs.code += isa.mov(registers.rax, name_bits[attr])
                        bs.code += isa.or_(MemRef(registers.r12, 16), registers.rax)
                        
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
                        func1 = util.UpdatableMovRax(bs.code, 0)
                        bs.code += isa.push(registers.rax)
                        func2 = util.UpdatableMovRax(bs.code, 0)
                        bs.code += isa.push(registers.rax)
                        bs.flow.stack.append(Function)
                        
                        def func_changed(*args):
                            for i in self.type.mro:
                                if attr in i.attrs:
                                    new = i.attrs[attr]
                                    break
                            else:
                                new = (say_functions[self.type.name, attr], 0)
                            func1.replace(new[0])
                            func2.replace(new[1])
                        
                        for i in self.type.mro:
                            i.attr_setters.setdefault(attr, []).append(func_changed)
                        
                        func_changed()
                        
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
strings = util.cdict(lambda s: ctypes.create_string_buffer(struct.pack("L", len(s)) + s + "\x00"))

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
        if arg_types == (Int,):
            def _(bs):
                assert bs.flow.stack.pop() is Int
                bs.code += isa.pop(registers.r13)
                assert bs.flow.stack.pop() is self
                bs.code += isa.pop(registers.r12)
                
                skip = bs.program.get_unique_label()
                end = bs.program.get_unique_label()
                bs.code += isa.test(registers.r12, 1)
                bs.code += isa.jz(skip)
                # short
                bs.code += isa.mov(registers.rax, registers.r12)
                bs.code += isa.shr(registers.rax, 1)
                bs.code += isa.and_(registers.rax, 127)
                bs.code += isa.lea(registers.r12, MemRef(registers.rsp, -15, data_size=None))
                bs.code += isa.jmp(end)
                bs.code += skip
                # long
                bs.code += isa.mov(registers.rax, MemRef(registers.r12))
                bs.code += end
                
                
                skip = bs.program.get_unique_label()
                bs.code += isa.cmp(registers.r13, 0)
                bs.code += isa.jge(skip)
                bs.code += isa.add(registers.r13, registers.rax)
                bs.code += skip
                
                bs.code += isa.mov(registers.rax, 0)
                bs.code += isa.mov(registers.al, MemRef(registers.r12, 8, registers.r13, data_size=8))
                bs.code += isa.shl(registers.rax, 8)
                bs.code += isa.mov(registers.al, 3)
                
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(Str)
        elif len(arg_types) == 1 and isinstance(arg_types[0], ProtoSlice):
            def _(bs):
                bs.this.append(bs.flow.stack[-1].store())
                @bs.this.append
                def _(bs):
                    step_type = bs.flow.stack.pop()
                    if step_type is Int:
                        bs.code += isa.pop(registers.r13)
                    elif step_type is NoneType:
                        pass
                    else:
                        assert False, step_type
                    
                    stop_type = bs.flow.stack.pop()
                    if stop_type is Int:
                        bs.code += isa.pop(registers.r12)
                    elif stop_type is NoneType:
                        pass
                    else:
                        assert False, stop_type
                    
                    start_type = bs.flow.stack.pop()
                    if start_type is Int:
                        bs.code += isa.pop(registers.r11)
                    elif start_type is NoneType:
                        pass
                    else:
                        assert False, start_type
                    
                    assert bs.flow.stack.pop() is self
                    bs.code += isa.pop(registers.r9)
                    
                    skip = bs.program.get_unique_label()
                    end = bs.program.get_unique_label()
                    
                    bs.code += isa.test(registers.r9, 1)
                    bs.code += isa.jz(skip)
                    
                    # short initial, string is on top of stack
                    bs.code += isa.mov(registers.r8, registers.r9)
                    bs.code += isa.shr(registers.r8, 1)
                    bs.code += isa.and_(registers.r8, 127)
                    bs.code += isa.lea(registers.r9, MemRef(registers.rsp, -7, data_size=None))
                    bs.code += isa.jmp(end)
                    
                    bs.code += skip
                    
                    # long initial
                    bs.code += isa.mov(registers.r8, MemRef(registers.r9))
                    bs.code += isa.add(registers.r9, 8)
                    
                    bs.code += end
                    
                    # r8 = length
                    # r9 = pointer
                    
                    # r11 = start
                    # r12 = stop
                    # r13 = step
                    
                    # r10 = slicelength
                    
                    #if step is None:
                    #    step = 1
                    if step_type is NoneType:
                        bs.code += isa.mov(registers.r13, 1)
                    
                    #if start is None:
                    if start_type is NoneType:
                        #start = step < 0 ? length - 1 : 0
                        if step_type is NoneType:
                            bs.code += isa.mov(registers.r11, 0)
                        else:
                            bs.code += isa.cmp(registers.r13, 0)
                            skip2 = bs.program.get_unique_label()
                            end2 = bs.program.get_unique_label()
                            bs.code += isa.jl(skip2)
                            bs.code += isa.mov(registers.r11, 0)
                            bs.code += isa.jmp(end2)
                            bs.code += skip2
                            bs.code += isa.mov(registers.r11, registers.r8)
                            bs.code += isa.dec(registers.r11)
                            bs.code += end2
                    #else:
                    else:
                        #if start < 0:
                        #    start += length
                        #    if start < 0:
                        #        start = step < 0 ? -1 : 0
                        #elif start >= length:
                        #    start = step < 0 ? length - 1 : length
                        bs.code += isa.cmp(registers.r11, 0)
                        skip2 = bs.program.get_unique_label()
                        end2 = bs.program.get_unique_label()
                        bs.code += isa.jl(skip2)
                        
                        bs.code += isa.cmp(registers.r11, registers.r8)
                        bs.code += isa.jl(end2)
                        
                        bs.code += isa.cmp(registers.r13, 0)
                        skip5 = bs.program.get_unique_label()
                        end5 = bs.program.get_unique_label()
                        bs.code += isa.jl(skip5)
                        bs.code += isa.mov(registers.r11, registers.r8)
                        bs.code += isa.jmp(end5)
                        bs.code += skip5
                        bs.code += isa.mov(registers.r11, registers.r8)
                        bs.code += isa.dec(registers.r11)
                        bs.code += end5
                        
                        bs.code += isa.jmp(end2)
                        bs.code += skip2
                        bs.code += isa.add(registers.r11, registers.r8)
                        
                        bs.code += isa.cmp(registers.r11, 0)
                        skip3 = bs.program.get_unique_label()
                        end3 = bs.program.get_unique_label()
                        bs.code += isa.jl(skip3)
                        bs.code += isa.jmp(end3)
                        bs.code += skip3
                        
                        bs.code += isa.cmp(registers.r13, 0)
                        skip4 = bs.program.get_unique_label()
                        end4 = bs.program.get_unique_label()
                        bs.code += isa.jl(skip4)
                        bs.code += isa.mov(registers.r11, 0)
                        bs.code += isa.jmp(end4)
                        bs.code += skip4
                        bs.code += isa.mov(registers.r11, -1)
                        bs.code += end4
                        
                        bs.code += end3
                        
                        bs.code += end2
                    
                    #if stop is None:
                    if stop_type is NoneType:
                        #stop = step < 0 ? -1 : length
                        if step_type is NoneType:
                            bs.code += isa.mov(registers.r12, 0)
                        else:
                            bs.code += isa.cmp(registers.r13, 0)
                            skip2 = bs.program.get_unique_label()
                            end2 = bs.program.get_unique_label()
                            bs.code += isa.jl(skip2)
                            bs.code += isa.mov(registers.r12, registers.r8)
                            bs.code += isa.jmp(end2)
                            bs.code += skip2
                            bs.code += isa.mov(registers.r12, -1)
                            bs.code += end2
                    #else:
                    else:
                        #if stop < 0:
                        #    stop += length
                        #    if stop < 0:
                        #        stop = step < 0 ? -1 : 0
                        #elif stop >= length:
                        #    stop = step < 0 ? length - 1 : length
                        bs.code += isa.cmp(registers.r12, 0)
                        skip2 = bs.program.get_unique_label()
                        end2 = bs.program.get_unique_label()
                        bs.code += isa.jl(skip2)
                        
                        bs.code += isa.cmp(registers.r12, registers.r8)
                        bs.code += isa.jl(end2)
                        
                        bs.code += isa.cmp(registers.r13, 0)
                        skip5 = bs.program.get_unique_label()
                        end5 = bs.program.get_unique_label()
                        bs.code += isa.jl(skip5)
                        bs.code += isa.mov(registers.r12, registers.r8)
                        bs.code += isa.jmp(end5)
                        bs.code += skip5
                        bs.code += isa.mov(registers.r12, registers.r8)
                        bs.code += isa.dec(registers.r12)
                        bs.code += end5
                        
                        bs.code += isa.jmp(end2)
                        bs.code += skip2
                        bs.code += isa.add(registers.r12, registers.r8)
                        
                        bs.code += isa.cmp(registers.r12, 0)
                        skip3 = bs.program.get_unique_label()
                        end3 = bs.program.get_unique_label()
                        bs.code += isa.jl(skip3)
                        bs.code += isa.jmp(end3)
                        bs.code += skip3
                        
                        bs.code += isa.cmp(registers.r13, 0)
                        skip4 = bs.program.get_unique_label()
                        end4 = bs.program.get_unique_label()
                        bs.code += isa.jl(skip4)
                        bs.code += isa.mov(registers.r12, 0)
                        bs.code += isa.jmp(end4)
                        bs.code += skip4
                        bs.code += isa.mov(registers.r12, -1)
                        bs.code += end4
                        
                        bs.code += end3
                        
                        bs.code += end2
                    
                    #if (step < 0 and stop >= start) or (step > 0 and start >= stop):
                    #        slicelength = 0
                    #elif step < 0:
                    #        slicelength = (stop - start + 1)/step + 1
                    #else:
                    #        slicelength = (stop - start - 1)/step + 1
                    
                    bs.code += isa.cmp(registers.r13, 0)
                    skip3 = bs.program.get_unique_label()
                    end3 = bs.program.get_unique_label()
                    bs.code += isa.jl(skip3)
                    # step > 0
                    bs.code += isa.cmp(registers.r12, registers.r11)
                    skip4 = bs.program.get_unique_label()
                    end4 = bs.program.get_unique_label()
                    bs.code += isa.jle(skip4)
                    # stop > start
                    bs.code += isa.mov(registers.rax, registers.r12)
                    bs.code += isa.sub(registers.rax, registers.r11)
                    bs.code += isa.dec(registers.rax)
                    
                    bs.code += isa.mov(registers.rbx, registers.r13)
                    bs.code += isa.mov(registers.rdx, 0)
                    bs.code += isa.cqo()
                    bs.code += isa.idiv(registers.rbx)
                    bs.code += isa.inc(registers.rax)
                    bs.code += isa.mov(registers.r10, registers.rax)
                    bs.code += isa.jmp(end4)
                    bs.code += skip4
                    bs.code += isa.mov(registers.r10, 0)
                    bs.code += end4
                    
                    bs.code += isa.jmp(end3)
                    bs.code += skip3
                    # step < 0
                    bs.code += isa.cmp(registers.r12, registers.r11)
                    skip4 = bs.program.get_unique_label()
                    end4 = bs.program.get_unique_label()
                    bs.code += isa.jge(skip4)
                    # stop < start
                    
                    bs.code += isa.mov(registers.rax, registers.r12)
                    bs.code += isa.sub(registers.rax, registers.r11)
                    bs.code += isa.inc(registers.rax)
                    bs.code += isa.mov(registers.rbx, registers.r13)
                    bs.code += isa.mov(registers.rdx, 0)
                    bs.code += isa.cqo()
                    bs.code += isa.idiv(registers.rbx)
                    bs.code += isa.inc(registers.rax)
                    bs.code += isa.mov(registers.r10, registers.rax)
                    bs.code += isa.jmp(end4)
                    bs.code += skip4
                    bs.code += isa.mov(registers.r10, 0)
                    
                    bs.code += end4
                    
                    bs.code += end3
                    
                    bs.code += isa.add(registers.r11, registers.r9)
                    bs.code += isa.add(registers.r12, registers.r9)
                    
                    skip = bs.program.get_unique_label()
                    end = bs.program.get_unique_label()
                    bs.code += isa.cmp(registers.r10, 7)
                    bs.code += isa.jle(skip)
                    # long
                    bs.code += isa.mov(registers.rdi, registers.r10)
                    bs.code += isa.add(registers.rdi, 8)
                    bs.code += isa.mov(registers.rax, util.malloc_addr)
                    bs.code += isa.push(registers.r10)
                    bs.code += isa.push(registers.r11)
                    bs.code += isa.call(registers.rax)
                    bs.code += isa.pop(registers.r11)
                    bs.code += isa.pop(registers.r10)
                    bs.code += isa.push(registers.rax)
                    bs.code += isa.mov(MemRef(registers.rax), registers.r10)
                    bs.code += isa.add(registers.rax, 8)
                    bs.code += isa.jmp(end)
                    
                    bs.code += skip
                    # short
                    bs.code += isa.mov(registers.rax, registers.r10)
                    bs.code += isa.shl(registers.rax, 1)
                    bs.code += isa.or_(registers.rax, 1)
                    bs.code += isa.push(registers.rax)
                    bs.code += isa.lea(registers.rax, MemRef(registers.rsp, 1, data_size=None))
                    
                    bs.code += end
                    
                    bs.code += isa.cmp(registers.r13, 0)
                    skip = bs.program.get_unique_label()
                    end = bs.program.get_unique_label()
                    bs.code += isa.jl(skip)
                    
                    last_end = bs.program.get_unique_label()
                    last_loop = bs.program.get_unique_label()
                    bs.code += last_loop
                    bs.code += isa.cmp(registers.r11, registers.r12)
                    bs.code += isa.jge(last_end)
                    bs.code += isa.mov(registers.cl, MemRef(registers.r11, data_size=8))
                    bs.code += isa.mov(MemRef(registers.rax, data_size=8), registers.cl)
                    bs.code += isa.add(registers.r11, registers.r13)
                    bs.code += isa.inc(registers.rax)
                    bs.code += isa.jmp(last_loop)
                    bs.code += last_end
                    bs.code += isa.jmp(end)
                    
                    bs.code += skip
                    last_end = bs.program.get_unique_label()
                    last_loop = bs.program.get_unique_label()
                    bs.code += last_loop
                    bs.code += isa.cmp(registers.r11, registers.r12)
                    bs.code += isa.jle(last_end)
                    bs.code += isa.mov(registers.cl, MemRef(registers.r11, data_size=8))
                    bs.code += isa.mov(MemRef(registers.rax, data_size=8), registers.cl)
                    bs.code += isa.add(registers.r11, registers.r13)
                    bs.code += isa.inc(registers.rax)
                    bs.code += isa.jmp(last_loop)
                    bs.code += last_end
                    
                    bs.code += end
                    
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
            
            skip = bs.program.get_unique_label()
            bs.code += isa.test(registers.rax, 1)
            bs.code += isa.jz(skip)
            bs.code += isa.mov(registers.rax, registers.rsp)
            bs.code += isa.sub(registers.rax, 7 + 8)
            bs.code += skip
            
            bs.code += isa.add(registers.rax, 8)
            
            bs.code += isa.mov(registers.r12, 0)
            bs.code += isa.mov(registers.r12b, MemRef(registers.rax, data_size=8))

            bs.code += isa.push(registers.r12)
            bs.flow.stack.append(Int)
        return _

@apply
class StrLenMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            
            skip = bs.program.get_unique_label()
            end = bs.program.get_unique_label()
            
            bs.code += isa.test(registers.rax, 1)
            bs.code += isa.jz(skip)
            bs.code += isa.shr(registers.rax, 1)
            bs.code += isa.and_(registers.rax, 127)
            bs.code += isa.jmp(end)
            
            bs.code += skip
            bs.code += isa.mov(registers.rax, MemRef(registers.rax))

            bs.code += end
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Int)
        return _

@apply
class StrNonZeroMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            
            skip = bs.program.get_unique_label()
            end = bs.program.get_unique_label()
            
            bs.code += isa.test(registers.rax, 1)
            bs.code += isa.jz(skip)
            bs.code += isa.shr(registers.rax, 1)
            bs.code += isa.and_(registers.rax, 127)
            bs.code += isa.jmp(end)
            
            bs.code += skip
            bs.code += isa.mov(registers.rax, MemRef(registers.rax))

            bs.code += end
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Bool)
        return _

@apply
class StrJoinMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert len(arg_types) == 1
        def _(bs):
            def _(bs):
                assert bs.flow.stack[-1] is arg_types[0]
            bs.this.append(
                ast.Call(
                    func=ast.Attribute(
                        value=_,
                        attr='__iter__',
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
                bs.this.append(util.dup)
                bs.this.append(
                    ast.Call(
                        func=ast.Attribute(
                            value=_,
                            attr='next',
                            ctx=ast.Load(),
                            ),
                        args=[],
                        keywords=[],
                        starargs=None,
                        kwargs=None,
                        ),
                    )
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
                
                skip = bs.program.get_unique_label()
                end = bs.program.get_unique_label()
                
                bs.code += isa.test(registers.rax, 1)
                bs.code += isa.jz(skip)
                bs.code += isa.shr(registers.rax, 1)
                bs.code += isa.and_(registers.rax, 127)
                bs.code += isa.jmp(end)
                
                bs.code += skip
                bs.code += isa.mov(registers.r12, MemRef(registers.rax))

                bs.code += end
                bs.code += isa.push(registers.r12)
                bs.flow.stack.append(Int)
                
                # x = top.__iter__()
                # while True:
                #     item = x.next()
                #     assert type is Str
                #     push item
                #     length += len(item)
                # alloc
                # copy
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
            
            bs.code += isa.cmp(registers.rsi, registers.rdi)
            bs.code += isa.mov(registers.rax, self.op_name in ('eq', 'le', 'ge'))
            bs.code += isa.je(end)
            
            skip = bs.program.get_unique_label()
            bs.code += isa.test(registers.rsi, 1)
            bs.code += isa.jz(skip)
            bs.code += isa.mov(registers.rax, registers.rsi)
            bs.code += isa.shr(registers.rax, 1)
            bs.code += isa.and_(registers.rax, 7)
            bs.code += isa.mov(MemRef(registers.rsp, -16), registers.rax)
            bs.code += isa.mov(registers.rax, registers.rsi)
            bs.code += isa.shr(registers.rax, 8)
            bs.code += isa.mov(MemRef(registers.rsp, -8), registers.rax)
            bs.code += isa.mov(registers.rsi, registers.rsp)
            bs.code += isa.sub(registers.rsi, 16)
            bs.code += skip
            
            skip = bs.program.get_unique_label()
            bs.code += isa.test(registers.rdi, 1)
            bs.code += isa.jz(skip)
            bs.code += isa.mov(registers.rax, registers.rdi)
            bs.code += isa.shr(registers.rax, 1)
            bs.code += isa.and_(registers.rax, 7)
            bs.code += isa.mov(MemRef(registers.rsp, -32), registers.rax)
            bs.code += isa.mov(registers.rax, registers.rdi)
            bs.code += isa.shr(registers.rax, 8)
            bs.code += isa.mov(MemRef(registers.rsp, -24), registers.rax)
            bs.code += isa.mov(registers.rdi, registers.rsp)
            bs.code += isa.sub(registers.rdi, 32)
            bs.code += skip
            
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
class StrAddMeth(_Type):
    size = 1
    def __call__(self, arg_types):
        assert arg_types == (Str,)
        def _(bs):
            assert bs.flow.stack.pop() is Str
            bs.code += isa.pop(registers.rsi)
            
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rdi)
            
            # r10 len 1
            # r11 pointer 1
            # r12 len 2
            # r13 pointer 2
            
            bs.code += isa.sub(registers.rsp, 16)
            
            skip = bs.program.get_unique_label()
            end = bs.program.get_unique_label()
            bs.code += isa.test(registers.rdi, 1)
            bs.code += isa.jnz(skip)
            # normal string
            bs.code += isa.mov(registers.r10, MemRef(registers.rdi))
            bs.code += isa.lea(registers.r11, MemRef(registers.rdi, 8, data_size=None))
            bs.code += isa.jmp(end)
            bs.code += skip
            # short string
            bs.code += isa.mov(registers.r10, registers.rdi)
            bs.code += isa.shr(registers.r10, 1)
            bs.code += isa.and_(registers.r10, 7)
            bs.code += isa.mov(MemRef(registers.rsp, 8), registers.rdi)
            bs.code += isa.lea(registers.r11, MemRef(registers.rsp, 9, data_size=None))
            bs.code += end
            
            skip = bs.program.get_unique_label()
            end = bs.program.get_unique_label()
            bs.code += isa.test(registers.rsi, 1)
            bs.code += isa.jnz(skip)
            # normal string
            bs.code += isa.mov(registers.r12, MemRef(registers.rsi))
            bs.code += isa.lea(registers.r13, MemRef(registers.rsi, 8, data_size=None))
            bs.code += isa.jmp(end)
            bs.code += skip
            # short string
            bs.code += isa.mov(registers.r12, registers.rsi)
            bs.code += isa.shr(registers.r12, 1)
            bs.code += isa.and_(registers.r12, 7)
            bs.code += isa.mov(MemRef(registers.rsp, 0), registers.rsi)
            bs.code += isa.lea(registers.r13, MemRef(registers.rsp, 1, data_size=None))
            bs.code += end
            
            end = bs.program.get_unique_label()
            skip = bs.program.get_unique_label()
            
            # r14 total length
            
            bs.code += isa.mov(registers.r14, registers.r10)
            bs.code += isa.add(registers.r14, registers.r12)
            bs.code += isa.cmp(registers.r14, 7)
            bs.code += isa.jle(skip)
            # long
            #bs.code += isa.ud2()
            bs.code += isa.lea(registers.rdi, MemRef(registers.r14, 8, data_size=None))
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.push(registers.r10)
            bs.code += isa.push(registers.r11)
            bs.code += isa.call(registers.rax)
            bs.code += isa.pop(registers.r11)
            bs.code += isa.pop(registers.r10)
            bs.code += isa.mov(MemRef(registers.rax), registers.r14)
            bs.code += isa.mov(registers.rcx, registers.r10)
            bs.code += isa.mov(registers.rsi, registers.r11)
            bs.code += isa.lea(registers.rdi, MemRef(registers.rax, 8, data_size=None))
            bs.code += isa.rep()
            bs.code += isa.movsb()
            bs.code += isa.mov(registers.rcx, registers.r12)
            bs.code += isa.mov(registers.rsi, registers.r13)
            bs.code += isa.lea(registers.rdi, MemRef(registers.rax, 8, registers.r10, data_size=None))
            bs.code += isa.rep()
            bs.code += isa.movsb()
            
            bs.code += isa.jmp(end)
            bs.code += skip
            # short
            #bs.code += isa.ud2()
            bs.code += isa.mov(registers.rax, registers.r14)
            bs.code += isa.mov(registers.rdx, 0)
            bs.code += isa.mov(registers.r14, 2**48 - 1)
            bs.code += isa.lea(registers.rcx, MemRef(registers.rdx, 8, index=registers.r10, scale=8, data_size=None))
            bs.code += isa.shl(registers.rax, 1)
            bs.code += isa.or_(registers.rax, 1)
            bs.code += isa.mov(registers.rbx, MemRef(registers.r11))
            bs.code += isa.and_(registers.rbx, registers.r14)
            bs.code += isa.shl(registers.rbx, 8)
            bs.code += isa.or_(registers.rax, registers.rbx)
            bs.code += isa.mov(registers.rbx, MemRef(registers.r13))
            bs.code += isa.and_(registers.rbx, registers.r14)
            bs.code += isa.shl(registers.rbx, registers.cl)
            bs.code += isa.or_(registers.rax, registers.rbx)
            
            bs.code += end
            bs.code += isa.add(registers.rsp, 16)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Str)
        return _

@apply
class Str(_Type):
    size = 1
    def load_constant(self, s):
        assert isinstance(s, str)
        def _(bs):
            if len(s) >= 8:
                bs.code += isa.mov(registers.rax, ctypes.cast(strings[s], ctypes.c_void_p).value)
            else:
                bs.code += isa.mov(registers.rax, struct.unpack("l", struct.pack("B7s", 2 * len(s) + 1, s))[0])
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Str)
        return _
    def to_python(self, data):
        i, = struct.unpack("l", data)
        
        if i & 1:
            first, data = struct.unpack("B7s", struct.pack("l", i))
            assert first & 1
            length = first >> 1
            return data[:length]
        else:
            length, = struct.unpack("l", ctypes.string_at(i, 8))
            return ctypes.string_at(i+8, length)
    
    def getattr___str__(self, bs): bs.flow.stack.append(StrStrMeth)
    def getattr___getitem__(self, bs): bs.flow.stack.append(StrGetitemMeth)
    def getattr___ord__(self, bs): bs.flow.stack.append(StrOrdMeth)
    def getattr___len__(self, bs): bs.flow.stack.append(StrLenMeth)
    def getattr_join(self, bs): bs.flow.stack.append(StrJoinMeth)
    def getattr___gt__(self, bs): bs.flow.stack.append(StrCmpMeths['gt'])
    def getattr___lt__(self, bs): bs.flow.stack.append(StrCmpMeths['lt'])
    def getattr___ge__(self, bs): bs.flow.stack.append(StrCmpMeths['ge'])
    def getattr___le__(self, bs): bs.flow.stack.append(StrCmpMeths['le'])
    def getattr___eq__(self, bs): bs.flow.stack.append(StrCmpMeths['eq'])
    def getattr___ne__(self, bs): bs.flow.stack.append(StrCmpMeths['ne'])
    def getattr___add__(self, bs): bs.flow.stack.append(StrAddMeth)
    def getattr___nonzero__(self, bs): bs.flow.stack.append(StrNonZeroMeth)

functions = []


def _get_func_say(x):
    functions.append("i can't find " + str(x))
    return len(functions) - 1

say_functions = util.cdict(_get_func_say)

@apply
class FunctionStr(_Type):
    size = 2
    def __call__(self, arg_types):
        assert not arg_types
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            def _(value):
                def _(bs):
                    if isinstance(functions[value], str):
                        assert False, functions[value]
                    bs.this.append(Str.load_constant("<function %s at %i>" % (functions[value].name, value)))
                return _
            util.unlift(bs, _, "_Function.__call__")
        return _

@apply
class Function(_Type):
    size = 2
    def getattr___str__(self, bs): bs.flow.stack.append(FunctionStr)
    def getattr___repr__(self, bs): bs.flow.stack.append(FunctionStr)
    def __call__(self, arg_types):
        def _(bs):
            assert bs.flow.stack[-1 - len(arg_types)] is self, bs.flow.stack[-1 - len(arg_types)]
            arg_size = sum(x.size for x in arg_types)
            bs.code += isa.mov(registers.rax, MemRef(registers.rsp, 8*arg_size + 8))
            bs.code += isa.push(registers.rax)
            
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
                            def _(bs, value=value):
                                exc = value < 0
                                if exc:
                                    value = ~value
                                bs.flow.stack.append(id_to_type[value])
                                if bs.flow.stack[-1].size >= 1:
                                    bs.code += isa.push(registers.r13)
                                if bs.flow.stack[-1].size >= 2:
                                    bs.code += isa.push(registers.r14)
                                if bs.flow.stack[-1].size >= 3:
                                    assert False
                                if exc:
                                    bs.flow.try_stack.pop()(bs)
                            return _
                        util.unlift(bs, _, "_Function.__call__ (inner)")
                return _
            util.unlift(bs, _, "_Function.__call__")
        return _

@apply
class GeneratorNext(_Type):
    size = 1

@apply
class Generator(_Type):
    size = 1
    def getattr_next(self, bs):
        bs.flow.stack.append(GeneratorNext)

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
            bs.flow.stack.append(self)
        return _
    def to_python(self, data):
        assert not data
    def getattr___str__(self, bs): bs.flow.stack.append(NoneStrMeth)

class ProtoSlice(_Type):
    def __init__(self, (start_type, stop_type, step_type)):
        self.start_type, self.stop_type, self.step_type = start_type, stop_type, step_type
        self.size = sum(x.size for x in [self.start_type, self.stop_type, self.step_type])
        _Type.__init__(self)
    def load(self):
        def _(bs):
            for arg_type in [self.start_type, self.stop_type, self.step_type][::-1]:
                assert bs.flow.stack.pop() is arg_type
            bs.flow.stack.append(self)
        return _
    def store(self):
        def _(bs):
            assert bs.flow.stack.pop() is self
            for arg_type in [self.start_type, self.stop_type, self.step_type]:
                bs.flow.stack.append(arg_type)
        return _
    def getattr_start(self, bs):
        bs.flow.stack.extend(self.types)
        for i in xrange(bs.flow.stack.pop().size):
            bs.code += isa.pop(registers.rax)
        for i in xrange(bs.flow.stack.pop().size):
            bs.code += isa.pop(registers.rax)
    def getattr_stop(self, bs):
        bs.flow.stack.extend(self.types)
        for i in xrange(bs.flow.stack.pop().size):
            bs.code += isa.pop(registers.rax)
        util.rem1(bs)
    def getattr_step(self, bs):
        bs.flow.stack.extend(self.types)
        util.rem2(bs)

protoslices = util.cdict(ProtoSlice)

@apply
class NotImplementedType(_Type):
    size = 0
    def load(self):
        def _(bs):
            bs.flow.stack.append(self)
        return _
    def to_python(self, data):
        assert not data
