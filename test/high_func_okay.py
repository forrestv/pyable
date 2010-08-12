def add_one(x):
    print "add_one", x
    return x + 1

def add_two(x):
    print "add_two", x
    return x + 1

x = add_one(5)
add_two(x)

#add_one(add_one(5))
