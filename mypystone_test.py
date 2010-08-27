def a():
  pass

import _pyable

list = _pyable.type("list", None, None)

def list___init__(self, iterable=None):
    self._used = 0
    self._allocated = 0
    if iterable is not None:
        for item in iterable:
            self.append(item)
list.__init__ = list___init__

def list___len__(self):
    return self._used
list.__len__ = list___len__

def list__grow(self):
    new_allocated = self._allocated * 2 + 1
    import _pyable
    new_store = _pyable.raw(4 * new_allocated)
    if self._used:
        new_store.copy_from(self._store, 4 * self._used)
    self._allocated = new_allocated
    self._store = new_store
list._grow = list__grow

def list_append(self, item):
    if self._used + 1 > self._allocated:
         self._grow()
    self._store.store_object(4 * self._used, item)
    self._used += 1
    return self
list.append = list_append

def list___getitem__(self, index):
    if index < 0:
        index += self._used
    if index >= self._used:
        return None
    return self._store.load_object(4 * index)
list.__getitem__ = list___getitem__

def list___setitem__(self, index, item):
    if index < 0:
        index += self._used
    if index >= self._used:
        return None
    self._store.store_object(4 * index, item)
list.__setitem__ = list___setitem__

def list_pop(self, index=-1):
    if index < 0:
        index += self._used
    if index < 0 or index >= self._used:
        return None
    res = self._store.load_object(4 * index)
    i = 4 * index
    while i + 4 < 4 * self._used:
        self._store[i] = self._store[i + 4]
        t += 1
    self._used -= 1
    return res
list.pop = list_pop

def list___mul__(self, other):
    print "other", other, self._used, 1 < self._used
    new = self.__class__()
    i = 0
    while i < other:
        j = 0
        print i
        print "XXX", 1 < self._used
        while j < self._used:
            #a = self[j]
        #b = new.append
            print j < self._used, "should be 1"
            print new is self
            new.append(self[j])
            j += 1
        i += 1
    print "other2"
    return new
list.__mul__ = list___mul__

def len(o):
    return o.__len__()

_pyable.set_list_impl(list)

#del list

def nothing(x):
    return x

def map(f, iterable):
    print "map"
    res = []
    i = 0
    j = iterable.__len__()
    while i < j:
        res.append(f(iterable[i]))
        i += 1
    print "end map"
    return res

def chr(i):
    return "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x20\x21\x22\x23\x24\x25\x26\x27\x28\x29\x2a\x2b\x2c\x2d\x2e\x2f\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x3a\x3b\x3c\x3d\x3e\x3f\x40\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f\x60\x61\x62\x63\x64\x65\x66\x67\x68\x69\x6a\x6b\x6c\x6d\x6e\x6f\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79\x7a\x7b\x7c\x7d\x7e\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff"[i]

def ord(i):
    return i.__ord__()

print 1

LOOPS = 100000

__version__ = "1.1"

Ident1, Ident2, Ident3, Ident4, Ident5 = 1, 2, 3, 4, 5

print 2

class Record:

    def __init__(self, PtrComp = None, Discr = 0, EnumComp = 0,
                       IntComp = 0, StringComp = 0):
        self.PtrComp = PtrComp
        self.Discr = Discr
        self.EnumComp = EnumComp
        self.IntComp = IntComp
        self.StringComp = StringComp

    def copy(self):
        return Record(self.PtrComp, self.Discr, self.EnumComp,
                      self.IntComp, self.StringComp)

print 3

TRUE = 1
FALSE = 0

IntGlob = 0
BoolGlob = FALSE
Char1Glob = '\0'
Char2Glob = '\0'

print 6

Array1Glob = [0]*51

print 5

Array2Glob = map(lambda x: map(nothing, x), [Array1Glob]*51)
PtrGlb = None
PtrGlbNext = None

print 4

def Proc0(loops):
    global IntGlob
    global BoolGlob
    global Char1Glob
    global Char2Glob
    global Array1Glob
    global Array2Glob
    global PtrGlb
    global PtrGlbNext

    PtrGlbNext = Record()
    PtrGlb = Record()
    PtrGlb.PtrComp = PtrGlbNext
    PtrGlb.Discr = Ident1
    PtrGlb.EnumComp = Ident3
    PtrGlb.IntComp = 40
    PtrGlb.StringComp = "DHRYSTONE PROGRAM, SOME STRING"
    String1Loc = "DHRYSTONE PROGRAM, 1'ST STRING"
    Array2Glob[8][7] = 10

    i = 0
    while i < loops:
        print "loop", i
        Proc5()
        Proc4()
        IntLoc1 = 2
        IntLoc2 = 3
        String2Loc = "DHRYSTONE PROGRAM, 2'ND STRING"
        EnumLoc = Ident2
        BoolGlob = not Func2(String1Loc, String2Loc)
        while IntLoc1 < IntLoc2:
            IntLoc3 = 5 * IntLoc1 - IntLoc2
            IntLoc3 = Proc7(IntLoc1, IntLoc2)
            IntLoc1 = IntLoc1 + 1
        Proc8(Array1Glob, Array2Glob, IntLoc1, IntLoc3)
        PtrGlb = Proc1(PtrGlb)
        CharIndex = 'A'
        while CharIndex <= Char2Glob:
            if EnumLoc == Func1(CharIndex, 'C'):
                EnumLoc = Proc6(Ident1)
            CharIndex = chr(ord(CharIndex)+1)
        IntLoc3 = IntLoc2 * IntLoc1
        IntLoc2 = IntLoc3 / IntLoc1
        IntLoc2 = 7 * (IntLoc3 - IntLoc2) - IntLoc1
        IntLoc1 = Proc2(IntLoc1)
        #print IntLoc2
        i += 1

