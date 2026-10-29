"""Translate only target VFS text; preserve every script, table field and other asset."""
from pathlib import Path
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import re
import zipfile

from hl5_vfs import Vfs
from hl5_text import dat_schema, parse_dat, build_dat, parse_scene
from english_layout import COLORS, PLACEHOLDERS, english_without_apostrophes, context_limits, reflow, visible_width, flowing_dialogue
from target_profile import verify_target

ROOT = Path(__file__).resolve().parents[1]
KO = re.compile(r'[\uac00-\ud7a3\u3131-\u318e]')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_text(raw):
    return raw.decode('cp949', 'surrogateescape')


def protected(source, translated):
    if Counter(PLACEHOLDERS.findall(source)) != Counter(PLACEHOLDERS.findall(translated)):
        raise ValueError('Placeholder changed')
    if Counter(c for c in source if c in COLORS) != Counter(c for c in translated if c in COLORS):
        raise ValueError('Font color/control code changed')
    prefix = re.match(r'^(?:N[0-9]|EVENT_)', source)
    if prefix and not translated.startswith(prefix.group()):
        raise ValueError('Scene display prefix changed')
    if source.count('\0') != translated.count('\0'):
        raise ValueError('Embedded string terminator changed')


def translate(reference, output):
    output = output.resolve()
    if not output.is_relative_to(ROOT / 'work') or output == ROOT / 'work':
        raise ValueError('Output must be inside work/')
    profile = json.loads((ROOT / 'config/target-profile.json').read_text(encoding='utf8'))
    apk = ROOT / 'inputs/hl5-original-01.01.00.apk'
    verify_target(apk, profile)
    if sha(reference.read_bytes()) != profile['reference_zip_sha256']:
        raise ValueError('Reference ZIP fingerprint mismatch')
    with zipfile.ZipFile(reference) as ref:
        def member(suffix):
            matches = [name for name in ref.namelist() if name.endswith('/' + suffix)]
            if len(matches) != 1:
                raise ValueError('Ambiguous reference member: ' + suffix)
            return ref.read(matches[0])
        catalog = json.loads(member('translations/catalog.json'))['slots']
        memory = {x['source']:x['translation'] for x in json.loads(member('translations/unique_strings.json'))['strings']}
        ref_vfs = Vfs(member('android/app/src/main/assets/data.vfs.mp3'))
    by_context = defaultdict(list)
    for slot in catalog:
        by_context[(slot['file'], slot['field_index'], slot['source'])].append(slot)
    overrides = json.loads((ROOT / 'translations/slot-overrides.json').read_text(encoding='utf8'))
    ui_path=ROOT/'translations/ui-overrides.json'
    ui_overrides=json.loads(ui_path.read_text(encoding='utf8')) if ui_path.exists() else {}
    with zipfile.ZipFile(apk) as source:
        raw = source.read('assets/data.vfs.mp3')
    vfs = Vfs(raw)
    if vfs.build() != raw:
        raise ValueError('VFS round-trip failed')
    replacements = {}; entries = []; stats = Counter(); differences = []; issues = []
    for asset in vfs.entries:
        schema = dat_schema(asset.name)
        if schema:
            records = parse_dat(asset.name, asset.data)
            original_records = parse_dat(asset.name, asset.data)
            if build_dat(records) != asset.data:
                raise ValueError('DAT round-trip failed: ' + asset.name)
            contexts = [(i,j,value,schema[1][j][0],row) for i,row in enumerate(records) for j,value in enumerate(row.fields)]
            old_ref = parse_dat(asset.name, ref_vfs.by_name[asset.name].data)
            stats['dat_files_verified'] += 1
        elif asset.name.endswith('.scn'):
            scene = parse_scene(asset.data)
            if scene.build() != asset.data:
                raise ValueError('SCN round-trip failed: ' + asset.name)
            original_strings = scene.strings.copy()
            contexts = [(i,0,value,'title' if i==scene.title_index else 'dialogue',None) for i,value in enumerate(scene.strings)]
            old_scene = parse_scene(ref_vfs.by_name[asset.name].data)
            if scene.prefix != old_scene.prefix:
                differences.append(asset.name)
            stats['scn_files_verified'] += 1
        else:
            continue
        for i,j,value,field,row in contexts:
            src = source_text(value)
            stats['text_slots_scanned'] += 1
            ui=ui_overrides.get(f'{asset.name}#{i}:{j}')
            if ui and ui['source_sha256']!=sha(value):
                raise ValueError('UI override source changed')
            if not KO.search(src) and not ui:
                stats['non_korean_slots_preserved'] += 1
                continue
            candidates = by_context.get((asset.name,j,src), [])
            # Source + asset + field context required. Row is not a transfer key.
            matching = next((c for c in candidates if c['row_index']==i), candidates[0] if candidates else None)
            sid = matching['id'] if matching else f'{asset.name}#{i}:' + ('str' if not schema else 'text')
            if not matching and sid not in overrides and not ui:
                raise ValueError('No source/context match: ' + sid)
            ref_text = memory.get(src)
            if ui:
                text=ui['translation'];provenance='verified_ui_label_override'
            elif sid in overrides:
                text = overrides[sid]; provenance = 'editorial_override'
            elif ref_text:
                text = english_without_apostrophes(ref_text).replace('~', "'")
                provenance = 'reference_source_and_file_field_match'
            else:
                raise ValueError('Missing reference English: ' + sid)
            # Keep stored trailing NULs, even for the one damaged target source.
            suffix = '\0' * (len(value)-len(value.rstrip(b'\0')))
            text = text.rstrip('\0')
            if field == 'name':
                text = text.replace('Tome of Restoration (5)','Restore Tome (5)').replace('Amulet of Rebirth (5)','Rebirth Amulet (5)')
                text = text.replace('Main Combat Gloves','Main Combat Glvs').replace('Crest of Retaliation','Retaliation Crest')
            reference_limit = (1 << (row.widths[j]*8))-1 if schema else (1 << (scene.widths[i]*8))-1
            cap, width = context_limits(asset.name,field,src,reference_limit)
            if field=='category':
                text={'Main Quest':'MAIN','Sub Quest':'SIDE','Hidden Quest':'HIDDEN',
                      '17th Mercenary':'17th Guild','17th Blacksmith':'17th Smith','9th Blacksmith':'9th Smith'}.get(text,text)
                width=84
            if not schema and field=='dialogue':
                text=flowing_dialogue(text);width=None
            elif ui:
                width=ui['width_px']
            elif width and field not in ('name','title','category'):
                text = reflow(text,width)
            text += suffix
            protected(src,text)
            encoded = text.encode('ascii')
            if len(encoded) > min(cap, reference_limit):
                issues.append(dict(id=sid,kind='bytes',actual=len(encoded),limit=min(cap,reference_limit),text=text))
            if (field in ('name','title','category') or ui) and width and max(map(visible_width,text.split(';')),default=0)>width:
                issues.append(dict(id=sid,kind='width',actual=max(map(visible_width,text.split(';'))),limit=width,text=text))
            if len(encoded)>reference_limit:
                continue
            if schema:
                row.fields[j] = encoded
                context = sha(b'|'.join(row.fragments))
            else:
                scene.strings[i] = encoded
                neighbors = original_strings[max(0,i-1):i] + original_strings[i+1:i+2]
                context = sha(scene.prefix + b'|'.join(neighbors))
            entries.append(dict(id=sid,file=asset.name,row=i,field_index=j,field=field,source=src,
                                source_sha256=sha(value),translation=text,max_bytes=min(cap,reference_limit),
                                width_px=width,context_sha256=context,provenance=provenance))
            stats['korean_slots_translated' if KO.search(src) else 'existing_ui_labels_corrected'] += 1
        if schema:
            compiled = build_dat(records); verified = parse_dat(asset.name,compiled)
            if [r.fragments for r in verified] != [r.fragments for r in original_records]:
                raise ValueError('DAT gameplay metadata changed')
        else:
            compiled = scene.build(); verified = parse_scene(compiled)
            if verified.prefix != scene.prefix or verified.widths != scene.widths:
                raise ValueError('SCN opcode/header changed')
        if compiled != asset.data:
            replacements[asset.name] = compiled
    if issues:
        (ROOT/'work/translation-layout-issues.json').write_text(json.dumps(issues,indent=2)+'\n')
        raise ValueError(f'{len(issues)} layout/byte issues; see work/translation-layout-issues.json')
    result = vfs.build(replacements); checked = Vfs(result)
    for old,new in zip(vfs.entries,checked.entries):
        if (old.name,old.hash)!=(new.name,new.hash) or old.name not in replacements and old.data!=new.data:
            raise ValueError('Non-text VFS asset/order/hash changed')
    output.mkdir(parents=True,exist_ok=True)
    (output/'data.vfs.mp3').write_bytes(result)
    payload = dict(schema_version=1,target_apk_sha256=profile['apk_sha256'],source_language='ko',target_language='en',
                   status='compiled_device_layout_validation_pending',entries=entries)
    (ROOT/'translations/catalog.json').write_text(json.dumps(payload,ensure_ascii=True,indent=2)+'\n',encoding='utf8')
    report = dict(stats=stats,source_vfs_sha256=sha(raw),english_vfs_sha256=sha(result),vfs_entries=len(vfs.entries),
                  changed_assets=list(replacements),reference_different_script_files_not_copied=differences,
                  scene_headers_and_bytecode_identical=True,dat_non_text_fragments_identical=True,
                  other_assets_identical=True,font_and_runtime_unchanged=True,device_tested=False)
    (output/'translation-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--out',type=Path,default=ROOT/'work/english-assets')
    args = parser.parse_args()
    translate(args.reference,args.out)
