"""Differential native font metrics, saved-text lookup and display-only wrapping."""
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import unittest
import zipfile
import sys
import re

import test_arm32_relocations as arm
import test_framebuffer_copy as frame
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from hl5_vfs import Vfs
from hl5_text import parse_dat
from english_layout import COLORS

STAGE=ROOT/'work/runner-final-1.0.0/app/src/main/cpp'
if not STAGE.exists():STAGE=ROOT/'work/runner-target/app/src/main/cpp'


@unittest.skipUnless(arm.unicorn and arm.COMPILERS and STAGE.exists(),'Requires local target/font stage and NDK')
class FontBridgeTests(unittest.TestCase):
    execute=frame.NativeFramebufferCopyTests.execute
    @classmethod
    def setUpClass(cls):
        temp=tempfile.TemporaryDirectory(prefix='font-native-',dir=ROOT/'work');cls.addClassCleanup(temp.cleanup)
        directory=Path(temp.name);source=directory/'font.cpp'
        source.write_text('''#include "font_metrics.h"
#include "render_text_data.h"
extern "C" __attribute__((visibility("default"))) unsigned run_font(unsigned op,const unsigned* a){
    const auto colors=reinterpret_cast<const uint8_t*>(a[7]);
    if(op==0)return hl5::font_width(reinterpret_cast<const uint8_t*>(a[0]),a[1],a[2],a[3],a[4],a[5],colors);
    if(op==1)return hl5::font_line_bytes(reinterpret_cast<const uint8_t*>(a[0]),a[1],a[2],a[3],a[6],a[4],a[5],colors);
    if(op==2){hl5::font_wrap_spaces(reinterpret_cast<char*>(a[0]),a[1],a[3],a[4]+1,colors);return a[0];}
    return reinterpret_cast<unsigned>(hl5::display_translation(reinterpret_cast<const char*>(a[0])));
}''',encoding='ascii')
        compiler=arm.COMPILERS[0];library=directory/'font.so'
        subprocess.run([str(compiler),'--target=armv7a-linux-androideabi26','--sysroot='+str(compiler.parents[1]/'sysroot'),
            '-shared','-fPIC','-marm','-std=c++17','-O3','-fno-exceptions','-fno-rtti','-fno-stack-protector',
            '-fno-jump-tables','-nostdlib','-Wl,-Bsymbolic','-Wl,--no-undefined','-I'+str(STAGE),str(source),'-o',str(library)],check=True,capture_output=True)
        cls.helper=library.read_bytes();cls.helper_entry=arm.elf_symbols(cls.helper)['run_font'].address+0x10000000
        with zipfile.ZipFile(ROOT/'inputs/hl5-original-01.01.00.apk') as apk:cls.target=apk.read('lib/armeabi/libHeroesLore5.so')
        symbols=arm.elf_symbols(cls.target)
        cls.width=symbols['_ZN5BFont8GetWidthEPciii'].address+0x40000000
        cls.line=symbols['_ZN5BFont19GetByteLenPrintableEPciiii'].address+0x40000000
    def setUp(self):
        uc=arm.unicorn.Uc(arm.unicorn.UC_ARCH_ARM,arm.unicorn.UC_MODE_ARM)
        for raw,bias in ((self.helper,0x10000000),(self.target,0x40000000)):
            h=struct.unpack_from('<16sHHIIIIIHHHHHH',raw);programs=[struct.unpack_from('<8I',raw,h[5]+i*h[9]) for i in range(h[10])];loads=[p for p in programs if p[0]==1]
            uc.mem_map(bias,(max(p[2]+p[5] for p in loads)+4095)&~4095)
            for _,offset,address,_,size,_,_,_ in loads:uc.mem_write(bias+address,raw[offset:offset+size])
        uc.mem_map(0x50000000,65536);uc.mem_map(0x70000000,4096);uc.mem_map(0x30000000,4096)
        uc.mem_write(0x50000018,COLORS.encode());uc.mem_write(0x50000080,COLORS.encode());self.uc=uc
    def policy(self,op,raw,start=0,limit=126,aw=5,kw=9,lines=1):
        self.uc.mem_write(0x50001000,raw+b'\0\0')
        args=[0x50001000,len(raw),start,limit,aw,kw,lines,0x50000080]
        self.uc.mem_write(0x50000100,struct.pack('<8I',*(x&0xffffffff for x in args)))
        return self.execute(self.helper_entry,[op,0x50000100])
    def test_width_and_line_helpers_match_original_arm_with_offsets_and_styles(self):
        rng=random.Random(125);samples=[b'  ABC }DEF| GHI;Next',bytes.fromhex('b1cdb0a120b8dec0cec4f9bdbac6ae')]
        samples += [''.join(rng.choice('ABCDEFG abc 123|};') for _ in range(rng.randint(1,140))).encode() for _ in range(28)]
        for raw in samples:
            for aw,kw in ((5,9),(4,8),(6,10)):
                self.uc.mem_write(0x50000046,bytes([kw,aw]))
                for limit in (54,114,126,220,476):
                    start=rng.randrange(len(raw));lines=rng.choice((1,2,3))
                    self.policy(0,raw,start,limit,aw,kw,lines)
                    expected=self.execute(self.width,[0x50000000,0x50001000,len(raw),start,limit])
                    self.assertEqual(self.policy(0,raw,start,limit,aw,kw,lines),expected,(raw,start,limit,aw,kw,lines))
                    expected=self.execute(self.line,[0x50000000,0x50001000,len(raw),start,limit,lines])
                    self.assertEqual(self.policy(1,raw,start,limit,aw,kw,lines),expected,(raw,start,limit,aw,kw,lines))
    def test_cached_korean_quest_is_translated_without_modifying_original_bytes(self):
        with zipfile.ZipFile(ROOT/'inputs/hl5-original-01.01.00.apk') as apk:v=Vfs(apk.read('assets/data.vfs.mp3'))
        original=parse_dat('c/csv/quest_0.dat',v.by_name['c/csv/quest_0.dat'].data)[2].fields[0].split(b'\0')[0]
        pointer=self.policy(3,original);self.assertNotEqual(pointer,0)
        result=bytearray()
        while True:
            value=bytes(self.uc.mem_read(pointer+len(result),1))
            if value==b'\0':break
            result.extend(value)
        self.assertEqual(bytes(result),b'Returning Home')
        self.assertEqual(bytes(self.uc.mem_read(0x50001000,len(original))),original)
        self.assertEqual(self.policy(3,b'not a translated label'),0)

    def test_actual_saved_quest_path_localizes_description_before_line_slicing(self):
        from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
        # Exercise the target's real QuestMgr -> DrawTextLine -> DrawText path.
        # Only libc and the final pixel draw are stubbed; pagination executes ARM.
        symbols=arm.elf_symbols(self.target);uc=self.uc
        hook_source=(ROOT/'tools/runtime/font_bridge.h').read_text()
        rules={n:(int(p),int(w)) for n,p,w in re.findall(r'\{"([^"]+)",(\d+),(-?\d+),-?\d+,0\}',hook_source)}
        line_symbol='_ZN5BFont12DrawTextLineEiiiiiPcii'
        self.assertIn(line_symbol,rules)
        helper=FontBridgeTests('runTest');helper.setUp()
        with zipfile.ZipFile(ROOT/'inputs/hl5-original-01.01.00.apk') as apk:v=Vfs(apk.read('assets/data.vfs.mp3'))
        original=parse_dat('c/csv/quest_0.dat',v.by_name['c/csv/quest_0.dat'].data)[2].fields[1]
        quest=bytearray(0x240);quest[28:28+len(original)+1]=original+b'\0'
        uc.mem_write(0x50006000,bytes(quest));uc.mem_write(0x50000046,b'\x09\x05')
        uc.mem_write(0x50004000,struct.pack('<I',0x50005000))
        uc.mem_write(0x5000f000,struct.pack('<II',0x50004000,0x50000000))
        fn=symbols['_ZN8QuestMgr15DrawQuestStringEssss'];bias=0x40000000
        got=bias+fn.address+24+struct.unpack_from('<I',fn.data,len(fn.data)-16)[0]
        uc.mem_write(got+struct.unpack_from('<I',fn.data,len(fn.data)-12)[0],struct.pack('<I',0x5000f000))
        uc.mem_write(got+struct.unpack_from('<I',fn.data,len(fn.data)-8)[0],struct.pack('<I',0x5000f004))
        chunks=[];translated=[]
        def cstring(machine,pointer):
            result=bytearray()
            for i in range(4096):
                ch=bytes(machine.mem_read(pointer+i,1))
                if ch==b'\0':return bytes(result)
                result.extend(ch)
            self.fail('Unterminated text')
        def args(count):
            values=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
            return values+list(struct.unpack('<'+'I'*(count-4),uc.mem_read(uc.reg_read(UC_ARM_REG_SP),(count-4)*4)))
        def callback(machine,address,size,data):
            if address==bias+symbols[line_symbol].address:
                values=args(9);pointer_index,width_index=rules[line_symbol]
                raw=cstring(uc,values[pointer_index]);self.assertEqual(raw,original)
                pointer=helper.policy(3,raw);self.assertNotEqual(pointer,0)
                english=cstring(helper.uc,pointer);helper.policy(2,english,limit=values[width_index])
                english=cstring(helper.uc,0x50001000);translated.append(english)
                uc.mem_write(0x50009000,english+b'\0')
                uc.mem_write(uc.reg_read(UC_ARM_REG_SP)+(pointer_index-4)*4,struct.pack('<I',0x50009000))
                return
            r0,r1,r2=(uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2))
            if address==0x400301b8:uc.reg_write(UC_ARM_REG_R0,len(cstring(uc,r0)))
            elif address==0x40030308:uc.mem_write(r0,bytes([r1&255])*r2)
            elif address==0x40030110:uc.mem_write(r0,bytes(uc.mem_read(r1,r2)))
            else:chunks.append(cstring(uc,args(7)[5]))
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        for address in (bias+symbols[line_symbol].address,0x400301b8,0x40030308,0x40030110,
                        bias+symbols['_ZN5BFont8DrawTextEiiiiPci'].address):
            uc.hook_add(arm.unicorn.UC_HOOK_CODE,callback,begin=address,end=address)
        for scroll in (0,2):self.execute(bias+fn.address,[0x50006000,20,80,138,scroll])
        self.assertEqual(len(chunks),2)
        self.assertTrue(chunks[0].startswith(b'Until Kaze reaches out,'))
        self.assertTrue(chunks[1]);self.assertTrue(all(b<128 for c in chunks for b in c))
        self.assertNotEqual(chunks[0],chunks[1])
        self.assertEqual(bytes(uc.mem_read(0x50006000,len(quest))),bytes(quest))
    def test_dynamic_wrap_uses_box_width_and_only_replaces_spaces(self):
        raw=b'Hmm... A building like the }Tower{ in the center of the capital is suspicious indeed...'
        outputs=[]
        for width in (220,384,476,504):
            self.policy(2,raw,limit=width)
            wrapped=bytes(self.uc.mem_read(0x50001000,len(raw)));outputs.append(wrapped)
            self.assertEqual(wrapped.replace(b';',b' '),raw)
        self.assertGreater(outputs[0].count(b';'),outputs[-1].count(b';'))
        self.assertGreater(outputs[-1].find(b';'),outputs[0].find(b';'))


if __name__=='__main__':unittest.main()
