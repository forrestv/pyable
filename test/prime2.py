x = 1010460

i = 2

#print -1

while i < 10000000:
    #print i
    #print -2
    #if i % 2 == 0:
    #    print -1000 - i
    while x % i == 0:
        #print -3
        print i
        #print -4
        x //= i
        #print -5
    i += 1
    #print -6
    #i += 1
    #print -7
#print -8
print x
