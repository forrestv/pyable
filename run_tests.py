#!/usr/bin/python

import glob
import subprocess

for item in glob.glob("test/*.py"):
    a = subprocess.Popen(["python", item], bufsize=4096, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    b = subprocess.Popen(["python", "main.py", item], bufsize=4096, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    a, _ = a.communicate()
    b, _ = b.communicate()
    
    if a == b:
        pass
    else:
        print "FAIL", item
