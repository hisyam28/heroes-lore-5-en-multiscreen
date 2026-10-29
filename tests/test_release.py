"""Verify the actual final package, update identity and shipped quest fix."""
from pathlib import Path
import hashlib
import json
import subprocess
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
RELEASE=json.loads((ROOT/'config/release.json').read_text())
APK=ROOT/'dist'/RELEASE['apk_file']
BASE=ROOT/'dist'/RELEASE['payload_baseline']
AAPT=ROOT/'work/android-tools/build-tools/android-16/aapt2.exe'


@unittest.skipUnless(APK.exists() and BASE.exists(),'Requires local final and baseline APKs')
class ReleasePackageTests(unittest.TestCase):
    def test_release_checksum_and_only_intended_package_payloads_change(self):
        self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(),RELEASE['payload_baseline_sha256'])
        self.assertEqual(APK.stat().st_size,RELEASE['apk_bytes'])
        self.assertEqual(hashlib.sha256(APK.read_bytes()).hexdigest(),RELEASE['apk_sha256'])
        allowed={'AndroidManifest.xml','lib/arm64-v8a/libhl5_arm64_bridge.so',
                 'lib/armeabi-v7a/libhl5_arm64_bridge.so'}
        with zipfile.ZipFile(BASE) as old,zipfile.ZipFile(APK) as new:
            names=lambda z:{n for n in z.namelist() if not n.startswith('META-INF/')}
            self.assertEqual(names(old),names(new))
            changed={n for n in names(old) if old.read(n)!=new.read(n)}
            self.assertEqual(changed,allowed)
            # The new text-line hook must be present in both actual host binaries.
            for name in allowed-{'AndroidManifest.xml'}:
                self.assertIn(b'_ZN5BFont12DrawTextLineEiiiiiPcii\0',new.read(name))

    @unittest.skipUnless(AAPT.exists(),'Requires local official Android Build Tools')
    def test_release_label_sdk_version_and_debug_flag(self):
        result=subprocess.run([str(AAPT),'dump','badging',str(APK)],capture_output=True,text=True,check=True).stdout
        self.assertIn("versionName='"+RELEASE['version_name']+"'",result)
        self.assertIn("versionCode='"+str(RELEASE['version_code'])+"'",result)
        self.assertIn("name='co.kr.eamobile.hl5.runner'",result)
        self.assertIn("application-label:'"+RELEASE['application_label']+"'",result)
        self.assertIn("minSdkVersion:'9'",result);self.assertIn("targetSdkVersion:'36'",result)
        self.assertNotIn('application-debuggable',result)
        self.assertNotIn('test',RELEASE['application_label'].lower())
        self.assertNotIn('test',APK.name.lower())


if __name__=='__main__':unittest.main()
