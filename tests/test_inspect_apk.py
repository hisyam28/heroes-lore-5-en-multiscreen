from io import BytesIO
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from inspect_apk import elf_info, inspect_apk


class ApkInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='inspect-', dir=ROOT / 'work')
        self.directory = Path(self.temporary.name).resolve()
        self.assertEqual(self.directory.parent, (ROOT / 'work').resolve())

    def tearDown(self):
        self.assertEqual(self.directory.parent, (ROOT / 'work').resolve())
        self.temporary.cleanup()

    def test_inventory_keeps_compatibility_unverified_and_input_intact(self):
        path = self.directory / 'fixture.apk'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('AndroidManifest.xml', b'\x03\x00\x08\x00')
            archive.writestr('assets/data.vfs.mp3', b'example-resource')
        before = path.read_bytes()
        result = inspect_apk(path)
        self.assertEqual(result['entry_count'], 2)
        self.assertEqual(result['resource_candidates'], ['assets/data.vfs.mp3'])
        self.assertIsNone(result['manifest']['package_name'])
        self.assertEqual(result['status'], 'inventory_only_compatibility_unverified')
        self.assertEqual(path.read_bytes(), before)

    def test_duplicate_or_unsafe_archive_paths_fail(self):
        for member in ['AndroidManifest.xml', '../escape', '/absolute', 'C:/escape']:
            with self.subTest(member=member):
                path = self.directory / 'bad.apk'
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    with zipfile.ZipFile(path, 'w') as archive:
                        archive.writestr('AndroidManifest.xml', b'manifest')
                        archive.writestr(member, b'ambiguous')
                with self.assertRaises(ValueError):
                    inspect_apk(path)

    def test_elf_architecture_and_truncated_program_header(self):
        for bits, machine, fmt in [(1, 40, '<16sHHIIIIIHHHHHH'),
                                   (2, 183, '<16sHHIQQQIHHHHHH')]:
            ident = b'\x7fELF' + bytes([bits, 1, 1]) + bytes(9)
            header = struct.pack(fmt, ident, 3, machine, 1, 0, 0, 0, 0,
                                 struct.calcsize(fmt), 0, 0, 0, 0, 0)
            parsed = elf_info(BytesIO(header), len(header))
            self.assertTrue(parsed['valid_header'])
            self.assertEqual(parsed['bits'], 32 if bits == 1 else 64)
            fields = list(struct.unpack(fmt, header))
            fields[5], fields[9], fields[10] = 4096, 32 if bits == 1 else 56, 1
            bad = struct.pack(fmt, *fields)
            self.assertFalse(elf_info(BytesIO(bad), len(bad))['valid_header'])


if __name__ == '__main__':
    unittest.main()
