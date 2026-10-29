"""Differential comparison with the immutable target's actual ARM instructions."""
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import unittest
import zipfile

import test_arm32_relocations as arm

ROOT = Path(__file__).resolve().parents[1]
APK = ROOT / 'inputs/hl5-original-01.01.00.apk'
SYMBOL = '_Z26internalGrpCopyFrameBufferiiiiiiiiP14_MC_GrpContexth'


@unittest.skipUnless(arm.unicorn and arm.COMPILERS and APK.exists(), 'Requires local target, NDK and Unicorn')
class NativeFramebufferCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix='copy-diff-', dir=ROOT / 'work')
        cls.addClassCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        source = directory / 'copy.cpp'
        source.write_text('''#include "framebuffer_copy.h"
extern "C" __attribute__((visibility("default")))
unsigned run_plan(const uint32_t* a, hl5::FramebufferCopyPlan* out) {
    return hl5::plan_opaque_framebuffer_copy(
        *reinterpret_cast<const hl5::GuestFramebuffer*>(a[0]), a[1], a[2], a[3], a[4],
        *reinterpret_cast<const hl5::GuestFramebuffer*>(a[5]), a[6], a[7],
        reinterpret_cast<const int32_t*>(a[8]), a[9], *out);
}
''', encoding='utf-8')
        compiler = arm.COMPILERS[0]
        library = directory / 'copy.so'
        subprocess.run([str(compiler), '--target=armv7a-linux-androideabi26',
                        '--sysroot=' + str(compiler.parents[1] / 'sysroot'), '-marm', '-shared', '-fPIC',
                        '-std=c++17', '-O2', '-mfpu=none', '-fno-vectorize', '-fno-slp-vectorize',
                        '-fno-exceptions', '-fno-rtti', '-fno-stack-protector',
                        '-nostdlib', '-Wl,--no-undefined', '-I' + str(ROOT / 'tools/runtime'),
                        str(source), '-o', str(library)], check=True, capture_output=True)
        cls.helper = library.read_bytes()
        cls.helper_entry = arm.elf_symbols(cls.helper)['run_plan'].address + 0x10000000
        with zipfile.ZipFile(APK) as archive:
            cls.target = archive.read('lib/armeabi/libHeroesLore5.so')
        cls.target_entry = arm.elf_symbols(cls.target)[SYMBOL].address + 0x40000000

    def setup_memory(self, bits=16, seed=0, overlapping=False):
        uc = arm.unicorn.Uc(arm.unicorn.UC_ARCH_ARM, arm.unicorn.UC_MODE_ARM)
        for raw, bias in ((self.helper, 0x10000000), (self.target, 0x40000000)):
            header = struct.unpack_from('<16sHHIIIIIHHHHHH', raw)
            programs = [struct.unpack_from('<8I', raw, header[5] + i * header[9]) for i in range(header[10])]
            load = [p for p in programs if p[0] == 1]
            length = max(p[2] + p[5] for p in load)
            uc.mem_map(bias, (length + 4095) & ~4095)
            for _, offset, address, _, filesz, _, _, _ in load:
                uc.mem_write(bias + address, raw[offset:offset + filesz])
        uc.mem_map(0x50000000, 65536)
        uc.mem_map(0x70000000, 4096)
        uc.mem_map(0x30000000, 4096)
        randomizer = random.Random(seed)
        self.dw, self.dh, self.sw, self.sh = [randomizer.randint(8, 30) for _ in range(4)]
        self.ds = self.dw * (bits // 8) + 8
        self.ss = self.sw * (bits // 8) + 4
        self.source_pixels = 0x50005000
        if overlapping:
            self.source_pixels = 0x50001000
        uc.mem_write(0x50000000, struct.pack('<4iI', self.dw, self.dh, self.ds, bits, 0x50001000))
        uc.mem_write(0x50000040, struct.pack('<4iI', self.sw, self.sh, self.ss, bits, self.source_pixels))
        self.initial = bytes(randomizer.randrange(256) for _ in range(self.ds * self.dh))
        uc.mem_write(0x50001000, self.initial)
        if not overlapping:
            uc.mem_write(self.source_pixels, bytes(randomizer.randrange(256) for _ in range(self.ss * self.sh)))
        self.uc = uc
        return randomizer

    def execute(self, entry, args, instruction_limit=2000000, timeout_us=3000000):
        uc = self.uc
        uc.reg_write(arm.UC_ARM_REG_CPSR, 0x10)
        uc.reg_write(arm.UC_ARM_REG_SP, 0x70000f00)
        uc.reg_write(arm.UC_ARM_REG_LR, 0x30000000)
        for register, argument in zip((arm.UC_ARM_REG_R0, arm.UC_ARM_REG_R1, arm.UC_ARM_REG_R2, arm.UC_ARM_REG_R3), args):
            uc.reg_write(register, argument & 0xffffffff)
        if len(args) > 4:
            uc.mem_write(0x70000f00, struct.pack('<' + 'I' * (len(args) - 4), *(x & 0xffffffff for x in args[4:])))
        uc.emu_start(entry, 0x30000000, timeout=timeout_us, count=instruction_limit)
        self.assertEqual(uc.reg_read(arm.UC_ARM_REG_PC), 0x30000000)
        return uc.reg_read(arm.UC_ARM_REG_R0)

    def plan(self, args, context):
        self.uc.mem_write(0x50000100, struct.pack('<16i', *context))
        self.uc.mem_write(0x50000200, struct.pack('<10I', *(v & 0xffffffff for v in args)))
        return self.execute(self.helper_entry, [0x50000200, 0x50000300])

    def test_native_rows_match_original_arm_pixels_and_clipping(self):
        for bits in (16, 32):
            for seed in range(24):
                with self.subTest(bits=bits, seed=seed):
                    rng = self.setup_memory(bits, seed)
                    context = [0] * 16
                    context[1:5] = [rng.randint(-3, 8), rng.randint(-3, 8), rng.randint(10, 40), rng.randint(10, 40)]
                    context[8] = 255
                    args = [0x50000000, rng.randint(0, 12), rng.randint(0, 12), rng.randint(1, 45),
                            rng.randint(1, 45), 0x50000040, rng.randint(0, 12), rng.randint(0, 12), 0x50000100, 0]
                    self.assertEqual(self.plan(args, context), 1)
                    plan = struct.unpack('<6I', self.uc.mem_read(0x50000300, 24))
                    self.execute(self.target_entry, args)
                    expected = bytes(self.uc.mem_read(0x50001000, len(self.initial)))
                    self.uc.mem_write(0x50001000, self.initial)
                    source, destination, source_stride, destination_stride, row_bytes, rows = plan
                    for row in range(rows):
                        pixels = bytes(self.uc.mem_read(source + row * source_stride, row_bytes))
                        self.uc.mem_write(destination + row * destination_stride, pixels)
                    self.assertEqual(bytes(self.uc.mem_read(0x50001000, len(self.initial))), expected)

    def test_blending_transparency_pixel_ops_and_negative_coordinates_fall_back(self):
        self.setup_memory()
        context = [0] * 16
        context[1:5] = [0, 0, 30, 30]
        context[8] = 255
        args = [0x50000000, 0, 0, 8, 8, 0x50000040, 0, 0, 0x50000100, 0]
        for kind in ('blend', 'transparent', 'operator', 'negative', 'huge'):
            with self.subTest(kind=kind):
                current_args, current_context = args[:], context[:]
                if kind == 'blend': current_context[8] = 254
                if kind == 'transparent': current_args[9] = 1
                if kind == 'operator': current_context[11] = 1
                if kind == 'negative': current_args[6] = -1
                if kind == 'huge': current_args[3] = 0x7fffffff
                self.assertEqual(self.plan(current_args, current_context), 0)

    def test_overlapping_buffers_keep_original_guest_path(self):
        self.setup_memory(overlapping=True)
        context = [0] * 16
        context[1:5] = [0, 0, 30, 30]
        context[8] = 255
        args = [0x50000000, 0, 0, 8, 8, 0x50000040, 0, 0, 0x50000100, 0]
        self.assertEqual(self.plan(args, context), 0)


if __name__ == '__main__':
    unittest.main()
