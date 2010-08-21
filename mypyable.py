from __future__ import division

import ctypes
import random
import ast

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
from corepy.arch.x86_64.lib.memory import MemRef

import compiler
import type_impl
import util

cfuncs = []

class _PythonFunction(type_impl._Type):
    size = 0
    return_area = ctypes.create_string_buffer(1024)
    def low_handler(self, args):
        #print args
        res = self.handler(*[arg.to_python(data) for arg, data in args])
        # TODO return_area
        assert res.size == 0
        return res.id
    def __call__(self, arg_types):
        @util.called_from_asm
        def handler(rsp):
            args = []
            #print ctypes.string_at(rsp, 
            for arg in arg_types[::-1]:
                size = arg.size * 8
                #print arg
                args.append((arg, ctypes.string_at(rsp, size)))
                rsp += size
            # right now we can only return empty types
            res = self.low_handler(args[::-1])
            return res
        handler_cfunc = ctypes.CFUNCTYPE(ctypes.c_int64, ctypes.c_int64)(handler)
        cfuncs.append(handler_cfunc)
        def _(bs):
            "handler(rsp)"
            bs.code += isa.mov(registers.rdi, registers.rsp)
            bs.code += isa.mov(registers.r12, registers.rsp)
            bs.code += isa.and_(registers.rsp, -16)
            bs.code += isa.mov(registers.rax, ctypes.cast(handler_cfunc, ctypes.c_void_p).value)
            bs.code += isa.call(registers.rax)
            bs.code += isa.mov(registers.rsp, registers.r12)
            for arg in arg_types[::-1]:
                assert bs.flow.stack.pop() is arg
                for i in xrange(arg.size):
                    bs.code += isa.pop(registers.rbx)
            assert bs.flow.stack.pop() is self
            bs.code += isa.push(registers.rax)
            def _(value):
                def _(bs):
                    type = type_impl.id_to_type[value]
                    for i in xrange(type.size):
                        bs.code += isa.push(MemRef(ctypes.cast(self.return_area, ctypes.c_void_p).value + i))
                    bs.flow.stack.append(type)
                    assert bs.flow.stack[-1].size == 0
                return _
            util.unlift(bs, _, "PythonFunction.__call__")
        return _

class _Type(_PythonFunction):
    def handler(self, name, bases, dict=None):
        if dict is None:
            dict = {}
        return type_impl.ProtoObject(name, bases, dict)
Type = type_impl.number(_Type())

class _Type_Number(type_impl._Type):
    size = 0
    def __call__(self, arg_types):
        assert len(arg_types) == 1
        def _(bs):
            for i in xrange(bs.flow.stack[-1].size):
                bs.code += isa.pop(registers.rax)
            assert bs.flow.stack.pop() is arg_types[0]
            for i in xrange(bs.flow.stack[-1].size):
                bs.code += isa.pop(registers.rax)
            assert bs.flow.stack.pop() is self
            bs.code += isa.push(arg_types[0].id)
            bs.flow.stack.append(type_impl.Int)
        return _
Type_Number = type_impl.number(_Type_Number())

class _RawStoreObjectMeth(type_impl._Type):
    size = 1
    def __call__(self, arg_types):
        assert len(arg_types) == 2, arg_types
        assert arg_types[0] is type_impl.Int
        def _(bs):
            type = bs.flow.stack.pop()
            for i, reg in zip(xrange(type.size), [registers.r11, registers.r12, registers.r13, registers.r14]):
                bs.code += isa.pop(reg)
            assert bs.flow.stack.pop() is type_impl.Int
            bs.code += isa.pop(registers.rbx)
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            
            bs.code += isa.shl(registers.rbx, 3)
            bs.code += isa.add(registers.rax, registers.rbx)
            
            bs.code += isa.mov(MemRef(registers.rax), type.id)
            
            for i, reg in zip(xrange(type.size), [registers.r11, registers.r12, registers.r13, registers.r14]):
                bs.code += isa.mov(MemRef(registers.rax, i * 8 + 8), reg)
            
            bs.code += isa.push(1 + type.size)
            bs.flow.stack.append(type_impl.Int)
        return _
