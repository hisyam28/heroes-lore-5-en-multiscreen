"""Local intro artwork: scoped color/layout changes with original game and timing guards."""
from pathlib import Path
from collections import defaultdict
import argparse
import hashlib
import json
import struct
import zipfile

from hl5_vfs import Vfs
from hl5_text import parse_dat,build_dat
from hl5_graphics import Gbm,Png,parse_mgr,build_mgr,rgb565,write_png
from translate_assets import protected

ROOT=Path(__file__).resolve().parents[1]
BASE_SHA='dfc424bbabc19a45512857250153af175143a130fcd429131aed8053357618ed'
SUBTITLE_BASE_SHA='f9ae23004ed4bf5a3069e7f1e2c110e223dad22f6a3cf8a1174ea0b87317cc96'
CAPTIONS={
 14:(15,'\uc131\uc9c0\uc5d0\uc11c \uc2dc\uc791\ub41c \uace0\ub300\uc885\uc758 \uc2b5\uaca9...','Ancient raid on Sanctuary...'),
 15:(16,'\uc778\uac04\uacfc \ub124\ubca0\ub4dc\ub294 \uc804\uc7c1\uc744 \uba48\ucdb0\uc57c \ud588\uace0;\uc624\ub974\ube44\uc2a4 \uad70\ub3c4\ub294 \ud3c9\ud654\ub97c \ub418\ucc3e\uc558\uc73c\ub2c8-','Humans and Neved ended the war.;Peace returned to Orbis...'),
 16:(17,'\uadf8\uac83\uc740 \ubb34\uc758\ubbf8\ud55c \uc804\uc7c1\uc744 \ub05d\ub0b4\uae30 \uc704\ud574;\uc2e0\uc774 \ub0b4\ub9b0 \uc7ac\uc559\uc774\uc5c8\uc744\uae4c?','Did a god send this disaster;to end a pointless war?'),
 17:(18,'\ub2e8\uc5b8\ucee8\ub370...','I say...'),
 18:(19,'\uc774 \uc138\uacc4\uc5d0 \uadf8\ub7f0 \uc2e0\uc740 \uc5c6\ub2e4.','No such god exists;in this world.')}
RATINGS={'age12':'12+','age15':'15+','age18':'18+','ageall':'ALL','agetest':'TEST',
         'crime':'CRIME','curse':'LANG.','drug':'DRUGS','fear':'FEAR','gamble':'GAMBLE',
         'sexual':'SEX','violence':'VIOLENT'}
MGR_SLOTS={'c/sp/imgcom/title.mgr':{5,6,14,15,16,17,18,19},
           'c/img/menu.mgr':{9,12,13,14,15,16,17,18,33}}
SUBTITLE_TEXT='Covenant of Darkness'
SUBTITLE_SIZE=(124,14)
SUBTITLE_SLICES=((0,24),(24,24),(48,24),(72,24),(96,28))
TITLE_CIF='c/sp/cif/title.cif'


def cif_parts(raw):
    # Target LoadSprData at 0xd7ae8: one-byte image list, groups,
    # sequences, frames and 4/9-byte draw records (coordinate mode zero).
    if raw[:2]!=b'\x01\x00':raise ValueError('Unknown title CIF image list')
    p=3;result=[]
    for group in range(raw[2]):
        sequences=raw[p];p+=1
        for sequence in range(sequences):
            frames=raw[p];p+=1
            for frame in range(frames):
                count=raw[p];p+=1
                for _ in range(count):
                    length=9 if raw[p]&128 else 4
                    if p+length>len(raw):raise ValueError('Truncated CIF draw record')
                    result.append((group,sequence,frame,p,raw[p:p+length]));p+=length
    if p!=len(raw):raise ValueError('Unknown title CIF tail')
    return result


