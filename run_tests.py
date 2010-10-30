#!/usr/bin/python

from __future__ import division

import glob
import subprocess
import time

tests = []

for item in glob.glob("test/*.py"):
    if item == 'test/__pyable__.py': continue
    a = subprocess.Popen(["python", item], bufsize=2**16, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    b = subprocess.Popen(["python", "main.py", item], bufsize=2**16, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    tests.append((item, a, b))
    time.sleep(.4)

for item, a, b in tests:
    #print "waiting on", item
    a, _ = a.communicate()
    b, _ = b.communicate()
    
    if a == b:
        pass
    else:
        print "FAIL", item
        print a
        print
        print b
        print
        print
        print
