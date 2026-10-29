"""Compile the loader's real ABS32 helper to ARM32 and execute it in Unicorn.

This exercises native relocation arithmetic, not an Android framework/device.
"""
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from target_profile import elf_symbols

try:
    import unicorn
    from unicorn.arm_const import UC_ARM_REG_CPSR, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP
    from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
except ImportError:
    unicorn = None

COMPILERS = sorted((ROOT / 'work/android-tools').glob('android-ndk-*/toolchains/llvm/prebuilt/windows-x86_64/bin/clang++.exe'))


def target_weak_abs32(raw):
    header = struct.unpack_from('<16sHHIIIIIHHHHHH', raw)
    sections = [struct.unpack_from('<10I', raw, header[6] + i * header[11]) for i in range(header[12])]
    programs = [struct.unpack_from('<8I', raw, header[5] + i * header[9]) for i in range(header[10])]
    for section in sections:
        if section[1] != 9:
            continue
        symbols = sections[section[6]]
        strings = sections[symbols[6]]
        names = raw[strings[4]:strings[4] + strings[5]]
        for address, info in struct.iter_unpack('<II', raw[section[4]:section[4] + section[5]]):
            if info & 255 != 2:
                continue
            symbol = struct.unpack_from('<IIIBBH', raw, symbols[4] + (info >> 8) * symbols[9])
            if symbol[5] == 0 and symbol[3] >> 4 == 2:
                name = names[symbol[0]:names.index(b'\0', symbol[0])].decode('ascii')
                for typ, offset, start, _, filesz, _, _, _ in programs:
                    if typ == 1 and start <= address < start + filesz:
                        yield name, struct.unpack_from('<I', raw, offset + address - start)[0]
                        break


@unittest.skipUnless(unicorn and COMPILERS, 'Optional ARM32 regression requires local NDK and Python unicorn')
class Arm32Abs32Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix='abs32-', dir=ROOT / 'work')
        cls.addClassCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        source = directory / 'policy.cpp'
        source.write_text('''#include "arm32_relocations.h"
extern "C" __attribute__((visibility("default")))
unsigned run_relocation(unsigned kind, unsigned base, unsigned value, unsigned addend) {
    hl5::Arm32RelocationSymbol symbol;
    symbol.value = value;
    if (kind == 0) { symbol.weak = true; symbol.function = true; }
    if (kind == 1) symbol.defined = true;
    if (kind == 2) { symbol.defined = true; symbol.absolute = true; }
    if (kind == 3) { symbol.host_resolved = true; symbol.host_address = value; }
    if (kind == 5) symbol.null_entry = true;
    if (kind == 6) { symbol.defined = true; symbol.function = true; }
    if (kind == 7) { symbol.weak = true; symbol.host_resolved = true; symbol.host_address = value; }
    unsigned result = 0;
    return hl5::resolve_arm_abs32(symbol, base, addend, result) ? result : 0xdeadbeefu;
}
''', encoding='utf-8')
        library = directory / 'policy.so'
        sysroot = COMPILERS[0].parents[1] / 'sysroot'
        command = [str(COMPILERS[0]), '--target=armv7a-linux-androideabi26', '--sysroot=' + str(sysroot),
                   '-marm', '-shared', '-fPIC', '-std=c++17', '-O2', '-fno-exceptions', '-fno-rtti',
                   '-fno-stack-protector', '-fno-jump-tables', '-nostdlib', '-Wl,--no-undefined',
                   '-I' + str(ROOT / 'tools/runtime'), str(source), '-o', str(library)]
        subprocess.run(command, check=True, capture_output=True)
        cls.raw = library.read_bytes()
        cls.entry = elf_symbols(cls.raw)['run_relocation'].address

    def run_policy(self, kind, base, value, addend):
        uc = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
        header = struct.unpack_from('<16sHHIIIIIHHHHHH', self.raw)
        programs = [struct.unpack_from('<8I', self.raw, header[5] + i * header[9]) for i in range(header[10])]
        load = [p for p in programs if p[0] == 1]
        bias = 0x10000000
        length = max(p[2] + p[5] for p in load)
        uc.mem_map(bias, (length + 4095) & ~4095)
        for _, offset, address, _, filesz, _, _, _ in load:
            uc.mem_write(bias + address, self.raw[offset:offset + filesz])
        uc.mem_map(0x70000000, 4096)
        uc.mem_map(0x30000000, 4096)
        uc.reg_write(UC_ARM_REG_CPSR, 0x10)
        uc.reg_write(UC_ARM_REG_SP, 0x70000fe0)
        uc.reg_write(UC_ARM_REG_LR, 0x30000000)
        for reg, argument in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), (kind, base, value, addend)):
            uc.reg_write(reg, argument)
        uc.emu_start(bias + self.entry, 0x30000000, timeout=1000000, count=10000)
        self.assertEqual(uc.reg_read(UC_ARM_REG_PC), 0x30000000)
        return uc.reg_read(UC_ARM_REG_R0)

    def test_unresolved_weak_absolute_is_zero_without_load_bias(self):
        self.assertEqual(self.run_policy(0, 0x40000000, 0, 0), 0)
        self.assertEqual(self.run_policy(0, 0x40000000, 0, 24), 24)

    def test_defined_and_absolute_symbols_use_different_bias_rules(self):
        self.assertEqual(self.run_policy(1, 0x40000000, 0x1234, 8), 0x4000123c)
        self.assertEqual(self.run_policy(2, 0x40000000, 0x1234, 8), 0x123c)

    def test_resolved_imports_and_missing_strong_imports(self):
        self.assertEqual(self.run_policy(3, 0x40000000, 0x30000010, 4), 0x30000014)
        self.assertEqual(self.run_policy(7, 0x40000000, 0x30000010, 4), 0x30000014)
        self.assertEqual(self.run_policy(4, 0x40000000, 0, 0), 0xdeadbeef)

    def test_null_symbol_preserves_addend(self):
        self.assertEqual(self.run_policy(5, 0x40000000, 0, 0x1234), 0x1234)

    def test_thumb_bit_is_applied_after_addend(self):
        self.assertEqual(self.run_policy(6, 0x40000000, 0x101, 1), 0x40000101)
        self.assertEqual(self.run_policy(1, 0x40000000, 0x101, 1), 0x40000102)

    def test_arm32_arithmetic_wraps_at_32_bits(self):
        self.assertEqual(self.run_policy(1, 0xfffff000, 0x2000, 0x34), 0x1034)

    def test_actual_target_weak_imports_are_accepted(self):
        apk = ROOT / 'inputs/hl5-original-01.01.00.apk'
        if not apk.exists():
            self.skipTest('Private target APK is unavailable')
        with zipfile.ZipFile(apk) as archive:
            relocations = list(target_weak_abs32(archive.read('lib/armeabi/libHeroesLore5.so')))
        self.assertEqual({name for name, _ in relocations}, {'__cxa_call_unexpected', '__gnu_Unwind_Find_exidx'})
        for name, addend in relocations:
            with self.subTest(name=name):
                self.assertEqual(self.run_policy(0, 0x40000000, 0, addend), addend)


if __name__ == '__main__':
    unittest.main()
