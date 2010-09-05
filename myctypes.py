from __future__ import division

import ctypes
import random
import ast

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
from corepy.arch.x86_64.lib.memory import MemRef

import type_impl
import util

int_regs = [registers.rdi, registers.rsi, registers.rdx, registers.rcx, registers.r8, registers.r9]
float_regs = [registers.xmm0, registers.xmm1, registers.xmm2, registers.xmm3, registers.xmm4, registers.xmm5, registers.xmm6, registers.xmm7]


class _FuncPtr(type_impl._Type):
    size = 0
    def __init__(self, (cdll, name)):
        type_impl._Type.__init__(self)
        self.func = cdll[name]
    def __call__(self, arg_types):
        def _(bs):
            ints = len([x for x in arg_types if x is type_impl.Int or x is type_impl.Str or x is Raw])
            floats = len([x for x in arg_types if x is type_impl.Float])
            pos = 0
            for arg_type in arg_types:
                type = bs.flow.stack.pop()
                if type is type_impl.Int:
                    ints -= 1
                    bs.code += isa.mov(int_regs[ints], MemRef(registers.rsp, pos))
                    pos += 8
                elif type is Raw:
                    ints -= 1
                    bs.code += isa.mov(int_regs[ints], MemRef(registers.rsp, pos))
                    pos += 8
                    bs.code += isa.add(int_regs[ints], 8)
                elif type is type_impl.Float:
                    floats -= 1
                    bs.code += isa.movsd(float_regs[floats], MemRef(registers.rsp, pos))
                    pos += 8
                elif type is type_impl.Str:
                    ints -= 1
                    bs.code += isa.mov(int_regs[ints], MemRef(registers.rsp, pos))
                    pos += 8
                    bs.code += isa.test(int_regs[ints], 1)
                    short = bs.program.get_unique_label()
                    end = bs.program.get_unique_label()
                    bs.code += isa.jnz(short)
                    # long
                    bs.code += isa.add(int_regs[ints], 8)
                    bs.code += isa.jmp(end)
                    bs.code += short
                    # short
                    bs.code += isa.shr(MemRef(registers.rsp), 8)
                    bs.code += isa.lea(int_regs[ints], MemRef(registers.rsp, pos - 8, data_size=None))
                    bs.code += end
                else:
                    assert False, type
            assert bs.flow.stack.pop() is self
            bs.code += isa.mov(registers.rax, ctypes.cast(self.func, ctypes.c_void_p).value)
            bs.code += isa.mov(registers.r12, registers.rsp)
            bs.code += isa.and_(registers.rsp, -16)
            bs.code += isa.call(registers.rax)
            bs.code += isa.mov(registers.rsp, registers.r12)
            bs.code += isa.add(registers.rsp, pos)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(type_impl.Int)
        return _
FuncPtrs = util.cdict(_FuncPtr)

class _CDLLInst(type_impl._Type):
    size = 0
    def __init__(self, name):
        type_impl._Type.__init__(self)
        self.cdll = ctypes.CDLL(name)
    def const_getattr(self, s):
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.flow.stack.append(FuncPtrs[self.cdll, s])
        return _
CDLLInsts = util.cdict(_CDLLInst)

@apply
class CDLL(type_impl._Type):
    size = 0
    def call_const(self, a):
        assert isinstance(a, ast.Str)
        def _(bs):
            assert bs.flow.stack.pop() is self
            bs.flow.stack.append(CDLLInsts[a.s])
        return _

@apply
class RawCopyFromMeth(type_impl._Type):
    size = 1
    def __call__(self, arg_types):
        assert len(arg_types) == 2
        assert arg_types[0] is Raw
        assert arg_types[1] is type_impl.Int
        def _(bs):
            assert bs.flow.stack.pop() is type_impl.Int
            bs.code += isa.pop(registers.r14)
            assert bs.flow.stack.pop() is Raw
            bs.code += isa.pop(registers.r13)
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.r12)
            
            bs.code += isa.shl(registers.r14, 3)
            
            bs.code += isa.mov(registers.rdi, registers.r12)
            bs.code += isa.mov(registers.rsi, registers.r13)
            bs.code += isa.mov(registers.rdx, registers.r14)
            bs.code += isa.mov(registers.rax, ctypes.cast(ctypes.memmove, ctypes.c_void_p).value)	
            bs.code += isa.call(registers.rax)
            
            bs.this.append(type_impl.NoneType.load())
        return _

