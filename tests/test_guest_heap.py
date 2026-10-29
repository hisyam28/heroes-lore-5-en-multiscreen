"""Compile the real recycling allocator and stress its ARM32 implementation."""
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import unittest

import test_arm32_relocations as arm
import test_framebuffer_copy as native

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(arm.unicorn and arm.COMPILERS, 'Requires local NDK and Unicorn')
class GuestHeapTests(unittest.TestCase):
    NODE_CAPACITY = 1024
    execute = native.NativeFramebufferCopyTests.execute

    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix='heap-native-', dir=ROOT/'work')
        cls.addClassCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        source = directory/'heap.cpp'
        source.write_text('''#include "guest_heap.h"
static hl5::GuestHeap<1024> heap;
extern "C" __attribute__((visibility("default")))
unsigned run_heap(unsigned operation, unsigned a, unsigned b) {
    switch (operation) {
        case 0: heap.reset(a,b); return heap.validate();
        case 1: return heap.allocate(a,b);
        case 2: return heap.release(a);
        case 3: return heap.in_use();
        case 4: return heap.largest_free();
        case 5: return heap.validate();
        case 6: return heap.resize_in_place(a,b);
        case 7: return heap.requested_size(a);
        case 8: return heap.peak();
        case 9: return heap.live_allocations();
        case 10: return heap.owns(a);
    }
    return 0;
}
'''.replace('GuestHeap<1024>', 'GuestHeap<' + str(cls.NODE_CAPACITY) + '>'),encoding='utf-8')
        compiler=arm.COMPILERS[0]
        library=directory/'heap.so'
        result=subprocess.run([str(compiler),'--target=armv7a-linux-androideabi26',
            '--sysroot='+str(compiler.parents[1]/'sysroot'),'-marm','-mfpu=none','-shared','-fPIC',
            '-std=c++17','-O2','-fvisibility=hidden','-Wl,-Bsymbolic','-fno-exceptions','-fno-rtti','-fno-stack-protector','-fno-builtin',
            '-fno-vectorize','-fno-slp-vectorize','-nostdlib','-Wl,--no-undefined',
            '-I'+str(ROOT/'tools/runtime'),str(source),'-o',str(library)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stderr)
        cls.raw=library.read_bytes()
        cls.entry=arm.elf_symbols(cls.raw)['run_heap'].address+0x10000000

    def setUp(self):
        self.uc=arm.unicorn.Uc(arm.unicorn.UC_ARCH_ARM,arm.unicorn.UC_MODE_ARM)
        header=struct.unpack_from('<16sHHIIIIIHHHHHH',self.raw)
        segments=[struct.unpack_from('<8I',self.raw,header[5]+i*header[9]) for i in range(header[10])]
        segments=[s for s in segments if s[0]==1]
        end=max(s[2]+s[5] for s in segments)
        self.uc.mem_map(0x10000000,(end+4095)&~4095)
        for _,offset,address,_,size,_,_,_ in segments:
            self.uc.mem_write(0x10000000+address,self.raw[offset:offset+size])
        self.uc.mem_map(0x70000000,4096);self.uc.mem_map(0x30000000,4096)
        self.assertEqual(self.call(0,0x50000000,16*1024*1024),1)

    def call(self,op,a=0,b=0):return self.execute(self.entry,[op,a,b])

    def test_repeated_large_scene_allocations_return_to_baseline(self):
        # The previous monotonic/no-op-free path exhausts 16 MiB on iteration 17.
        for cycle in range(600):
            pointer=self.call(1,1024*1024,8)
            self.assertEqual(pointer,0x50000000,cycle)
            self.assertEqual(self.call(2,pointer),1)
        self.assertEqual(self.call(3),0)
        self.assertEqual(self.call(4),16*1024*1024)
        self.assertEqual(self.call(8),1024*1024)
        self.assertEqual(self.call(5),1)

    def test_alignment_and_neighbor_coalescing_recover_entire_heap(self):
        pointers=[self.call(1,size,alignment) for size,alignment in [(17,8),(3000,4096),(9,16),(100,4)]]
        for pointer,alignment in zip(pointers,(8,4096,16,4)):
            self.assertNotEqual(pointer,0);self.assertEqual(pointer%alignment,0)
        for index in (1,3,0,2):self.assertEqual(self.call(2,pointers[index]),1)
        self.assertEqual(self.call(4),16*1024*1024)
        self.assertEqual(self.call(5),1)

    def test_invalid_double_free_and_exhaustion_do_not_damage_live_allocations(self):
        pointer=self.call(1,16*1024*1024,8)
        self.assertEqual(self.call(1,8,8),0)
        self.assertEqual(self.call(2,pointer+8),0)
        self.assertEqual(self.call(2,0),1)
        self.assertEqual(self.call(7,pointer),16*1024*1024)
        self.assertEqual(self.call(2,pointer),1)
        self.assertEqual(self.call(2,pointer),0)
        self.assertEqual(self.call(1,0xffffffff,8),0)
        self.assertEqual(self.call(1,8,3),0)
        self.assertEqual(self.call(5),1)

    def test_zero_allocations_are_distinct_and_resize_preserves_address(self):
        first=self.call(1,0,8);second=self.call(1,0,8)
        self.assertNotEqual(first,second)
        self.assertEqual(self.call(6,first,200),0)
        self.assertEqual(self.call(2,second),1)
        self.assertEqual(self.call(6,first,200),1)
        self.assertEqual(self.call(7,first),200)
        self.assertEqual(self.call(6,first,16),1)
        self.assertEqual(self.call(3),16)
        self.assertEqual(self.call(2,first),1)
        self.assertEqual(self.call(5),1)

    def test_randomized_churn_preserves_live_ranges_and_metadata(self):
        rng=random.Random(8142);live={}
        for _ in range(1200):
            if live and rng.randrange(3)==0:
                pointer=rng.choice(list(live));self.assertEqual(self.call(2,pointer),1);del live[pointer]
            else:
                size=rng.randrange(1,48000);alignment=rng.choice((4,8,16,256,4096))
                pointer=self.call(1,size,alignment)
                self.assertNotEqual(pointer,0);self.assertEqual(pointer%alignment,0)
                for other,length in live.items():self.assertTrue(pointer+size<=other or other+length<=pointer)
                live[pointer]=size
            self.assertEqual(self.call(5),1)
        for pointer in list(live):self.assertEqual(self.call(2,pointer),1)
        self.assertEqual(self.call(9),0);self.assertEqual(self.call(4),16*1024*1024)
        self.assertEqual(self.call(5),1)


if __name__=='__main__':unittest.main()
