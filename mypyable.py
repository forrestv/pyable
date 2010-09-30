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
    def load(self):
        def _(bs):
            bs.flow.stack.append(self)
        return _

@apply
class Type(_PythonFunction):
    def handler(self, name, bases, dict):
        if bases is None:
            bases = []
        if dict is None:
            dict = {}
        return type_impl.ProtoObject(name, bases, dict)

@apply
class Type_Number(type_impl._Type):
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

@apply
class RawStoreObjectMeth(type_impl._Type):
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

@apply
class RawLoadObjectMeth(type_impl._Type):
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
            bs.code += isa.pop(registers.rbx)
            assert bs.flow.stack.pop() is self
            bs.code += isa.pop(registers.rax)
            
            bs.code += isa.shl(registers.rbx, 3)
            bs.code += isa.add(registers.rax, registers.rbx)
            
            bs.code += isa.push(MemRef(registers.rax))
            bs.flow.stack.append(type_impl.Int)
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
            
            bs.code += isa.mov(MemRef(registers.rax), registers.rcx)
            
            type_impl.NoneType.load()(bs)
        return _
@apply
class Raw(type_impl._Type):
    size = 1
    def getattr___getitem__(self, bs): bs.flow.stack.append(RawGetitemMeth)
    def getattr___setitem__(self, bs): bs.flow.stack.append(RawSetitemMeth)
    def getattr_load_object(self, bs): bs.flow.stack.append(RawLoadObjectMeth)
    def getattr_store_object(self, bs): bs.flow.stack.append(RawStoreObjectMeth)
    def getattr_copy_from(self, bs): bs.flow.stack.append(RawCopyFromMeth)

@apply
class RawType(type_impl._Type):
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

list_impl = None
@apply
class SetListImpl(_PythonFunction):
    def handler(self, new):
        global list_impl
        assert list_impl is None, "list_impl can only be set once"
        list_impl = new
        return type_impl.NoneType

dict_impl = None
@apply
class SetDictImpl(_PythonFunction):
    def handler(self, new):
        global dict_impl
        assert dict_impl is None, "dict_impl can only be set once"
        dict_impl = new
        return type_impl.NoneType

StopIteration_impl = None
@apply
class SetStopIterationImpl(_PythonFunction):
    def handler(self, new):
        global StopIteration_impl
        assert StopIteration_impl is None, "StopIteration_impl can only be set once"
        StopIteration_impl = new
        return type_impl.NoneType

SyntaxError_impl = None
@apply
class SetSyntaxErrorImpl(_PythonFunction):
    def handler(self, new):
        global SyntaxError_impl
        assert SyntaxError_impl is None, "SyntaxError_impl can only be set once"
        SyntaxError_impl = new
        return type_impl.NoneType

NameError_impl = None
@apply
class SetNameErrorImpl(_PythonFunction):
    def handler(self, new):
        global NameError_impl
        assert NameError_impl is None, "NameError_impl can only be set once"
        NameError_impl = new
        return type_impl.NoneType

AssertionError_impl = None
@apply
class SetAssertionErrorImpl(_PythonFunction):
    def handler(self, new):
        global AssertionError_impl
        assert AssertionError_impl is None, "AssertionError_impl can only be set once"
        AssertionError_impl = new
        return type_impl.NoneType

AttributeError_impl = None
@apply
class SetAttributeErrorImpl(_PythonFunction):
    def handler(self, new):
        global AttributeError_impl
        assert AttributeError_impl is None, "AttributeError_impl can only be set once"
        AttributeError_impl = new
        return type_impl.NoneType

@apply
class ArgGetter(_PythonFunction):
    def handler(self, i):
        import sys
        return sys.argv[i]

@apply
class ArgGetterGetItem(type_impl._Type):
    size = 0
    def __call__(self, arg_types):
        assert arg_types == (type_impl.Int,)
        def _(bs):
            assert bs.flow.stack.pop() is type_impl.Int
            assert bs.flow.stack.pop() is self
            def _(value):
                def _(bs):
                    import sys
                    bs.this.append(type_impl.Str.load_constant(sys.argv[1 + value]))
                return _
            util.unlift(bs, _, "ArgGetterGetItem")
        return _

@apply
class ArgGetterLen(type_impl._Type):
    size = 0
    def __call__(self, arg_types):
        assert arg_types == ()
        def _(bs):
            assert bs.flow.stack.pop() is self
            import sys
            bs.this.append(type_impl.Int.load_constant(len(sys.argv[1:])))
        return _

@apply
class ArgGetter(type_impl._Type):
    size = 0
    def getattr___getitem__(self, bs):
        bs.flow.stack.append(ArgGetterGetItem)
    def getattr___len__(self, bs):
        bs.flow.stack.append(ArgGetterLen)

@apply
class PyableModule(type_impl._Type):
    size = 0
    def getattr_type(self, bs): bs.flow.stack.append(Type)
    def getattr_type_number(self, bs): bs.flow.stack.append(Type_Number)
    def getattr_raw(self, bs): bs.flow.stack.append(RawType)
    def getattr_set_list_impl(self, bs): bs.flow.stack.append(SetListImpl)
    def getattr_set_list_impl(self, bs): bs.flow.stack.append(SetDictImpl)
    def getattr_set_StopIteration_impl(self, bs): bs.flow.stack.append(SetStopIterationImpl)
    def getattr_set_SyntaxError_impl(self, bs): bs.flow.stack.append(SetSyntaxErrorImpl)
    def getattr_set_NameError_impl(self, bs): bs.flow.stack.append(SetNameErrorImpl)
    def getattr_set_AssertionError_impl(self, bs): bs.flow.stack.append(SetAssertionErrorImpl)
    def getattr_set_AttributeError_impl(self, bs): bs.flow.stack.append(SetAttributeErrorImpl)
    def getattr_args(self, bs):
        bs.flow.stack.append(ArgGetter)
        return
        import sys
        for arg in sys.argv[1:]:
            bs.this.append(type_impl.Str.load_constant(arg))
        bs.this.append(type_impl.prototuples[(type_impl.Str,) * len(sys.argv[1:])].load())
