#!/usr/bin/env python3
"""Build the private, target-profiled ARM32/ARM64 runner. Never modifies the input APK.

Runner sources/dependencies remain local in work; no upstream binary is fetched
or substituted by this tool. This is an experimental sideload build, not a claim
that boot, gameplay, save migration or every Android device has been tested.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

from inspect_apk import elf_info, sha256_file
from target_profile import profile_header, verify_target
from legacy_compat import COMPATIBILITY, MIN_SDK, MODERN_MIN_SDK, build_primary, verify_dex_split
from apk_packaging import verify_resource_table

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str | Path) -> None:
    subprocess.run([str(arg) for arg in args], check=True)


def local_output(path: Path) -> Path:
    path = path.resolve()
    if not any(path.is_relative_to(ROOT / folder) for folder in ('work', 'dist')):
        raise ValueError('Outputs must stay in work/ or dist/')
    return path


def verify_assets(apk: Path, source: Path, profile: dict) -> dict[str, str]:
    verify_target(apk, profile)
    if (source / 'cpp/target_profile.h').read_text(encoding='utf-8') != profile_header(profile):
        raise ValueError('Staged runtime header disagrees with verified profile')
    expected = {
        'libHeroesLore5.so': profile['native_libraries'][0],
        'data.vfs.mp3': profile['resource_archives'][0],
    }
    hashes = {}
    with zipfile.ZipFile(apk) as baseline:
        for name, entry in expected.items():
            raw = baseline.read(entry['path'])
            digest = hashlib.sha256(raw).hexdigest()
            if digest != entry['sha256'] or sha256_file(source / 'assets' / name) != digest:
                raise ValueError('Baseline/staged asset mismatch: ' + name)
            hashes[name] = digest
        if baseline.read('assets/mtouchdevice.txt') != (source / 'assets/mtouchdevice.txt').read_bytes():
            raise ValueError('Target input configuration changed')
    stage_path = source.parents[2] / 'runner-stage.json'
    stage = json.loads(stage_path.read_text(encoding='utf-8'))
    if stage['apk_sha256'] != profile['apk_sha256']:
        raise ValueError('Staging manifest target mismatch')
    staged_files = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    if staged_files - {'assets/target-assets.json'} != set(stage['files']):
        raise ValueError('Staged runner file set changed; prepare a new stage')
    for relative, digest in stage['files'].items():
        if sha256_file(source / relative) != digest:
            raise ValueError('Staged runner changed; prepare again: ' + relative)
    return hashes


def verify_host_library(path: Path, abi: str = 'arm64-v8a') -> dict:
    raw = path.read_bytes()
    elf = elf_info(BytesIO(raw), len(raw))
    bits, machine = (64, 'AArch64') if abi == 'arm64-v8a' else (32, 'ARM')
    if not elf.get('valid_header') or elf.get('bits') != bits or elf.get('machine') != machine:
        raise ValueError('Host runner ELF does not match ABI: ' + abi)
    aligns = elf['load_segment_alignments']
    if not aligns or any(align < 16384 for align in aligns):
        raise ValueError('Host ELF is not 16 KB aligned')
    return elf


def verify_jni_exports(source: Path, host: Path, ndkbin: Path) -> list[str]:
    activity = source / 'java/co/kr/eamobile/hl5/runner/MainActivity.java'
    methods = re.findall(r'\bnative\s+\w+\s+(\w+)\s*\(', activity.read_text(encoding='utf-8'))
    expected = {'Java_co_kr_eamobile_hl5_runner_MainActivity_' + method for method in methods}
    result = subprocess.run([str(ndkbin / 'llvm-nm.exe'), '-D', '--defined-only', str(host)],
                            check=True, capture_output=True, text=True)
    exported = {line.split()[-1] for line in result.stdout.splitlines() if line.split()}
    if not expected or expected - exported:
        raise ValueError('Packaged host is missing Java native entry points: ' + ', '.join(sorted(expected - exported)))
    return sorted(expected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, default=ROOT / 'inputs/hl5-original-01.01.00.apk')
    parser.add_argument('--runner', type=Path, default=ROOT / 'work/runner-target/app/src/main')
    parser.add_argument('--ndk', type=Path, required=True)
    parser.add_argument('--jdk', type=Path, required=True)
    parser.add_argument('--build-tools', type=Path, required=True)
    parser.add_argument('--android-jar', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT / 'dist/hl5-01.01.00-test8-stability.apk')
    parser.add_argument('--include-legacy', action='store_true', help='Include the original native ARM engine for Android 2.3-4.4')
    parser.add_argument('--legacy-android-jar', type=Path, help='Official API9 android.jar for the legacy-only launcher')
    parser.add_argument('--english-vfs',type=Path)
    parser.add_argument('--version-code',type=int)
    parser.add_argument('--version-name')
    parser.add_argument('--application-label')
    parser.add_argument('--release',action='store_true',help='Disable Android debuggable flag; retain the existing update signer')
    args = parser.parse_args()
    if args.include_legacy and (args.legacy_android_jar is None or not args.legacy_android_jar.is_file()):
        parser.error('--include-legacy requires --legacy-android-jar (API9)')
    min_sdk = MIN_SDK if args.include_legacy else 26
    native_sdk = MODERN_MIN_SDK if args.include_legacy else 26
    if args.include_legacy and args.out == ROOT / 'dist/hl5-01.01.00-test8-stability.apk':
        args.out = ROOT / 'dist/hl5-01.01.00-test10-install.apk'
    if args.english_vfs and (not args.version_code or not args.version_name or
            args.out.resolve().name in ('hl5-01.01.00-test10-install.apk','hl5-01.01.00-test11-en.apk')):
        parser.error('English runtime builds require explicit version and a new output; preserve test10/test11 baselines')
    profile = json.loads((ROOT / 'config/target-profile.json').read_text(encoding='utf-8'))
    if profile.get('status') != 'statically_profiled_runtime_unverified':
        raise ValueError('Missing static target profile')
    source = local_output(args.runner)
    hashes = verify_assets(args.apk, source, profile)
    translated_vfs=None
    if args.english_vfs:
        from build_english_apk import verify_assets as verify_translation
        translated_vfs=args.english_vfs.read_bytes()
        verify_translation((source/'assets/data.vfs.mp3').read_bytes(),translated_vfs)
        mapping=source.parents[2]/'render-map-report.json'
        if not mapping.is_file() or json.loads(mapping.read_text())['english_vfs_sha256']!=hashlib.sha256(translated_vfs).hexdigest():
            raise ValueError('Display dictionary and packaged English VFS must match; prepare a new localized stage')
        hashes['data.vfs.mp3']=hashlib.sha256(translated_vfs).hexdigest()
    (source / 'assets/target-assets.json').write_text(json.dumps(hashes), encoding='utf-8')
    build_root = local_output(ROOT / 'work/android-build')
    build_root.mkdir(parents=True, exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix='run-', dir=build_root))
    for folder in ('classes', 'dex', 'lib'):
        (build / folder).mkdir(parents=True, exist_ok=True)
    output = local_output(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    ndkbin = args.ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    cpp = source / 'cpp'
    exports = build / 'runner-exports.map'
    exports.write_text('{ global: Java_co_kr_eamobile_hl5_runner_MainActivity_*; local: *; };\n', encoding='utf-8')
    units = ('native_runner', 'arm32_elf_loader', 'arm32_native_engine',
             'gles_bridge', 'vfs_adapter', 'jni_bridge_core')
    dependencies = {'arm64-v8a': ('aarch64-linux-android' + str(native_sdk), 'unicorn_static_sha256')}
    if 'unicorn_arm32_static_sha256' in profile['runner_dependency']:
        dependencies['armeabi-v7a'] = ('armv7a-linux-androideabi' + str(native_sdk), 'unicorn_arm32_static_sha256')
    hosts = {}
    for abi, (target, dependency_key) in dependencies.items():
        unicorn = cpp / 'third_party/unicorn/lib' / abi / 'libunicorn.a'
        if sha256_file(unicorn) != profile['runner_dependency'][dependency_key]:
            raise ValueError('Unrecognized local Unicorn dependency: ' + abi)
        directory = build / 'lib' / abi
        directory.mkdir()
        host = directory / 'libhl5_arm64_bridge.so'
        architecture = ['-marm', '-march=armv7-a', '-mfpu=vfpv3-d16'] if abi == 'armeabi-v7a' else []
        run(ndkbin / 'clang++.exe', '--target=' + target,
            '--sysroot=' + str(args.ndk / 'toolchains/llvm/prebuilt/windows-x86_64/sysroot'),
            *architecture, '-shared', '-fPIC', '-std=c++17', '-O3', '-static-libstdc++',
            '-ffunction-sections', '-fdata-sections', '-fvisibility=hidden',
            '-Wl,--gc-sections', '-Wl,--exclude-libs,ALL', '-Wl,--version-script=' + str(exports),
            '-Wl,-z,max-page-size=16384', '-Wl,-z,common-page-size=16384', '-Wl,-z,noexecstack',
            '-I' + str(cpp), '-I' + str(cpp / 'third_party/unicorn/include'),
            *[cpp / (unit + '.cpp') for unit in units], unicorn,
            '-ldl', '-llog', '-lm', '-latomic', '-o', host)
        unstripped = host.with_name('libhl5_arm64_bridge.unstripped.so')
        unstripped.write_bytes(host.read_bytes())
        run(ndkbin / 'llvm-strip.exe', '--strip-unneeded', host)
        hosts[abi] = {'path': host, 'unstripped': unstripped, 'elf': verify_host_library(host, abi),
                      'jni_exports': verify_jni_exports(source, host, ndkbin)}
    host = hosts['arm64-v8a']['path']
    unstripped = hosts['arm64-v8a']['unstripped']
    elf = hosts['arm64-v8a']['elf']
    jni_exports = hosts['arm64-v8a']['jni_exports']
    java = args.jdk / 'bin/java.exe'
    run(args.jdk / 'bin/javac.exe', '-encoding', 'UTF-8', '-source', '8', '-target', '8',
        '-classpath', args.android_jar, '-d', build / 'classes',
        *sorted((source / 'java').rglob('*.java')))
    run(java, '-cp', args.build_tools / 'lib/d8.jar', 'com.android.tools.r8.D8',
        '--min-api', str(native_sdk), '--lib', args.android_jar, '--output', build / 'dex',
        *sorted((build / 'classes').rglob('*.class')))
    legacy_primary = None
    legacy_evidence = None
    if args.include_legacy:
        legacy_primary = build_primary(run, args.apk, build, args.jdk, args.legacy_android_jar,
                                       args.build_tools / 'lib/d8.jar')
        legacy_evidence = verify_dex_split(args.apk, legacy_primary.read_bytes(), (build / 'dex/classes.dex').read_bytes())
        legacy_evidence['old_android_jar_sha256'] = sha256_file(args.legacy_android_jar)
    base = build / 'base.apk'
    manifest_source=COMPATIBILITY/'AndroidManifest.xml' if args.include_legacy else source/'AndroidManifest.xml'
    if args.version_code or args.version_name or args.application_label or args.release:
        manifest_text=manifest_source.read_text(encoding='utf8')
        if args.version_code:
            manifest_text=re.sub(r'android:versionCode="[^"]*"','android:versionCode="'+str(args.version_code)+'"',manifest_text)
        if args.version_name:
            if not re.fullmatch(r'[A-Za-z0-9.\-]+',args.version_name):raise ValueError('Invalid version name')
            manifest_text=re.sub(r'android:versionName="[^"]*"','android:versionName="'+args.version_name+'"',manifest_text)
        if args.application_label:
            if not re.fullmatch(r'[A-Za-z0-9 .\-]+',args.application_label):raise ValueError('Invalid app label')
            manifest_text=re.sub(r'android:label="[^"]*"','android:label="'+args.application_label+'"',manifest_text)
        if args.release:
            manifest_text=re.sub(r'android:debuggable="[^"]*"','android:debuggable="false"',manifest_text)
        manifest_source=build/'AndroidManifest.xml';manifest_source.write_text(manifest_text,encoding='utf8')
    # AAPT2 handles the SDK 36 resource table; legacy AAPT may reject it.
    if args.include_legacy:
        run(args.build_tools / 'aapt2.exe', 'link', '-o', base, '-I', args.android_jar,
            '-I', args.apk, '--manifest', manifest_source)
    else:
        compiled = build / 'resources.zip'
        run(args.build_tools / 'aapt2.exe', 'compile', '--dir', source / 'res', '-o', compiled)
        run(args.build_tools / 'aapt2.exe', 'link', '-o', base, '-I', args.android_jar,
            '--manifest', manifest_source, compiled)
    unsigned = build / 'unsigned.apk'
    with zipfile.ZipFile(base) as zin, zipfile.ZipFile(unsigned, 'w') as zout:
        for item in zin.infolist():
            if args.include_legacy and (item.filename == 'resources.arsc' or item.filename.startswith('res/')):
                continue
            zout.writestr(item, zin.read(item.filename))
        zout.write(legacy_primary or build / 'dex/classes.dex', 'classes.dex', compress_type=zipfile.ZIP_DEFLATED)
        if args.include_legacy:
            zout.write(build / 'dex/classes.dex', 'classes2.dex', compress_type=zipfile.ZIP_DEFLATED)
            with zipfile.ZipFile(args.apk) as baseline:
                for item in baseline.infolist():
                    if item.filename == 'resources.arsc':
                        # Preserve the decoded bytes/IDs, not the baseline ZIP codec.
                        # Target SDK30+ rejects compressed tables even when zipalign passes.
                        zout.writestr(item, baseline.read(item.filename), compress_type=zipfile.ZIP_STORED)
                    elif item.filename.startswith('res/'):
                        zout.writestr(item, baseline.read(item.filename))
                    elif item.filename.startswith('assets/') and not (source / item.filename).is_file() and not item.is_dir():
                        zout.writestr(item, baseline.read(item.filename))
                original = baseline.read(profile['native_libraries'][0]['path'])
                for abi in ('armeabi', 'armeabi-v7a'):
                    zout.writestr('lib/' + abi + '/libHeroesLore5.so', original, compress_type=zipfile.ZIP_DEFLATED)
        for abi, item in hosts.items():
            zout.write(item['path'], 'lib/' + abi + '/libhl5_arm64_bridge.so', compress_type=zipfile.ZIP_STORED)
        for asset in sorted((source / 'assets').iterdir()):
            if asset.is_file():
                # VFS must stay seekable/uncompressed for audio. TargetAssets
                # extracts the guest SO via a stream and verifies its raw hash.
                compression = zipfile.ZIP_DEFLATED if asset.name == 'libHeroesLore5.so' else zipfile.ZIP_STORED
                if asset.name=='data.vfs.mp3' and translated_vfs is not None:
                    zout.writestr('assets/'+asset.name,translated_vfs,compress_type=zipfile.ZIP_STORED)
                else:zout.write(asset, 'assets/' + asset.name, compress_type=compression)
    aligned = build / 'aligned.apk'
    run(args.build_tools / 'zipalign.exe', '-f', '-P', '16', '4', unsigned, aligned)
    verify_resource_table(aligned, 36)
    keystore = ROOT / 'work/local-test.keystore'
    if not keystore.exists():
        run(args.jdk / 'bin/keytool.exe', '-genkeypair', '-keystore', keystore,
            '-storepass', 'android', '-keypass', 'android', '-alias', 'hl5-test',
            '-dname', 'CN=HL5 Local Test', '-keyalg', 'RSA', '-keysize', '2048',
            '-validity', '3650')
    signer = args.build_tools / 'lib/apksigner.jar'
    run(java, '-jar', signer, 'sign', '--ks', keystore, '--ks-pass', 'pass:android',
        '--key-pass', 'pass:android', '--min-sdk-version', str(min_sdk),
        '--v1-signing-enabled', str(args.include_legacy).lower(), '--v2-signing-enabled', 'true',
        '--v3-signing-enabled', 'true', '--out', output, aligned)
    run(java, '-jar', signer, 'verify', '--verbose', '--print-certs', output)
    run(args.build_tools / 'zipalign.exe', '-c', '-P', '16', '4', output)
    resource_storage = verify_resource_table(output, 36)
    with zipfile.ZipFile(output) as result, zipfile.ZipFile(args.apk) as original:
        for name, entry in {'libHeroesLore5.so': profile['native_libraries'][0],
                            'data.vfs.mp3': profile['resource_archives'][0]}.items():
            expected=translated_vfs if name=='data.vfs.mp3' and translated_vfs is not None else original.read(entry['path'])
            if result.read('assets/' + name) != expected:
                raise ValueError('Final packaged baseline asset changed: ' + name)
        if result.read('assets/mtouchdevice.txt') != original.read('assets/mtouchdevice.txt'):
            raise ValueError('Final target input configuration changed')
        if args.include_legacy:
            for item in original.infolist():
                if item.filename=='assets/data.vfs.mp3' and translated_vfs is not None:continue
                if item.filename == 'resources.arsc' or item.filename.startswith(('res/', 'assets/')) and not item.is_dir():
                    if result.read(item.filename) != original.read(item.filename):
                        raise ValueError('Legacy baseline resource changed: ' + item.filename)
            for abi in ('armeabi', 'armeabi-v7a'):
                if result.read('lib/' + abi + '/libHeroesLore5.so') != original.read(profile['native_libraries'][0]['path']):
                    raise ValueError('Legacy native engine changed')
            verify_dex_split(args.apk, result.read('classes.dex'), result.read('classes2.dex'))
    if sha256_file(args.apk) != profile['apk_sha256']:
        raise ValueError('Input APK changed during build')
    report = {
        'status': 'signed_release_device_validation_pending' if args.release else 'signed_experimental_build_device_tests_pending',
        'input_sha256': profile['apk_sha256'], 'output_sha256': sha256_file(output),
        'apk_bytes': output.stat().st_size, 'host_elf': elf,
        'host_library_bytes': host.stat().st_size,
        'host_unstripped_bytes': unstripped.stat().st_size,
        'packaged_host_debug_symbols': False,
        'verified_jni_exports': jni_exports,
        'host_abis': {abi: {'elf': item['elf'], 'bytes': item['path'].stat().st_size,
                           'verified_jni_exports': item['jni_exports'], 'device_tested': False}
                      for abi, item in hosts.items()},
        'baseline_assets_identical': {k:v for k,v in hashes.items() if k!='data.vfs.mp3' or translated_vfs is None},
        'packaged_asset_hashes':hashes, 'target_sdk': 36, 'min_sdk': min_sdk,
        'modern_host_min_sdk': native_sdk, 'legacy_compatibility': legacy_evidence,
        'resource_table_storage': resource_storage,
        'english_vfs_applied':translated_vfs is not None,
        'version_code':args.version_code,'version_name':args.version_name,
        'release_build':args.release,
        'physical_device_tested': False, 'gameplay_verified': False,
        'build_directory': str(build.relative_to(ROOT)),
        'output_apk': output.relative_to(ROOT).as_posix(),
        'scope': 'ARM32/ARM64 runtime adaptation; original Korean guest SO/VFS and touch asset retained',
        'runner_source_hashes': {str(p.relative_to(source)): sha256_file(p)
                                 for p in sorted(source.rglob('*')) if p.is_file()},
    }
    if args.include_legacy:
        report['compatibility_source_hashes'] = {p.name: sha256_file(p) for p in COMPATIBILITY.iterdir() if p.is_file()}
        report['scope'] = 'Original native ARM engine on API9-20; optimized ARM32/ARM64 runner on API21+; device tests pending'
    (ROOT / 'work/android-build-report.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Release APK:' if args.release else 'Experimental APK:', output)
    print('SHA-256:', report['output_sha256'])
    print('Device boot, input, audio, FPS and save persistence still require testing.')


if __name__ == '__main__':
    main()
