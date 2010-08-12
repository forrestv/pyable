def add_one(x):
    print "add_one", x
    return x + 1

def add_two(x):
    print "add_two", x
    return x + 1

add_two(add_one(5))

#add_one(add_one(5))
