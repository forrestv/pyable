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

if sys.argv[1] == "--debug":
    util.DEBUG = 1
    sys.argv[1:] = sys.argv[2:]

filename = os.path.join(os.path.dirname(__file__), "lib", "main.py")
filename = sys.argv[1]
tree = ast.parse(open(filename).read(), filename)

if util.DEBUG:
    print util.dump(tree)

main_module = compiler.Function(ast.FunctionDef(
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

def make_root():
    return compiler.translate("make_root", compiler.Flow(None), this=[
        lambda bs: bs.code.add(isa.push(0)), # moot scope
        main_module(),
        lambda bs: bs.code.add(isa.pop(registers.rax)), # moot scope
        lambda bs: bs.code.add(isa.ret()),
        None,
    ])

def caller():
    p = util.Program()
    code = p.get_stream()
    util.add_redirection(code, lambda rdi: util.get_call(make_root()))
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
