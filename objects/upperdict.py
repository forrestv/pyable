# dict that handles typing in the compiler

import ctypes
import struct
import ast

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
from corepy.arch.x86_64.lib.memory import MemRef

import util
import mypyable
import type_impl
from type_impl import _Type

@apply
class Unset(_Type):
    size = 0

class Attribute(object):
    def __init__(self, name):
        self.container = ctypes.create_string_buffer(8 * type_impl.max_size)
        
        type = Unset
        self.value = util.WatchedValue(type)
        
        self.id_container = ctypes.create_string_buffer(8)
        def update_value(new_value):
            self.id_container.raw = struct.pack("l", new_value.id)
        self.value.watch_now(update_value)
        
        @util.called_from_asm
        def type_changed(new_type_id):
            new_type = type_impl.id_to_type[new_type_id]
            #print name, "-", self.value.value, "->", new_type
            self.value.set(new_type)
        self.type_setter = ctypes.CFUNCTYPE(None, ctypes.c_long)(type_changed)

class UpperDict(_Type):
    size = 0
    def __init__(self):
        _Type.__init__(self)
        self.contents = util.cdict(Attribute)
    
    def get_name(self, attr):
        def _(bs):
            content = self.contents[attr]
            def load_type(type):
                def _(bs):
                    if type is Unset:
                        if mypyable.NameError_impl is None:
                            bs.this.append(ast.Raise(ast.Str(s=""), None, None))
                            return
                        bs.this.append(ast.Raise(
                            type=ast.Call(
                                func=mypyable.NameError_impl.load,
                                args=[ast.Str(s=attr)],
                                keywords=[],
                                starargs=None,
                                kwargs=None,
                                ),
                            inst=None,
                            tback=None,
                        ))
                        return
                    addr = ctypes.cast(content.container, ctypes.c_void_p).value
                    if type.size:
                        bs.code += isa.mov(registers.rax, addr)
                        for i in xrange(type.size):
                            bs.code += isa.push(MemRef(registers.rax, 8 * i))
                    bs.flow.stack.append(type)
                return _
            util.branch_on_watched(bs, content.value, load_type)
        return _
    
    def set_name(self, attr):
        def _(bs):
            content = self.contents[attr]
            
            type = bs.flow.stack.pop()
            
            # we could use a watcher to modify the generated code to not require a memory access.
            skip = bs.program.get_unique_label()
            bs.code += isa.mov(registers.rax, ctypes.cast(content.id_container, ctypes.c_void_p).value)
            bs.code += isa.cmp(MemRef(registers.rax), type.id)
            bs.code += isa.je(skip)
            bs.code += isa.mov(registers.rax, ctypes.cast(content.type_setter, ctypes.c_void_p).value)
            bs.code += isa.mov(registers.rdi, type.id)
            bs.code += isa.call(registers.rax)
            bs.code += skip
            
            if type is not content.value.value: content.value.set(type)
            # i'm pretty sure we can do this - this code will immediately be executed after and this fits in with code generation
            # BUT things that use it before it have to be altered properly
            # right now they will just raise an error - render_code hasn't been defined
            # it should ignore this and wait for the asm code above to modify it.
            
            addr = ctypes.cast(content.container, ctypes.c_void_p).value
            if type.size:
                bs.code += isa.mov(registers.rax, addr)
                for i in reversed(xrange(type.size)):
                    bs.code += isa.pop(MemRef(registers.rax, 8 * i))
        return _
    
    def del_name(self, attr):
        bs.flow.stack.append(Unset)
        bs.flow.this.append(self.set_name(attr))

builtin = UpperDict()
