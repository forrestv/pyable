oldrange = range

def range(start, end=None, step=1):
    assert step
    if end is None:
        end = start
        start = 0
    result = []
    i = start
    while (i < end and step > 0) or (i > end and step < 0):
        result.append(i)
        i += step
    return result

import random

for i in xrange(1000):
    a = random.randrange(-1000, 1000)
    assert range(a) == oldrange(a)

for i in xrange(1000):
    a = random.randrange(-1000, 1000)
    b = random.randrange(-1000, 1000)
    assert range(a, b) == oldrange(a, b)

for i in xrange(1000):
    a = random.randrange(-1000, 1000)
    b = random.randrange(-1000, 1000)
    c = random.randrange(-1000, 1000)
    while c == 0:
        c = random.randrange(-1000, 1000)
    assert range(a, b, c) == oldrange(a, b, c)
