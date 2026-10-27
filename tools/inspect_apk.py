#!/usr/bin/env python3
"""Read-only APK inventory. This does not certify game/runtime compatibility."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import zipfile


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def elf_info(stream, size: int) -> dict:
    header = stream.read(64)
    if len(header) < 16 or header[:4] != b'\x7fELF':
        return {'valid_header': False, 'reason': 'Not an ELF header'}
    bits = {1: 32, 2: 64}.get(header[4])
    endian = {1: '<', 2: '>'}.get(header[5])
    if bits is None or endian is None:
        return {'valid_header': False, 'reason': 'Unknown ELF class or byte order'}
    fmt = endian + ('16sHHIIIIIHHHHHH' if bits == 32 else '16sHHIQQQIHHHHHH')
    if len(header) < struct.calcsize(fmt):
        return {'valid_header': False, 'reason': 'Truncated ELF header'}
    fields = struct.unpack_from(fmt, header)
    phoff, phsize, phcount = fields[5], fields[9], fields[10]
    phfmt = endian + ('8I' if bits == 32 else 'II6Q')
    if phcount and (phsize != struct.calcsize(phfmt) or
                    phoff + phsize * phcount > size or phsize * phcount > 1024 * 1024):
        return {'valid_header': False, 'reason': 'Invalid program header range'}
    alignments = []
    if phcount:
        stream.seek(phoff)
        for _ in range(phcount):
            raw = stream.read(phsize)
            if len(raw) != phsize:
                return {'valid_header': False, 'reason': 'Truncated program header'}
            program = struct.unpack(phfmt, raw)
            if program[0] == 1:
                alignments.append(program[-1])
    return {'valid_header': True, 'bits': bits,
            'machine': {40: 'ARM', 183: 'AArch64', 3: 'x86', 62: 'x86_64'}.get(fields[2], str(fields[2])),
            'load_segment_alignments': alignments}


def inspect_apk(path: Path) -> dict:
    entries = []
    libraries = []
    with zipfile.ZipFile(path) as archive:
        names = [info.filename for info in archive.infolist()]
        duplicates = [name for name, count in Counter(names).items() if count > 1]
        if duplicates:
            raise ValueError('Ambiguous duplicate ZIP entries: ' + ', '.join(duplicates[:5]))
        for name in names:
            relative = PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
                raise ValueError('Unsafe archive path: ' + name)
        if 'AndroidManifest.xml' not in names:
            raise ValueError('APK has no AndroidManifest.xml')
        for info in archive.infolist():
            if info.is_dir():
                continue
            digest = hashlib.sha256()
            with archive.open(info) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            entry = {'path': info.filename, 'bytes': info.file_size,
                     'compressed_bytes': info.compress_size,
                     'zip_compression': info.compress_type, 'sha256': digest.hexdigest()}
            entries.append(entry)
            parts = PurePosixPath(info.filename).parts
            if info.filename.endswith('.so'):
                with archive.open(info) as stream:
                    elf = elf_info(stream, info.file_size)
                libraries.append({'path': info.filename,
                                  'packaged_abi': parts[1] if len(parts) == 3 and parts[0] == 'lib' else None,
                                  'sha256': entry['sha256'], 'elf': elf})
        with archive.open('AndroidManifest.xml') as stream:
            prefix = stream.read(32)
        manifest_kind = 'binary_xml' if prefix.startswith(b'\x03\x00\x08\x00') else 'unparsed'
    resources = [e['path'] for e in entries if e['path'].lower().endswith(
        ('.vfs.mp3', '.vfs', '/binary.mod', '.jar')) or e['path'] == 'binary.mod']
    return {'schema_version': 1, 'status': 'inventory_only_compatibility_unverified',
            'apk': {'filename': path.name, 'bytes': path.stat().st_size, 'sha256': sha256_file(path)},
            'manifest': {'kind': manifest_kind, 'package_name': None,
                         'version_name': None, 'version_code': None,
                         'note': 'Use Android manifest tooling to obtain package/version; not inferred here.'},
            'entry_count': len(entries), 'native_libraries': libraries,
            'resource_candidates': resources, 'entries': entries}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    parser.add_argument('--out', type=Path, default=Path('work/target-inventory.json'))
    args = parser.parse_args()
    result = inspect_apk(args.apk)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Inventoried {result['entry_count']} entries and {len(result['native_libraries'])} libraries.")
    print('SHA-256: ' + result['apk']['sha256'])
    print('Compatibility is unverified. Inventory: ' + str(args.out))


if __name__ == '__main__':
    main()
