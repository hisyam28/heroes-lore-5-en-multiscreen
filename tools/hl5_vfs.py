"""Strict HL5 VFS reader; discovers and verifies the target manifest, never its index."""
from dataclasses import dataclass
from pathlib import PurePosixPath
import struct


def djb2(name: str) -> int:
    value = 5381
    for byte in name.lstrip('/\\').encode('ascii'):
        value = (value * 33 + byte) & 0xffffffff
    return value


@dataclass(frozen=True)
class Entry:
    name: str
    hash: int
    data: bytes


class Vfs:
    def __init__(self, raw: bytes):
        records = []; position = 0
        while position < len(raw):
            if position + 8 > len(raw):
                raise ValueError('Truncated VFS header')
            hashed, length = struct.unpack_from('<II', raw, position); position += 8
            if length > len(raw) - position:
                raise ValueError('Truncated VFS payload')
            records.append((hashed, raw[position:position + length])); position += length
        candidates = []
        for index, (_, data) in enumerate(records):
            if len(data) < 4 or struct.unpack_from('<I', data)[0] != len(records) - 1:
                continue
            try:
                parts = data[4:].split(b'\0')
                if parts[-1] != b'' or len(parts) != len(records):
                    continue
                names = [part.decode('ascii') for part in parts[:-1]]
                if len(set(names)) != len(names):
                    continue
                if any(not name or '\\' in name or ':' in name or PurePosixPath(name).is_absolute()
                       or '..' in PurePosixPath(name).parts for name in names):
                    continue
                named = [record for i, record in enumerate(records) if i != index]
                if all(djb2(name) == record[0] for name, record in zip(names, named)):
                    candidates.append((index, names))
            except (UnicodeError, ValueError):
                continue
        if len(candidates) != 1:
            raise ValueError('VFS manifest is missing or ambiguous')
        self.manifest_index, names = candidates[0]
        if '__manifest__.bin' in names:
            raise ValueError('Reserved VFS manifest name')
        names.insert(self.manifest_index, '__manifest__.bin')
        self.entries = [Entry(name, hashed, data) for name, (hashed, data) in zip(names, records)]
        self.by_name = {entry.name: entry for entry in self.entries}

    def build(self, replacements=None) -> bytes:
        replacements = replacements or {}
        if replacements.keys() - self.by_name.keys() or '__manifest__.bin' in replacements:
            raise ValueError('Unknown VFS asset or manifest replacement')
        return b''.join(struct.pack('<II', entry.hash, len(replacements.get(entry.name, entry.data)))
                        + replacements.get(entry.name, entry.data) for entry in self.entries)
