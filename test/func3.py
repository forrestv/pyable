def get_new_x(cur_x):
    return cur_x + 1

x = 3
y = -x*2

print x
print y

while x < 10000000:
    x = get_new_x(x)

print y
print x
