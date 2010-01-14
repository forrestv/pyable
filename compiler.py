import parser
import symbol
import sys
import token

def read_tree(file_):
    return parser.suite(file_.read()).totuple()

by_type = {}
def print_tree(tree, indent=0):
    if isinstance(tree, str):
        print indent*"    " + repr(tree)
    else:
        assert isinstance(tree[0], int)
        try:
            name = symbol.sym_name[tree[0]]
        except KeyError:
            name = token.tok_name[tree[0]]
        else:
            by_type.setdefault(name, []).append(tree)
        print indent*"    " + name
        for item in tree[1:]:
            print_tree(item, indent + 1)

class Symbol(object):
    def __init__(self, name, children):
        self.name = name
        self.children = list(children)
        for child in self.children:
            child.parent = self
    def __repr__(self):
        return self.name + repr(self.children)

class Token(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value
    def __repr__(self):
        return "%s(%r)" % (self.name, self.value)


class SymbolHandler(object):
    def _default(self, name, children):
        res = []
        for child in children:
            if child[0] in token.tok_name:
                print "_default(%r, ...) has children tokens" % name
                continue
            res.append(self.handle(child))
        return Symbol(name, res)
    def handle(self, s):
        i = s[0]
        try:
            symbol_name = symbol.sym_name[i]
            try:
                handler = getattr(self, symbol_name)
            except AttributeError:
                return self._default(symbol_name, s[1:])
            else:
                return handler(s[1:])
        except KeyError:
            token_name = token.tok_name[i]
            assert len(s) == 2
            assert False, "SymbolHandler.handle called with token %s %r" % (token_name, s[1])
            return Token(token_name, s[1])
symbol_handler = SymbolHandler()

def convert_tree(s):
    i = s[0]
    try:
        symbol_name = symbol.sym_name[i]
        return Symbol(symbol_name, map(convert_tree, s[1:]))
    except KeyError:
        token_name = token.tok_name[i]
        assert len(s) == 2
        return Token(token_name, s[1])
    

class NameFinder(SymbolHandler):
    def _default(self, name, children):
        res = set()
        for child in children:
            if child[0] in token.tok_name:
                print "_default(%r, ...) has children tokens" % name
                continue
            res.update(self.handle(child))
        return res
    def atom(self, children):
        print children
        return [x[1] for x in children if x[0] == token.NAME]
name_finder = NameFinder()

class Compiler(SymbolHandler):
    def AMPER(self, value):
        pass
    def AMPEREQUAL(self, value):
        pass
    def AT(self, value):
        pass
    def BACKQUOTE(self, value):
        pass
    def CIRCUMFLEX(self, value):
        pass
    def CIRCUMFLEXEQUAL(self, value):
        pass
    def COLON(self, value):
        pass
    def COMMA(self, value):
        pass
    def DEDENT(self, value):
        pass
    def DOT(self, value):
        pass
    def DOUBLESLASH(self, value):
        pass
    def DOUBLESLASHEQUAL(self, value):
        pass
    def DOUBLESTAR(self, value):
        pass
    def DOUBLESTAREQUAL(self, value):
        pass
    def ENDMARKER(self, value):
        pass
    def EQEQUAL(self, value):
        pass
    def EQUAL(self, value):
        pass
    def ERRORTOKEN(self, value):
        pass
    def GREATER(self, value):
        pass
    def GREATEREQUAL(self, value):
        pass
    def INDENT(self, value):
        pass
    def LBRACE(self, value):
        pass
    def LEFTSHIFT(self, value):
        pass
    def LEFTSHIFTEQUAL(self, value):
        pass
    def LESS(self, value):
        pass
    def LESSEQUAL(self, value):
        pass
    def LPAR(self, value):
        pass
    def LSQB(self, value):
        pass
    def MINEQUAL(self, value):
        pass
    def MINUS(self, value):
        pass
    def NAME(self, value):
        pass
    def NEWLINE(self, value):
        pass
    def NOTEQUAL(self, value):
        pass
    def NT_OFFSET(self, value):
        pass
    def NUMBER(self, value):
        pass
    def N_TOKENS(self, value):
        pass
    def OP(self, value):
        pass
    def PERCENT(self, value):
        pass
    def PERCENTEQUAL(self, value):
        pass
    def PLUS(self, value):
        pass
    def PLUSEQUAL(self, value):
        pass
    def RBRACE(self, value):
        pass
    def RIGHTSHIFT(self, value):
        pass
    def RIGHTSHIFTEQUAL(self, value):
        pass
    def RPAR(self, value):
        pass
    def RSQB(self, value):
        pass
    def SEMI(self, value):
        pass
    def SLASH(self, value):
        pass
    def SLASHEQUAL(self, value):
        pass
    def STAR(self, value):
        pass
    def STAREQUAL(self, value):
        pass
    def STRING(self, value):
        pass
    def TILDE(self, value):
        pass
    def VBAR(self, value):
        pass
    def VBAREQUAL(self, value):
        pass
    def while_stmt(self, children):
        print children
    def __call__(self, s):
        if isinstance(s, Symbol):
            if hasattr(self, s.name):
                getattr(self, s.name)(s.children)
            else:
                getattr(self, s.name + "_pre", lambda: None)()
                first = True
                for child in s.children:
                    if first:
                        first = False
                    else:
                        getattr(self, s.name + "_mid", lambda: None)()
                    self(child)
                getattr(self, s.name + "_post", lambda: None)()
        else:
            assert isinstance(s, Token)
            getattr(self, s.name)(s.value)
compiler = Compiler()

class while_stmt(object):
    def __init__(self, node):
        type, children = node
        print children
        assert ast.name == 'while_stmt'
        assert ast.children[0] == (token.NAME, 'while')
        self.test = ast.children[1]
        assert ast.children[2] == (token.NAME, ':')
        self.suite = ast.children[2]
  

if __name__ == "__main__":
    tree = read_tree(open(sys.argv[1]))
    print_tree(tree)
    print
    #print name_finder.handle(tree)
    print
    print
    tree = convert_tree(tree)
    #print tree
    compiler(tree)
    while_stmt(*by_type['while_stmt'])
