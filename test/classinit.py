class x(object):
    def __init__(self, y):
        print y
        self.y = y

print 1
z = x()
print 2
print z
print z.y