@apply
class RawGetitemMeth(type_impl._Type):
    size = 1
    def __call__(self, arg_types):
        assert len(arg_types) == 1
        assert arg_types[0] is type_impl.Int
        def _(bs):
            assert bs.flow.stack.pop() is type_impl.Int
            bs.code += isa.pop(registers.rcx)
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rbx)
            
            bs.code += isa.add(registers.rbx, registers.rcx)
            
            bs.code += isa.mov(regsisters.rax, 0)
            bs.code += isa.mov(registers.ax, MemRef(registers.rbx, data_size=8))
            bs.code += isa.shl(registers.rax, 8)
            bs.code += isa.mov(registers.ax, 2 * 1 + 1)
            
            bs.flow.stack.append(type_impl.Str)
        return _
@apply
class RawSetitemMeth(type_impl._Type):
    size = 1
    def __call__(self, arg_types):
        assert len(arg_types) == 2, arg_types
        assert arg_types[0] is type_impl.Int
        assert arg_types[1] is type_impl.Int
        def _(bs):
            assert bs.flow.stack.pop() is type_impl.Int
            bs.code += isa.pop(registers.rcx)
            assert bs.flow.stack.pop() is type_impl.Int
            bs.code += isa.pop(registers.rbx)
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            
            bs.code += isa.shl(registers.rbx, 3)
            bs.code += isa.add(registers.rax, registers.rbx)
            bs.code += isa.add(registers.rax, registers.rbx)
            
            bs.code += isa.mov(MemRef(registers.rax), registers.rcx)
            
            type_impl.NoneType.load()(bs)
        return _
@apply
class Raw(type_impl._Type):
    size = 1
    #def getattr___getitem__(self, bs): bs.flow.stack.append(RawGetitemMeth)
    #def getattr___setitem__(self, bs): bs.flow.stack.append(RawSetitemMeth)
    #def getattr_load_object(self, bs): bs.flow.stack.append(RawLoadObjectMeth)
    #def getattr_store_object(self, bs): bs.flow.stack.append(RawStoreObjectMeth)
    #def getattr_copy_from(self, bs): bs.flow.stack.append(RawCopyFromMeth)
    def getattr_raw(self, bs):
        bs.code += isa.pop(registers.r12)
        bs.code += isa.mov(registers.rdi, MemRef(registers.r12))
        bs.code += isa.add(registers.rdi, 8)
        bs.code += isa.mov(registers.rax, util.malloc_addr)
        bs.code += isa.call(registers.rax)
        bs.code += isa.push(registers.rax)
        bs.code += isa.mov(registers.rdi, registers.rax)
        bs.code += isa.mov(registers.rsi, registers.r12)
        bs.code += isa.mov(registers.rcx, MemRef(registers.r12))
        bs.code += isa.add(registers.rcx, 8)
        bs.code += isa.rep()
        bs.code += isa.movsb()
        bs.flow.stack.append(type_impl.Str)

@apply
class RawType(type_impl._Type):
    size = 0
    def __call__(self, arg_types):
        assert len(arg_types) == 1
        assert arg_types[0] is type_impl.Int
        def _(bs):
            assert bs.flow.stack.pop() is type_impl.Int
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.r12)
            bs.code += isa.mov(registers.rdi, registers.r12)
            bs.code += isa.add(registers.rdi, 8)
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.call(registers.rax)
            bs.code += isa.push(registers.rax)
            bs.code += isa.mov(MemRef(registers.rax), registers.r12)
            bs.flow.stack.append(Raw)
        return _

@apply
class CtypesModule(type_impl._Type):
    size = 0
    def getattr_CDLL(self, bs): bs.flow.stack.append(CDLL)
    def getattr_create_string_buffer(self, bs): bs.flow.stack.append(RawType)
