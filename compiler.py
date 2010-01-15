import parser
import symbol
import sys
import token

def read_tree(file_):
    return parser.suite(file_.read()).totuple()

def print_tree(tree, indent=0):
    if isinstance(tree, str):
        print indent*"    " + repr(tree)
    else:
        assert isinstance(tree[0], int)
        try:
            name = symbol.sym_name[tree[0]]
        except KeyError:
            name = token.tok_name[tree[0]]
        print indent*"    " + name
        for item in tree[1:]:
            print_tree(item, indent + 1)

def make_type_dict(s, d=None):
    if d is None:
        d = {}
    d.setdefault(s[0], []).append(s)
    if len(s) == 2 and not isinstance(s[1], tuple):
        return d
    for child in s[1:]:
        make_type_dict(child, d)
    return d

class while_stmt(object):
    def __init__(self, node):
        symbol_while_stmt, token_name_while, condition, token_colon, body = node
        del node
        
        assert symbol_while_stmt == symbol.while_stmt
        assert token_name_while == (token.NAME, 'while')
        self.condition = test(condition)
        assert token_colon == (token.COLON, ':')
        self.body = suite(body)
        
        print self.__dict__

class suite(object):
    def __new__(self, node):
        if len(node) == 2:
            symbol_suite, single_body = node
            assert symbol_suite == symbol.suite
            body = [simple_stmt(single_body)]
        else:
            symbol_suite, token_newline, token_indent = node[:3]
            body = node[3:-1]
            token_dedent = node[-1]
            assert symbol_suite == symbol.suite
            assert token_newline == (token.NEWLINE, '')
            assert token_indent == (token.INDENT, '')
            body = map(simple_stmt, body)
            assert token_dedent == (token.DEDENT, '')
        return body

class simple_stmt(object):
    def __new__(self, node):
        if len(node) == 2:
            symbol_suite, single_body = node
            assert symbol_suite == symbol.suite
            body = [simple_stmt(single_body)]
        else:
            symbol_suite, token_newline, token_indent = node[:3]
            body = node[3:-1]
            token_dedent = node[-1]
            assert symbol_suite == symbol.suite
            assert token_newline == (token.NEWLINE, '')
            assert token_indent == (token.INDENT, '')
            body = map(simple_stmt, body)
            assert token_dedent == (token.DEDENT, '')
        return body

class test(object):
    def __new__(self, node):
        return None

if __name__ == "__main__":
    tree = read_tree(open(sys.argv[1]))
    print_tree(tree)
    print
    type_dict = make_type_dict(tree)
    while_stmt(*type_dict[symbol.while_stmt])
