# Copyright (c) 2006-2009 The Trustees of Indiana University.                   
# All rights reserved.                                                          
#                                                                               
# Redistribution and use in source and binary forms, with or without            
# modification, are permitted provided that the following conditions are met:   
#                                                                               
# - Redistributions of source code must retain the above copyright notice, this 
#   list of conditions and the following disregisters.claimer.                            
#                                                                               
# - Redistributions in binary form must reproduce the above copyright notice,   
#   this list of conditions and the following disregisters.claimer in the documentation   
#   and/or other materiregisters.als provided with the distribution.                      
#                                                                               
# - Neither the Indiana University nor the names of its contributors may be used
#   to endorse or promote products derived from this software without specific  
#   prior written permission.                                                   
#                                                                               
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"   
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE     
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE   
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL    
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR    
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER    
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.          

import array

import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
import corepy.arch.x86_64.platform as platform
from corepy.arch.x86_64.lib.memory import MemRef
import corepy.lib.extarray as extarray
import corepy.arch.x86_64.lib.util as util

def Test():
    program = platform.Program()
    code = program.get_stream()
    processor = platform.Processor()
    params = platform.ExecParams()
    params.p1 = 3

    lbl1 = program.get_label("lbl1")
    lbl2 = program.get_label("lbl2")

    code.add(isa.xor(program.gp_return, program.gp_return))

    code.add(isa.cmp(program.gp_return, 1))
    code.add(isa.jne(lbl1))

    code.add(isa.ud2())
    code.add(isa.ud2())

    code.add(lbl1)
    code.add(isa.cmp(program.gp_return, 1))
    code.add(isa.je(lbl2))
    code.add(isa.add(program.gp_return, 12))
    code.add(lbl2)

    program.add(code)
    #program.print_code(pro = True, epi = True, hex = True) 
    ret = processor.execute(program, mode = 'int')
    print "ret", ret
    assert(ret == 12)

    program.reset()
    code.reset()

    code.add(isa.xor(program.gp_return, program.gp_return))

    code.add(isa.cmp(program.gp_return, 1))
    code.add(isa.jne(28))

    code.add(isa.ud2())
    code.add(isa.ud2())

    code.add(isa.cmp(program.gp_return, 1))
    code.add(isa.je(37))
    code.add(isa.add(program.gp_return, 12))

    program.add(code)
    program.print_code(hex = True, pro = True, epi = True) 
    ret = processor.execute(program)
    print "ret", ret
    assert(ret == 12)

    program.reset()
    code.reset()

    call_lbl = program.get_label("call_fn")

    code.add(isa.xor(program.gp_return, program.gp_return))
    code.add(isa.call(call_lbl))
    code.add(isa.jmp(program.lbl_epilogue))
    code.add(isa.mov(program.gp_return, 75))
    code.add(isa.mov(program.gp_return, 42))
    code.add(call_lbl)
    code.add(isa.mov(program.gp_return, 15))
    code.add(isa.ret())

    program.add(code)
    program.print_code()
    ret = processor.execute(program, mode = 'int')
    print "ret", ret
    assert(ret == 15)


    program.reset()
    code.reset()

    fwd_lbl = program.get_label("FORWARD")
    bck_lbl = program.get_label("BACKWARD")

    code.add(isa.xor(program.gp_return, program.gp_return))
    code.add(bck_lbl)
    code.add(isa.cmp(program.gp_return, 1))
    code.add(isa.jne(fwd_lbl))
    r_foo = program.acquire_register()
    for i in xrange(0, 65):
      code.add(isa.pop(r_foo))
    program.release_register(r_foo)
    code.add(fwd_lbl)

    program.add(code)
    ret = processor.execute(program, mode = 'int')
    print "ret", ret
    assert(ret == 0)


    program.reset()
    code.reset()

    loop_lbl = program.get_label("LOOP")
    out_lbl = program.get_label("OUT")
    skip_lbl = program.get_label("SKIP")

    code.add(isa.xor(program.gp_return, program.gp_return))
    code.add(loop_lbl)
    r_foo = program.acquire_register()
    for i in range(0, 1):
      for i in xrange(0, 24):
        code.add(isa.add(r_foo, MemRef(registers.rsp, 4)))

      code.add(isa.add(program.gp_return, 4))
      code.add(isa.cmp(program.gp_return, 20))
      code.add(isa.je(out_lbl))

      for i in xrange(0, 24):
        code.add(isa.add(r_foo, MemRef(registers.rsp, 4)))

      code.add(isa.cmp(program.gp_return, 32))
      code.add(isa.jne(loop_lbl))

    code.add(out_lbl)

    code.add(isa.jmp(skip_lbl))
    for i in xrange(0, 2):
      code.add(isa.add(r_foo, MemRef(registers.rsp, 4)))
    code.add(skip_lbl)

    program.release_register(r_foo)
    program.add(code)
    ret = processor.execute(program, mode = 'int')
    print "ret", ret
    assert(ret == 20)


    program.reset()
    code.reset()

    r_tmp = program.acquire_registers(2)

    loop_lbl = program.get_label("LOOP")
    else_lbl = program.get_label("ELSE")
    finish_lbl = program.get_label("finish")

    code.add(isa.mov(program.gp_return, 0))
    code.add(isa.mov(r_tmp[0], 0))

    code.add(loop_lbl)

    code.add(isa.add(program.gp_return, 1))
    code.add(isa.cmp(program.gp_return, 16))
    code.add(isa.jge(finish_lbl))

    code.add(isa.add(r_tmp[0], program.gp_return))
    code.add(isa.mov(r_tmp[1], r_tmp[0]))
    code.add(isa.and_(r_tmp[1], 0x1))
    code.add(isa.jnz(else_lbl))

    code.add(isa.add(r_tmp[0], 1))
    code.add(isa.jmp(loop_lbl))

    code.add(else_lbl)
    code.add(isa.add(r_tmp[0], r_tmp[1]))
    code.add(isa.jmp(loop_lbl))

    code.add(finish_lbl)
    code.add(isa.mov(program.gp_return, r_tmp[0]))

    program.release_registers(r_tmp)

    program.add(code)
    ret = processor.execute(program, mode = 'int')
    print "ret", ret
    assert(ret == 135)


    program.reset()
    code.reset()

    loop_lbl = program.get_label("LOOP")

    r_one = program.acquire_register()
    code.add(isa.xor(program.gp_return, program.gp_return))
    code.add(isa.xor(registers.rcx, registers.rcx))
    code.add(isa.mov(r_one, 1))

    code.add(loop_lbl)
    code.add(isa.inc(program.gp_return))
    code.add(isa.cmp(program.gp_return, 7))
    code.add(isa.cmove(registers.rcx, r_one))
    code.add(isa.jrcxz(loop_lbl))

    program.release_register(r_one)

    program.add(code)
    program.print_code(hex = True)
    ret = processor.execute(program, mode = 'int')
    print "ret", ret
    assert(ret == 7)


    program.reset()
    code.reset()

    r_tmp = program.acquire_register()
    code.add(isa.mov(program.gp_return, registers.rdi))
    code.add(isa.xor(r_tmp, r_tmp))
    code.add(isa.mov(r_tmp, -1))
    code.add(isa.mov(registers.cl, 1))
    code.add(isa.shld(program.gp_return, r_tmp, registers.cl))

    program.release_register(r_tmp)
    program.add(code)
    ret = processor.execute(program, params = params, mode = 'int')
    print "ret", ret
    assert(ret == 7)


    program.reset()
    code.reset()

    code.add(isa.add(registers.eax, 200))
    code.add(isa.xor(registers.eax, registers.eax))
    code.add(isa.add(registers.al, 32))
    code.add(isa.add(registers.bl, 32))
    code.add(isa.xor(registers.bl, registers.bl))
    code.add(isa.mov(registers.dil, registers.al))
    code.add(isa.add(registers.rdi, 0))
    code.add(isa.mov(registers.eax, registers.edi))
    code.add(isa.mov(registers.al, registers.dil))

    code.add(isa.imul(registers.ax, registers.ax, 4))
    code.add(isa.imul(registers.eax, registers.ebx, 10))
    code.add(isa.mov(registers.cx, 1232))
    code.add(isa.sub(registers.ax, registers.cx))
    code.add(isa.xor(registers.eax,registers.eax))
    code.add(isa.mov(registers.eax,registers.ebx))
    code.add(isa.clc())
    code.add(isa.rcl(registers.eax, 1))
    code.add(isa.rcr(registers.eax, 1))


    program.add(code)
    #ret = processor.execute(program, debug = True, params = params)
    id1 = processor.execute(program, params = params, mode = 'int', async = True)
    id2 = processor.execute(program, params = params, mode = 'int', async = True)
    ret = processor.execute(program, params = params, mode = 'int')
    print "Return main thread: %d" % (ret)
    assert(ret == 1280)
    ret = processor.join(id1)
    print "Return thread 1: %d" % (ret)
    assert(ret == 1280)
    ret = processor.join(id2)
    print "Return thread 2: %d" % (ret)
    assert(ret == 1280)


    program.reset()
    code.reset()

    code.add(isa.fldpi())
    code.add(isa.pxor(registers.xmm0, registers.xmm0))
    code.add(isa.fld1())
    code.add(isa.fadd(registers.st0, registers.st0))
    code.add(isa.fmulp())
    code.add(isa.fsin())
    code.add(isa.fcos())
    code.add(isa.fld1())
    code.add(isa.fyl2xp1())

    # x86_64 now uses registers.xmm0 to return floats, not registers.st0.  So here, just make room
    # on the stack, convert the FP result to an int and store it on the stack,
    # then pop it into rax, the int return register.
    code.add(isa.push(program.gp_return))
    code.add(isa.fistp(MemRef(registers.rsp)))
    code.add(isa.pop(program.gp_return))

    program.add(code)
    program.print_code(hex = True)
    ret = processor.execute(program, params = params, mode = 'int')
    assert(ret == 1)
    print "Return main thread: %d" % (ret)


    program.reset()
    code.reset()

    lbl_ok = program.get_label("OK")
    code.add(isa.emms())
    code.add(isa.movd(registers.xmm0, registers.edi))
    code.add(isa.mov(registers.ebx, registers.edi))

    code.add(isa.cmp(registers.ebx, 3))
    code.add(isa.je(lbl_ok))
    code.add(isa.movd(registers.eax, registers.xmm0))
    code.add(isa.cmp(registers.eax, 3))
    code.add(isa.je(lbl_ok))
    code.add(isa.ud2())

    code.add(lbl_ok)
    code.add(isa.xor(registers.eax, registers.eax))
    code.add(isa.movd(registers.xmm1, registers.ebx))
    code.add(isa.paddq(registers.xmm0, registers.xmm1))
    code.add(isa.pextrw(registers.ecx, registers.xmm0, 0))
    code.add(isa.pxor(registers.mm1, registers.mm1))
    code.add(isa.pinsrw(registers.mm1, registers.ecx, 0))
    code.add(isa.movq2dq(registers.xmm0, registers.mm1))
    code.add(isa.movdq2q(registers.mm2, registers.xmm0))
    code.add(isa.movd(registers.edx,registers.mm2))
    code.add(isa.movd(registers.xmm5,registers.edx))
    code.add(isa.movd(registers.ecx, registers.xmm5))
    code.add(isa.pxor(registers.xmm6, registers.xmm6))
    code.add(isa.pinsrw(registers.xmm6, registers.ecx, 0))
    code.add(isa.movd(registers.eax, registers.xmm6))

    program.add(code)
    program.print_code(hex = True)
    ret = processor.execute(program, params = params, mode = 'int')
    print "Return main thread: %d" % (ret)
    assert(ret == 6)


    program.reset()
    code.reset()

    code.add(isa.mov(registers.edx, 0x1234))
    code.add(isa.mov(registers.eax, 0xFFFF))
    code.add(isa.xchg(registers.edx, registers.eax))

    program.add(code)
    program.print_code(hex = True)
    ret = processor.execute(program, params = params)
    print "ret:", ret
    assert(ret == 0x1234)


    program.reset()
    code.reset()

    code.add(isa.mov(program.gp_return, registers.rsp))
    code.add(isa.pushfq())
    code.add(isa.sub(program.gp_return, registers.rsp))
    code.add(isa.add(registers.rsp, program.gp_return))

    program.add(code)
    program.print_code(hex = True)
    ret = processor.execute(program, params = params)
    print "ret:", ret
    assert(ret == 8)


    program.reset()
    code.reset()

    data = extarray.extarray('H', xrange(0, 16))

    r_128 = program.acquire_register(reg_type = registers.XMMRegister)
    regs = program.acquire_registers(4)

    code.add(isa.mov(regs[0], data.buffer_info()[0]))
    code.add(isa.movaps(r_128, MemRef(regs[0], data_size = 128)))
    code.add(isa.pextrw(program.gp_return, r_128, 0))
    code.add(isa.pextrw(regs[1], r_128, 1))
    code.add(isa.pextrw(regs[2], r_128, 2))
    code.add(isa.pextrw(regs[3], r_128, 3))
    code.add(isa.shl(regs[1], 16))
    code.add(isa.shl(regs[2], 32))
    code.add(isa.shl(regs[3], 48))
    code.add(isa.or_(program.gp_return, regs[1]))
    code.add(isa.or_(program.gp_return, regs[2]))
    code.add(isa.or_(program.gp_return, regs[3]))

    program.release_register(r_128)
    program.release_registers(regs)

    program.add(code)
    program.print_code()
    ret = processor.execute(program, mode = 'int')
    print "ret %x" % ret
    assert(ret == 0x0003000200010000)


    program.reset()
    code.reset()

    util.load_float(code, registers.xmm0, 3.14159)

    program.add(code)
    ret = processor.execute(program, mode = 'fp')
    print "ret", ret
    assert(ret - 3.14159 < 0.00001)

    return

Test()

