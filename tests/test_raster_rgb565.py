"""Differential RGB565 tests against the fingerprinted target ARM routines."""
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import unittest
import zipfile

import test_arm32_relocations as arm
import test_framebuffer_copy as diff

ROOT = Path(__file__).resolve().parents[1]
ALPHA = '_ZN7Graphic13FillRectAlphaEiiiiihi'
MIRROR = '_ZN7Graphic22DrawImageMirrorClip565EiiiiiP8GbmImageiihi'
FRAME_BLEND = '_ZN7Graphic28ChangeFrameBufferBlending565Eiihh'
SPRITE_BLEND = '_ZN7Graphic24DrawImageBlendingClip565EiiiiiP8GbmImageiihhhi'
RECT_BLEND = '_ZN7Graphic16FillRectBlendingEiiiiihhi'


@unittest.skipUnless(arm.unicorn and arm.COMPILERS and diff.APK.exists(), 'Requires local target, NDK and Unicorn')
class Raster565Tests(unittest.TestCase):
    setup_memory = diff.NativeFramebufferCopyTests.setup_memory
    execute = diff.NativeFramebufferCopyTests.execute

    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix='raster-diff-', dir=ROOT / 'work')
        cls.addClassCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        source = directory / 'raster.cpp'
        source.write_text('''#include "raster_rgb565.h"
extern "C" __attribute__((visibility("default")))
unsigned run_raster(unsigned operation, const uint32_t* a) {
    auto& fb = *reinterpret_cast<const hl5::GuestFramebuffer*>(a[operation==4 ? 0 : 1]);
    if (operation == 4) {
        hl5::RasterRect rect;
        auto context=reinterpret_cast<const int32_t*>(a[5]);
        if (!hl5::plan_context_fill565(fb,a[1],a[2],a[3],a[4],context,rect)) return 0;
        for (int y=0; y<rect.height; ++y) {
            auto row=reinterpret_cast<uint16_t*>(fb.pixels+(rect.y+y)*fb.stride+rect.x*2);
            for (int x=0;x<rect.width;++x) row[x]=context[5];
        }
        return 1;
    }
    if (operation == 2 || operation == 3) {
        unsigned mode=(operation==2 ? a[3] : a[6])&255;
        unsigned alpha=operation==2 ? a[4] : a[7];
        unsigned color=operation==2 ? a[2] : a[8];
        hl5::RasterRect rect;
        if (mode>15 || !hl5::plan_alpha_fill565(fb,*reinterpret_cast<const uint8_t*>(a[0]+0x5c),
                operation==2 ? 0 : a[2],operation==2 ? 0 : a[3],
                operation==2 ? fb.width : a[4],operation==2 ? fb.height : a[5],rect)) return 0;
        if (operation==2 && fb.stride!=fb.width*2) return 0;
        auto table=reinterpret_cast<const uint8_t*>(a[0]+0x6d+mode*1024);
        for (int y=0;y<rect.height;++y) {
            auto row=reinterpret_cast<uint16_t*>(fb.pixels+(rect.y+y)*fb.stride+rect.x*2);
            hl5::table_blend_row565(row,rect.width,color,alpha,table);
        }
        return 1;
    }
    if (operation == 0) {
        hl5::RasterRect rect;
        if (!hl5::plan_alpha_fill565(fb, *reinterpret_cast<const uint8_t*>(a[0]+0x5c),
                a[2],a[3],a[4],a[5],rect)) return 0;
        for (int y=0; y<rect.height; ++y) {
            auto row=reinterpret_cast<uint16_t*>(fb.pixels+(rect.y+y)*fb.stride+rect.x*2);
            hl5::alpha_fill_row565(row,rect.width,a[7],a[6]);
        }
        return 1;
    }
    hl5::IndexedBlitPlan plan;
    const auto& image=*reinterpret_cast<const hl5::GuestIndexedImage*>(a[6]);
    if (!hl5::plan_indexed_blit565(fb,reinterpret_cast<const int32_t*>(a[0]+0x40e0),
            a[2],a[3],a[4],a[5],image,a[7],a[8],a[9]&255,a[operation==5?12:10],plan)) return 0;
    if(operation==5 && (a[10]>15 || !(a[11]&255))) return 0;
    uint32_t key=*reinterpret_cast<const uint32_t*>(0x4016a234);
    for (int y=0; y<plan.destination.height; ++y) {
        int dy=plan.destination.y+(plan.flip_y ? plan.destination.height-1-y : y);
        auto row=reinterpret_cast<uint16_t*>(fb.pixels+dy*fb.stride+plan.destination.x*2);
        auto src=reinterpret_cast<const uint8_t*>(image.pixels+(plan.sy+y)*plan.source_stride);
        if(operation==5) hl5::indexed_blend_row565(row,src,reinterpret_cast<const uint16_t*>(image.palette),
            plan.sx,plan.destination.width,plan.bits,plan.flip_x,key,a[11],reinterpret_cast<const uint8_t*>(a[0]+0x6d+a[10]*1024));
        else hl5::indexed_blit_row565(row,src,reinterpret_cast<const uint16_t*>(image.palette),
            plan.sx,plan.destination.width,plan.bits,plan.flip_x,key);
    }
    return 1;
}
''', encoding='utf-8')
        compiler = arm.COMPILERS[0]
        builtins = next((compiler.parents[1] / 'lib/clang').rglob('libclang_rt.builtins-arm-android.a'))
        library = directory / 'raster.so'
        subprocess.run([str(compiler), '--target=armv7a-linux-androideabi26',
                        '--sysroot=' + str(compiler.parents[1] / 'sysroot'), '-marm', '-shared', '-fPIC',
                        '-std=c++17', '-O2', '-mfpu=none', '-fno-vectorize', '-fno-slp-vectorize',
                        '-fno-exceptions', '-fno-rtti', '-fno-stack-protector', '-nostdlib',
                        '-Wl,--no-undefined', '-I' + str(ROOT / 'tools/runtime'), str(source), str(builtins), '-o', str(library)],
                       check=True, capture_output=True)
        cls.helper = library.read_bytes()
        cls.helper_entry = arm.elf_symbols(cls.helper)['run_raster'].address + 0x10000000
        with zipfile.ZipFile(diff.APK) as archive:
            cls.target = archive.read('lib/armeabi/libHeroesLore5.so')
        symbols = arm.elf_symbols(cls.target)
        cls.sprite_blend_entry=symbols[SPRITE_BLEND].address+0x40000000
        cls.alpha_entry = symbols[ALPHA].address + 0x40000000
        cls.mirror_entry = symbols[MIRROR].address + 0x40000000
        cls.frame_blend_entry = symbols[FRAME_BLEND].address + 0x40000000
        cls.rect_blend_entry = symbols[RECT_BLEND].address + 0x40000000
        cls.context_fill_entry = symbols['MC_grpFillRect'].address + 0x40000000
        # Resolve the kernel singleton's RELATIVE GOT reference from its actual
        # getter instructions. MC_grpFillRect calls the getter and ignores it.
        getter = symbols['_ZN18MIDASKernelManager11getInstanceEv']
        cls.kernel_got = 0x40000000 + ((getter.address + 16 + struct.unpack_from('<I', getter.data, 24)[0]
                                      + struct.unpack_from('<I', getter.data, 28)[0]) & 0xffffffff)

    def setup_raster(self, width=64, height=64, padding=0, seed=0):
        self.setup_memory(seed=seed)
        self.dw, self.dh, self.ds = width, height, width * 2 + padding
        self.uc.mem_write(0x50000000, struct.pack('<4iI', width, height, self.ds, 16, 0x50001000))
        rng = random.Random(seed)
        self.initial = bytes(rng.randrange(256) for _ in range(self.ds * height))
        self.uc.mem_write(0x50001000, self.initial)
        self.uc.mem_write(0x5000905c, b'\x01')
        self.uc.mem_write(0x5000d0e0, struct.pack('<4i', 0, 0, width, height))
        # The original mirror routine accesses SKIP_COLOR through this RELATIVE
        # GOT slot. These addresses are derived from this exact target binary.
        self.uc.mem_write(0x4015ecc0, struct.pack('<I', 0x4016a234))
        self.uc.mem_write(self.kernel_got, struct.pack('<I', 0x50008000))
        self.uc.mem_write(0x50008000, b'\0\0\0\0')
        return rng

    def native(self, operation, args):
        self.uc.mem_write(0x50000200, struct.pack('<' + 'I' * len(args), *(v & 0xffffffff for v in args)))
        return self.execute(self.helper_entry, [operation, 0x50000200])

    def compare(self, operation, args, target_entry):
        self.execute(target_entry, args)
        expected = bytes(self.uc.mem_read(0x50001000, len(self.initial)))
        self.uc.mem_write(0x50001000, self.initial)
        self.assertEqual(self.native(operation, args), 1)
        self.assertEqual(bytes(self.uc.mem_read(0x50001000, len(self.initial))), expected)

    def test_alpha_fill_matches_original_rounding_and_bounds(self):
        for seed in range(32):
            for alpha in (0, 1, 127, 128, 254, 255):
                with self.subTest(seed=seed, alpha=alpha):
                    rng = self.setup_raster(19, 15, padding=2, seed=seed)
                    args = [0x50009000, 0x50000000, rng.randint(-8, 25), rng.randint(-8, 20),
                            rng.randint(1, 30), rng.randint(1, 25), alpha, rng.randrange(0x1000000)]
                    self.compare(0, args, self.alpha_entry)

    def test_indexed_sprites_match_original_palette_mirroring_anchor_and_skip_color(self):
        for bits in (4, 8):
            for mirror in (16, 8, 4, 12):
                for anchor in (0, 16, 32, 2, 4, 18, 20, 34, 36):
                    for sx in (0, 1):
                        with self.subTest(bits=bits, mirror=mirror, anchor=anchor, sx=sx):
                            rng = self.setup_raster(seed=mirror + anchor + sx)
                            image_width, image_height = 13, 12
                            stride = (image_width + 1) // 2 if bits == 4 else image_width
                            self.uc.mem_write(0x50000080, struct.pack('<BBHHHII', bits | 16, 0, image_width,
                                                                 image_height, 0, 0x50007000, 0x50005000))
                            self.uc.mem_write(0x50005000, bytes(rng.randrange(256) for _ in range(stride * image_height)))
                            palette = [0x1234] + [rng.randrange(65536) for _ in range(255)]
                            self.uc.mem_write(0x50007000, struct.pack('<256H', *palette))
                            self.uc.mem_write(0x4016a234, struct.pack('<I', 0x1234))
                            args = [0x50009000, 0x50000000, 25, 24, 8, 7, 0x50000080, sx, 2, mirror, anchor]
                            self.compare(1, args, self.mirror_entry)

    def test_transparent_sprite_blending_matches_target_modes_alpha_and_mirroring(self):
        cases=0
        for bits in (4,8):
            for mirror in (16,8,4,12):
                for mode in (0,1,7,15):
                    for alpha in (1,7,8,127,247,248,255):
                        rng=self.setup_raster(seed=bits+mirror+mode+alpha)
                        iw,ih=13,12;stride=(iw+1)//2 if bits==4 else iw
                        self.uc.mem_write(0x50000080,struct.pack('<BBHHHII',bits|16,0,iw,ih,0,0x50007000,0x50005000))
                        self.uc.mem_write(0x50005000,bytes(rng.randrange(256) for _ in range(stride*ih)))
                        self.uc.mem_write(0x50007000,struct.pack('<256H',0x1234,*[rng.randrange(65536) for _ in range(255)]))
                        self.uc.mem_write(0x4016a234,struct.pack('<I',0x1234))
                        self.uc.mem_write(0x5000906d+mode*1024,bytes(rng.randrange(32) for _ in range(1024)))
                        args=[0x50009000,0x50000000,25,24,8,7,0x50000080,1,2,mirror,mode,alpha,18]
                        self.compare(5,args,self.sprite_blend_entry);cases+=1
        self.assertEqual(cases,224)

    def test_unmirrored_edge_blits_and_blends_match_target(self):
        cases=0
        positions=((-4,20),(58,20),(20,-4),(20,58),(-4,-4),(58,58),(0,0),(52,52))
        for bits in (4,8):
            for clip in ((0,0,64,64),(3,4,59,60)):
                for x,y in positions:
                    for op,alpha in ((1,255),(5,127),(5,255)):
                        rng=self.setup_raster(seed=bits+x+y+op+alpha)
                        iw,ih=17,15;stride=(iw+1)//2 if bits==4 else iw
                        self.uc.mem_write(0x5000d0e0,struct.pack('<4i',*clip))
                        self.uc.mem_write(0x50000080,struct.pack('<BBHHHII',bits|16,0,iw,ih,0,0x50007000,0x50005000))
                        self.uc.mem_write(0x50005000,bytes(rng.randrange(256) for _ in range(stride*ih)))
                        self.uc.mem_write(0x50007000,struct.pack('<256H',0x1234,*[rng.randrange(65536) for _ in range(255)]))
                        self.uc.mem_write(0x4016a234,struct.pack('<I',0x1234))
                        self.uc.mem_write(0x5000906d+7*1024,bytes(rng.randrange(32) for _ in range(1024)))
                        args=[0x50009000,0x50000000,x,y,14,10,0x50000080,1,2,16]
                        args+=([0] if op==1 else [7,alpha,0])
                        self.compare(op,args,self.mirror_entry if op==1 else self.sprite_blend_entry);cases+=1
        self.assertEqual(cases,96)

    def test_edge_clipping_and_unsupported_format_keep_guest_path(self):
        self.setup_raster()
        self.uc.mem_write(0x50000080, struct.pack('<BBHHHII', 8, 0, 13, 12, 0, 0x50007000, 0x50005000))
        args = [0x50009000, 0x50000000, -1, 24, 8, 7, 0x50000080, 0, 2, 16, 0]
        self.compare(1,args,self.mirror_entry)
        args[2] = 25
        args[9] = 99
        self.assertEqual(self.native(1, args), 0)
        self.uc.mem_write(0x5000905c, b'\x02')
        alpha = [0x50009000, 0x50000000, 0, 0, 8, 7, 128, 0xffffff]
        self.assertEqual(self.native(0, alpha), 0)

    def test_whole_frame_effects_preserve_target_lookup_and_alpha_quantization(self):
        for mode in range(16):
            for alpha in (0, 1, 127, 247, 248, 255):
                with self.subTest(mode=mode, alpha=alpha):
                    rng=self.setup_raster(19,15,seed=mode+alpha)
                    self.uc.mem_write(0x5000906d+mode*1024,bytes(rng.randrange(256) for _ in range(1024)))
                    args=[0x50009000,0x50000000,rng.randrange(0x1000000),mode,alpha]
                    self.compare(2,args,self.frame_blend_entry)

    def test_rectangle_effects_match_original_bounds_and_color(self):
        for mode in range(16):
            for alpha in (0, 1, 127, 247, 248, 255):
                with self.subTest(mode=mode, alpha=alpha):
                    rng=self.setup_raster(19,15,padding=2,seed=mode+alpha)
                    self.uc.mem_write(0x5000906d+mode*1024,bytes(rng.randrange(256) for _ in range(1024)))
                    args=[0x50009000,0x50000000,rng.randint(-8,20),rng.randint(-8,20),
                          rng.randint(1,30),rng.randint(1,25),mode,alpha,rng.randrange(0x1000000)]
                    self.compare(3,args,self.rect_blend_entry)

    def test_context_fill_matches_original_negative_sizes_clipping_and_padding(self):
        for seed in range(64):
            with self.subTest(seed=seed):
                rng=self.setup_raster(19,15,padding=2,seed=seed)
                context=[0]*16
                context[1:5]=[-2,2,rng.randint(9,25),rng.randint(8,20)]
                context[5]=rng.randrange(0x7fffffff);context[8]=255
                self.uc.mem_write(0x50000100,struct.pack('<16i',*context))
                args=[0x50000000,rng.randint(-8,20),rng.randint(-8,20),
                      rng.randint(-20,25),rng.randint(-20,25),0x50000100]
                self.compare(4,args,self.context_fill_entry)


if __name__ == '__main__':
    unittest.main()
