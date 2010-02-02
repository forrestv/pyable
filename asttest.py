import ast
import sys

import greenlet

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
import corepy.arch.x86_64.platform as platform
from corepy.arch.x86_64.lib.memory import MemRef
import corepy.lib.extarray as extarray
import corepy.arch.x86_64.lib.util as util

import util
from cdict import cdict

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

def add_parents(node, parent=None):
    node.parent = parent
    for fieldname, value in ast.iter_fields(node):
        if isinstance(value, ast.AST):
            add_parents(value, (node, fieldname))
        elif isinstance(value, list):
            for i, child in enumerate(value):
                assert isinstance(child, ast.AST)
                add_parents(child, (node, fieldname, i))

class BlockStatus(object):
    def __init__(self):
        self.program = util.BareProgram()
        self.code = self.program.get_stream()
        self.locs = {}
        self.local_count = 0
        self.on_true = None
    def get_loc(self, name):
        if name not in self.locs:
            self.locs[name] = self.local_count*8
            self.local_count += 1
        return self.locs[name]
    def finalise(self):
        self.program.add(self.code)
        self.program.cache_code()
        return self.program #return Block(self.program)

class Block(object):
    def __init__(self, program):
        self.program = program

class Function(object):
    def __init__(self, ast):
        self.ast = ast
        assert isinstance(self.ast, ast.FunctionDef)
        self.addr = None
        self.program = None
    def _get_addr(self):
        if self.addr is None:
            self._render()
        return self.addr
    def add_call(self, code):
        if self.addr:
            code.add(isa.mov(registers.rax, util.fake_int(self.addr)))
            code.add(isa.call(registers.rax))
        else:
            util.Redirection(_redir_callback)
    def redir_callback(self, redir):
        redir.replace(util.get_call(self._get_addr()))

functions = {}

