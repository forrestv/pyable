def merge(seqs):
    #print seqs
    seqs = map(list, seqs)
    res = []
    while True:
      nonemptyseqs = [seq for seq in seqs if seq]
      if not nonemptyseqs:
          return res
      for seq in nonemptyseqs: # find merge candidates among seq heads
          cand = seq[0]
          nothead = [s for s in nonemptyseqs if cand in s[1:]]
          if nothead:
              cand = None # reject candidate
          else:
              break
      if not cand:
          raise "Inconsistent hierarchy"
      res.append(cand)
      for seq in nonemptyseqs: # remove cand
          if seq[0] == cand:
              del seq[0]

def mro(C, get_bases):
    "Compute the class precedence list (mro) according to C3"
    res = merge([[C]] + [mro(x, get_bases) for x in get_bases(C)] + [list(get_bases(C))])
    #print C, "->", res
    return res

if __name__ == "__main__":
    d = {
        'object': [],
        'A': ['object'],
        'B': ['A'],
        'C': ['object'],
        'D': ['C'],
        'E': ['C'],
        'F': ['B', 'D', 'E'],
    }
    print mro('F', lambda n: d[n])
        

