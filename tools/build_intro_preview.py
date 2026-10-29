"""Build a local Heroes Lore 5 APK with English intro assets; never publish or alter Git."""
from pathlib import Path
import argparse
import json
import re
import tempfile
import zipfile

from apk_packaging import verify_resource_table
from build_english_apk import run,sha
from localize_intro import BASE_SHA,SUBTITLE_BASE_SHA,verify_intro_assets,verify_subtitle_revision
from hl5_graphics import Png,write_png,resize_rgba

ROOT=Path(__file__).resolve().parents[1]


def build(a):
    base=a.base.resolve();out=a.out.resolve()
    base_digest=sha(base.read_bytes())
    if base_digest not in (BASE_SHA,SUBTITLE_BASE_SHA):raise ValueError('Unknown accepted preview baseline')
    if not out.is_relative_to(ROOT/'dist') or out==base or out.exists():raise ValueError('Choose a new local APK file in dist/')
    source=a.vfs.read_bytes()
    icon_source=a.icon.read_bytes();icon_image=Png(icon_source)
    if icon_image.width!=icon_image.height:raise ValueError('The supplied launcher icon must be square')
    icon=write_png(192,192,resize_rgba(icon_image,192,192))
    with zipfile.ZipFile(base) as z:
        verify=verify_subtitle_revision if base_digest==SUBTITLE_BASE_SHA else verify_intro_assets
        changes=verify(z.read('assets/data.vfs.mp3'),source)
        icon_changed=z.read('res/drawable/icon.png')!=icon
        fingerprints=json.loads(z.read('assets/target-assets.json'))
    fingerprints['data.vfs.mp3']=sha(source)
    stage=Path(tempfile.mkdtemp(prefix='intro-preview-',dir=ROOT/'work'))
    (stage/'launcher-icon-192.png').write_bytes(icon)
    text=(ROOT/'tools/compatibility/AndroidManifest.xml').read_text(encoding='utf8')
    if not re.fullmatch(r'\d+\.\d+\.\d+',a.version_name) or a.version_code<=1010103:raise ValueError('Invalid preview update version')
    for key,value in (('versionCode',str(a.version_code)),('versionName',a.version_name),('label','Heroes Lore 5'),('debuggable','false')):
        text=re.sub(r'android:'+key+r'="[^"]*"','android:'+key+'="'+value+'"',text)
    manifest=stage/'AndroidManifest.xml';manifest.write_text(text,encoding='utf8')
    compiled=stage/'manifest.apk'
    run(a.build_tools/'aapt2.exe','link','-o',compiled,'-I',a.android_jar,'-I',ROOT/'inputs/hl5-original-01.01.00.apk','--manifest',manifest)
    with zipfile.ZipFile(compiled) as z:binary_manifest=z.read('AndroidManifest.xml')
    unsigned=stage/'unsigned.apk'
    with zipfile.ZipFile(base) as old,zipfile.ZipFile(unsigned,'w') as new:
        for entry in old.infolist():
            if entry.filename.startswith('META-INF/'):continue
            raw=old.read(entry.filename)
            if entry.filename=='assets/data.vfs.mp3':raw=source
            elif entry.filename=='assets/target-assets.json':raw=json.dumps(fingerprints).encode()
            elif entry.filename=='AndroidManifest.xml':raw=binary_manifest
            elif entry.filename=='res/drawable/icon.png':raw=icon
            new.writestr(entry,raw)
    aligned=stage/'aligned.apk';run(a.build_tools/'zipalign.exe','-f','-P','16','4',unsigned,aligned)
    verify_resource_table(aligned,36)
    key=ROOT/'work/local-test.keystore'
    if not key.is_file():raise ValueError('Existing update key is required')
    java=a.jdk/'bin/java.exe';signer=a.build_tools/'lib/apksigner.jar'
    run(java,'-jar',signer,'sign','--ks',key,'--ks-pass','pass:android','--key-pass','pass:android',
        '--min-sdk-version','9','--v1-signing-enabled','true','--v2-signing-enabled','true','--v3-signing-enabled','true','--out',out,aligned)
    certificates=[run(java,'-jar',signer,'verify','--verbose','--print-certs',p) for p in (base,out)]
    digest=lambda s:next(line.split(': ',1)[1] for line in s.splitlines() if line.startswith('Signer #1 certificate SHA-256 digest:'))
    if digest(certificates[0])!=digest(certificates[1]):raise ValueError('Update signer changed')
    run(a.build_tools/'zipalign.exe','-c','-P','16','4',out)
    allowed={'AndroidManifest.xml','assets/data.vfs.mp3','assets/target-assets.json'}
    if icon_changed:allowed.add('res/drawable/icon.png')
    with zipfile.ZipFile(base) as old,zipfile.ZipFile(out) as new:
        names=lambda z:{n for n in z.namelist() if not n.startswith('META-INF/')}
        if names(old)!=names(new):raise ValueError('APK entry set changed')
        if {n for n in names(old) if old.read(n)!=new.read(n)}!=allowed:raise ValueError('Unexpected APK payload change')
        if new.getinfo('assets/data.vfs.mp3').compress_type!=0:raise ValueError('VFS is no longer seekable')
    trees=[run(a.build_tools/'aapt2.exe','dump','xmltree',p,'--file','AndroidManifest.xml') for p in (base,out)]
    normalize=lambda t:[line for line in t.splitlines() if not any(k+'(' in line for k in ('versionCode','versionName','label'))]
    if normalize(trees[0])!=normalize(trees[1]):raise ValueError('Manifest behavior changed')
    report={'status':'local_preview_device_validation_pending','application_label':'Heroes Lore 5','version_name':a.version_name,
            'version_code':a.version_code,'base_apk_sha256':base_digest,'apk_sha256':sha(out.read_bytes()),'apk_bytes':out.stat().st_size,
            'apk':out.relative_to(ROOT).as_posix(),'changed_apk_entries':sorted(allowed),'changed_vfs_assets':changes,
            'same_signer_sha256':digest(certificates[1]),'native_libraries_and_dex_identical':True,
            'animation_timing_identical':True,'title_cif_identical_to_1_0_3':base_digest==SUBTITLE_BASE_SHA,'script_opcodes_save_and_input_identical':True,
            'resource_table':verify_resource_table(out,36),'physical_device_tested':False,'published':False}
    report['icon']={'source_sha256':sha(icon_source),'packaged_sha256':sha(icon),'dimensions':[192,192],
                    'resource_path':'res/drawable/icon.png','resource_ids_unchanged':True,'source_composition_preserved':True}
    (ROOT/('work/intro-outline-build-report.json' if base_digest==SUBTITLE_BASE_SHA else 'work/intro-preview-build-report.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,default=ROOT/'dist/heroes-lore-5-v1.0.3.apk')
    p.add_argument('--vfs',type=Path,default=ROOT/'work/intro-v104-assets/data.vfs.mp3')
    p.add_argument('--out',type=Path,default=ROOT/'dist/heroes-lore-5-v1.0.5-art.apk')
    p.add_argument('--version-name',default='1.0.5');p.add_argument('--version-code',type=int,default=1010105)
    p.add_argument('--icon',type=Path,required=True,help='Provided app icon; converted to launcher size without cropping')
    for name in ('jdk','build-tools','android-jar'):p.add_argument('--'+name,type=Path,required=True)
    build(p.parse_args())