RawStoreObjectMeth = type_impl.number(_RawStoreObjectMeth())


class _RawLoadObjectMeth(type_impl._Type):
    size = 1
    def __call__(self, arg_types):
        assert len(arg_types) == 1
        assert arg_types[0] is type_impl.Int
        def _(bs):
            assert bs.flow.stack.pop() is type_impl.Int
            bs.code += isa.pop(registers.r13)
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.r12)
            
            bs.code += isa.shl(registers.r13, 3)
            bs.code += isa.add(registers.r12, registers.r13)
            
            bs.code += isa.push(MemRef(registers.r12))
            
            def _(value):
                def _(bs):
                    type = type_impl.id_to_type[value]
                    for i in reversed(xrange(type.size)):
                        bs.code += isa.push(MemRef(registers.r12, i * 8 + 8))
                    bs.flow.stack.append(type)
                return _
            util.unlift(bs, _, "RawLoadObjectMeth.__call__")
        return _
RawLoadObjectMeth = type_impl.number(_RawLoadObjectMeth())

class _RawCopyFromMeth(type_impl._Type):
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
RawCopyFromMeth = type_impl.number(_RawCopyFromMeth())

class _Raw(type_impl._Type):
    size = 1
    def getitem(self):
        def _(bs):
            assert bs.flow.stack.pop() is type_impl.Int
            bs.code += isa.pop(registers.rbx)
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            
            bs.code += isa.shl(registers.rbx, 3)
            bs.code += isa.add(registers.rax, registers.rbx)
            
            bs.code += isa.push(MemRef(registers.rax))
            bs.flow.stack.append(type_impl.Int)
        return _
    def setitem(self):
        def _(bs):
            assert bs.flow.stack.pop() is type_impl.Int
            bs.code += isa.pop(registers.rbx)
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            assert bs.flow.stack.pop() is type_impl.Int
            bs.code += isa.pop(registers.rcx)
            
            bs.code += isa.shl(registers.rbx, 3)
            bs.code += isa.add(registers.rax, registers.rbx)
            
            bs.code += isa.mov(MemRef(registers.rax), registers.rcx)
        return _
    def const_getattr(self, attr):
        if attr == "store_object":
            def _(bs):
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(RawStoreObjectMeth)
            return _
        elif attr == "load_object":
            def _(bs):
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(RawLoadObjectMeth)
            return _
        elif attr == "copy_from":
            def _(bs):
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(RawCopyFromMeth)
            return _
        else:
            assert False, attr
        
Raw = type_impl.number(_Raw())

class _RawType(type_impl._Type):
    size = 0
    def __call__(self, arg_types):
        assert len(arg_types) == 1
        assert arg_types[0] is type_impl.Int
        def _(bs):
            assert bs.flow.stack.pop() is type_impl.Int
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rdi)
            bs.code += isa.shl(registers.rdi, 3)
            bs.code += isa.mov(registers.rax, util.malloc_addr)
            bs.code += isa.call(registers.rax)
            bs.code += isa.push(registers.rax)
            bs.flow.stack.append(Raw)
        return _
RawType = type_impl.number(_RawType())

list_impl = None

class _SetListImpl(_PythonFunction):
    def handler(self, new):
        global list_impl
        assert list_impl is None, "list_impl can only be set once"
        list_impl = new
        return type_impl.NoneType
SetListImpl = type_impl.number(_SetListImpl())

class _PyableModule(type_impl._Type):
    size = 0
    def const_getattr(self, s):
        if s == "type":
            def _(bs):
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(Type)
            return _
        elif s == "type_number":
            def _(bs):
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(Type_Number)
            return _
        elif s == "raw":
            def _(bs):
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(RawType)
            return _
        elif s == "set_list_impl":
            def _(bs):
                assert bs.flow.stack.pop() is self
                bs.flow.stack.append(SetListImpl)
            return _
        else:
            assert False, s
PyableModule = type_impl.number(_PyableModule())
