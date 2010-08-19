def f1(x):
    return x * 2

def f2(y, f):
    return f(y + 7)

print f2(43, f1)


