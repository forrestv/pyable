#!/usr/bin/python

from __future__ import division

import glob
import subprocess

tests = []

for item in glob.glob("test/*.py"):
    a = subprocess.Popen(["python", item], bufsize=2**16, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    b = subprocess.Popen(["python", "main.py", item], bufsize=2**16, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tests.append((item, a, b))

for item, a, b in tests:
    #print "waiting on", item
    a, _ = a.communicate()
    b, _ = b.communicate()
    
    if a == b:
        pass
    else:
        print "FAIL", item
