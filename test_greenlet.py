import greenlet

print dir(greenlet)

def traverse(c=3):
    if c == 0:
        print "start"
        o.switch(5)
        print "end"
    else:
        traverse(c-1)
    return 3

def f():
    print "start"
    print "end"

o = greenlet.getcurrent()
print o
g = greenlet.greenlet(traverse)
print 1
x = g.switch()
print 2
print x
y = g.switch()
print y
