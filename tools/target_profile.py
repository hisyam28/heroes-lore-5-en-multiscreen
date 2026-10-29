"""Verify the immutable target and the symbol evidence before preparing a runner."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import struct
import zipfile

from inspect_apk import inspect_apk


@dataclass(frozen=True)
class Symbol:
    address: int
    size: int
    data: bytes


def elf_symbols(raw: bytes) -> dict[str, Symbol]:
    """Read bounded ELF32/ARM dynamic symbols; never infer a table's end."""
    def bounded(offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset + size > len(raw):
            raise ValueError('Truncated ELF range')
        return raw[offset:offset + size]

    header = struct.unpack('<16sHHIIIIIHHHHHH', bounded(0, 52))
    if header[0][:7] != b'\x7fELF\x01\x01\x01' or header[1:3] != (3, 40):
        raise ValueError('Expected little-endian ARM32 shared ELF')
    phoff, shoff, phsize, phcount, shsize, shcount = (
        header[5], header[6], header[9], header[10], header[11], header[12])
    if phsize != 32 or shsize != 40 or not phcount or not shcount:
        raise ValueError('Unsupported ELF header tables')
    phraw = bounded(phoff, phsize * phcount)
    shraw = bounded(shoff, shsize * shcount)
    segments = list(struct.iter_unpack('<8I', phraw))
    sections = list(struct.iter_unpack('<10I', shraw))
    for typ, offset, address, _, filesz, memsz, _, _ in segments:
        if typ == 1:
            bounded(offset, filesz)
            if filesz > memsz or address + memsz > 0xffffffff:
                raise ValueError('Invalid ELF load segment')
    tables = [s for s in sections if s[1] == 11]
    if len(tables) != 1:
        raise ValueError('Expected one dynamic symbol table')
    table = tables[0]
    if table[9] != 16 or table[5] % 16 or table[6] >= len(sections):
        raise ValueError('Invalid ELF symbol table')
    strings = sections[table[6]]
    if strings[1] != 3:
        raise ValueError('Invalid symbol string table')
    names = bounded(strings[4], strings[5])
    result = {}
    for nameoff, address, size, _, _, section in struct.iter_unpack('<IIIBBH', bounded(table[4], table[5])):
        if not nameoff or section == 0:
            continue
        end = names.find(b'\0', nameoff)
        if nameoff >= len(names) or end < 0:
            raise ValueError('Invalid ELF symbol name')
        name = names[nameoff:end].decode('ascii')
        data = b''
        for typ, offset, start, _, filesz, _, _, _ in segments:
            if typ == 1 and start <= address and address + size <= start + filesz:
                data = bounded(offset + address - start, size)
                break
        if name in result:
            raise ValueError('Ambiguous dynamic symbol: ' + name)
        result[name] = Symbol(address, size, data)
    return result


def verify_target(apk: Path, profile: dict) -> dict:
    if profile.get('status') != 'statically_profiled_runtime_unverified':
        raise ValueError('A statically verified target profile is required')
    inventory = inspect_apk(apk)
    if inventory['apk']['sha256'] != profile['apk_sha256']:
        raise ValueError('Target APK fingerprint mismatch; refusing unknown version')
    with zipfile.ZipFile(apk) as archive:
        guest = archive.read(profile['native_libraries'][0]['path'])
        for entry in profile['native_libraries'] + profile['resource_archives']:
            if hashlib.sha256(archive.read(entry['path'])).hexdigest() != entry['sha256']:
                raise ValueError('Target asset fingerprint mismatch')
    symbols = elf_symbols(guest)
    for name, expected in profile['runtime_profile']['required_symbols'].items():
        symbol = symbols.get(name)
        if symbol is None or symbol.address != expected['address'] or symbol.size != expected['bytes']:
            raise ValueError('Target symbol mismatch: ' + name)
        if 'sha256' in expected and hashlib.sha256(symbol.data).hexdigest() != expected['sha256']:
            raise ValueError('Target function mismatch: ' + name)
    runtime = profile['runtime_profile']
    if runtime['gv_address'] != symbols['gv'].address or runtime['menu_vtable_address'] != symbols['_ZTV13StateMainMenu'].address:
        raise ValueError('Runtime symbol profile mismatch')
    # Instruction locations below were inspected in this fingerprinted target.
    # ARM LDR/STR immediate and LDRSB immediate have different immediate layouts.
    state_word = struct.unpack_from('<I', symbols['_Z12mainStateMgrv'].data, 0x44)[0]
    offline_word = struct.unpack_from('<I', symbols['_ZN13StateMainMenu8KeyTitleEi'].data, 0x30)[0]
    sms_word = struct.unpack_from('<I', symbols['_ZN8CommonUi17LoadLocalSaveDataEv'].data, 0x50)[0]
    derived = {'state_offset': state_word & 0xfff,
               'offline_flag_offset': ((offline_word >> 4) & 0xf0) | (offline_word & 0xf),
               'sms_flag_offset': sms_word & 0xfff}
    if any(runtime[name] != value for name, value in derived.items()):
        raise ValueError('Runtime field offset disagrees with target instructions')
    return inventory


def profile_header(profile: dict) -> str:
    fields = ('gv_address', 'menu_vtable_address', 'state_offset', 'offline_flag_offset', 'sms_flag_offset')
    return ('#pragma once\n#include <cstdint>\nnamespace hl5 { namespace target {\n' +
            ''.join(f'constexpr uint32_t {name} = 0x{profile["runtime_profile"][name]:x};\n' for name in fields) + '}}\n')