def subtitle_layout(raw):
    result=bytearray(raw)
    # Coordinates are image centers, verified in target SPRITE::DrawSprite
    # at 0xd6864 and Graphic drawing. Preserve alpha, scaling and timing.
    old_x={14:-34,15:-22,16:-12,17:1,18:12,19:-10}
    for group,seq,frame,offset,part in cif_parts(raw):
        slot=part[1]
        if slot not in old_x:continue
        x,y=struct.unpack_from('<bb',part,2)
        if slot==19:new_x=-40
        else:
            start,width=SUBTITLE_SLICES[slot-14];new_x=-102+start+width//2
        struct.pack_into('<bb',result,offset+2,x-old_x[slot]+new_x,y+17)
    return bytes(result)


def gold_palette(frame):
    # Keep color count and the transparent key; only these logo colors change.
    anchors=((16,6,0),(115,50,0),(240,157,24),(255,238,166),(255,255,230))
    raw=bytearray(frame.raw);slots=[i for i,c in enumerate(frame.palette) if c!=0xf81f]
    for n,i in enumerate(slots):
        value=n*(len(anchors)-1)/(len(slots)-1);a=min(int(value),len(anchors)-2);f=value-a
        r,g,b=(int(anchors[a][k]*(1-f)+anchors[a+1][k]*f) for k in range(3))
        struct.pack_into('<H',raw,6+i*2,(r>>3)<<11|(g>>2)<<5|(b>>3))
    return Gbm(bytes(raw))



def sha(raw):return hashlib.sha256(raw).hexdigest()


def glyphs(font,text,advance=6):
    result=[]
    if any(not 32<=ord(c)<=126 for c in text):raise ValueError('Caption requires ASCII font')
    for i,c in enumerate(text):
        for y,row in enumerate(font[6+(ord(c)-32)*11:6+(ord(c)-31)*11]):
            for x in range(5):
                if row&(128>>x):result.append((i*advance+x,y-1))
    return result,max(0,len(text)*advance-1),8


def text_on_plane(plane,width,height,font,text,foreground,rect=None,advance=6):
    x,y,w,h=rect or (0,0,width,height);lines=text.split(';')
    total=len(lines)*12-4;top=y+(h-total)//2
    if total>h:raise ValueError('Caption height overflow: '+text)
    for number,line in enumerate(lines):
        points,length,_=glyphs(font,line,advance)
        if length>w:raise ValueError('Caption width overflow: '+line)
        left=x+(w-length)//2
        for xx,yy in points:
            xx+=left;yy+=top+number*12
            if not (x<=xx<x+w and y<=yy<y+h and 0<=xx<width and 0<=yy<height):raise ValueError('Glyph outside allowed region')
            plane[yy*width+xx]=foreground


def nearest(palette,color,exclude=()):
    return min((i for i in range(len(palette)) if i not in exclude),
               key=lambda i:sum((a-b)**2 for a,b in zip(palette[i][:3],color)))


def subtitle_mask(font):
    width,height=SUBTITLE_SIZE;mask=[0]*(width*height)
    text_on_plane(mask,width,height,font,SUBTITLE_TEXT.upper(),1)
    return bytes(mask)


def subtitle_outline(mask):
    # The inverse subtitle cell is the dark underlay. Dilate its mask once
    # before the five gold foreground pieces are blended over it; dark pixels
    # inside the additive foreground cells would not create a visible stroke.
    width,height=SUBTITLE_SIZE;result=bytearray(mask)
    for y in range(height):
        for x in range(width):
            if not mask[y*width+x]:continue
            for yy in range(max(0,y-1),min(height,y+2)):
                for xx in range(max(0,x-1),min(width,x+2)):result[yy*width+xx]=1
    return bytes(result)


