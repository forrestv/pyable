from __future__ import division

import struct
import ctypes

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
from corepy.arch.x86_64.lib.memory import MemRef

import util

id_to_type = {}

def number(inst):
    inst.id = len(id_to_type)
    assert inst.id not in id_to_type
    id_to_type[inst.id] = inst
    return inst

class _Type(object):
    def copy(self):
        return self.__class__()
    def __repr__(self):
        return self.__class__.__name__
    def getattr(self):
        return None
    def getattr_const_string(self):
        return None
Type = number(_Type())

class _Int(_Type):
    def getattr_const_string(self, s):
        def _(bs, this):
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
            else:
                assert False
        return _
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
            def _(bs, this):
                bs.code += isa.pop(registers.rbx)
                bs.code += isa.pop(registers.rax)
                bs.code += isa.sub(registers.rax, registers.rbx)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(Int)
            return _
        return NotImplemented
    
    def __mul__(self, other):
        if isinstance(other, type(Int)):
            def _(bs, this):
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
            bs.code += isa.mov(registers.rax, ctypes.cast(strings[s], ctypes.c_void_p).value)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Str)
        return _
Str = number(_Str())

class _Function(_Type):
    pass
Function = number(_Function())

class _NoneType(_Type):
    def load(self):
        def _(bs, this):
            bs.flow.stack.append(NoneType)
        return _
NoneType = number(_NoneType())

class _List(_Type):
    def append(self):
        # [self, element]
        def _(bs, this):
            # r12 = element pointer
            # r13 = list pointer
            # r14 = new len
            
            bs.code += isa.pop(registers.r12)
            r12_type = bs.flow.stack.pop()
            bs.code += isa.pop(registers.r13)
            r13_type = bs.flow.stack.pop()
            
            assert r13_type is List
            
            bs.code += isa.mov(registers.r14, MemRef(registers.r13))
            bs.code += isa.add(registers.r14, 1)
            
            bs.code += isa.cmp(registers.r11, MemRef(registers.rax, 8))
            skip_realloc = bs.program.get_unique_label()
            bs.code += isa.jle(skip_realloc)
            
            # allocated = allocated * 2 + 1
            bs.code += isa.mov(registers.rax, util.realloc_addr)
            bs.code += isa.mov(registers.rdi, MemRef(registers.r13, 16))
            bs.code += isa.mov(registers.rsi, MemRef(registers.r13, 8))
            bs.code += isa.mul(registers.rsi, 2)
            bs.code += isa.add(registers.rsi, 1)
            bs.code += isa.mov(MemRef(registers.r13, 8), registers.rdi)
            bs.code += isa.mul(registers.rsi, 16)
            bs.code += isa.call(registers.rax)
            bs.code += isa.mov(MemRef(registers.r13, 16), registers.rax)
            
            bs.code += skip_realloc
            
            #bs.code += isa.inc(MemRef(
            
    def load(self):
        def _(bs, this):
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.mov(registers.rdi, 24)
            bs.code += isa.call(registers.rax)
            bs.code += isa.mov(MemRef(registers.rax), 0) # length
            bs.code += isa.mov(MemRef(registers.rax, 8), 0) # allocated length
            bs.code += isa.mov(MemRef(registers.rax, 16), 0) # pointer
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(List)
        return _
List = number(_List())
