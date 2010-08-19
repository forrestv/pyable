import _pyable

print (1 is 2) + (2 is not 3) * 2 + (0 is None) * 4 + (None is None) * 8 + (None is not 1) * 16 + (None is not None) * 32 + (None is _pyable) * 64
