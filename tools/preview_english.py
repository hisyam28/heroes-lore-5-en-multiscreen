"""Render a layout contact sheet using the unchanged target's actual ASCII bitmap font."""
from pathlib import Path
import json
import struct
import zipfile
import zlib
from hl5_vfs import Vfs
from english_layout import COLORS,native_lines

ROOT=Path(__file__).resolve().parents[1]


def main():
    with zipfile.ZipFile(ROOT/'inputs/hl5-original-01.01.00.apk') as apk:
        font=Vfs(apk.read('assets/data.vfs.mp3')).by_name['c/font/eng.fnt'].data
    if font[:6]!=b'HNF\1\10\13' or len(font)!=6+95*11:
        raise ValueError('Unrecognized target bitmap font')
    entries=json.loads((ROOT/'translations/catalog.json').read_text())['entries']
    chosen=[]
    for predicate in [lambda e:e['file']=='c/csv/menu_text.dat' and len(e['translation'])>60,
                      lambda e:e['file'].startswith('c/ep/') and e['field']=='dialogue' and len(e['translation'])>60,
                      lambda e:e['id']=='c/csv/skill_00.dat#20:description',
                      lambda e:e['file'].startswith('c/csv/quest_') and e['field']=='description',
                      lambda e:e['file'].startswith('c/csv/item_') and e['field']=='name',
                      lambda e:e['file'].startswith('c/csv2/help_') and e['field']=='body']:
        chosen.append(next(e for e in entries if predicate(e)))
    width,height=840,760;pixels=bytearray(bytes([17,20,28])*(width*height))
    def pixel(x,y,color):
        if 0<=x<width and 0<=y<height:pixels[(y*width+x)*3:(y*width+x)*3+3]=bytes(color)
    def text(value,x,y,color=(238,240,245)):
        current=x
        for char in value:
            if char in COLORS:continue
            if char in '\0;':break
            code=ord(char)
            if not 32<=code<=126:raise ValueError('Preview requires English font characters')
            glyph=font[6+(code-32)*11:6+(code-31)*11]
            for dy,row in enumerate(glyph):
                for dx in range(8):
                    if row & (128>>dx):pixel(current+dx,y+dy,color)
            current+=6
    text('ENGLISH ASSET LAYOUT - ORIGINAL 5x11 FONT / 6px ADVANCE',18,12,(120,220,210))
    text('Layout samples - not Android gameplay screenshots. First 12 lines shown.',18,28)
    metrics=[]
    for index,entry in enumerate(chosen):
        x=18+(index%2)*412;y=56+(index//2)*230
        box=entry['width_px'] or 360;lines=native_lines(entry['translation'],box)
        text(entry['file'].split('/')[-1]+' - '+entry['field'],x,y,(120,220,210))
        text(str(box)+'px / '+str(len(lines))+' lines',x,y+15,(160,170,188))
        for xx in range(box+2):pixel(x+xx,y+32,(80,100,120));pixel(x+xx,y+210,(80,100,120))
        for yy in range(179):pixel(x,y+32+yy,(80,100,120));pixel(x+box+1,y+32+yy,(80,100,120))
        for row,line in enumerate(lines[:12]):text(line,x+1,y+36+row*14)
        metrics.append({'id':entry['id'],'width':box,'lines':len(lines),'font_unchanged':True})
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    raw=b''.join(b'\0'+pixels[y*width*3:(y+1)*width*3] for y in range(height))
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
    (ROOT/'work/english-font-layout.png').write_bytes(png)
    (ROOT/'work/english-layout-preview.json').write_text(json.dumps(metrics,indent=2)+'\n')
    print('Generated work/english-font-layout.png from unchanged bitmap font')


if __name__=='__main__':main()
