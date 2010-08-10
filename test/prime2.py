x = 1010460

i = 2
while i < 100000000:
    while x % i == 0:
        print i
        x //= i
    i += 1

if x != 1:
    print x
