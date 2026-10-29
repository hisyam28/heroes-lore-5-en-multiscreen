"""Validate the local-only intro assets and the unchanged game/runtime payloads."""
from pathlib import Path
import json
import struct
import subprocess
import sys
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from hl5_graphics import Gbm,Png,parse_mgr,build_mgr
from hl5_vfs import Vfs
from localize_intro import verify_intro_assets,MGR_SLOTS,SUBTITLE_TEXT,SUBTITLE_SLICES,subtitle_mask,subtitle_outline,verify_subtitle_revision,TITLE_CIF,cif_parts,subtitle_layout
import test_arm32_relocations as arm
import test_framebuffer_copy as frame

BASE=ROOT/'dist/heroes-lore-5-english-multiscreen-v1.0.0.apk'
APK=ROOT/'dist/heroes-lore-5-v1.0.4.apk'
OUTPUT=ROOT/'work/intro-v104-assets/data.vfs.mp3'


@unittest.skipUnless(BASE.exists() and OUTPUT.exists(),'Requires local intro assets')
class IntroAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(BASE) as z:cls.before=z.read('assets/data.vfs.mp3')
        cls.after=OUTPUT.read_bytes()

    def test_sprite_roundtrip_preserves_dimensions_palette_and_padding(self):
        for raw in (self.before,self.after):
            v=Vfs(raw)
            for name in MGR_SLOTS:
                frames=parse_mgr(v.by_name[name].data)
                self.assertEqual(build_mgr([f.build(f.indices) for f in frames]),v.by_name[name].data)
            for e in v.entries:
                if e.name.startswith('__rating/'):
                    image=Png(e.data);rebuilt=Png(image.build_indexed(image.plane))
                    self.assertEqual(image.plane,rebuilt.plane)
                    self.assertEqual(image.palette,rebuilt.palette)

    def test_only_verified_intro_assets_change_and_script_art_input_are_protected(self):
        self.assertEqual(len(verify_intro_assets(self.before,self.after)),16)
        old,new=Vfs(self.before),Vfs(self.after)
        for e in old.entries:
            if (e.name.endswith('.cif') and e.name!=TITLE_CIF) or e.name.endswith('.scn') or e.name.startswith('c/font/') or e.name=='mtouchdevice.txt':
                self.assertEqual(e.data,new.by_name[e.name].data,e.name)
        name='c/sp/imgcom/title.mgr';parts=[f.raw for f in parse_mgr(new.by_name[name].data)]
        changed=bytearray(parts[5]);changed[2]^=1;parts[5]=bytes(changed)
        with self.assertRaises(ValueError):verify_intro_assets(self.before,new.build({name:build_mgr(parts)}))
        with self.assertRaises(ValueError):verify_intro_assets(self.before,new.build({'c/font/eng.fnt':b'changed'}))

    def test_malformed_sprite_and_png_are_rejected(self):
        for raw in (b'',b'\1\0\0\0',struct.pack('<I',5000)):
            with self.assertRaises(ValueError):parse_mgr(raw)
        for raw in (b'',b'\x18\1\0\0\0\0',b'\x18\1\1\0\1\0\0\0\2'):
            with self.assertRaises(ValueError):Gbm(raw)
        image=next(e.data for e in Vfs(self.after).entries if e.name.startswith('__rating/'))
        invalid=bytearray(image);invalid[-1]^=1
        with self.assertRaises(ValueError):Png(invalid)

    def test_full_subtitle_survives_animated_cell_slicing(self):
        self.assertEqual(SUBTITLE_TEXT,'Covenant of Darkness')
        frames=parse_mgr(Vfs(self.after).by_name['c/sp/imgcom/title.mgr'].data)
        original=parse_mgr(Vfs(self.before).by_name['c/sp/imgcom/title.mgr'].data)
        font=Vfs(self.after).by_name['c/font/eng.fnt'].data
        mask=subtitle_mask(font);restored=bytearray(124*14)
        for part,(offset,width) in enumerate(SUBTITLE_SLICES):
            image=frames[14+part];background=original[14+part].indices[0]
            for y in range(14):
                for x in range(width):
                    restored[y*124+offset+x]=int(image.indices[y*width+x]!=background)
        self.assertEqual(bytes(restored),mask)
        full=frames[19]
        self.assertEqual(bytes(int(n!=original[19].indices[0]) for n in full.indices),subtitle_outline(mask))
        # Keep the original V and crescent emblem; no extra Arabic 5 is added.
        self.assertEqual(frames[3].raw,original[3].raw);self.assertEqual(frames[4].raw,original[4].raw)

    def test_subtitle_animation_keeps_timing_and_stays_below_the_wordmark(self):
        old,new=Vfs(self.before),Vfs(self.after)
        self.assertEqual(new.by_name[TITLE_CIF].data,subtitle_layout(old.by_name[TITLE_CIF].data))
        frames=parse_mgr(new.by_name['c/sp/imgcom/title.mgr'].data)
        count=0
        for group,seq,frame,offset,part in cif_parts(new.by_name[TITLE_CIF].data):
            if part[1] not in range(14,20):continue
            x,y=struct.unpack_from('<bb',part,2);image=frames[part[1]]
            # Wordmark center y=-26 and h=57: bottom=3. Subtitle starts at 5.
            self.assertGreaterEqual(y-image.height//2,5)
            self.assertLessEqual(y+(image.height+1)//2,20)
            self.assertGreaterEqual(x-image.width//2,-103)
            self.assertLessEqual(x+(image.width+1)//2,90);count+=1
        self.assertGreater(count,100)
        before=cif_parts(old.by_name[TITLE_CIF].data);after=cif_parts(new.by_name[TITLE_CIF].data)
        self.assertEqual(len(before),len(after))
        for a,b in zip(before,after):
            self.assertEqual(a[:4],b[:4])
            if a[4][1] in range(14,20):self.assertEqual(a[4][:2]+a[4][4:],b[4][:2]+b[4][4:])
            else:self.assertEqual(a[4],b[4])

    @unittest.skipUnless(APK.exists(),'Requires local preview APK')
    def test_local_apk_only_changes_manifest_vfs_and_cache_digest(self):
        with zipfile.ZipFile(BASE) as old,zipfile.ZipFile(APK) as new:
            names=lambda z:{n for n in z.namelist() if not n.startswith('META-INF/')}
            self.assertEqual(names(old),names(new))
            self.assertEqual({n for n in names(old) if old.read(n)!=new.read(n)},
                             {'AndroidManifest.xml','assets/data.vfs.mp3','assets/target-assets.json','res/drawable/icon.png',
                              'lib/armeabi-v7a/libhl5_arm64_bridge.so','lib/arm64-v8a/libhl5_arm64_bridge.so'})
            self.assertEqual(new.read('assets/data.vfs.mp3'),self.after)
            self.assertEqual(old.read('resources.arsc'),new.read('resources.arsc'))
            # This revision must retain every performance/logic payload from 1.0.3.
            with zipfile.ZipFile(ROOT/'dist/heroes-lore-5-v1.0.3.apk') as previous:
                self.assertEqual({n for n in names(previous) if previous.read(n)!=new.read(n)},
                                 {'AndroidManifest.xml','assets/data.vfs.mp3','assets/target-assets.json'})
                self.assertEqual(verify_subtitle_revision(previous.read('assets/data.vfs.mp3'),self.after),
                                 ['c/sp/imgcom/title.mgr'])
            icon=Png(new.read('res/drawable/icon.png'));self.assertEqual((icon.width,icon.height),(192,192))
        aapt=ROOT/'work/android-tools/build-tools/android-16/aapt2.exe'
        data=subprocess.run([str(aapt),'dump','badging',str(APK)],capture_output=True,text=True,check=True).stdout
        self.assertIn("application-label:'Heroes Lore 5'",data);self.assertIn("versionCode='1010104'",data)
        self.assertIn("minSdkVersion:'9'",data);self.assertIn("targetSdkVersion:'36'",data)
        self.assertNotIn('application-debuggable',data)


@unittest.skipUnless(arm.unicorn and OUTPUT.exists(),'Requires local target and Unicorn')
class NativeIntroSpriteTests(unittest.TestCase):
    execute=frame.NativeFramebufferCopyTests.execute
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(BASE) as z:cls.target=z.read('assets/libHeroesLore5.so');cls.before=Vfs(z.read('assets/data.vfs.mp3'))
        cls.after=Vfs(OUTPUT.read_bytes());cls.symbols=arm.elf_symbols(cls.target)

    def test_target_loader_reads_original_and_translated_sprite_buffers_identically(self):
        from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_LR,UC_ARM_REG_PC
        uc=arm.unicorn.Uc(arm.unicorn.UC_ARCH_ARM,arm.unicorn.UC_MODE_ARM)
        header=struct.unpack_from('<16sHHIIIIIHHHHHH',self.target)
        loads=[struct.unpack_from('<8I',self.target,header[5]+i*header[9]) for i in range(header[10])]
        loads=[p for p in loads if p[0]==1]
        uc.mem_map(0x40000000,(max(p[2]+p[5] for p in loads)+4095)&~4095)
        for _,off,address,_,size,_,_,_ in loads:uc.mem_write(0x40000000+address,self.target[off:off+size])
        uc.mem_map(0x50000000,1024*1024);uc.mem_map(0x70000000,4096);uc.mem_map(0x30000000,4096);self.uc=uc
        fn=self.symbols['_ZN8GbmImage14LoadImageResIDEjh'];heap=[0x50020000]
        got=0x40000000+fn.address+40+struct.unpack_from('<I',fn.data,len(fn.data)-8)[0]
        uc.mem_write(got+struct.unpack_from('<I',fn.data,len(fn.data)-4)[0],struct.pack('<I',0x4016a234))
        uc.mem_write(0x4016a234,struct.pack('<I',0xf81f))
        allocate=0x40000000+self.symbols['MC_knlCalloc'].address
        release=0x40000000+self.symbols['_ZN10StaticUtil7DM_FREEERj'].address
        def hook(machine,address,size,data):
            a,b,c=(uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2))
            if address==allocate:
                uc.reg_write(UC_ARM_REG_R0,heap[0]);uc.mem_write(heap[0],bytes(a));heap[0]+=(a+7)&~7
            elif address==release:uc.mem_write(a,bytes(4))
            else:uc.mem_write(a,bytes(uc.mem_read(b,c)))
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        for address in (allocate,release,0x40030110):uc.hook_add(arm.unicorn.UC_HOOK_CODE,hook,begin=address,end=address)
        cases=0
        for vfs in (self.before,self.after):
            for name,slots in MGR_SLOTS.items():
                frames=parse_mgr(vfs.by_name[name].data)
                for i in sorted(slots):
                    frame=frames[i];heap[0]=0x50020000;uc.mem_write(0x50000000,bytes(24));uc.mem_write(0x50004000,frame.raw)
                    self.execute(0x40000000+fn.address,[0x50000000,0x50004000,1])
                    obj=bytes(uc.mem_read(0x50000000,24));self.assertEqual(obj[:6],frame.raw[:6])
                    pal,pixels,backup=struct.unpack_from('<III',obj,8)
                    self.assertEqual(bytes(uc.mem_read(pal,frame.count*2)),frame.raw[6:frame.offset])
                    self.assertEqual(bytes(uc.mem_read(backup,frame.count*2)),frame.raw[6:frame.offset])
                    self.assertEqual(bytes(uc.mem_read(pixels,len(frame.raw)-frame.offset)),frame.raw[frame.offset:])
                    self.assertEqual(bytes(uc.mem_read(0x50004000,len(frame.raw))),frame.raw);cases+=1
        self.assertEqual(cases,34)


if __name__=='__main__':unittest.main()
