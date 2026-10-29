"""Compare optimized save DES rounds with the fingerprinted original ARM code."""
from pathlib import Path
import json
import random
import struct
import subprocess
import tempfile
import unittest
import zipfile
import test_arm32_relocations as arm
import test_framebuffer_copy as frame

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(arm.unicorn and arm.COMPILERS,'Requires NDK and Unicorn')
class SaveCryptoTests(unittest.TestCase):
    setup_memory=frame.NativeFramebufferCopyTests.setup_memory
    execute=frame.NativeFramebufferCopyTests.execute
    @classmethod
    def setUpClass(cls):
        temp=tempfile.TemporaryDirectory(prefix='save-crypto-',dir=ROOT/'work');cls.addClassCleanup(temp.cleanup)
        source=Path(temp.name)/'crypto.cpp';library=source.with_suffix('.so')
        source.write_text('''#include <cstddef>
extern "C" void* memset(void* d,int c,size_t n){auto p=(unsigned char*)d;for(size_t i=0;i<n;++i)p[i]=c;return d;}
extern "C" void* memcpy(void* d,const void* s,size_t n){auto p=(unsigned char*)d;auto q=(const unsigned char*)s;for(size_t i=0;i<n;++i)p[i]=q[i];return d;}
#include "save_crypto.h"
#include "save_commit.h"
extern "C" __attribute__((visibility("default"))) unsigned run_commit(unsigned scenario){
    hl5::SaveCommitTracker tracker;unsigned syncs=0,closes=0;
    auto sync=[&](int fd){++syncs;return scenario==2?-1:0;};
    auto close=[&](int fd){++closes;return scenario==3?-1:0;};
    if(scenario!=0)for(unsigned i=0;i<100;++i)if(!tracker.mark(7))return 0;
    int rc=hl5::commit_save_close(tracker,7,sync,close);
    if(syncs!=(scenario==0?0:1)||closes!=1||tracker.dirty(7))return 0;
    if(rc!=((scenario==2||scenario==3)?-1:0))return 0;
    for(int fd=3;fd<67;++fd)if(!tracker.mark(fd))return 0;
    if(tracker.mark(67))return 0;
    tracker.clear(8);if(!tracker.mark(67)||tracker.dirty(8))return 0;
    return 1;
}
extern "C" __attribute__((visibility("default"))) unsigned run_crypto(unsigned* l,unsigned* r,const unsigned char* key){
return hl5::des_round_bits(l,r,key,reinterpret_cast<const unsigned char*>(0x4015ed74),
reinterpret_cast<const unsigned char*>(0x4015eda4),reinterpret_cast<const unsigned char*>(0x4015edc4));}
''')
        c=arm.COMPILERS[0]
        subprocess.run([str(c),'--target=armv7a-linux-androideabi21','--sysroot='+str(c.parents[1]/'sysroot'),
            '-shared','-fPIC','-marm','-std=c++17','-O3','-mfpu=none','-fno-vectorize','-fno-slp-vectorize',
            '-fno-builtin','-fno-exceptions','-fno-rtti','-fno-stack-protector','-nostdlib','-Wl,--no-undefined','-Wl,-Bsymbolic',
            '-I'+str(ROOT/'tools/runtime'),str(source),'-o',str(library)],check=True,capture_output=True)
        cls.helper=library.read_bytes();cls.helper_entry=arm.elf_symbols(cls.helper)['run_crypto'].address+0x10000000
        cls.commit_entry=arm.elf_symbols(cls.helper)['run_commit'].address+0x10000000
        with zipfile.ZipFile(frame.APK) as z:cls.target=z.read('lib/armeabi/libHeroesLore5.so')
        cls.symbols=arm.elf_symbols(cls.target);cls.target_entry=cls.symbols['desRound'].address+0x40000000

    def test_encrypt_and_reverse_key_rounds_are_byte_exact(self):
        from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_LR
        self.setup_memory()
        # These GOT slots are derived from desRound's target instruction literals.
        for off,address in ((0x238,0x15ed74),(0x1d0,0x15eda4),(0x260,0x16e730),(0x138,0x15edc4)):
            self.uc.mem_write(0x4015e780+off,struct.pack('<I',0x40000000+address))
        def memset(uc,address,size,data):
            dst=uc.reg_read(UC_ARM_REG_R0);value=uc.reg_read(UC_ARM_REG_R1);n=uc.reg_read(UC_ARM_REG_R2)
            uc.mem_write(dst,bytes([value&255])*n);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        self.uc.hook_add(arm.unicorn.UC_HOOK_CODE,memset,begin=0x40030308,end=0x40030308)
        rng=random.Random(10329);instructions=[]
        for seed in range(24):
            halves=struct.pack('<64I',*[rng.randrange(2) for _ in range(64)])
            key=bytes(rng.randrange(2) for _ in range(768))
            for reverse in (False,True):
                selected=b''.join(key[i:i+48] for i in range(720,-1,-48)) if reverse else key
                self.uc.mem_write(0x4016e730,selected);self.uc.mem_write(0x50004000,halves)
                self.execute(self.target_entry,[0x50004000,0x50004080])
                expected=bytes(self.uc.mem_read(0x50004000,256))
                self.assertEqual(bytes(self.uc.mem_read(0x4016e730,768)),selected)
                self.uc.mem_write(0x50004000,halves)
                self.assertEqual(self.execute(self.helper_entry,[0x50004000,0x50004080,0x4016e730]),1)
                self.assertEqual(bytes(self.uc.mem_read(0x50004000,256)),expected,(seed,reverse))
        invalid=struct.pack('<64I',2,*([0]*63));self.uc.mem_write(0x50004000,invalid)
        self.assertEqual(self.execute(self.helper_entry,[0x50004000,0x50004080,0x4016e730]),0)
        self.assertEqual(bytes(self.uc.mem_read(0x50004000,256)),invalid)

    def test_save_fence_once_before_close_handles_errors_and_descriptor_reuse(self):
        self.setup_memory()
        for scenario in (0,1,2,3):self.assertEqual(self.execute(self.commit_entry,[scenario]),1)

if __name__=='__main__':unittest.main()
