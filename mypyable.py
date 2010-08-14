import ctypes
import random
import ast

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
from corepy.arch.x86_64.lib.memory import MemRef

import type_impl
import util

class _PyableModule(type_impl._Type):
    size = 0
    def getattr_const_string(self, s):
        if s == "object":
            def _(bs, this):
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(Object)
            return _
CtypesModule = type_impl.number(_CtypesModule())
