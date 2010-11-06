from __future__ import division

import ast
import sys
import struct
import random
import time
import os

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
import corepy.arch.x86_64.platform as platform
from corepy.arch.x86_64.lib.memory import MemRef

import util
import type_impl
import compiler

#sys.stdout = None

filename = os.path.join(os.path.dirname(__file__), "lib", "main.py")

if sys.argv[1:] and sys.argv[1] == "--debug":
    util.DEBUG = True
    sys.argv[1:] = sys.argv[2:]

if sys.argv[1:] and sys.argv[1] == "--override":
    override = True
    filename = sys.argv[2]
    sys.argv[1:] = sys.argv[3:]
    
tree = ast.parse(open(filename).read(), filename)

#if util.DEBUG:
#    print util.dump(tree)

main_module = compiler.Function([None], ast.FunctionDef(
    name="__main__",
    args=ast.arguments(
        args=[],
        vararg=None,
        kwarg=None,
        defaults=[],
    ),
    body=tree.body,
    decorator_list=[],
))

def uncaught_exception(bs):
    #type = bs.flow.stack.pop()
    #if type is type_impl.Str:
    #    bs.code += isa.pop(registers.rdi)
    #    bs.code += isa.mov(registers.rax, util.print_string_addr)
    #    bs.code += isa.call(registers.rax)
    #    bs.code += isa.mov(registers.rax, util.print_nl_addr)
    #    bs.code += isa.call(registers.rax)
    #    bs.code += isa.mov(registers.rsp, registers.rbp)
    #    bs.code += isa.pop(registers.rbp)
    #    bs.code += isa.ret()
    #    return
    #for i in xrange(type.size): bs.code += isa.pop(registers.rax)
    #bs.this.append(ast.Str(s="uncaught exception. type: " + repr(type)))
    #@bs.flow.try_stack.append
    #def _(bs):
    #    print list(bs.flow.stack), "XXX"
    #bs.this.append(
    #    ast.Call(
    #        func=ast.Attribute(
    #            value=lambda bs: None,
    #            attr='__str__',
    #            ctx=ast.Load(),
    #            ),
    #        args=[],
    #        keywords=[],
    #        starargs=None,
    #        kwargs=None,
    #        ),
    #    )
    if 0:
        bs.this.append(ast.Attribute(
            value=lambda bs: None,
            attr="message",
            ctx=ast.Load(),
        ))
    @bs.this.append
    def _(bs):
        assert bs.flow.stack[-1] is type_impl.Str, list(bs.flow.stack)
        bs.flow.stack.pop()
        bs.code += isa.mov(registers.rax, util.print_string_addr)
        bs.code += isa.pop(registers.rdi)
        bs.code += isa.call(registers.rax)
        bs.code += isa.mov(registers.rax, util.print_nl_addr)
        bs.code += isa.call(registers.rax)
        bs.code += isa.mov(registers.rsp, registers.rbp)
        bs.code += isa.pop(registers.rbp)
        bs.code += isa.ret()
    bs.this.append(compiler.end)

def make_root():
    return compiler.translate("make_root", compiler.Flow(), this=[
        lambda bs: bs.code.add(isa.push(registers.rbp)),
        lambda bs: bs.code.add(isa.mov(registers.rbp, registers.rsp)),
        lambda bs: bs.flow.try_stack.append(uncaught_exception),
        #main_module.load(),
        #ast.Call(
        #    func=lambda bs: None,
        #    args=[],
        #    keywords=[],
        #    starargs=None,
        #    kwargs=None,
        #    ),
        tree.body,
        lambda bs: bs.code.add(isa.mov(registers.rsp, registers.rbp)),
        lambda bs: bs.code.add(isa.pop(registers.rbp)),
        lambda bs: bs.code.add(isa.ret()),
        compiler.end,
    ])

def caller():
    p = util.Program()
    code = p.get_stream()
    code += isa.mov(registers.rax, make_root())
    code += isa.call(registers.rax)
    #util.add_redirection(code, lambda rdi: util.get_call(make_root()))
    p.add(code)
    p.cache_code()
    util.debug(p, "caller")
    return p
caller = caller()

processor = platform.Processor()
if util.DEBUG:
    print "START"
    start = time.time()
processor.execute(caller)
if util.DEBUG:
    end = time.time()
    print "END", end - start

util.post()
