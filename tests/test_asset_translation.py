"""Protect gameplay bytes and native font behavior while translating only Korean fields."""
from pathlib import Path
from collections import Counter
import json
import random
import struct
import sys
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from hl5_vfs import Vfs
from hl5_text import parse_dat,build_dat,dat_schema,parse_scene
from english_layout import line_bytes,native_lines,visible_width,COLORS
from translate_assets import protected,KO
from build_english_apk import verify_assets
import test_arm32_relocations as arm
import test_framebuffer_copy as frame

BASE=ROOT/'dist/hl5-01.01.00-test10-install.apk'
OUTPUT=ROOT/'dist/heroes-lore-5-english-multiscreen-v1.0.0.apk'


@unittest.skipUnless(BASE.exists() and OUTPUT.exists(),'Requires private English build')
class AssetTranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(BASE) as apk:cls.old=apk.read('assets/data.vfs.mp3')
        with zipfile.ZipFile(OUTPUT) as apk:cls.new=apk.read('assets/data.vfs.mp3')

    def test_all_target_formats_roundtrip_and_script_metadata_are_preserved(self):
        a,b=Vfs(self.old),Vfs(self.new)
        self.assertEqual(a.build(),self.old);self.assertEqual(b.build(),self.new)
        changed=verify_assets(self.old,self.new)
        self.assertGreater(len(changed),200)
        self.assertEqual(len(a.entries),2205)
        for entry in a.entries:
            if dat_schema(entry.name):self.assertEqual(build_dat(parse_dat(entry.name,entry.data)),entry.data)
            elif entry.name.endswith('.scn'):self.assertEqual(parse_scene(entry.data).build(),entry.data)

    def test_only_korean_and_approved_ui_fields_change_and_controls_stay_intact(self):
        a,b=Vfs(self.old),Vfs(self.new);translated=0
        for entry in a.entries:
            if dat_schema(entry.name):
                first=[v for r in parse_dat(entry.name,entry.data) for v in r.fields]
                second=[v for r in parse_dat(entry.name,b.by_name[entry.name].data) for v in r.fields]
            elif entry.name.endswith('.scn'):
                first=parse_scene(entry.data).strings;second=parse_scene(b.by_name[entry.name].data).strings
            else:continue
            self.assertEqual(len(first),len(second))
            for old,new in zip(first,second):
                source=old.decode('cp949','surrogateescape')
                if not KO.search(source):
                    if old!=new:
                        rules=json.loads((ROOT/'translations/ui-overrides.json').read_text())
                        self.assertTrue(any(r['source']==source and r['translation'].encode()==new for r in rules.values()))
                else:
                    text=new.decode('ascii');self.assertFalse(KO.search(text));protected(source,text);translated+=1
        self.assertEqual(translated,13825)

    def test_font_artwork_guest_dex_and_input_remain_byte_identical(self):
        with zipfile.ZipFile(BASE) as a,zipfile.ZipFile(OUTPUT) as b:
            allowed={'AndroidManifest.xml','assets/data.vfs.mp3','assets/target-assets.json',
                     'lib/arm64-v8a/libhl5_arm64_bridge.so','lib/armeabi-v7a/libhl5_arm64_bridge.so'}
            for name in a.namelist():
                if not name.startswith('META-INF/') and name not in allowed:self.assertEqual(a.read(name),b.read(name),name)
        a,b=Vfs(self.old),Vfs(self.new)
        for name in a.by_name:
            if name.startswith('c/font/'):self.assertEqual(a.by_name[name].data,b.by_name[name].data)

    def test_metadata_or_artwork_changes_are_rejected(self):
        archive=Vfs(self.new)
        with self.assertRaises(ValueError):verify_assets(self.old,archive.build({'c/font/eng.fnt':b'bad'}))
        name=next(e.name for e in archive.entries if e.name.endswith('.scn'))
        raw=bytearray(archive.by_name[name].data);raw[5]^=1
        with self.assertRaises(ValueError):verify_assets(self.old,archive.build({name:bytes(raw)}))
        name='c/csv/common_text.dat';records=parse_dat(name,archive.by_name[name].data)
        records[0].fields[0]=b'CHANGED ENGLISH LABEL'
        with self.assertRaisesRegex(ValueError,'Non-Korean text changed'):
            verify_assets(self.old,archive.build({name:build_dat(records)}))

    def test_catalog_labels_fit_and_native_wrap_stays_within_width(self):
        catalog=json.loads((ROOT/'translations/catalog.json').read_text())
        self.assertEqual(len(catalog['entries']),13897)
        for entry in catalog['entries']:
            text=entry['translation'];self.assertLessEqual(len(text.encode('ascii')),entry['max_bytes'])
            if entry['width_px']:
                for line in native_lines(text,entry['width_px']):
                    self.assertLessEqual(visible_width(line),entry['width_px'],entry['id'])

    def test_fixed_stat_cells_and_quest_location_are_single_line(self):
        vfs=Vfs(self.new)
        rows=parse_dat('c/csv/common_text.dat',vfs.by_name['c/csv/common_text.dat'].data)
        # These share a narrow row with a numeric value; wrapping is not allowed.
        for index in (23,24,25,26,27,28,29,30,31,35,36,37,40,41,42,43,44,45,291,292):
            value=rows[index].fields[0].decode('ascii')
            self.assertNotIn(';',value);self.assertLessEqual(visible_width(value),42,(index,value))
        rows=parse_dat('c/csv/ingame_text.dat',vfs.by_name['c/csv/ingame_text.dat'].data)
        for row in rows[:41]:
            value=row.fields[0].decode('ascii')
            self.assertNotIn(';',value);self.assertLessEqual(visible_width(value),84,value)

    def test_home_buttons_have_consistent_case_and_dialogue_flows(self):
        catalog=json.loads((ROOT/'translations/catalog.json').read_text())['entries']
        vfs=Vfs(self.new)
        menus={field for name in ('c/csv/menu_text.dat','c/csv/common_text.dat')
               for row in parse_dat(name,vfs.by_name[name].data) for field in row.fields}
        for label in ('GAME;START','EXPERT','STORAGE','UPDATE','OPTIONS','RECORDS','HELP','SUPPORT','EXIT'):
            self.assertIn(label.encode('ascii'),menus)
        for entry in catalog:
            if entry['field']=='dialogue':
                self.assertIsNone(entry['width_px'])
                # Explicit paragraphs remain; old 360px hard wraps are removed.
                self.assertNotIn(';',entry['translation'].replace(';;',''))


