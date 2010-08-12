from __future__ import division

import ast
import sys
import struct
import random
import time

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

tree = ast.parse(open(sys.argv[1]).read())

if util.DEBUG:
    print util.dump(tree)

def make_root():
    return compiler.translate("make_root", compiler.Flow(None), this=[
        main_module(),
        lambda bs, this: bs.code.add(isa.ret()),
        None,
    ])

main_module = compiler.Module(tree, "__main__")

def caller():
    p = util.Program()
    code = p.get_stream()
    util.Redirection(code, lambda caller: caller.replace(util.get_call(make_root())))
    p.add(code)
    p.cache_code()
    util.debug(p, "caller")
    return p
caller = caller()

processor = platform.Processor()
if util.DEBUG:
    import time
    print "STARTING"
    start = time.time()
ret = processor.execute(caller, mode='int')
if util.DEBUG:
    end = time.time()
    print "END", ret, end-start
