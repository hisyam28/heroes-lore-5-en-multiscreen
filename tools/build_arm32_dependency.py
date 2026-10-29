"""Build the local ARM32 Unicorn dependency from a fingerprinted source ZIP."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = 'https://codeload.github.com/unicorn-engine/unicorn/zip/refs/tags/2.1.2'
SOURCE_SHA256 = '4caf20f161004a9a5fc8eeff5f014a16495f9af4c3dc022caa747c13bae78ced'


def build(ndk, cmake, ninja, shell_directory, record_profile=False):
    output = (ROOT / 'work/dependencies').resolve()
    if not output.is_relative_to((ROOT / 'work').resolve()):
        raise ValueError('Dependency output must stay in work/')
    output.mkdir(parents=True, exist_ok=True)
    archive = output / 'unicorn-2.1.2-source.zip'
    if not archive.exists():
        urllib.request.urlretrieve(SOURCE_URL, archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unrecognized source ZIP; refusing compilation')
    with zipfile.ZipFile(archive) as zipped:
        for item in zipped.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in item.filename or ':' in item.filename:
                raise ValueError('Unsafe source path')
            if item.external_attr >> 16 & 0o170000 == 0o120000:
                raise ValueError('Source symlinks are unsupported')
        for item in zipped.infolist():
            if item.is_dir():
                continue
            path = output.joinpath(*PurePosixPath(item.filename).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(zipped.read(item))
    source = output / 'unicorn-2.1.2'
    bundle = source / 'cmake/bundle_static.cmake'
    bundle.write_text(bundle.read_text().replace('-E create_symlink', '-E copy_if_different'), newline='\n')
    host_tools = output / 'host-tools'
    host_tools.mkdir(exist_ok=True)
    shutil.copyfile(ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strings.exe', host_tools / 'strings.exe')
    environment = os.environ.copy()
    environment['PATH'] = os.pathsep.join((str(host_tools), str(shell_directory), environment['PATH']))
    # This configure script only checks existence and never queries packages.
    # All required compatibility code is part of the fingerprinted source.
    environment['PKG_CONFIG'] = str(shell_directory / 'false.exe')
    directory = output / 'unicorn-arm32-build'
    configure = [str(cmake), '-S', str(source), '-B', str(directory), '-G', 'Ninja',
                 '-DCMAKE_MAKE_PROGRAM:FILEPATH=' + str(ninja),
                 '-DCMAKE_TOOLCHAIN_FILE=' + str(ndk / 'build/cmake/android.toolchain.cmake'),
                 '-DANDROID_ABI=armeabi-v7a', '-DANDROID_PLATFORM=android-26',
                 '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
                 '-DUNICORN_ARCH=arm', '-DBUILD_SHARED_LIBS=OFF', '-DUNICORN_BUILD_TESTS=OFF',
                 '-DUNICORN_INSTALL=OFF', '-DUNICORN_LEGACY_STATIC_ARCHIVE=ON', '-DCMAKE_C_FLAGS=']
    with (output / 'arm32-configure.log').open('w') as log:
        subprocess.run(configure, stdout=log, stderr=subprocess.STDOUT, env=environment, check=True)
    configuration = directory / 'config-host.h'
    if not configuration.exists() or '#define CONFIG_POSIX' not in configuration.read_text():
        raise ValueError('QEMU configure did not produce Android/POSIX headers; inspect the local log')
    with (output / 'arm32-build.log').open('w') as log:
        subprocess.run([str(cmake), '--build', str(directory), '--target', 'unicorn_archive', '-j', '4'],
                       stdout=log, stderr=subprocess.STDOUT, env=environment, check=True)
    library = directory / 'libunicorn.a'
    digest = hashlib.sha256(library.read_bytes()).hexdigest()
    provenance = {'source_url': SOURCE_URL, 'source_sha256': SOURCE_SHA256,
                  'library_sha256': digest, 'abi': 'armeabi-v7a', 'min_sdk': 26,
                  'source_patch': 'Optional .o symlink replaced by byte-identical copy on Windows'}
    (output / 'arm32-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    if record_profile:
        path = ROOT / 'config/target-profile.json'
        profile = json.loads(path.read_text())
        profile['runner_dependency']['unicorn_arm32_static_sha256'] = digest
        profile['runner_dependency']['arm32_source_archive_sha256'] = SOURCE_SHA256
        path.write_text(json.dumps(profile, indent=2) + '\n', newline='\n')
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('ndk', 'cmake', 'ninja', 'shell-directory'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--record-profile', action='store_true')
    args = parser.parse_args()
    print('Local ARM32 dependency SHA-256:', build(
        args.ndk.resolve(), args.cmake.resolve(), args.ninja.resolve(),
        args.shell_directory.resolve(), args.record_profile))


if __name__ == '__main__':
    main()
