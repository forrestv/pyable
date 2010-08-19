#!/bin/bash

for X in test/*.py ; do
  cmp <(python $X 2>&1) <(python main.py $X 2>&1) >/dev/null || echo $X &
done

sleep 2
