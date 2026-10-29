"""Check install-time resource table storage rules, beyond ZIP alignment alone."""
from pathlib import Path
import struct
import zipfile


def verify_resource_table(apk: Path, target_sdk: int) -> dict:
    with zipfile.ZipFile(apk) as archive:
        if archive.namelist().count('resources.arsc') != 1:
            raise ValueError('APK must contain exactly one resources.arsc')
        entry = archive.getinfo('resources.arsc')
        with apk.open('rb') as stream:
            stream.seek(entry.header_offset)
            header = stream.read(30)
        if len(header) != 30 or header[:4] != b'PK\x03\x04':
            raise ValueError('Invalid resources.arsc local ZIP header')
        name_size, extra_size = struct.unpack_from('<HH', header, 26)
        offset = entry.header_offset + 30 + name_size + extra_size
        stored = entry.compress_type == zipfile.ZIP_STORED
        aligned = offset % 4 == 0
        if target_sdk >= 30 and (not stored or not aligned):
            raise ValueError('INSTALL_PARSE_FAILED_RESOURCES_ARSC_COMPRESSED: target SDK30+ requires '
                             'uncompressed resources.arsc aligned to 4 bytes')
        return {'compression': entry.compress_type, 'uncompressed': stored,
                'data_offset': offset, 'aligned_4_bytes': aligned, 'target_sdk': target_sdk}
