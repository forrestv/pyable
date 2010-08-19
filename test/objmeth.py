import _pyable

A = _pyable.type("a", None, None)

def A___init__(self):
    print "hi!"
A.__init__ = A___init__


def A_method1(self):
    print "method!"
A.method1 = A_method1

a = A()

x = a.method1()
