from copy import deepcopy
import json
from pathlib import Path
import struct
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from inspect_apk import sha256_file
from prepare_android_runner import prepare
from target_profile import elf_symbols, verify_target


class RunnerBoundaryTests(unittest.TestCase):
    def test_staging_cannot_write_outside_work_or_replace_existing_directory(self):
        for destination in (ROOT / 'inputs/new-runner', ROOT / 'work', ROOT / 'work/../dist/runner'):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                prepare(Path('unused.apk'), Path('unused.zip'), destination, {})

    def test_elf_parser_rejects_invalid_architecture_and_truncated_tables(self):
        ident = b'\x7fELF' + bytes([1, 1, 1]) + bytes(9)
        for machine, phsize, shsize in ((183, 32, 40), (40, 31, 40), (40, 32, 39), (40, 32, 40)):
            raw = struct.pack('<16sHHIIIIIHHHHHH', ident, 3, machine, 1, 0, 52, 84, 0, 52, phsize, 1, shsize, 1, 0)
            with self.subTest(machine=machine, phsize=phsize, shsize=shsize), self.assertRaises(ValueError):
                elf_symbols(raw)


@unittest.skipUnless((ROOT / 'inputs/hl5-original-01.01.00.apk').exists(), 'Private target APK is not installed locally')
class LocalTargetProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apk = ROOT / 'inputs/hl5-original-01.01.00.apk'
        cls.profile = json.loads((ROOT / 'config/target-profile.json').read_text(encoding='utf-8'))

    def test_verified_inventory_preserves_input(self):
        before = sha256_file(self.apk)
        inventory = verify_target(self.apk, self.profile)
        self.assertEqual(inventory['apk']['sha256'], self.profile['apk_sha256'])
        self.assertEqual(before, sha256_file(self.apk))

    def test_unknown_fingerprint_and_changed_symbol_evidence_are_rejected(self):
        for kind in ('apk', 'symbol', 'code'):
            profile = deepcopy(self.profile)
            if kind == 'apk':
                profile['apk_sha256'] = '0' * 64
            elif kind == 'symbol':
                profile['runtime_profile']['required_symbols']['gv']['address'] += 4
            else:
                profile['runtime_profile']['required_symbols']['_Z12mainStateMgrv']['sha256'] = '0' * 64
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                verify_target(self.apk, profile)

    def test_reference_offsets_are_rejected_against_target_instructions(self):
        for field, wrong in [('state_offset', 0x27c), ('offline_flag_offset', 142), ('sms_flag_offset', 43)]:
            profile = deepcopy(self.profile)
            profile['runtime_profile'][field] = wrong
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'field offset'):
                verify_target(self.apk, profile)

    def test_undefined_imports_are_not_exposed_as_guest_entry_points(self):
        with zipfile.ZipFile(self.apk) as archive:
            symbols = elf_symbols(archive.read(self.profile['native_libraries'][0]['path']))
        self.assertNotIn('malloc', symbols)
        self.assertIn('Java_co_kr_eamobile_CletEntry_nativeStartApp', symbols)


if __name__ == '__main__':
    unittest.main()
