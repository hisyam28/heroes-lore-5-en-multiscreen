"""Lossless text-field edits: opaque DAT metadata and SCN bytecode stay untouched."""
from dataclasses import dataclass
import struct


def dat_schema(path):
    name = path.split('/')[-1]
    if path.startswith('c/csv2/help_'):
        return (0, (('title', 2, 0), ('body', 2, 0)))
    if not path.startswith('c/csv/'):
        return None
    if name in ('common_text.dat','ingame_text.dat','menu_text.dat','mission_text.dat','name.dat','tips.dat'):
        return (0, (('text', 1, 0),))
    if name in ('class.dat','buildup.dat','set_option.dat','mission_list.dat') or name.startswith('enemy_') and name not in ('enemy_g.dat','enemy_g_expert.dat'):
        return (0, (('name', 1, 0),))
    if name.startswith('cash_'):
        return (3, (('name', 1, 2), ('description', 1, 0)))
    if name.startswith('skill_'):
        return (0, (('name', 1, 47), ('description', 1, 0)))
    if name.startswith(('item_', 'smith_')):
        return (2, (('name', 1, 4), ('description', 1, 0)))
    if name.startswith('quest_'):
        return (3, (('title', 1, 0), ('description', 1, 0), ('category', 1, 0)))
    return None


@dataclass
class TextRecord:
    fields: list[bytes]
    widths: list[int]
    fragments: list[bytes]

    def build(self, fields=None):
        fields = self.fields if fields is None else fields
        if len(fields) != len(self.fields):
            raise ValueError('Text field count changed')
        result = self.fragments[0]
        for value, width, fragment in zip(fields, self.widths, self.fragments[1:]):
            if len(value) >= 1 << (width * 8):
                raise ValueError('Text length does not fit original encoding')
            result += len(value).to_bytes(width, 'little') + value + fragment
        return result


def parse_dat(path, raw):
    schema = dat_schema(path)
    if schema is None or len(raw) < 2:
        raise ValueError('Unknown or truncated DAT')
    start, specs = schema
    count = struct.unpack_from('<H', raw)[0]; position = 2; records = []
    for _ in range(count):
        if position + 2 > len(raw):
            raise ValueError('Truncated DAT row size')
        size = struct.unpack_from('<H', raw, position)[0]; position += 2
        row = raw[position:position + size]; position += size
        if len(row) != size or len(row) < start:
            raise ValueError('Truncated DAT row')
        cursor = start; fields = []; widths = []; fragments = [row[:start]]
        for _, width, gap in specs:
            if cursor + width > size:
                raise ValueError('Truncated DAT string length')
            length = int.from_bytes(row[cursor:cursor + width], 'little'); cursor += width
            if cursor + length + gap > size:
                raise ValueError('DAT string overlaps metadata boundary')
            fields.append(row[cursor:cursor + length]); widths.append(width); cursor += length
            fragments.append(row[cursor:cursor + gap]); cursor += gap
        fragments[-1] += row[cursor:]
        records.append(TextRecord(fields, widths, fragments))
    if position != len(raw):
        raise ValueError('DAT trailing bytes')
    return records


def build_dat(records):
    chunks = [struct.pack('<H', len(records))]
    for row in records:
        raw = row.build()
        if len(raw) > 65535:
            raise ValueError('DAT row too long')
        chunks += [struct.pack('<H', len(raw)), raw]
    return b''.join(chunks)


@dataclass
class Scene:
    prefix: bytes
    widths: list[int]
    strings: list[bytes]
    title_index: int

    def build(self, strings=None):
        strings = self.strings if strings is None else strings
        if len(strings) != len(self.strings):
            raise ValueError('Scene string count changed')
        lengths = []
        for value, width in zip(strings, self.widths):
            if len(value) >= 1 << (width * 8):
                raise ValueError('Scene text requires a header change; shorten it')
            lengths.append(len(value).to_bytes(width, 'little'))
        return self.prefix + b''.join(lengths) + b''.join(strings)


def parse_scene(raw):
    if len(raw) < 16:
        raise ValueError('Truncated scene')
    mtf = raw[:3] == b'\3\3\3'
    types = (2, 2, 3) if mtf else tuple(raw[:3]); position = 4 if mtf else 3
    if any(t not in (0, 1, 2, 3) for t in types):
        raise ValueError('Unknown scene length types')
    title = raw[position + 1]; position += 12
    for typ in types[:2]:
        if position >= len(raw):
            raise ValueError('Truncated scene scripts')
        count = raw[position]; position += 1; total = 0; width = 2 if typ > 1 else 1
        for _ in range(count):
            if position + width > len(raw):
                raise ValueError('Truncated script lengths')
            total += int.from_bytes(raw[position:position + width], 'little'); position += width
        position += total
    count_width = 2 if types[2] == 3 else 1
    if types[2] == 3:
        position += 1
    if position + count_width > len(raw):
        raise ValueError('Truncated scene strings')
    count = int.from_bytes(raw[position:position + count_width], 'little'); position += count_width
    prefix = raw[:position]; lengths = []; width = 2 if types[2] > 1 else 1
    for _ in range(count):
        if position + width > len(raw):
            raise ValueError('Truncated string lengths')
        lengths.append(int.from_bytes(raw[position:position + width], 'little')); position += width
    strings = []
    for length in lengths:
        if position + length > len(raw):
            raise ValueError('Truncated scene string')
        strings.append(raw[position:position + length]); position += length
    if position != len(raw):
        raise ValueError('Scene trailing bytes')
    return Scene(prefix, [width] * count, strings, title)
