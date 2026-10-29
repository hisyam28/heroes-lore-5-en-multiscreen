#!/usr/bin/env python3
"""Stage a pinned reference runner plus an audited overlay and untouched target assets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

from inspect_apk import sha256_file
from target_profile import profile_header, verify_target

ROOT = Path(__file__).resolve().parents[1]


def prepare(apk: Path, reference: Path, output: Path, profile: dict, localization_vfs: Path | None = None) -> Path:
    output = output.resolve()
    if not output.is_relative_to(ROOT / 'work') or output == ROOT / 'work':
        raise ValueError('Stage must be a new directory inside work/')
    if output.exists():
        raise ValueError('Stage already exists; choose a new output directory')
    verify_target(apk, profile)
    if sha256_file(reference) != profile['reference_zip_sha256']:
        raise ValueError('Reference ZIP fingerprint mismatch')
    with zipfile.ZipFile(reference) as archive:
        names = [i.filename for i in archive.infolist()]
        if len(set(names)) != len(names):
            raise ValueError('Duplicate reference archive paths')
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:
                raise ValueError('Unsafe reference archive path')
        prefixes = {n.split('/android/app/src/main/')[0] for n in names if '/android/app/src/main/' in n}
        if len(prefixes) != 1:
            raise ValueError('Ambiguous reference runner root')
        prefix = prefixes.pop() + '/android/app/src/main/'
        source = output / 'app/src/main'
        for info in archive.infolist():
            if not info.filename.startswith(prefix) or info.is_dir():
                continue
            relative = PurePosixPath(info.filename[len(prefix):])
            if not relative.parts or relative.parts[0] == 'assets':
                continue
            if info.external_attr >> 16 & 0o170000 == 0o120000:
                raise ValueError('Reference symlinks are unsupported')
            destination = source.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(info))
    overlay = ROOT / 'tools/runner-modern.patch'
    subprocess.run(['git', 'apply', '--check', '--directory=' + output.relative_to(ROOT).as_posix(), str(overlay)], cwd=ROOT, check=True)
    subprocess.run(['git', 'apply', '--directory=' + output.relative_to(ROOT).as_posix(), str(overlay)], cwd=ROOT, check=True)
    for header in sorted((ROOT / 'tools/runtime').glob('*.h')):
        (source / 'cpp' / header.name).write_bytes(header.read_bytes())
    (source / 'cpp/target_profile.h').write_text(profile_header(profile), encoding='utf-8')
    assets = source / 'assets'
    assets.mkdir(exist_ok=True)
    with zipfile.ZipFile(apk) as baseline:
        for entry, name in [(profile['native_libraries'][0], 'libHeroesLore5.so'),
                            (profile['resource_archives'][0], 'data.vfs.mp3'),
                            ({'path': 'assets/mtouchdevice.txt'}, 'mtouchdevice.txt')]:
            (assets / name).write_bytes(baseline.read(entry['path']))
    unicorn = source / 'cpp/third_party/unicorn/lib/arm64-v8a/libunicorn.a'
    if sha256_file(unicorn) != profile['runner_dependency']['unicorn_static_sha256']:
        raise ValueError('Reference Unicorn dependency mismatch')
    if 'unicorn_arm32_static_sha256' in profile['runner_dependency']:
        arm32 = ROOT / 'work/dependencies/unicorn-arm32-build/libunicorn.a'
        if sha256_file(arm32) != profile['runner_dependency']['unicorn_arm32_static_sha256']:
            raise ValueError('Local ARM32 Unicorn dependency mismatch')
        destination = source / 'cpp/third_party/unicorn/lib/armeabi-v7a/libunicorn.a'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(arm32.read_bytes())
    if localization_vfs:
        from build_render_map import generate
        with zipfile.ZipFile(ROOT/'dist/hl5-01.01.00-test11-en.apk') as previous:
            old_english=previous.read('assets/data.vfs.mp3')
        evidence=generate((assets/'data.vfs.mp3').read_bytes(),localization_vfs.read_bytes(),old_english,source/'cpp/render_text_data.h')
        (output/'render-map-report.json').write_text(json.dumps(evidence,indent=2)+'\n')
    manifest = {'apk_sha256': profile['apk_sha256'], 'reference_zip_sha256': profile['reference_zip_sha256'],
                'overlay_sha256': sha256_file(overlay),
                'files': {p.relative_to(source).as_posix(): sha256_file(p) for p in sorted(source.rglob('*')) if p.is_file()}}
    (output / 'runner-stage.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, default=ROOT / 'inputs/hl5-original-01.01.00.apk')
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT / 'work/runner-target')
    parser.add_argument('--localization-vfs',type=Path)
    args = parser.parse_args()
    profile = json.loads((ROOT / 'config/target-profile.json').read_text(encoding='utf-8'))
    print('Prepared:', prepare(args.apk, args.reference, args.out, profile,args.localization_vfs))


if __name__ == '__main__':
    main()
