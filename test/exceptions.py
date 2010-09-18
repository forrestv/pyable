try:
    raise Exception()
    print "tra-la-la"
except Exception:
    print "ahh!"
else:
    print "else!"
finally:
    print "finally!"
print "end"
