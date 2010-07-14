springboarders = []
def get_current():
    return springboarders[-1]

def springboarder(root):
    def f(*args, **kwargs):
        stack = [root(*args, **kwargs)]
        while True:
            try:
                v = stack[-1].next()
            except StopIteration:
                stack.pop()
                if not stack:
                    return
                continue
            if v[0] is None:
                if len(v) == 1:
                    value = None
                else:
                    value, = v[1:]
                r = yield value
            else:
                if len(v) == 1:
                    func, args, kwargs = v[0], (), {}
                elif len(v) == 2:
                    func, args, kwargs = v[0], v[1], {}
                else:
                    func, args, kwargs = v
                stack.append(func(*args, **kwargs))
    return f

@springboarder
def compile(t):
    yield compile2, (t,)

def compile2(t):
    yield None, t
    return
    if t == 0:
        yield None, 5
    else:
        yield compile2, (t - 1,)

x = compile(100)
for y in x:
    print y
