a = b = 1

while a < 100000:
    print a
    print (a, b)[0], (a, b)[1], (b, a)[1], (b, a)[0]
    a, b = b, a + b
