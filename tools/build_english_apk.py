"""Repackage the accepted test10 APK; only VFS, its cache digest and version may change."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tempfile
import zipfile

from apk_packaging import verify_resource_table
from hl5_vfs import Vfs
from hl5_text import dat_schema,parse_dat,parse_scene
from translate_assets import KO,protected

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = '45243f4268f50dd30478d0439ea7345ecb7b9528a5e333fa11e8672fe7804e79'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def verify_assets(before, after):
    a,b=Vfs(before),Vfs(after)
    if [(e.name,e.hash) for e in a.entries]!=[(e.name,e.hash) for e in b.entries]:
        raise ValueError('VFS entry order/name/hash changed')
    changed=[]
    ui_path=ROOT/'translations/ui-overrides.json'
    ui=json.loads(ui_path.read_text(encoding='utf8')) if ui_path.exists() else {}
    for x,y in zip(a.entries,b.entries):
        if x.data==y.data:continue
        if dat_schema(x.name):
            first,second=parse_dat(x.name,x.data),parse_dat(x.name,y.data)
            if len(first)!=len(second) or [r.fragments for r in first]!=[r.fragments for r in second]:
                raise ValueError('DAT metadata changed: '+x.name)
            pairs=[(old,new,f'{x.name}#{i}:{j}') for i,(a,b) in enumerate(zip(first,second)) for j,(old,new) in enumerate(zip(a.fields,b.fields))]
        elif x.name.endswith('.scn'):
            first,second=parse_scene(x.data),parse_scene(y.data)
            if (first.prefix,first.widths)!=(second.prefix,second.widths):
                raise ValueError('SCN bytecode/header changed: '+x.name)
            pairs=[(a,b,None) for a,b in zip(first.strings,second.strings)]
        else:raise ValueError('Non-text asset changed: '+x.name)
        for old,new,key in pairs:
            source=old.decode('cp949','surrogateescape')
            if not KO.search(source) and old!=new:
                rule=ui.get(key)
                if not rule or sha(old)!=rule['source_sha256'] or new!=rule['translation'].encode('ascii'):
                    raise ValueError('Non-Korean text changed without approved UI rule: '+x.name)
            if old!=new:protected(source,new.decode('ascii'))
        changed.append(x.name)
    return changed


def run(*args):
    result=subprocess.run(list(map(str,args)),capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout


def build(args):
    base=args.base.resolve();out=args.out.resolve()
    if sha(base.read_bytes())!=BASE_SHA:raise ValueError('Unrecognized accepted runtime baseline')
    if not out.is_relative_to(ROOT/'dist') or out==base:raise ValueError('Output must be new file in dist/')
    source=args.vfs.read_bytes()
    with zipfile.ZipFile(base) as archive:
        changes=verify_assets(archive.read('assets/data.vfs.mp3'),source)
        hashes=json.loads(archive.read('assets/target-assets.json'))
    hashes['data.vfs.mp3']=sha(source)
    buildroot=Path(tempfile.mkdtemp(prefix='english-',dir=ROOT/'work'))
    manifest=(ROOT/'tools/compatibility/AndroidManifest.xml').read_text(encoding='utf8')
    if 'android:versionCode="1010010"' not in manifest:raise ValueError('Baseline manifest source changed')
    manifest=manifest.replace('android:versionCode="1010010"','android:versionCode="1010011"').replace('01.01.00-test10-install','01.01.00-test11-en')
    (buildroot/'AndroidManifest.xml').write_text(manifest,encoding='utf8')
    compiled=buildroot/'manifest.apk'
    run(args.build_tools/'aapt2.exe','link','-o',compiled,'-I',args.android_jar,
        '-I',ROOT/'inputs/hl5-original-01.01.00.apk','--manifest',buildroot/'AndroidManifest.xml')
    with zipfile.ZipFile(compiled) as archive:binary_manifest=archive.read('AndroidManifest.xml')
    unsigned=buildroot/'unsigned.apk'
    with zipfile.ZipFile(base) as archive,zipfile.ZipFile(unsigned,'w') as output:
        for item in archive.infolist():
            if item.filename.startswith('META-INF/'):continue
            raw=archive.read(item.filename)
            if item.filename=='assets/data.vfs.mp3':raw=source
            elif item.filename=='assets/target-assets.json':raw=json.dumps(hashes).encode()
            elif item.filename=='AndroidManifest.xml':raw=binary_manifest
            output.writestr(item,raw)
    aligned=buildroot/'aligned.apk'
    run(args.build_tools/'zipalign.exe','-f','-P','16','4',unsigned,aligned)
    verify_resource_table(aligned,36)
    key=ROOT/'work/local-test.keystore'
    if not key.is_file():raise ValueError('Existing signing key required; refusing to generate a new signer')
    java=args.jdk/'bin/java.exe';signer=args.build_tools/'lib/apksigner.jar'
    run(java,'-jar',signer,'sign','--ks',key,'--ks-pass','pass:android','--key-pass','pass:android',
        '--min-sdk-version','9','--v1-signing-enabled','true','--v2-signing-enabled','true','--v3-signing-enabled','true','--out',out,aligned)
    certs=[run(java,'-jar',signer,'verify','--verbose','--print-certs',apk) for apk in (base,out)]
    def certificate(text):return next(s.split(': ',1)[1] for s in text.splitlines() if s.startswith('Signer #1 certificate SHA-256 digest:'))
    if certificate(certs[0])!=certificate(certs[1]):raise ValueError('Update signer changed')
    run(args.build_tools/'zipalign.exe','-c','-P','16','4',out)
    allowed={'assets/data.vfs.mp3','assets/target-assets.json','AndroidManifest.xml'}
    with zipfile.ZipFile(base) as a,zipfile.ZipFile(out) as b:
        names=lambda z:{n for n in z.namelist() if not n.startswith('META-INF/')}
        if names(a)!=names(b):raise ValueError('APK entry set changed')
        different={n for n in names(a) if a.read(n)!=b.read(n)}
        if different!=allowed:raise ValueError('Unexpected APK payload change: '+str(different))
        if b.getinfo('assets/data.vfs.mp3').compress_type!=0:raise ValueError('VFS must remain seekable')
        # Compare parsed manifest trees, allowing only version attributes.
        trees=[run(args.build_tools/'aapt2.exe','dump','xmltree',apk,'--file','AndroidManifest.xml') for apk in (base,out)]
        normalized=lambda t:[line for line in t.splitlines() if 'versionCode(' not in line and 'versionName(' not in line]
        if normalized(trees[0])!=normalized(trees[1]):raise ValueError('Manifest behavior changed')
    report=dict(status='signed_english_asset_build_device_tests_pending',base_apk_sha256=BASE_SHA,
                output_sha256=sha(out.read_bytes()),output_apk=out.relative_to(ROOT).as_posix(),apk_bytes=out.stat().st_size,
                changed_apk_entries=sorted(allowed),changed_vfs_assets=changes,english_vfs_sha256=sha(source),
                native_libraries_and_dex_identical=True,fonts_and_input_identical=True,script_bytecode_identical=True,
                target_asset_fingerprint_updated=True,resource_storage=verify_resource_table(out,36),
                same_signer_sha256=certificate(certs[1]),physical_device_tested=False)
    (ROOT/'work/english-build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('English APK:',out,'SHA256:',report['output_sha256'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,default=ROOT/'dist/hl5-01.01.00-test10-install.apk')
    parser.add_argument('--vfs',type=Path,default=ROOT/'work/english-assets/data.vfs.mp3')
    parser.add_argument('--out',type=Path,default=ROOT/'dist/hl5-01.01.00-test11-en.apk')
    for name in ('jdk','build-tools','android-jar'):parser.add_argument('--'+name,type=Path,required=True)
    build(parser.parse_args())
