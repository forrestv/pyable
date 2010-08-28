def ord(x):
    return x.__ord__()

a = "hello world"

print a

print a[0]

print a[3]

print ord(a[5])
print ord(a[7])
print ord(a[2])


print ord("aaaaaaaaaaaaaaaaaaaaaaaaaaaa")
print ord("a")
