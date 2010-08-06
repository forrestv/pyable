from __future__ import division

import struct

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
from corepy.arch.x86_64.lib.memory import MemRef

class Type(object):
    def copy(self):
        return self.__class__()

class Int(Type):
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
                assert self is not other
                assert self.register is not other.register
                bs.code += isa.add(self.register, other.register)
                bs.code += isa.push(self.register)
                bs.stack.append(Int())
            return _
        return NotImplemented
    __radd__ = __add__
    
    def __sub__(self, other):
        if isinstance(other, Int):
            def _(bs, this):
                bs.code += isa.sub(self.register, other.register)
                bs.code += isa.push(self.register)
                bs.stack.append(Int())
            return _
        return NotImplemented
    
    def __mul__(self, other):
        if isinstance(other, Int):
            def _(bs, this):
                bs.code += isa.imul(self.register, other.register)
                bs.code += isa.push(self.register)
                bs.stack.append(Int())
            return _
        return NotImplemented
    __rmul__ = __mul__
    
    def __div__(self, other):
        if isinstance(other, Int):
            def _(bs, this):
                bs.code += isa.mov(registers.rdx, 0)
                bs.code += isa.mov(registers.rax, self.register)
                bs.code += isa.idiv(other.register)
                bs.code += isa.push(registers.rax)
                bs.stack.append(Int())
            return _
        return NotImplemented
    
    def __floordiv__(self, other):
        if isinstance(other, Int):
            def _(bs, this):
                bs.code += isa.mov(registers.rdx, 0)
                bs.code += isa.mov(registers.rax, self.register)
                bs.code += isa.idiv(other.register)
                bs.code += isa.push(registers.rax)
                bs.stack.append(Int())
            return _
        return NotImplemented
    
    def __mod__(self, other):
        if isinstance(other, Int):
            def _(bs, this):
                bs.code += isa.mov(registers.rdx, 0)
                bs.code += isa.mov(registers.rax, self.register)
                bs.code += isa.idiv(other.register)
                bs.code += isa.push(registers.rdx)
                bs.stack.append(Int())
            return _
        return NotImplemented

class Float(Type):
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
                bs.code += isa.push(self.register)
                bs.code += isa.push(other.register)
                bs.code.add(isa.movsd(registers.xmm0, MemRef(registers.rsp, 0)))
                bs.code.add(isa.movsd(registers.xmm1, MemRef(registers.rsp, 8)))
                bs.code.add(isa.addsd(registers.xmm0, registers.xmm1))
                bs.code.add(isa.movsd(MemRef(registers.rsp, 8), registers.xmm0))
                bs.code.add(isa.pop(registers.rax))
                bs.stack.append(Float())
            return _
        return NotImplemented
    __radd__ = __add__

class Tuple(object):
    def load_constant(self, ast):
        assert isinstance(ast)

class Object(object):
    pass
