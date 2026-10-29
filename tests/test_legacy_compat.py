"""Check routing against the actual API9 SDK and old/modern DEX isolation."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from legacy_compat import COMPATIBILITY, build_primary, dex_classes, verify_dex_split

JDKS = list((ROOT / 'work/android-tools').glob('jdk-*/bin/javac.exe'))
OLD_ANDROID = ROOT / 'work/android-tools/platform/android-9/android.jar'
BASELINE = ROOT / 'inputs/hl5-original-01.01.00.apk'
OUTPUT = ROOT / 'dist/heroes-lore-5-english-multiscreen-v1.0.0.apk'


@unittest.skipUnless(JDKS and OLD_ANDROID.exists(), 'Requires local official API9 SDK and JDK')
class LegacyRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix='legacy-routing-', dir=ROOT / 'work')
        cls.addClassCleanup(temporary.cleanup)
        cls.directory = Path(temporary.name)
        cls.javac = JDKS[0]
        result = subprocess.run([str(cls.javac), '-source', '7', '-target', '7', '-bootclasspath', str(OLD_ANDROID),
            '-d', str(cls.directory), str(COMPATIBILITY / 'CompatibilityActivity.java')], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr)
        harness = cls.directory / 'RoutingHarness.java'
        harness.write_text('''public class RoutingHarness {
    public static void main(String[] args) {
        System.out.print(co.kr.eamobile.hl5.runner.CompatibilityActivity.routeFor(Integer.parseInt(args[0]),args[1]));
    }
}''', encoding='utf-8')
        result = subprocess.run([str(cls.javac), '-cp', str(cls.directory) + ';' + str(OLD_ANDROID),
            '-d', str(cls.directory), str(harness)], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr)

    def route(self, sdk, abi):
        result = subprocess.run([str(self.javac.with_name('java.exe')), '-cp', str(self.directory) + ';' + str(OLD_ANDROID),
            'RoutingHarness', str(sdk), abi], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_android_gingerbread_through_kitkat_uses_original_native_engine(self):
        for sdk in (9, 10, 14, 15, 16, 17, 18, 19, 20):
            for abi in ('armeabi', 'armeabi-v7a'):
                with self.subTest(sdk=sdk, abi=abi):
                    self.assertEqual(self.route(sdk, abi), 'co.kr.eamobile.HeroesLore5.HeroesLore5')

    def test_android_5_through_16_arm32_and_arm64_use_modern_runner(self):
        for sdk in (21, 22, 23, 24, 25, 26, 28, 30, 34, 35, 36):
            for abi in ('armeabi-v7a', 'arm64-v8a'):
                with self.subTest(sdk=sdk, abi=abi):
                    self.assertEqual(self.route(sdk, abi), 'co.kr.eamobile.hl5.runner.MainActivity')
        self.assertEqual(self.route(21, 'armeabi'), 'co.kr.eamobile.HeroesLore5.HeroesLore5')


class LegacyDexValidationTests(unittest.TestCase):
    def test_corrupt_and_non_legacy_dex_are_rejected(self):
        for raw in (b'', b'dex\n039\0' + bytes(200), b'dex\n035\0' + bytes(200)):
            with self.subTest(raw=raw[:8]), self.assertRaises(ValueError):
                dex_classes(raw)

    @unittest.skipUnless(BASELINE.exists(), 'Requires private target APK')
    def test_real_baseline_and_old_sdk_fingerprints_reject_corruption(self):
        with zipfile.ZipFile(BASELINE) as baseline:
            raw = baseline.read('classes.dex')
        self.assertIn('Lco/kr/eamobile/CletEntry;', dex_classes(raw))
        changed = raw[:-1] + bytes([raw[-1] ^ 1])
        with self.assertRaisesRegex(ValueError, 'checksum'):
            dex_classes(changed)
        with tempfile.TemporaryDirectory(prefix='legacy-sdk-', dir=ROOT / 'work') as temporary:
            wrong = Path(temporary) / 'wrong.jar'
            wrong.write_bytes(b'Not the official API9 SDK')
            with self.assertRaisesRegex(ValueError, 'Unrecognized API9 SDK'):
                build_primary(None, BASELINE, Path(temporary), Path('unused'), wrong, Path('unused'))

    @unittest.skipUnless(BASELINE.exists() and OUTPUT.exists(), 'Requires locally built universal APK')
    def test_built_apk_keeps_legacy_and_modern_definitions_in_separate_dex(self):
        with zipfile.ZipFile(OUTPUT) as apk:
            evidence = verify_dex_split(BASELINE, apk.read('classes.dex'), apk.read('classes2.dex'))
            self.assertFalse(evidence['device_tested'])
            with self.assertRaisesRegex(ValueError, 'Legacy classes'):
                verify_dex_split(BASELINE, apk.read('classes2.dex'), apk.read('classes.dex'))


if __name__ == '__main__':
    unittest.main()
