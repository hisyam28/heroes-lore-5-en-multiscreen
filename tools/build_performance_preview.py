"""Compile an isolated native overlay and repack the local art preview; no publication."""
from pathlib import Path
import argparse
import json
import tempfile
import zipfile
from build_android_test import verify_assets,verify_host_library,verify_jni_exports
from build_english_apk import run,sha
from apk_packaging import verify_resource_table

ROOT=Path(__file__).resolve().parents[1]

def build(a):
    profile=json.loads((ROOT/'config/target-profile.json').read_text())
    source=a.runner.resolve();out=a.out.resolve();art=a.art.resolve()
    if not out.is_relative_to(ROOT/'dist') or out.exists():raise ValueError('Choose a new output in dist/')
    if not a.report.resolve().is_relative_to(ROOT/'work'):raise ValueError('Reports must stay in work/')
    verify_assets(ROOT/'inputs/hl5-original-01.01.00.apk',source,profile)
    previous=json.loads(a.art_report.read_text())
    if sha(art.read_bytes())!=previous['apk_sha256']:raise ValueError('Unknown local art preview')
    stage=Path(tempfile.mkdtemp(prefix='performance-preview-',dir=ROOT/'work'))
    cpp=source/'cpp';ndkbin=a.ndk/'toolchains/llvm/prebuilt/windows-x86_64/bin'
    exports=stage/'exports.map'
    exports.write_text('{ global: Java_co_kr_eamobile_hl5_runner_MainActivity_*; local: *; };\n')
    units=('native_runner','arm32_elf_loader','arm32_native_engine','gles_bridge','vfs_adapter','jni_bridge_core')
    hosts={};evidence={}
    for abi,target in (('arm64-v8a','aarch64-linux-android21'),('armeabi-v7a','armv7a-linux-androideabi21')):
        dependency=cpp/'third_party/unicorn/lib'/abi/'libunicorn.a'
        expected=profile['runner_dependency']['unicorn_static_sha256' if abi=='arm64-v8a' else 'unicorn_arm32_static_sha256']
        if sha(dependency.read_bytes())!=expected:raise ValueError('Unrecognized dependency')
        host=stage/(abi+'.so');architecture=['-marm','-march=armv7-a','-mfpu=vfpv3-d16'] if abi=='armeabi-v7a' else []
        run(ndkbin/'clang++.exe','--target='+target,'--sysroot='+str(ndkbin.parent/'sysroot'),
            *architecture,'-shared','-fPIC','-std=c++17','-O3','-static-libstdc++',
            '-ffunction-sections','-fdata-sections','-fvisibility=hidden','-Wl,--gc-sections',
            '-Wl,--exclude-libs,ALL','-Wl,--version-script='+str(exports),'-Wl,-z,max-page-size=16384',
            '-Wl,-z,common-page-size=16384','-Wl,-z,noexecstack','-I'+str(cpp),
            '-I'+str(cpp/'third_party/unicorn/include'),*[cpp/(u+'.cpp') for u in units],dependency,
            '-ldl','-llog','-lm','-latomic','-o',host)
        run(ndkbin/'llvm-strip.exe','--strip-unneeded',host)
        evidence[abi]={'elf':verify_host_library(host,abi),'jni_exports':verify_jni_exports(source,host,ndkbin),
                       'sha256':sha(host.read_bytes())}
        hosts['lib/'+abi+'/libhl5_arm64_bridge.so']=host.read_bytes()
    unsigned=stage/'unsigned.apk'
    with zipfile.ZipFile(art) as old,zipfile.ZipFile(unsigned,'w') as new:
        for entry in old.infolist():
            if not entry.filename.startswith('META-INF/'):
                new.writestr(entry,hosts.get(entry.filename,old.read(entry.filename)))
    aligned=stage/'aligned.apk';run(a.build_tools/'zipalign.exe','-f','-P','16','4',unsigned,aligned)
    java=a.jdk/'bin/java.exe';signer=a.build_tools/'lib/apksigner.jar'
    run(java,'-jar',signer,'sign','--ks',ROOT/'work/local-test.keystore','--ks-pass','pass:android',
        '--key-pass','pass:android','--min-sdk-version','9','--v1-signing-enabled','true',
        '--v2-signing-enabled','true','--v3-signing-enabled','true','--out',out,aligned)
    signatures=[run(java,'-jar',signer,'verify','--verbose','--print-certs',p) for p in (art,out)]
    digest=lambda s:next(x.split(': ',1)[1] for x in s.splitlines() if x.startswith('Signer #1 certificate SHA-256 digest:'))
    if digest(signatures[0])!=digest(signatures[1]):raise ValueError('Update signer changed')
    run(a.build_tools/'zipalign.exe','-c','-P','16','4',out)
    with zipfile.ZipFile(art) as old,zipfile.ZipFile(out) as new:
        names=lambda z:{n for n in z.namelist() if not n.startswith('META-INF/')}
        if names(old)!=names(new) or {n for n in names(old) if old.read(n)!=new.read(n)}!=set(hosts):
            raise ValueError('Unexpected performance payload change')
    report={'kind':'local_preview_physical_validation_pending','apk':out.relative_to(ROOT).as_posix(),
        'apk_sha256':sha(out.read_bytes()),'apk_bytes':out.stat().st_size,'version_name':previous['version_name'],'version_code':previous['version_code'],
        'application_label':'Heroes Lore 5','art_apk_sha256':previous['apk_sha256'],
        'changed_entries_from_art':sorted(hosts),'hosts':evidence,'same_signer_sha256':digest(signatures[1]),
        'dex_original_guest_legacy_libraries_and_save_format_unchanged':True,
        'optimizations':['Byte-exact native DES rounds using the live original key',
                         'Byte-exact RGB565 sprite blending and normal-orientation edge clipping',
                         'One save durability fence before close instead of one per write'],
        'resources':verify_resource_table(out,36),'physical_device_tested':False,'published':False}
    a.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--art-report',type=Path,default=ROOT/'work/intro-preview-build-report.json')
    p.add_argument('--report',type=Path,default=ROOT/'work/performance-preview-build-report.json')
    p.add_argument('--runner',type=Path,default=ROOT/'work/runner-v103-perf-build/app/src/main')
    p.add_argument('--art',type=Path,default=ROOT/'dist/heroes-lore-5-v1.0.3-art.apk')
    p.add_argument('--out',type=Path,default=ROOT/'dist/heroes-lore-5-v1.0.3.apk')
    for name in ('ndk','jdk','build-tools'):p.add_argument('--'+name,type=Path,required=True)
    build(p.parse_args())
