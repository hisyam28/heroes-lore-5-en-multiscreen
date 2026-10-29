"""Reproduce the installer rejection missed by zipalign/signature checks."""
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from apk_packaging import verify_resource_table


class ResourceTableStorageTests(unittest.TestCase):
    def archive(self, compression, unaligned=False):
        temporary = tempfile.TemporaryDirectory(prefix='packaging-', dir=ROOT / 'work')
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / 'test.apk'
        with zipfile.ZipFile(path, 'w') as archive:
            if unaligned:
                archive.writestr('a', b'')
            archive.writestr('resources.arsc', b'unchanged resource bytes', compress_type=compression)
        return path

    def test_compressed_table_is_rejected_even_at_an_aligned_offset(self):
        path = self.archive(zipfile.ZIP_DEFLATED)
        old = verify_resource_table(path, 29)
        self.assertTrue(old['aligned_4_bytes'])
        with self.assertRaisesRegex(ValueError, 'INSTALL_PARSE_FAILED_RESOURCES_ARSC_COMPRESSED'):
            verify_resource_table(path, 36)

    def test_uncompressed_but_unaligned_table_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'aligned to 4 bytes'):
            verify_resource_table(self.archive(zipfile.ZIP_STORED, unaligned=True), 36)

    def test_stored_aligned_table_passes_without_changing_its_content(self):
        path = self.archive(zipfile.ZIP_STORED)
        self.assertTrue(verify_resource_table(path, 36)['uncompressed'])
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(archive.read('resources.arsc'), b'unchanged resource bytes')

    def test_missing_and_duplicate_tables_are_rejected(self):
        path = self.archive(zipfile.ZIP_STORED)
        with zipfile.ZipFile(path, 'a') as archive:
            with self.assertWarns(UserWarning):
                archive.writestr('resources.arsc', b'duplicate')
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            verify_resource_table(path, 36)
        with zipfile.ZipFile(path, 'w'):
            pass
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            verify_resource_table(path, 36)

    @unittest.skipUnless((ROOT / 'dist/hl5-01.01.00-test9-legacy.apk').exists(), 'Requires local rejected test9')
    def test_rejected_test9_reproduces_the_platform_storage_failure(self):
        with self.assertRaisesRegex(ValueError, 'INSTALL_PARSE_FAILED_RESOURCES_ARSC_COMPRESSED'):
            verify_resource_table(ROOT / 'dist/hl5-01.01.00-test9-legacy.apk', 36)

    @unittest.skipUnless((ROOT / 'dist/hl5-01.01.00-test10-install.apk').exists(), 'Requires local test10')
    def test_fixed_test10_satisfies_modern_installer_storage_rules(self):
        evidence = verify_resource_table(ROOT / 'dist/hl5-01.01.00-test10-install.apk', 36)
        self.assertTrue(evidence['uncompressed'])
        self.assertTrue(evidence['aligned_4_bytes'])


if __name__ == '__main__':
    unittest.main()
