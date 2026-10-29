"""Keep original Dalvik classes/resources separate from the modern ART runner."""
from pathlib import Path
import hashlib
import struct
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
COMPATIBILITY = ROOT / 'tools/compatibility'
MIN_SDK = 9
MODERN_MIN_SDK = 21
API9_JAR_SHA256 = '99bddc4363e5be6cc2fe9e243465cd9856c64b2c8238e1e1023acae59bb88469'


def dex_classes(raw: bytes) -> set[str]:
    """Read only validated DEX035 class definitions, not arbitrary string matches."""
    if len(raw) < 112 or raw[:8] != b'dex\n035\0':
        raise ValueError('Legacy Dalvik requires a DEX035 file')
    if struct.unpack_from('<I', raw, 32)[0] != len(raw):
        raise ValueError('DEX length mismatch')
    if struct.unpack_from('<II', raw, 36) != (112, 0x12345678):
        raise ValueError('Unsupported DEX header')
    if hashlib.sha1(raw[32:]).digest() != raw[12:32] or zlib.adler32(raw[12:]) != struct.unpack_from('<I', raw, 8)[0]:
        raise ValueError('DEX checksum mismatch')

    def table(header, stride):
        count, offset = struct.unpack_from('<II', raw, header)
        if offset < 112 or offset + count * stride > len(raw):
            raise ValueError('Truncated DEX table')
        return [offset + i * stride for i in range(count)]

    strings = []
    for item in table(56, 4):
        offset = struct.unpack_from('<I', raw, item)[0]
        for _ in range(5):
            if offset >= len(raw):
                raise ValueError('Truncated DEX string length')
            byte = raw[offset]; offset += 1
            if byte < 128:
                break
        else:
            raise ValueError('Invalid DEX string length')
        end = raw.find(b'\0', offset)
        if end < 0:
            raise ValueError('Unterminated DEX string')
        strings.append(raw[offset:end])
    types = []
    for item in table(64, 4):
        index = struct.unpack_from('<I', raw, item)[0]
        if index >= len(strings):
            raise ValueError('Invalid DEX type')
        types.append(strings[index])
    classes = set()
    for item in table(96, 32):
        index = struct.unpack_from('<I', raw, item)[0]
        if index >= len(types):
            raise ValueError('Invalid DEX class')
        classes.add(types[index].decode('ascii'))
    return classes


def build_primary(run, apk: Path, build: Path, jdk: Path, old_android_jar: Path, d8: Path) -> Path:
    if hashlib.sha256(old_android_jar.read_bytes()).hexdigest() != API9_JAR_SHA256:
        raise ValueError('Unrecognized API9 SDK; refusing to claim old-API compilation')
    classes = build / 'legacy-classes'
    dex = build / 'legacy-dex'
    classes.mkdir(); dex.mkdir()
    run(jdk / 'bin/javac.exe', '-encoding', 'UTF-8', '-source', '7', '-target', '7',
        '-bootclasspath', old_android_jar, '-d', classes, COMPATIBILITY / 'CompatibilityActivity.java')
    original = build / 'original.dex'
    with zipfile.ZipFile(apk) as baseline:
        original.write_bytes(baseline.read('classes.dex'))
    run(jdk / 'bin/java.exe', '-cp', d8, 'com.android.tools.r8.D8', '--min-api', str(MIN_SDK),
        '--lib', old_android_jar, '--output', dex, original, *sorted(classes.rglob('*.class')))
    if {p.name for p in dex.iterdir()} != {'classes.dex'}:
        raise ValueError('Legacy primary DEX unexpectedly needs multidex')
    return dex / 'classes.dex'


def verify_dex_split(apk: Path, primary: bytes, modern: bytes) -> dict:
    with zipfile.ZipFile(apk) as baseline:
        original = baseline.read('classes.dex')
    originals = dex_classes(original)
    legacy = dex_classes(primary)
    art = dex_classes(modern)
    launcher = 'Lco/kr/eamobile/hl5/runner/CompatibilityActivity;'
    main = 'Lco/kr/eamobile/hl5/runner/MainActivity;'
    if not originals <= legacy or legacy != originals | {launcher}:
        raise ValueError('Legacy classes missing or unexpected classes in primary DEX')
    if main not in art or legacy & art:
        raise ValueError('Modern/legacy DEX separation is invalid')
    return {'original_dex_sha256': hashlib.sha256(original).hexdigest(),
            'original_classes_preserved': len(originals), 'legacy_primary_classes': len(legacy),
            'modern_secondary_classes': len(art), 'primary_dex_version': '035',
            'old_launcher_compilation_api': MIN_SDK, 'modern_min_sdk': MODERN_MIN_SDK,
            'original_java_reencoded_by_d8': True, 'device_tested': False}
