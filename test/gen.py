def xrange(start, end=None, step=1):
    assert step
    if end is None:
        end = start
        start = 0
    i = start
    while (i < end and step > 0) or (i > end and step < 0):
        yield i
        i += step


for i in xrange(10):
    print i
