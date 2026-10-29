"""Bounded lossless readers for the target's indexed GBM/MGR and PNG assets."""
from dataclasses import dataclass
import struct
import zlib


@dataclass
class Gbm:
    raw: bytes

    def __post_init__(self):
        if len(self.raw)<6:raise ValueError('Truncated GBM header')
        self.kind,self.count,self.width,self.height=struct.unpack_from('<BBHH',self.raw)
        self.bits=self.kind&15
        if self.bits not in (4,8) or not self.count or self.count>(1<<self.bits) or not self.width or not self.height:
            raise ValueError('Unsupported indexed GBM')
        self.stride=(self.width+1)//2 if self.bits==4 else self.width
        self.offset=6+self.count*2
        if len(self.raw)!=self.offset+self.stride*self.height:raise ValueError('GBM payload length mismatch')
        self.palette=struct.unpack_from('<'+'H'*self.count,self.raw,6)
        self.indices=[]
        for y in range(self.height):
            for x in range(self.width):
                byte=self.raw[self.offset+y*self.stride+(x//2 if self.bits==4 else x)]
                index=(byte&15 if x&1 else byte>>4) if self.bits==4 else byte
                if index>=self.count:raise ValueError('GBM palette index out of bounds')
                self.indices.append(index)

    def build(self,indices=None):
        if indices is None:return self.raw
        if len(indices)!=self.width*self.height or any(not 0<=n<self.count for n in indices):
            raise ValueError('Invalid GBM pixel plane')
        data=bytearray(self.raw)
        for y in range(self.height):
            for x in range(self.width):
                position=self.offset+y*self.stride+(x//2 if self.bits==4 else x);index=indices[y*self.width+x]
                if self.bits==8:data[position]=index
                elif x&1:data[position]=(data[position]&240)|index
                else:data[position]=(data[position]&15)|(index<<4)
        return bytes(data)


def parse_mgr(raw):
    if len(raw)<4:raise ValueError('Truncated MGR')
    count=struct.unpack_from('<I',raw)[0]
    if count>4096:raise ValueError('Invalid MGR count')
    position=4;frames=[]
    for _ in range(count):
        if position+4>len(raw):raise ValueError('Truncated MGR length')
        length=struct.unpack_from('<I',raw,position)[0];position+=4
        if length>len(raw)-position:raise ValueError('Truncated MGR frame')
        frames.append(Gbm(raw[position:position+length]));position+=length
    if position!=len(raw):raise ValueError('Unexpected MGR tail')
    return frames


def build_mgr(frames):
    return struct.pack('<I',len(frames))+b''.join(struct.pack('<I',len(raw))+raw for raw in frames)


def rgb565(value):
    return (((value>>11)&31)*255//31,((value>>5)&63)*255//63,(value&31)*255//31)


def png_chunk(kind,data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)


def write_png(width,height,rgba):
    if len(rgba)!=width*height*4:raise ValueError('Invalid RGBA plane')
    scan=b''.join(b'\0'+bytes(rgba[y*width*4:(y+1)*width*4]) for y in range(height))
    return (b'\x89PNG\r\n\x1a\n'+png_chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+
            png_chunk(b'IDAT',zlib.compress(scan))+png_chunk(b'IEND',b''))


def resize_rgba(image,width,height):
    """Area resampling for Android icon sizing; keep the entire source image."""
    if not 0<width<=image.width or not 0<height<=image.height:raise ValueError('Only bounded icon downsampling is supported')
    rgba=image.rgba();result=bytearray()
    for y in range(height):
        y0=y*image.height//height;y1=(y+1)*image.height//height
        for x in range(width):
            x0=x*image.width//width;x1=(x+1)*image.width//width
            alpha=red=green=blue=0
            for yy in range(y0,y1):
                for xx in range(x0,x1):
                    p=(yy*image.width+xx)*4;a=rgba[p+3];alpha+=a
                    red+=rgba[p]*a;green+=rgba[p+1]*a;blue+=rgba[p+2]*a
            count=(y1-y0)*(x1-x0)
            result.extend((red//alpha if alpha else 0,green//alpha if alpha else 0,
                           blue//alpha if alpha else 0,alpha//count))
    return bytes(result)


class Png:
    def __init__(self,raw):
        if raw[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Invalid PNG')
        self.raw=raw;self.chunks=[];p=8
        while p<len(raw):
            if p+12>len(raw):raise ValueError('Truncated PNG chunk')
            size=struct.unpack_from('>I',raw,p)[0];kind=raw[p+4:p+8];data=raw[p+8:p+8+size]
            if p+12+size>len(raw) or zlib.crc32(kind+data)&0xffffffff!=struct.unpack_from('>I',raw,p+8+size)[0]:
                raise ValueError('PNG CRC/length mismatch')
            self.chunks.append((kind,data));p+=12+size
        if not self.chunks or self.chunks[0][0]!=b'IHDR' or self.chunks[-1][0]!=b'IEND':raise ValueError('Missing PNG bounds')
        self.width,self.height,self.depth,self.kind,compression,filtering,interlace=struct.unpack('>IIBBBBB',self.chunks[0][1])
        if not 0<self.width<=16384 or not 0<self.height<=16384 or self.depth!=8 or self.kind not in (2,3,6) or compression or filtering or interlace:
            raise ValueError('Unsupported PNG encoding')
        channels={2:3,3:1,6:4}[self.kind];stride=self.width*channels
        scan=zlib.decompress(b''.join(d for k,d in self.chunks if k==b'IDAT'))
        if len(scan)!=(stride+1)*self.height:raise ValueError('PNG scan length mismatch')
        previous=bytearray(stride);plane=bytearray()
        for y in range(self.height):
            mode=scan[y*(stride+1)];row=bytearray(scan[y*(stride+1)+1:(y+1)*(stride+1)])
            if mode>4:raise ValueError('Invalid PNG filter')
            for x in range(stride):
                a=row[x-channels] if x>=channels else 0;b=previous[x];c=previous[x-channels] if x>=channels else 0
                if mode==1:predict=a
                elif mode==2:predict=b
                elif mode==3:predict=(a+b)//2
                elif mode==4:
                    v=a+b-c;dist=(abs(v-a),abs(v-b),abs(v-c));predict=(a,b,c)[dist.index(min(dist))]
                else:predict=0
                row[x]=(row[x]+predict)&255
            plane.extend(row);previous=row
        self.plane=bytes(plane);self.palette=None
        if self.kind==3:
            palette=next(d for k,d in self.chunks if k==b'PLTE');alpha=next((d for k,d in self.chunks if k==b'tRNS'),b'')
            self.palette=[tuple(palette[i:i+3])+(alpha[i//3] if i//3<len(alpha) else 255,) for i in range(0,len(palette),3)]
            if any(n>=len(self.palette) for n in plane):raise ValueError('PNG palette index out of bounds')

    def rgba(self):
        if self.kind==6:return self.plane
        if self.kind==2:return bytes(c for i in range(0,len(self.plane),3) for c in (*self.plane[i:i+3],255))
        return bytes(c for n in self.plane for c in self.palette[n])

    def build_indexed(self,plane):
        if self.kind!=3 or len(plane)!=self.width*self.height or any(n>=len(self.palette) for n in plane):
            raise ValueError('Invalid indexed PNG plane')
        scan=b''.join(b'\0'+bytes(plane[y*self.width:(y+1)*self.width]) for y in range(self.height))
        result=bytearray(self.raw[:8]);written=False
        for kind,data in self.chunks:
            if kind==b'IDAT':
                if written:continue
                data=zlib.compress(scan);written=True
            result.extend(png_chunk(kind,data))
        return bytes(result)
