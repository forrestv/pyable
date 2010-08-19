import _pyable

t1 = _pyable.raw(100)
t2 = _pyable.raw(200)

t1[50] = 4141
t2[100] = 50
t2[50] = 42

print t1[50]

print t2[100]


t1[0] = 42
t1.store_object(1, t2)

print

print t1[0]
#print t1[1]
#print t1[2]

t2.store_object(20, 43)

print t1.load_object(1).load_object(20)
