x = 996570036

i = 2
while i*i < x:
    while x % i == 0:
        print i
        x //= i
    i += 1

if x != 1:
    print x