def compile(bs, t):
    if isinstance(t, list):
        for x in t:
            bs = compile(bs, x)
    elif isinstance(t, ast.Module):
        enter_index = bs.code.add(isa.enter(128, 0)) - 1
        bs = compile(bs, t.body)
        bs.code.add(isa.leave())
        bs.code.add(isa.ret())
        #bs.code[enter_index] = isa.enter(len(bs.locs)*8, 0)
    elif isinstance(t, ast.FunctionDef):
        enter_index = bs.code.add(isa.enter(128, 0)) - 1
        bs = compile(bs, t.body)
        bs.code.add(isa.leave())
        bs.code.add(isa.ret())
    elif isinstance(t, ast.AugAssign):
        bs = compile(bs, ast.Assign(targets=[t.target],
            value=ast.BinOp(left=t.target, op=t.op, right=t.value)))
    elif isinstance(t, ast.Assign):
        bs = compile(bs, t.value)
        assert len(t.targets) == 1
        target = t.targets[0]
        assert isinstance(target, ast.Name)
        assert isinstance(target.ctx, ast.Store)
        bs.code.add(isa.pop(MemRef(registers.rsp, bs.get_loc(target.id))))
    elif isinstance(t, ast.Expr):
        bs = compile(bs, t.value)
        bs.code.add(isa.add(registers.rsp, 8)) #bs.code.add(isa.pop(registers.rax))
    elif isinstance(t, ast.Num):
        bs.code.add(isa.push(t.n))
    elif isinstance(t, ast.Name):
        bs.code.add(isa.push(MemRef(registers.rsp, bs.get_loc(t.id))))
    elif isinstance(t, ast.If):
        def make_a():
            a
        bs.on_true = lambda bs: util.Redirection(bs.code, make_a)
        bs = compile_wrap(bs, t.test)
        util.Redirection(bs.code, make_b) # jmp
        p = bs.finalise()
        blocks.append(p)
        refs['a'] = p
        p.print_code()
        caller.replace(util.get_jmp(p.inst_addr()))
        util.Redirection(bs.code, make_a)
        g = greenlet.getcurrent()
        bs = g.parent.switch(bs)
    elif isinstance(t, ast.While):
        a = object()
        def make_a(caller):
            if 'a' in refs:
                p = refs['a']
            else:
                print "make_a"
                bs = BlockStatus()
                bs.on_true = lambda bs: util.Redirection(bs.code, make_b)
                bs = compile_wrap(bs, t.test)
                util.Redirection(bs.code, make_c) # jmp
                p = bs.finalise()
                blocks.append(p)
                refs['a'] = p
                p.print_code()
            caller.replace(util.get_jmp(p.inst_addr()))
        def make_b(caller):
            if 'b' in refs:
                p = refs['b']
            else:
                print "make_b"
                bs = BlockStatus()
                bs = compile_wrap(bs, t.body)
                util.Redirection(bs.code, make_a)
                p = bs.finalise()
                blocks.append(p)
                refs['b'] = p
                p.print_code()
            if 0:
                bs = BlockStatus()
                bs = compile_wrap(bs, t.body)
                util.Redirection(bs.code, make_a)
                p = bs.finalise()
                blocks.append(p)
            caller.replace(util.get_jmp(p.inst_addr()))
        def make_c(caller):
            if 'c' in refs:
                p = refs['c']
            else:
                print "make_c"
                bs = BlockStatus()
                bs = g.switch(bs)
                p = bs.finalise()
                blocks.append(p)
                refs['c'] = p
                p.print_code()
            caller.replace(util.get_jmp(p.inst_addr()))
        util.Redirection(bs.code, make_a)
        g = greenlet.getcurrent() # save current for make_c
        bs = g.parent.switch(bs) # return, with results in res
    elif isinstance(t, ast.Compare):
        assert bs.on_true
        compile(bs, t.left)
        c, = t.comparators
        compile(bs, c)
        bs.code.add(isa.pop(registers.rbx))
        bs.code.add(isa.pop(registers.rax))
        bs.code.add(isa.cmp(registers.rax, registers.rbx))
        op, = t.ops
        label = bs.program.get_unique_label()
        if isinstance(op, ast.Lt):
            bs.code.add(isa.jge(label))
        elif isinstance(op, ast.Gt):
            bs.code.add(isa.jle(label))
        elif isinstance(op, ast.LtE):
            bs.code.add(isa.jg(label))
        elif isinstance(op, ast.GtE):
            bs.code.add(isa.jl(label))
        elif isinstance(op, ast.Eq):
            bs.code.add(isa.jne(label))
        elif isinstance(op, ast.NotEq):
            bs.code.add(isa.je(label))
        else:
            assert False, op
        bs.on_true(bs)
        bs.on_true = None
        bs.code.add(label)
    elif isinstance(t, ast.Print):
        bs.code.add(isa.mov(registers.rdi, MemRef(registers.rsp, bs.get_loc(t.values[0].id))))
        bs.code.add(isa.mov(registers.rax, util.print_int64_addr))
        #code.add(isa.sub(regsisters
        bs.code.add(isa.call(registers.rax))
    elif isinstance(t, ast.UnaryOp):
        compile(bs, t.operand)
        bs.code.add(isa.pop(registers.rax))
        if isinstance(t.op, ast.USub):
            bs.code.add(isa.neg(registers.rax))
        else:
            assert False, t.op
        bs.code.add(isa.push(registers.rax))
    elif isinstance(t, ast.BinOp):
        compile(bs, t.left)
        compile(bs, t.right)
        bs.code.add(isa.pop(registers.rbx))
        bs.code.add(isa.pop(registers.rax))
        if isinstance(t.op, ast.Add):
            bs.code.add(isa.add(registers.rax, registers.rbx))
        elif isinstance(t.op, ast.Sub):
            bs.code.add(isa.sub(registers.rax, registers.rbx))
        elif isinstance(t.op, ast.Mult):
            bs.code.add(isa.imul(registers.rax, registers.rbx))
        elif isinstance(t.op, ast.Div):
            bs.code.add(isa.idiv(registers.rbx))
        else:
            assert False, t.op
        bs.code.add(isa.push(registers.rax))
    else:
        assert False, t
    return bs

def compile_wrap(bs, t):
    g = greenlet.greenlet(compile)
    return g.switch(bs, t)
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
    refs[1]


prerefs = {}
refs = cdict(lambda k: prerefs.pop(k)())
tree = ast.parse(open(sys.argv[1]).read())
#print tree
#print dump(tree)
#fadf
#add_parents(tree)
#print tree.parent
print dump(tree)
blocks = []
def make_root(redir):
    bs = BlockStatus()
    r = compile_wrap(bs, tree)
    p = bs.finalise()
    blocks.append(p)
    #p.print_code(pro=True, epi=True)
    if 1:
        print "make_root"
        p.print_code()
    redir.replace(util.get_call(p.inst_addr()))

def caller():
    program = util.Program()
    code = program.get_stream()
    util.Redirection(code, make_root)
    program.add(code)
    program.cache_code()
    return program
caller = caller()

processor = platform.Processor()
import time
print "STARTING"
start = time.time()
ret = processor.execute(caller, mode='int')
end = time.time()
print "END", ret, end-start
