print "a"

def add_one(x):
    return x + 1

print "b"

def add_two(x):
    return add_one(add_one(x))

print "c"

print add_two(40)

print "d"