class MalformedTextTests(unittest.TestCase):
    def test_truncated_and_unknown_containers_are_rejected(self):
        for data in (b'',b'\0'*7,b'\1\0\xff\xff'):
            with self.assertRaises(ValueError):Vfs(data)
        with self.assertRaises(ValueError):parse_dat('c/csv/name.dat',b'\1\0\2\0\5X')
        with self.assertRaises(ValueError):parse_scene(b'\0'*5)
    def test_original_string_length_encoding_cannot_be_upgraded(self):
        # One SCN string, original u8 lengths. The compiler must reject 256 bytes.
        scene=parse_scene(bytes([1,1,1])+bytes(12)+bytes([0,0,1,1])+b'A')
        with self.assertRaises(ValueError):scene.build([b'B'*256])


@unittest.skipUnless(arm.unicorn and (ROOT/'inputs/hl5-original-01.01.00.apk').exists(),'Requires target and Unicorn')
class NativeFontDifferentialTests(unittest.TestCase):
    execute=frame.NativeFramebufferCopyTests.execute
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(ROOT/'inputs/hl5-original-01.01.00.apk') as apk:cls.raw=apk.read('lib/armeabi/libHeroesLore5.so')
        cls.entry=arm.elf_symbols(cls.raw)['_ZN5BFont19GetByteLenPrintableEPciiii'].address+0x40000000
    def setUp(self):
        uc=arm.unicorn.Uc(arm.unicorn.UC_ARCH_ARM,arm.unicorn.UC_MODE_ARM)
        head=struct.unpack_from('<16sHHIIIIIHHHHHH',self.raw)
        programs=[struct.unpack_from('<8I',self.raw,head[5]+i*head[9]) for i in range(head[10])]
        loads=[p for p in programs if p[0]==1]
        uc.mem_map(0x40000000,(max(p[2]+p[5] for p in loads)+4095)&~4095)
        for _,offset,address,_,size,_,_,_ in loads:uc.mem_write(0x40000000+address,self.raw[offset:offset+size])
        uc.mem_map(0x50000000,65536);uc.mem_map(0x70000000,4096);uc.mem_map(0x30000000,4096)
        uc.mem_write(0x50000018,COLORS.encode('ascii'));uc.mem_write(0x50000046,bytes([9,5]));self.uc=uc
    def test_layout_model_matches_actual_target_arm_font(self):
        rng=random.Random(19)
        samples=['  Long words and }colored| text','Text;next line','English without apostrophes','한글 문장 테스트']
        samples+=[''.join(rng.choice('ABC abc123;}|') for _ in range(rng.randint(1,120))) for _ in range(32)]
        for text in samples:
            raw=text.encode('cp949');self.uc.mem_write(0x50001000,raw+b'\0')
            for width in (54,114,126,156,220,360):
                self.assertEqual(self.execute(self.entry,[0x50000000,0x50001000,len(raw),0,width,1]),line_bytes(raw,width))


if __name__=='__main__':unittest.main()
