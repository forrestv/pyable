import ast

import greenlet

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

def compile(t, res, on_true=None):
    if isinstance(t, ast.Module):
        for x in t.body:
            res = compile(x, res)
        res.append("ret")
    elif isinstance(t, ast.Assign):
        res = compile(t.value, res)
        assert len(t.targets) == 1
        target = t.targets[0]
        assert isinstance(target, ast.Name)
        assert isinstance(target.ctx, ast.Store)
        res.append("pop %s" % target.id)
    elif isinstance(t, ast.Num):
        res.append("push %i" % t.n)
    elif isinstance(t, ast.While):
        def make_b():
            res = []
            for x in t.body:
                res.extend(compile_wrap(x))
            res.append(("jmp", make_a))
            return res
        def make_c():
            return g.switch()
        def make_a():
            res = compile_wrap(t.test, on_true=("jmp", make_b))
            res.append(("jmp", make_c))
            return res
        res.append(("jmp", make_a))
        # MAGIC
        g = greenlet.getcurrent()
        g.parent.switch()
        res = []
        print "BACK"
    elif isinstance(t, ast.Compare):
        res.append("COMPARE, IF YES %r" % (on_true,))
        #for x in t:
        #    compile(x, res)
    elif isinstance(t, ast.Print):
        res.append("call print %s" % t.values)
    else:
        print t
    return res

#def compile2(a):
#    def push_ast(a):
#        t.append((a, 0))
#    t = []
#    push_ast(a)
#    while t:
#        a = t.pop()
#        if 

def compile_wrap(t, on_true=None):
    g = greenlet.greenlet(compile)
    res = []
    g.switch(t, res, on_true)
    return res

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
