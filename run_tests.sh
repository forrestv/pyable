#!/bin/bash

for X in test/*.py ; do
  echo $X
  cmp <(python $X) <(python main.py $X) && echo GOOD || echo BAD
  echo
  echo
  echo
  echo
done
