from __future__ import division

import struct
import ctypes

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
from corepy.arch.x86_64.lib.memory import MemRef

import util

id_to_class = {}

def number(inst):
    inst.id = len(id_to_class)
    assert inst.id not in id_to_class
    id_to_class[inst.id] = inst
    return inst

class _Type(object):
    def copy(self):
        return self.__class__()
Type = number(_Type())

class _Int(_Type):
    def load_constant(self, value):
        assert isinstance(value, int)
        value = int(value)
        def _(bs, this):
            bs.code += isa.mov(registers.rax, value)
        return _
    def __neg__(self):
        def _(bs, this):
            bs.code += isa.neg(registers.rax)
        return _
    
    def __add__(self, other):
        if isinstance(other, type(Int)):
            def _(bs, this):
                assert self is not other
                assert self.register is not other.register
                bs.code += isa.add(self.register, other.register)
                bs.code += isa.push(self.register)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
    __radd__ = __add__
    
    def __sub__(self, other):
        if isinstance(other, type(Int)):
            def _(bs, this):
                bs.code += isa.sub(self.register, other.register)
                bs.code += isa.push(self.register)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
    
    def __mul__(self, other):
        if isinstance(other, type(Int)):
            def _(bs, this):
                bs.code += isa.imul(self.register, other.register)
                bs.code += isa.push(self.register)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
    __rmul__ = __mul__
    
    def __div__(self, other):
        if isinstance(other, type(Int)):
            def _(bs, this):
                bs.code += isa.mov(registers.rdx, 0)
                bs.code += isa.mov(registers.rax, self.register)
                bs.code += isa.idiv(other.register)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
    
    def __floordiv__(self, other):
        if isinstance(other, type(Int)):
            def _(bs, this):
                bs.code += isa.mov(registers.rdx, 0)
                bs.code += isa.mov(registers.rax, self.register)
                bs.code += isa.idiv(other.register)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
    
    def __mod__(self, other):
        if isinstance(other, type(Int)):
            def _(bs, this):
                bs.code += isa.mov(registers.rdx, 0)
                bs.code += isa.mov(registers.rax, self.register)
                bs.code += isa.idiv(other.register)
                bs.code += isa.push(registers.rdx)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
Int = number(_Int())

class _Float(_Type):
    def load_constant(self, value):
        assert isinstance(value, float)
        value = float(value)
        def _(bs, this):
            bs.code += isa.mov(registers.rax, struct.unpack("l", struct.pack("d", value))[0])
        return _
    def __neg__(self):
        def _(bs, this):
            bs.code += isa.neg(registers.rax)
        return _
    def __add__(self, other):
        if isinstance(other, type(Float)):
            def _(bs, this):
                bs.code += isa.push(self.register)
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp))
                bs.code += isa.mov(MemRef(registers.rsp), other.register)
                bs.code += isa.movsd(registers.xmm1, MemRef(registers.rsp))
                bs.code += isa.addsd(registers.xmm0, registers.xmm1)
                bs.code += isa.movsd(MemRef(registers.rsp), registers.xmm0)
                bs.flow.stack.append(Float)
            return _
        elif isinstance(other, type(Int)):
            def _(bs, this):
                bs.code += isa.cvtsi2sd(registers.xmm1, other.register)
                bs.code += isa.push(self.register)
                bs.code += isa.movsd(registers.xmm0, MemRef(registers.rsp))
                bs.code += isa.addsd(registers.xmm0, registers.xmm1)
                bs.code += isa.movsd(MemRef(registers.rsp), registers.xmm0)
                bs.flow.stack.append(Float)
            return _
        return NotImplemented
    __radd__ = __add__
Float = number(_Float())

class _Tuple(_Type):
    def load_constant(self, ast):
        assert isinstance(ast)
Tuple = number(_Tuple())

class _Object(_Type):
    pass
Object = number(_Object())

strings = util.cdict(lambda s: ctypes.create_string_buffer(struct.pack("L", len(s)) + s))

class _Str(_Type):
    def load_constant(self, s):
        assert isinstance(s, str)
        def _(bs, this):
            bs.code += isa.push(ctypes.cast(strings[s], ctypes.c_void_p).value)
            bs.flow.stack.append(Str)
        return _
Str = number(_Str())

class _Function(_Type):
    pass
Function = number(_Function())
