import _pyable
type = _pyable.type
type_number = _pyable.type_number

mytype = type("hi", None, None)

def f(self):
   print "init'd!"
   self.x = 4
   print "i have", self.x
mytype.__init__ = f

x = mytype()

def g(self):
   print "init'd! 2"
   self.x = 5
   print "i have", self.x
   #del self.x
mytype.__init__ = g

y = mytype()

#print "_pyable", type_number(_pyable)
#print "1", type_number(1)
#print "\"hi\"", type_number("hi")
#print "type", type_number(type)
#print "type_number", type_number(type_number)
#print "mytype", type_number(mytype)
#print "f", type_number(f)
#print "g", type_number(g)
#print "x", type_number(x)
#print "y", type_number(y)

#dict = type("dict", ())
#
#def hash(o):
#    return o.__hash__()

#def dict_init(self):
#    self.

print "woot"

print x.x
print y.x
