x = list()
x = list()

x.append("first")
print x[0]

i = 0
while i < 10:
    x.append(5)
    i += 1
x.append("hello!")
i = 0
while i < 10:
    x.append(6)
    i += 1

print x[0]
#print x[10001]

print "after"

i = 0
while i < 10:
    print x.pop()
    i += 1

print "arr", len(x)

if 1: pass

y = [1, 2, 3]

print "test"

if 1: pass

print "bar", y[0]
print y[1]
print y[2]
