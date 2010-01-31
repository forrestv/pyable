import greenlet

print dir(greenlet)

saved = []

def traverse(c=3):
    if c == 0:
        print "start"
        o = greenlet.getcurrent()
        print o
        print "mid"
        saved.append(o)
        print "switching .."
        r = o.parent.switch(5)
        print "... done with", r
        print "end"
    else:
        traverse(c-1)
    return 3

g = greenlet.greenlet(traverse)
x = g.switch()
print "x", x
print saved
y = saved[0].switch()
print "y", y