def subtitle_gbm(frame,font,part=None):
    mask=subtitle_mask(font);width,height=SUBTITLE_SIZE
    if part is None:mask=subtitle_outline(mask)
    if part is not None:
        offset,width=SUBTITLE_SLICES[part]
        mask=bytes(mask[y*SUBTITLE_SIZE[0]+offset+x] for y in range(height) for x in range(width))
        frame=gold_palette(frame)
    colors=[rgb565(c) for c in frame.palette];background=frame.indices[0]
    foreground=nearest(colors,(0,0,0) if part is None else (255,238,166))
    header=bytearray(frame.raw[:frame.offset]);struct.pack_into('<HH',header,2,width,height)
    size=((width+1)//2 if frame.bits==4 else width)*height
    cell=Gbm(bytes(header)+bytes(size))
    return cell.build([foreground if bit else background for bit in mask])


def verify_subtitle_revision(before,after):
    old,new=Vfs(before),Vfs(after);name='c/sp/imgcom/title.mgr'
    if [(e.name,e.hash) for e in old.entries]!=[(e.name,e.hash) for e in new.entries]:
        raise ValueError('Subtitle revision changed VFS identity/order')
    if [e.name for e in old.entries if e.data!=new.by_name[e.name].data]!=[name]:
        raise ValueError('Only subtitle artwork may change from 1.0.3')
    first,last=parse_mgr(old.by_name[name].data),parse_mgr(new.by_name[name].data)
    if len(first)!=len(last):raise ValueError('Subtitle frame count changed')
    for i,(a,b) in enumerate(zip(first,last)):
        if i!=19 and a.raw!=b.raw:raise ValueError('Non-outline title sprite changed')
        if i==19 and (len(a.raw)!=len(b.raw) or a.raw[:a.offset]!=b.raw[:b.offset]):
            raise ValueError('Subtitle dimensions/header/palette changed')
    font=new.by_name['c/font/eng.fnt'].data;mask=subtitle_outline(subtitle_mask(font))
    cell=last[19];background=first[19].indices[0]
    foreground=nearest([rgb565(c) for c in cell.palette],(0,0,0))
    if cell.indices!=[foreground if bit else background for bit in mask]:
        raise ValueError('Subtitle pixels differ from the bounded outline')
    return [name]


def styled_caption_gbm(frame,font,text):
    # Recover the original Hangul's row brightness instead of painting every
    # English stroke with the palette's brightest white.
    colors=[rgb565(c) for c in frame.palette];background=frame.indices[0]
    mask=[0]*len(frame.indices);text_on_plane(mask,frame.width,frame.height,font,text,1)
    levels=[]
    for y in range(frame.height):
        values=sorted(sum(colors[i]) for i in frame.indices[y*frame.width:(y+1)*frame.width] if i!=background)
        levels.append(values[int((len(values)-1)*.8)]//3 if values else None)
    pixels=[background]*len(mask)
    for pos,bit in enumerate(mask):
        if not bit:continue
        y=pos//frame.width
        row=min((i for i,v in enumerate(levels) if v is not None),key=lambda i:abs(i-y))
        tone=levels[row];pixels[pos]=nearest(colors,(tone,tone,tone),[background])
    return frame.build(pixels)


def caption_gbm(frame,font,text,color=(255,255,255),rect=None,advance=6):
    colors=[rgb565(c) for c in frame.palette];background=frame.indices[0]
    pixels=list(frame.indices) if rect else [background]*len(frame.indices)
    if rect:
        black=nearest(colors,(0,0,0));x,y,w,h=rect
        for yy in range(y,y+h):
            for xx in range(x,x+w):pixels[yy*frame.width+xx]=black
    if not rect and frame.palette[background]!=0xf81f and sum(colors[background])>500 and color==(255,255,255):
        color=(0,0,0)
    foreground=nearest(colors,color,exclude=[i for i,c in enumerate(frame.palette) if c==0xf81f])
    text_on_plane(pixels,frame.width,frame.height,font,text,foreground,rect,advance)
    return frame.build(pixels)


def wordmark_gbm(frame,source):
    rgba=source.rgba();sw,sh=source.width,source.height
    occupied=[(i%(sw),i//sw) for i in range(sw*sh) if rgba[i*4+3]>=96]
    if not occupied:raise ValueError('Empty wordmark')
    left=min(x for x,y in occupied);right=max(x for x,y in occupied)+1
    top=min(y for x,y in occupied);bottom=max(y for x,y in occupied)+1
    scale=min(frame.width/(right-left),frame.height/(bottom-top))
    dw=max(1,int((right-left)*scale));dh=max(1,int((bottom-top)*scale))
    ox=(frame.width-dw)//2;oy=(frame.height-dh)//2
    colors=[rgb565(c) for c in frame.palette];skip=[i for i,c in enumerate(frame.palette) if c==0xf81f]
    pixels=[frame.indices[0]]*len(frame.indices);cache={}
    for y in range(dh):
        sy0=top+int(y*(bottom-top)/dh);sy1=top+max(int((y+1)*(bottom-top)/dh),int(y*(bottom-top)/dh)+1)
        for x in range(dw):
            sx0=left+int(x*(right-left)/dw);sx1=left+max(int((x+1)*(right-left)/dw),int(x*(right-left)/dw)+1)
            alpha=red=green=blue=0
            for sy in range(sy0,sy1):
                for sx in range(sx0,sx1):
                    p=(sy*sw+sx)*4;a=rgba[p+3];alpha+=a
                    red+=rgba[p]*a;green+=rgba[p+1]*a;blue+=rgba[p+2]*a
            if alpha//((sy1-sy0)*(sx1-sx0))<96:continue
            color=(red//alpha,green//alpha,blue//alpha)
            if color not in cache:cache[color]=nearest(colors,color,skip)
            pixels[(y+oy)*frame.width+x+ox]=cache[color]
    return frame.build(pixels)


def oval_caption_gbm(frame,font,text):
    # Recover the dim oval gradient from text-free outer rings. Keep every
    # pixel outside the caption box, including the silhouette, unchanged.
    if (frame.width,frame.height,frame.count)!=(192,50,59):raise ValueError('Unknown intro oval profile')
    colors=[rgb565(c) for c in frame.palette];pixels=list(frame.indices)
    rings=defaultdict(list)
    def radius(x,y):return int((((x-95.5)/96)**2+((y-24.5)/25)**2)*80)
    for y in range(frame.height):
        for x in range(frame.width):
            index=frame.indices[y*frame.width+x]
            if index<25 and not (8<=x<185 and 11<=y<39):rings[radius(x,y)].append(colors[index])
    background={r:tuple(sorted(c[k] for c in values)[len(values)//2] for k in range(3)) for r,values in rings.items()}
    for y in range(11,39):
        for x in range(8,185):
            if frame.palette[frame.indices[y*frame.width+x]]==0xf81f and radius(x,y)>=74:continue
            r=radius(x,y);sample=background[min(background,key=lambda known:abs(known-r))]
            pixels[y*frame.width+x]=nearest(colors[:25],sample)
    text_on_plane(pixels,frame.width,frame.height,font,text,nearest(colors,(255,170,30)),(20,11,152,28))
    return frame.build(pixels)


def rating_png(raw,font,label):
    image=Png(raw)
    if (image.width,image.height,image.kind)!=(45,53,3):raise ValueError('Unknown rating icon profile')
    pixels=list(image.plane);transparent=[i for i,c in enumerate(image.palette) if c[3]<128]
    black=nearest(image.palette,(0,0,0),transparent);white=nearest(image.palette,(255,255,255),transparent)
    for y in range(44,53):
        for x in range(1,44):
            if image.palette[pixels[y*45+x]][3]:pixels[y*45+x]=black
    text_on_plane(pixels,45,53,font,label,white,(1,44,43,9))
    return image.build_indexed(pixels)


def verify_intro_assets(before,after):
    first,last=Vfs(before),Vfs(after);changes=[]
    if [(e.name,e.hash) for e in first.entries]!=[(e.name,e.hash) for e in last.entries]:raise ValueError('VFS identity/order changed')
    allowed=set(MGR_SLOTS)|{'c/csv/menu_text.dat',TITLE_CIF}|{'__rating/'+n+'.png' for n in RATINGS}
    for a,b in zip(first.entries,last.entries):
        if a.data==b.data:continue
        if a.name not in allowed:raise ValueError('Unexpected intro asset change: '+a.name)
        changes.append(a.name)
        if a.name in MGR_SLOTS:
            old,new=parse_mgr(a.data),parse_mgr(b.data)
            if len(old)!=len(new):raise ValueError('MGR frame count changed')
            for i,(x,y) in enumerate(zip(old,new)):
                if x.raw==y.raw:continue
                if i not in MGR_SLOTS[a.name]:raise ValueError('Unexpected sprite slot')
                if a.name.endswith('/title.mgr'):
                    if i in (5,6):
                        if y.raw[:6]!=x.raw[:6] or y.palette!=gold_palette(x).palette:raise ValueError('Unknown logo palette/header')
                    else:
                        width=SUBTITLE_SIZE[0] if i==19 else SUBTITLE_SLICES[i-14][1]
                        palette=x.palette if i==19 else gold_palette(x).palette
                        if (y.kind,y.count,y.width,y.height)!=(x.kind,x.count,width,SUBTITLE_SIZE[1]) or y.palette!=palette:
                            raise ValueError('Unknown subtitle sprite profile')
                elif len(x.raw)!=len(y.raw) or x.raw[:x.offset]!=y.raw[:y.offset]:raise ValueError('Sprite header/palette changed')
        elif a.name==TITLE_CIF:
            if b.data!=subtitle_layout(a.data):raise ValueError('Unexpected title animation change')
        elif a.name.startswith('__rating/'):
            x,y=Png(a.data),Png(b.data)
            if [(k,d) for k,d in x.chunks if k!=b'IDAT']!=[(k,d) for k,d in y.chunks if k!=b'IDAT']:
                raise ValueError('Rating PNG metadata changed')
            for i,(old,new) in enumerate(zip(x.plane,y.plane)):
                if old!=new and not (44<=i//45<53 and 1<=i%45<44):raise ValueError('Rating artwork outside caption changed')
        else:
            old,new=parse_dat(a.name,a.data),parse_dat(b.name,b.data)
            if len(old)!=len(new) or [r.fragments for r in old]!=[r.fragments for r in new]:raise ValueError('Intro DAT metadata changed')
            expected={row:text.encode('ascii') for row,source,text in CAPTIONS.values()}
            for i,(x,y) in enumerate(zip(old,new)):
                if x.fields!=y.fields and (i not in expected or y.fields!=[expected[i]]):raise ValueError('Unexpected caption DAT change')
    if set(changes)!=allowed:raise ValueError('Missing expected intro localization asset')
    return changes


def localize(base,original,wordmark,output):
    if sha(base.read_bytes())!=BASE_SHA:raise ValueError('Unknown accepted APK baseline')
    if sha(original.read_bytes())!=json.loads((ROOT/'config/target-profile.json').read_text())['apk_sha256']:
        raise ValueError('Unknown original target APK')
    with zipfile.ZipFile(base) as apk:raw=apk.read('assets/data.vfs.mp3')
    with zipfile.ZipFile(original) as apk:source_raw=apk.read('assets/data.vfs.mp3')
    vfs,source=Vfs(raw),Vfs(source_raw);font=vfs.by_name['c/font/eng.fnt'].data
    source_png=Png(wordmark.read_bytes());replacements={};record=[]
    for name in MGR_SLOTS:
        if vfs.by_name[name].data!=source.by_name[name].data:raise ValueError('Intro source differs from original target')
        frames=parse_mgr(vfs.by_name[name].data);parts=[f.raw for f in frames]
        if name.endswith('/title.mgr'):
            for i in (5,6):parts[i]=wordmark_gbm(gold_palette(frames[i]),source_png)
            for part,i in enumerate(range(14,19)):parts[i]=subtitle_gbm(frames[i],font,part)
            parts[19]=subtitle_gbm(frames[19],font)
        else:
            parts[9]=caption_gbm(frames[9],font,'KR',(255,190,30))
            parts[12]=caption_gbm(frames[12],font,'AGES 12+',rect=(8,96,87,23))
            parts[13]=caption_gbm(frames[13],font,'GAMBLING',rect=(8,96,87,23))
            for i,(row,expected,text) in CAPTIONS.items():
                actual=parse_dat('c/csv/menu_text.dat',source.by_name['c/csv/menu_text.dat'].data)[row].fields[0].decode('cp949')
                if actual!=expected:raise ValueError('Intro caption source/context mismatch')
                protected(expected,text)
                parts[i]=oval_caption_gbm(frames[i],font,text) if i==18 else styled_caption_gbm(frames[i],font,text)
                record.append({'frame':i,'dat_row':row,'source':expected,'translation':text})
            parts[33]=caption_gbm(frames[33],font,'TRIAL;VERSION',(210,255,160))
        replacements[name]=build_mgr(parts)
    replacements[TITLE_CIF]=subtitle_layout(vfs.by_name[TITLE_CIF].data)
    dat=parse_dat('c/csv/menu_text.dat',vfs.by_name['c/csv/menu_text.dat'].data)
    for row,expected,text in CAPTIONS.values():dat[row].fields[0]=text.encode('ascii')
    replacements['c/csv/menu_text.dat']=build_dat(dat)
    for name,label in RATINGS.items():
        path='__rating/'+name+'.png';replacements[path]=rating_png(vfs.by_name[path].data,font,label)
    result=vfs.build(replacements);changes=verify_intro_assets(raw,result)
    output.mkdir(parents=True,exist_ok=True);(output/'data.vfs.mp3').write_bytes(result)
    report={'base_apk_sha256':BASE_SHA,'base_vfs_sha256':sha(raw),'output_vfs_sha256':sha(result),
            'wordmark_source_sha256':sha(wordmark.read_bytes()),'changed_assets':changes,'captions':record,
            'full_game_title':'Heroes Lore 5: Covenant of Darkness','home_wordmark':'Heroes Lore',
            'subtitle':SUBTITLE_TEXT,'home_uses_original_roman_V':True,'subtitle_outline_pixels':1,
            'logo_palette':'warm gold, bronze outline and ivory highlights','subtitle_layout':'single 124x14 line below wordmark; five animated pieces retained',
            'caption_palette_matches_original':True,'title_cif_only_subtitle_coordinates_changed':True,'animation_timing_unchanged':True,
            'script_opcodes_and_save_logic_unchanged':True,'physical_device_tested':False,'published':False}
    (output/'intro-translation-report.json').write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf8')
    for name in MGR_SLOTS:
        for i,frame in enumerate(parse_mgr(replacements[name])):
            if i in MGR_SLOTS[name]:
                rgba=bytes(c for n in frame.indices for c in (*rgb565(frame.palette[n]),255))
                (output/(name.split('/')[-1]+'.'+str(i)+'.png')).write_bytes(write_png(frame.width,frame.height,rgba))
    print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--wordmark',type=Path,required=True)
    p.add_argument('--out',type=Path,default=ROOT/'work/intro-english-assets')
    p.add_argument('--base',type=Path,default=ROOT/'dist/heroes-lore-5-english-multiscreen-v1.0.0.apk')
    p.add_argument('--original',type=Path,default=ROOT/'inputs/hl5-original-01.01.00.apk');a=p.parse_args()
    if not a.out.resolve().is_relative_to(ROOT/'work'):raise ValueError('Intro outputs must stay in work/')
    localize(a.base,a.original,a.wordmark,a.out)
