x = 541410078285358631


while x % 2 == 0:
    print 2
    x //= 2

while x % 3 == 0:
    print 3
    x //= 3

i = 5

while i * i <= x:
    while x % i == 0:
        print i
        x //= i
    
    i += 2
    
    while x % i == 0:
        print i
        x //= i
    
    i += 4

if x != 1:
    print x

