class A(object):
    def go(self, n):
        return n + 2
    def other(self, m):
        return self.go(m)

class B(A):
    def go(self, k):
        return k - 2

a = A()
print a.go(5), a.other(7)
b = B()
print b.go(5), b.other(7)

