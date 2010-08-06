a = b = 1

while a < 100000:
    print a
    print b
    #print (a, b)[0]
    #print (a, b)[1]
    #print (b, a)[1]
    #print (b, a)[0]
    c = b + a
    a = b
    b = c
    #a, b = b, a + b
    print c
    print
