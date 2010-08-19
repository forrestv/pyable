import _pyable

list = _pyable.type("list", None, None)

def list___init__(self, iterable=None):
    self._used = 0
    self._allocated = 0
    if iterable is not None:
        for item in iterable:
            self.append(item)
list.__init__ = list___init__

def list___len__(self):
    return self._used
list.__len__ = list___len__

def list__grow(self):
    new_allocated = self._allocated * 2 + 1
    import _pyable
    new_store = _pyable.raw(4 * new_allocated)
    if self._used:
        new_store.copy_from(self._store, 4 * self._used)
    self._allocated = new_allocated
    self._store = new_store
list._grow = list__grow

def list_append(self, item):
    if self._used + 1 > self._allocated:
         self._grow()
    self._store.store_object(4 * self._used, item)
    self._used += 1
    return self
list.append = list_append

def list___getitem__(self, index):
    if index < 0:
        index += self._used
    if index >= self._used:
        return None
    return self._store.load_object(4 * index)
list.__getitem__ = list___getitem__

def list_pop(self, index=-1):
    if index < 0:
        index += self._used
    if index < 0 or index >= self._used:
        return None
    res = self._store.load_object(4 * index)
    i = 4 * index
    while i + 4 < 4 * self._used:
        self._store[i] = self._store[i + 4]
        t += 1
    self._used -= 1
    return res
list.pop = list_pop

def len(o):
    return o.__len__()

_pyable.set_list_impl(list)


x = list()
x = list()

x.append("first")
print x[0]

i = 0
while i < 10:
    x.append(5)
    i += 1
x.append("hello!")
i = 0
while i < 10:
    x.append(6)
    i += 1

print x[0]
print x[10001]

print "after"

i = 0
while i < 100:
    print x.pop()
    i += 1

print "arr", len(x)

if 1: pass

y = [1, 2, 3]

print "test"

if 1: pass

print "bar", y[0]
print y[1]
print y[2]
