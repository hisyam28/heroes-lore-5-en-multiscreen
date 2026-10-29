"""Byte-exact palette optimization versus the target's actual ARM implementation."""
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import unittest
import zipfile
import test_arm32_relocations as arm
import test_framebuffer_copy as frame

ROOT=Path(__file__).resolve().parents[1]
SYMBOL='_ZN7Graphic17ChangeBlendingPalEP8GbmImageihhhh'


@unittest.skipUnless(arm.unicorn and arm.COMPILERS,'Requires local NDK and Unicorn')
class PaletteBlendTests(unittest.TestCase):
    execute=frame.NativeFramebufferCopyTests.execute
    @classmethod
    def setUpClass(cls):
        temp=tempfile.TemporaryDirectory(prefix='palette-diff-',dir=ROOT/'work');cls.addClassCleanup(temp.cleanup)
        directory=Path(temp.name);source=directory/'palette.cpp';library=directory/'palette.so'
        source.write_text('''#include "raster_rgb565.h"
extern "C" __attribute__((visibility("default"))) unsigned run_palette(const unsigned* a){
    auto image=reinterpret_cast<const unsigned char*>(a[1]);
    auto palette=*reinterpret_cast<const unsigned*>(image+8);auto backup=*reinterpret_cast<const unsigned*>(image+16);
    hl5::palette_blend565(reinterpret_cast<uint16_t*>(palette),reinterpret_cast<const uint16_t*>(backup),image[1],
        a[2],a[4],a[5]&255,a[6]&255,*reinterpret_cast<const unsigned*>(0x4016a234),reinterpret_cast<const uint8_t*>(a[0]+0x6d+a[3]*1024));
    const_cast<unsigned char*>(image)[20]=1;return a[1];
}''',encoding='ascii')
        c=arm.COMPILERS[0]
        subprocess.run([str(c),'--target=armv7a-linux-androideabi26','--sysroot='+str(c.parents[1]/'sysroot'),'-shared','-fPIC','-marm','-std=c++17','-O3','-fno-exceptions','-fno-rtti','-fno-stack-protector','-nostdlib','-Wl,--no-undefined','-I'+str(ROOT/'tools/runtime'),str(source),'-o',str(library)],check=True,capture_output=True)
        cls.helper=library.read_bytes();cls.helper_entry=arm.elf_symbols(cls.helper)['run_palette'].address+0x10000000
        with zipfile.ZipFile(ROOT/'inputs/hl5-original-01.01.00.apk') as apk:cls.target=apk.read('lib/armeabi/libHeroesLore5.so')
        s=arm.elf_symbols(cls.target)[SYMBOL];cls.target_entry=s.address+0x40000000
        cls.got=0x40000000+s.address+28+struct.unpack_from('<I',s.data,len(s.data)-8)[0]+struct.unpack_from('<I',s.data,len(s.data)-4)[0]
    def setUp(self):
        uc=arm.unicorn.Uc(arm.unicorn.UC_ARCH_ARM,arm.unicorn.UC_MODE_ARM)
        for raw,bias in ((self.helper,0x10000000),(self.target,0x40000000)):
            h=struct.unpack_from('<16sHHIIIIIHHHHHH',raw);ps=[struct.unpack_from('<8I',raw,h[5]+i*h[9]) for i in range(h[10])];load=[p for p in ps if p[0]==1]
            uc.mem_map(bias,(max(p[2]+p[5] for p in load)+4095)&~4095)
            for _,off,address,_,size,_,_,_ in load:uc.mem_write(bias+address,raw[off:off+size])
        uc.mem_map(0x50000000,65536);uc.mem_map(0x70000000,4096);uc.mem_map(0x30000000,4096)
        uc.mem_write(self.got,struct.pack('<I',0x4016a234));self.uc=uc
    def test_palette_alpha_flags_modes_and_transparency_match_target(self):
        rng=random.Random(998);cases=0
        for mode in (0,1,7,15):
            table=bytes(rng.randrange(32) for _ in range(1024));self.uc.mem_write(0x50000000+0x6d+mode*1024,table);self.uc.mem_write(0x5000005c,b'\1')
            for alpha in (0,1,7,8,127,247,248,255):
                for flags in ((0,0),(1,0),(0,1),(1,1)):
                    for count in (0,16,255):
                        backup=struct.pack('<255H',*[rng.randrange(65536) for _ in range(255)])
                        current=bytes(rng.randrange(256) for _ in range(510))
                        skip=struct.unpack_from('<H',backup)[0];self.uc.mem_write(0x4016a234,struct.pack('<I',skip))
                        image=struct.pack('<BBHHHIII',8,count,8,8,0,0x50009000,0x5000a000,0x50008000)+b'\0\0\0\0'
                        self.uc.mem_write(0x50007000,image);self.uc.mem_write(0x50008000,backup);self.uc.mem_write(0x50009000,current)
                        args=[0x50000000,0x50007000,rng.getrandbits(32),mode,alpha,*flags]
                        result=self.execute(self.target_entry,args);expected=bytes(self.uc.mem_read(0x50009000,510));expected_image=bytes(self.uc.mem_read(0x50007000,len(image)))
                        self.uc.mem_write(0x50009000,current);self.uc.mem_write(0x50007000,image);self.uc.mem_write(0x50006000,struct.pack('<7I',*args))
                        self.assertEqual(self.execute(self.helper_entry,[0x50006000]),result)
                        self.assertEqual(bytes(self.uc.mem_read(0x50009000,510)),expected,(mode,alpha,flags,count))
                        self.assertEqual(bytes(self.uc.mem_read(0x50007000,len(image))),expected_image)
                        self.assertEqual(bytes(self.uc.mem_read(0x50008000,510)),backup);cases+=1
        self.assertEqual(cases,384)


if __name__=='__main__':unittest.main()
