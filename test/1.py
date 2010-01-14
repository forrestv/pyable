x = 0
while x < 1000000:
    x += 1
print x

#block0
#    x = 0
#    jmp block1

#block1
#    if x < 100000:
#        jmp block2
#    jmp block3

#block2
#    x += 1
#    jmp block1

#block3
#    print x
#    ret


#while ->

#    ...
#    jmp blocka

#blocka
#    if COND:
#        jmp blockb
#    jmp blockc

#blockb
#    BODY
#    jmp blocka

#blockc
#    ...

#pass around a block, adding on to it, making new ones

#def while(block):
#    blocka = Block()
#    blockb = Block()
#    blockc = Block()
#    
#    block.add(jmp(blocka))
#    
#    blocka.add(if(cond) jmp(blockb))
#    blobka.add(jmp(blockc))
#    
#    body(blockb, continue=jmp(blocka), break=jmp(blockc))
#    blockb.add(jmp(blocka))
#    
#    return blockc
