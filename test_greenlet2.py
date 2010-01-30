import greenlet

print dir(greenlet)

def traverse(c=3):
    if c == 0:
        print "start"
        o = greenlet.getcurrent()
        print o
        print "mid"
        o.switch(5)
        print "end"
    else:
        traverse(c-1)
    return 3

x=  traverse()
print x
