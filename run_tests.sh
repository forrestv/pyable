for X in test/* ; do
  echo $X
  cmp <(python $X) <(python asttest.py $X) && echo GOOD || echo BAD
  sleep 1
  echo
  echo
  echo
  echo
done
