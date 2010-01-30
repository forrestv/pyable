import corepy.arch.x86_64.isa as isa
import corepy.arch.x86_64.types.registers as registers
import corepy.arch.x86_64.platform as platform
from corepy.arch.x86_64.lib.memory import MemRef
import corepy.lib.extarray as extarray
import corepy.arch.x86_64.lib.util as util

program = platform.Program()
code = program.get_stream()

label1 = program.get_label("label1")
label2 = program.get_label("label2")

code.add(isa.mov(program.gp_return, 0))

code.add(lbl1)
code.add(isa.cmp(program.gp_return, 1000000))
code.add(isa.je(lbl2))
code.add(isa.jmp(lbl1))
code.add(lbl2)

program.add(code)

program.print_code(pro = True, epi = True, hex = True)

processor = platform.Processor()
ret = processor.execute(program, mode='int')
print "ret", ret