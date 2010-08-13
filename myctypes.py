import ctypes
import random
import ast

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
from corepy.arch.x86_64.lib.memory import MemRef

import type_impl
import util

def wrap_func(func_):
    class _FuncPtr(type_impl._Type):
        func = func_
        def __call__(self, arg_types):
            def _(bs, this):
                regs = [registers.rdi, registers.rsi, registers.rdx, registers.rcx, registers.r8, registers.r9]
                regs = regs[:len(arg_types)]
                for arg, reg in reversed(zip(arg_types, regs)):
                    assert arg is type_impl.Int is bs.flow.stack.pop()
                    bs.code += isa.pop(reg)
                assert bs.flow.stack.pop() is self
                bs.code += isa.mov(registers.rax, ctypes.cast(self.func, ctypes.c_void_p).value)
                bs.code += isa.call(registers.rax)
                bs.code += isa.push(registers.rax)
                bs.flow.stack.append(type_impl.Int)
            return _
    return type_impl.number(_FuncPtr())

def load_cdll(name):
    class _CDLLInst(type_impl._Type):
        cdll = ctypes.CDLL(name)
        def getattr_const_string(self, s):
            def _(bs, this):
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(wrap_func(self.cdll[s]))
            return _
    return type_impl.number(_CDLLInst())

class _CDLL(type_impl._Type):
    def call_const(self, a):
        assert isinstance(a, ast.Str)
        def _(bs, this):
            assert bs.flow.stack.pop() is self
            bs.flow.stack.append(load_cdll(a.s))
        return _
        
CDLL = type_impl.number(_CDLL())

class _CtypesModule(type_impl._Type):
    def getattr_const_string(self, s):
        if s == "CDLL":
            def _(bs, this):
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(CDLL)
            return _
CtypesModule = type_impl.number(_CtypesModule())
