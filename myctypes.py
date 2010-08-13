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

def wrap_func(func_):
    class _FuncPtr(type_impl._Type):
        size = 0
        func = func_
        def __call__(self, arg_types):
            def _(bs, this):
                ints = len([x for x in arg_types if x is type_impl.Int])
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
    return type_impl.number(_FuncPtr())

def load_cdll(name):
    class _CDLLInst(type_impl._Type):
        size = 0
        cdll = ctypes.CDLL(name)
        def getattr_const_string(self, s):
            def _(bs, this):
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(wrap_func(self.cdll[s]))
            return _
    return type_impl.number(_CDLLInst())

class _CDLL(type_impl._Type):
    size = 0
    def call_const(self, a):
        assert isinstance(a, ast.Str)
        def _(bs, this):
            assert bs.flow.stack.pop() is self
            bs.flow.stack.append(load_cdll(a.s))
        return _
        
CDLL = type_impl.number(_CDLL())

class _CtypesModule(type_impl._Type):
    size = 0
    def getattr_const_string(self, s):
        if s == "CDLL":
            def _(bs, this):
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(CDLL)
            return _
CtypesModule = type_impl.number(_CtypesModule())
