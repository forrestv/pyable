import ast

import greenlet


import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
import corepy.arch.x86_64.platform as platform
from corepy.arch.x86_64.lib.memory import MemRef
import corepy.lib.extarray as extarray
import corepy.arch.x86_64.lib.util as util

def dump(node, annotate_fields=True, include_attributes=False):
    """
    Return a formatted dump of the tree in *node*.  This is mainly useful for
    debugging purposes.  The returned string will show the names and the values
    for fields.  This makes the code impossible to evaluate, so if evaluation is
    wanted *annotate_fields* must be set to False.  Attributes such as line
    numbers and column offsets are not dumped by default.  If this is wanted,
    *include_attributes* can be set to True.
    """
    def _format(node,indent=4):
        if isinstance(node, ast.AST):
            fields = [(a, _format(b, indent+4)) for a, b in ast.iter_fields(node)]
            rv = node.__class__.__name__ + '(\n'
            for field in fields:
                rv += ' '*indent + '%s=%s,\n' % field
            if include_attributes and node._attributes:
                rv += fields and ', ' or ' '
                rv += ', '.join('%s=%s' % (a, _format(getattr(node, a), indent+4))
                                for a in node._attributes)
            return rv + ' '*indent + ')'
        elif isinstance(node, list):
            return '[\n%s%s\n%s]' % (' '*indent,(',\n'+' '*indent).join(_format(x, indent+4) for x in node), ' '*indent)
        return repr(node)
    if not isinstance(node, ast.AST):
        raise TypeError('expected AST, got %r' % node.__class__.__name__)
    return _format(node)

tree = ast.parse(open('test/1.py').read())
def add_parents(node, parent=None):
    node.parent = parent
    for fieldname, value in ast.iter_fields(node):
        if isinstance(value, ast.AST):
            add_parents(value, (node, fieldname))
        elif isinstance(value, list):
            for i, child in enumerate(value):
                assert isinstance(child, ast.AST)
                add_parents(child, (node, fieldname, i))
add_parents(tree)
print tree.parent
print dump(tree)

class EndBlock(Exception): pass

#class AstTraverser(object):
#    def __init__(self, 

refs = {}

class BlockProgress(object):
    def __init__(self, code):
        self.code = code
        self.locs = {}

class Block(object):
    def __init__(self, program):
        self.program = program

def make_block_from_tree(tree):
    program = platform.Program()
    code = program.get_stream()
    greenlet.greenlet(compile).switch(t, code, on_true)
    program.add(code)
    program.cache_code()
    return program

def make_block_from_func(f):
    program = platform.Program()
    code = program.get_stream()
    greenlet.greenlet(f).switch(code, on_true)
    program.add(code)
    program.cache_code()
    return program

def compile(bs, t):
    if isinstance(t, ast.Module):
        for x in t.body:
            bs = compile(bs, x)
        bs.code.add(isa.ret())
    elif isinstance(t, ast.Assign):
        res = compile(bs, t.value)
        assert len(t.targets) == 1
        target = t.targets[0]
        assert isinstance(target, ast.Name)
        assert isinstance(target.ctx, ast.Store)
        bs.code.add(isa.pop(target.id))
    elif isinstance(t, ast.Num):
        res.add(isa.push(t.n))
    elif isinstance(t, ast.While):
        def make_b(code):
            res = []
            for x in t.body:
                res.extend(compile_wrap(x))
            res.append(("jmp", make_a))
            return res
        def make_c(code):
            return g.switch([])
        def make_a(code):
            res = compile_wrap(t.test, on_true=("jmp", make_b))
            res.append(("jmp", make_c))
            return res
        res.append(("jmp", make_a))
        g = greenlet.getcurrent() # save current for make_c
        res = g.parent.switch(res) # return, with results in res
    elif isinstance(t, ast.Compare):
        res.add("COMPARE, IF YES %r" % (on_true,))
    elif isinstance(t, ast.Print):
        res.add("call print %s" % t.values)
    else:
        print t
    return res

def compile_wrap(t, on_true=None):
    g = greenlet.greenlet(compile)
    res = []
    g.switch(t, res, on_true)
    return res
'''
res = compile_wrap(tree)
print res
make_a = res[2][1]
print make_a
res2 = make_a()
print res2
make_c = res2[1][1]
print make_c
res3 = make_c()
print res3
'''
def add_root(tree):
    def make_root(tree):
        program = platform.Program()
        locs = {}
        code = program.get_stream()
        compile(tree, code, locs)
        program.add(code)
        program.cache_code()
        return program
    refs[


r = do_it(tree)
print r
