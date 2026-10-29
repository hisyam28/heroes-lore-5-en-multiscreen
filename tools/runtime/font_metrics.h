#ifndef HL5_FONT_METRICS_H
#define HL5_FONT_METRICS_H
#include <stdint.h>
namespace hl5 {
static inline bool font_escape(uint8_t c,const uint8_t* colors) {
    if(c==59)return true;
    for(unsigned i=0;i<11;++i)if(c==colors[i])return true;
    return false;
}
static inline int32_t font_width(const uint8_t* text,int32_t end,int32_t start,
    int32_t limit,int32_t ascii_width,int32_t hangul_width,const uint8_t* colors) {
    int32_t width=0,printed=0;
    for(int32_t i=start;i<end;) {
        uint8_t c=text[i];
        if(c==32 && printed==0){++i;++printed;continue;}
        if(c&128) {
            if(text[i+1]==0)break;
            int32_t next=width+hangul_width+1;
            if(limit>0 && next>limit)break;
            width=next;i+=2;++printed;
        } else {
            if(c==0 || c==59)break;
            if(font_escape(c,colors)){++i;++printed;continue;}
            int32_t next=width+ascii_width+1;
            if(limit>0 && next>limit)break;
            width=next;++i;++printed;
        }
    }
    return width;
}
static inline int32_t font_line_bytes(const uint8_t* text,int32_t end,int32_t start,
    int32_t limit,int32_t lines,int32_t ascii_width,int32_t hangul_width,const uint8_t* colors) {
    int32_t i=start,width=0,line=0;
    while(i<end && line<lines) {
        uint8_t c=text[i];
        if(c==32 && width==0){++i;continue;}
        if(c&128) {
            if(width+hangul_width<limit){width+=hangul_width+1;i+=2;}
            else {++line;width=0;}
        } else if(font_escape(c,colors)) {
            if(c==59){++line;width=0;}
            ++i;
        } else if(limit<=width+ascii_width){++line;width=0;}
        else {width+=ascii_width+1;++i;}
    }
    return i-start;
}
static inline void font_wrap_spaces(char* text,uint32_t length,int width,int advance,const uint8_t* colors){
    if(width<advance || width>16384 || advance<1 || advance>32)return;
    for(uint32_t i=0;i<length;++i)if(static_cast<uint8_t>(text[i])&128)return;
    int used=0;uint32_t last=0xffffffffu,start=0;
    for(uint32_t i=0;i<length;++i){
        uint8_t c=text[i];
        if(c==59){used=0;last=0xffffffffu;start=i+1;continue;}
        if(font_escape(c,colors))continue;
        if(c==32 && used==0)continue;
        if(used+advance>width){
            if(last!=0xffffffffu && last>=start){
                text[last]=';';start=last+1;used=0;
                for(uint32_t k=start;k<i;++k)if(!font_escape(text[k],colors))used+=advance;
                last=0xffffffffu;
            }else{used=0;start=i;last=0xffffffffu;}
        }
        if(c==32)last=i;
        used+=advance;
    }
}
}
#endif
