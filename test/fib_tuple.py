a = b = 1

while a < 1000000000000000:
    print a
    print b
    print (a, b)[0]
    print (a, b)[1]
    print (b, a)[1]
    print (b, a)[0]
    a, b = b, a + b
    print -1