def Proc1(PtrParIn):
    PtrParIn.PtrComp = NextRecord = PtrGlb.copy()
    PtrParIn.IntComp = 5
    NextRecord.IntComp = PtrParIn.IntComp
    NextRecord.PtrComp = PtrParIn.PtrComp
    NextRecord.PtrComp = Proc3(NextRecord.PtrComp)
    if NextRecord.Discr == Ident1:
        NextRecord.IntComp = 6
        NextRecord.EnumComp = Proc6(PtrParIn.EnumComp)
        NextRecord.PtrComp = PtrGlb.PtrComp
        NextRecord.IntComp = Proc7(NextRecord.IntComp, 10)
    else:
        PtrParIn = NextRecord.copy()
    NextRecord.PtrComp = None
    return PtrParIn

def Proc2(IntParIO):
    IntLoc = IntParIO + 10
    while 1:
        if Char1Glob == 'A':
            IntLoc = IntLoc - 1
            IntParIO = IntLoc - IntGlob
            EnumLoc = Ident1
        if EnumLoc == Ident1:
            break
    return IntParIO

def Proc3(PtrParOut):
    global IntGlob

    if PtrGlb is not None:
        PtrParOut = PtrGlb.PtrComp
    else:
        IntGlob = 100
    PtrGlb.IntComp = Proc7(10, IntGlob)
    return PtrParOut

def Proc4():
    global Char2Glob

    BoolLoc = Char1Glob == 'A'
    BoolLoc = BoolLoc or BoolGlob
    Char2Glob = 'B'

def Proc5():
    global Char1Glob
    global BoolGlob

    Char1Glob = 'A'
    BoolGlob = FALSE

def Proc6(EnumParIn):
    EnumParOut = EnumParIn
    if not Func3(EnumParIn):
        EnumParOut = Ident4
    if EnumParIn == Ident1:
        EnumParOut = Ident1
    elif EnumParIn == Ident2:
        if IntGlob > 100:
            EnumParOut = Ident1
        else:
            EnumParOut = Ident4
    elif EnumParIn == Ident3:
        EnumParOut = Ident2
    elif EnumParIn == Ident4:
        pass
    elif EnumParIn == Ident5:
        EnumParOut = Ident3
    return EnumParOut

def Proc7(IntParI1, IntParI2):
    IntLoc = IntParI1 + 2
    IntParOut = IntParI2 + IntLoc
    return IntParOut

def Proc8(Array1Par, Array2Par, IntParI1, IntParI2):
    global IntGlob

    IntLoc = IntParI1 + 5
    Array1Par[IntLoc] = IntParI2
    Array1Par[IntLoc+1] = Array1Par[IntLoc]
    Array1Par[IntLoc+30] = IntLoc
    IntIndex = IntLoc
    while IntIndex < IntLoc+2:
        Array2Par[IntLoc][IntIndex] = IntLoc
        IntIndex += 1
    Array2Par[IntLoc][IntLoc-1] = Array2Par[IntLoc][IntLoc-1] + 1
    Array2Par[IntLoc+20][IntLoc] = Array1Par[IntLoc]
    IntGlob = 5

def Func1(CharPar1, CharPar2):
    CharLoc1 = CharPar1
    CharLoc2 = CharLoc1
    if CharLoc2 != CharPar2:
        return Ident1
    else:
        return Ident2

def Func2(StrParI1, StrParI2):
    IntLoc = 1
    while IntLoc <= 1:
        if Func1(StrParI1[IntLoc], StrParI2[IntLoc+1]) == Ident1:
            CharLoc = 'A'
            IntLoc = IntLoc + 1
    if CharLoc >= 'W' and CharLoc <= 'Z':
        IntLoc = 7
    if CharLoc == 'X':
        return TRUE
    else:
        if StrParI1 > StrParI2:
            IntLoc = IntLoc + 7
            return TRUE
        else:
            return FALSE

def Func3(EnumParIn):
    EnumLoc = EnumParIn
    if EnumLoc == Ident3: return TRUE
    return FALSE
print "ahh"
Proc0(LOOPS)
