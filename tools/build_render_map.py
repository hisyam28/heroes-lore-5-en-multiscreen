"""Build a readonly display dictionary for Korean text cached in older save data."""
from pathlib import Path
import argparse
import hashlib
import json
from hl5_vfs import Vfs
from hl5_text import parse_dat,dat_schema
from translate_assets import KO


def fnv(raw):
    value=2166136261
    for byte in raw:value=((value^byte)*16777619)&0xffffffff
    return value


def generate(old_vfs,new_vfs,previous_vfs,output):
    old,new,previous=Vfs(old_vfs),Vfs(new_vfs),Vfs(previous_vfs);pairs={};ambiguous=set()
    def add(source,english):
        source=source.split(b'\0')[0];english=english.split(b'\0')[0]
        if not source or source==english:return
        if source in pairs and pairs[source]!=english:ambiguous.add(source)
        else:pairs[source]=english
    for entry in old.entries:
        if not dat_schema(entry.name):continue
        a=parse_dat(entry.name,entry.data);b=parse_dat(entry.name,new.by_name[entry.name].data)
        c=parse_dat(entry.name,previous.by_name[entry.name].data)
        for x,y,z in zip(a,b,c):
            for source,english,prior in zip(x.fields,y.fields,z.fields):
                add(source,english);add(prior,english)
    extra=Path(__file__).resolve().parents[1]/'translations/native-display-overrides.json'
    if extra.exists():
        for item in json.loads(extra.read_text(encoding='utf8')):
            add(bytes.fromhex(item['source_hex']),item['translation'].encode('ascii'))
    # Exact duplicated Korean phrases must have one display translation.
    # Ambiguous entries stay untouched rather than guessing from a saved pointer.
    for source in ambiguous:pairs.pop(source,None)
    records=[];blob=bytearray()
    for source,english in sorted(pairs.items(),key=lambda p:(fnv(p[0]),p[0])):
        a=len(blob);blob.extend(source+b'\0');b=len(blob);blob.extend(english+b'\0')
        records.append((fnv(source),a,b))
    chunks=['#ifndef HL5_RENDER_TEXT_DATA_H','#define HL5_RENDER_TEXT_DATA_H','#include <stdint.h>',
            'namespace hl5 {','struct RenderTextEntry { uint32_t hash,source,english; };',
            'static const unsigned char render_text_blob[] = {']
    chunks += [','.join(str(b) for b in blob[i:i+32])+',' for i in range(0,len(blob),32)]
    chunks += ['};','static const RenderTextEntry render_text_entries[] = {']
    chunks += [f'{{{h}u,{a}u,{b}u}},' for h,a,b in records]
    chunks += ['};','static inline const char* display_translation(const char* source) {',
               'uint32_t hash=2166136261u; for(const unsigned char* p=(const unsigned char*)source;*p;++p)hash=(hash^*p)*16777619u;',
               'unsigned left=0,right=sizeof(render_text_entries)/sizeof(render_text_entries[0]);',
               'while(left<right){unsigned mid=left+(right-left)/2;if(render_text_entries[mid].hash<hash)left=mid+1;else right=mid;}',
               'for(unsigned i=left;i<sizeof(render_text_entries)/sizeof(render_text_entries[0]) && render_text_entries[i].hash==hash;++i){',
               'const unsigned char* a=render_text_blob+render_text_entries[i].source;const unsigned char* b=(const unsigned char*)source;',
               'while(*a && *a==*b){++a;++b;}if(*a==*b)return (const char*)render_text_blob+render_text_entries[i].english;',
               '}return nullptr;}','}','#endif']
    output.write_text('\n'.join(chunks)+'\n',encoding='ascii',newline='\n')
    return {'entries':len(records),'blob_bytes':len(blob),'ambiguous_entries_excluded':len(ambiguous),
            'english_vfs_sha256':hashlib.sha256(new_vfs).hexdigest(),'save_files_modified':False}


if __name__=='__main__':
    import zipfile
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vfs',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    with zipfile.ZipFile(root/'dist/hl5-01.01.00-test11-en.apk') as apk:prior=apk.read('assets/data.vfs.mp3')
    with zipfile.ZipFile(root/'inputs/hl5-original-01.01.00.apk') as apk:old=apk.read('assets/data.vfs.mp3')
    print(json.dumps(generate(old,args.vfs.read_bytes(),prior,args.out)))
