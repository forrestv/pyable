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
            ints = len([x for x in arg_types if x is type_impl.Int or x is type_impl.Str])
            floats = len([x for x in arg_types if x is type_impl.Float])
            for arg_type in arg_types:
                type = bs.flow.stack.pop()
                if type is type_impl.Int:
                    ints -= 1
                    bs.code += isa.pop(int_regs[ints])
                elif type is type_impl.Float:
                    floats -= 1
                    bs.code += isa.movsd(float_regs[floats], MemRef(registers.rsp))
                    bs.code += isa.pop(registers.rax)
                elif type is type_impl.Str:
                    ints -= 1
                    bs.code += isa.pop(int_regs[ints])
                    bs.code += isa.add(int_regs[ints], 8)
                else:
                    assert False, type
            assert bs.flow.stack.pop() is self
            bs.code += isa.mov(registers.rax, ctypes.cast(self.func, ctypes.c_void_p).value)
            bs.code += isa.mov(registers.r12, registers.rsp)
            bs.code += isa.and_(registers.rsp, -16)
            bs.code += isa.call(registers.rax)
            bs.code += isa.mov(registers.rsp, registers.r12)
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
class CtypesModule(type_impl._Type):
    size = 0
    def getattr_CDLL(self, bs): bs.flow.stack.append(CDLL)
