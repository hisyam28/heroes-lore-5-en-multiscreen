#ifndef HL5_FONT_BRIDGE_H
#define HL5_FONT_BRIDGE_H
#include "font_metrics.h"
#include "render_text_data.h"

// Display scratch only: no save, quest or original string is modified.
static uint32_t g_font_arena=0,g_font_cursor=0;
static constexpr uint32_t font_arena_size=512*1024;
static uint64_t g_font_metric_calls=0,g_cached_text_draws=0;
static std::vector<uint8_t> g_font_metric_buffer;
static void font_bridge_reset(){g_font_arena=g_font_cursor=0;g_font_metric_calls=g_cached_text_draws=0;}
static void font_bridge_begin_frame(){g_font_cursor=0;}
static bool font_arena_pointer(uint32_t pointer){return g_font_arena && pointer>=g_font_arena && pointer<g_font_arena+font_arena_size;}
static bool font_read_text(uint32_t pointer,std::string& result){
    result.clear();if(pointer<0x10000)return false;
    while(result.size()<4096){
        char bytes[128];uint32_t current=pointer+static_cast<uint32_t>(result.size());
        uint32_t count=std::min<uint32_t>(128,4096-(current&4095));
        if(!g_native_engine.read_memory(current,bytes,count))return false;
        auto end=static_cast<char*>(memchr(bytes,0,count));
        if(end){result.append(bytes,end-bytes);return true;}
        result.append(bytes,count);
    }return false;
}
static uint32_t font_display_copy(const std::string& value){
    if(!g_font_arena)g_font_arena=g_native_engine.allocate_heap(font_arena_size,8);
    uint32_t length=static_cast<uint32_t>(value.size()+1);
    uint32_t reserved=(length+3)&~3u;
    if(reserved>font_arena_size-g_font_cursor)return 0;
    uint32_t pointer=g_font_arena+g_font_cursor;
    if(!g_native_engine.write_memory(pointer,value.c_str(),length))return 0;
    g_font_cursor+=reserved;return pointer;
}
static std::string font_word_wrap(std::string text,int width,int advance,const uint8_t* colors){
    if(!text.empty())hl5::font_wrap_spaces(&text[0],static_cast<uint32_t>(text.size()),width,advance,colors);
    return text;
}
static bool font_argument(uc_engine* uc,unsigned index,uint32_t& value,bool write=false){
    static const int registers[]={UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3};
    if(index<4)return (write?uc_reg_write(uc,registers[index],&value):uc_reg_read(uc,registers[index],&value))==UC_ERR_OK;
    uint32_t stack=0;uc_reg_read(uc,UC_ARM_REG_SP,&stack);stack+=(index-4)*4;
    return write?g_native_engine.write_memory(stack,&value,4):g_native_engine.read_memory(stack,&value,4);
}
struct FontTextHook{const char* symbol;unsigned pointer;int width;int length;uc_hook hook;};
static void localize_font_text(uc_engine* uc,uint64_t,uint32_t,void* opaque){
    try{
        auto& rule=*static_cast<FontTextHook*>(opaque);uint32_t pointer=0,font=0;
        if(!font_argument(uc,rule.pointer,pointer) || font_arena_pointer(pointer))return;
        std::string original;if(!font_read_text(pointer,original))return;
        const char* translated=hl5::display_translation(original.c_str());
        std::string text=translated?translated:original;
        uint32_t supplied=0;
        if(rule.length>=0 && (!font_argument(uc,rule.length,supplied) || supplied!=original.size()))return;
        if(rule.width>=0){
            uint32_t width=0;uint8_t object[72];font_argument(uc,0,font);
            if(font_argument(uc,rule.width,width) && g_native_engine.read_memory(font,object,sizeof(object)))
                text=font_word_wrap(std::move(text),static_cast<int32_t>(width),static_cast<int8_t>(object[71])+1,object+24);
        }
        if(text==original)return;
        uint32_t replacement=font_display_copy(text);if(!replacement)return;
        font_argument(uc,rule.pointer,replacement,true);
        if(rule.length>=0){supplied=static_cast<uint32_t>(text.size());font_argument(uc,rule.length,supplied,true);}
        if(translated)++g_cached_text_draws;
    }catch(const std::exception& e){g_native_engine.abort_execution(e.what());}
     catch(...){g_native_engine.abort_execution("Display text bridge failed");}
}
static void accelerate_font_metrics(uc_engine* uc,uint64_t,uint32_t,void* opaque){
    try{
        bool lines=opaque!=nullptr;uint32_t args[6]={},lr=0;
        if(!read_raster_arguments(uc,args,lines?6:5,lr))return;
        int32_t end=args[2],start=args[3];
        if(end<0 || end>4096 || start<0 || start>end || args[1]<0x10000)return;
        uint8_t font[72];
        if(!g_native_engine.read_memory(args[0],font,sizeof(font)))return;
        int aw=static_cast<int8_t>(font[71]),kw=static_cast<int8_t>(font[70]);
        if(aw<0 || aw>31 || kw<0 || kw>31 || (lines && static_cast<int32_t>(args[4])<=std::max(aw,kw)))return;
        g_font_metric_buffer.resize(static_cast<size_t>(end)+2);
        if(!g_native_engine.read_memory(args[1],g_font_metric_buffer.data(),end+1))return;
        int32_t value=lines?hl5::font_line_bytes(g_font_metric_buffer.data(),end,start,args[4],args[5],aw,kw,font+24)
                           :hl5::font_width(g_font_metric_buffer.data(),end,start,args[4],aw,kw,font+24);
        uint32_t result=static_cast<uint32_t>(value);uc_reg_write(uc,UC_ARM_REG_R0,&result);uc_reg_write(uc,UC_ARM_REG_PC,&lr);
        ++g_font_metric_calls;
    }catch(const std::exception& e){g_native_engine.abort_execution(e.what());}
     catch(...){g_native_engine.abort_execution("Font metrics bridge failed");}
}
static void install_font_bridge(){
    font_bridge_reset();
    static FontTextHook rules[]={
      {"_ZN5BFont8DrawTextEiiiPc",4,-1,-1,0},
      {"_ZN5BFont8DrawTextEiiiPci",4,-1,-1,0},
      {"_ZN5BFont8DrawTextEiiiiPci",5,-1,-1,0},
      {"_ZN5BFont8DrawTextEiiiPcii",4,-1,-1,0},
      {"_ZN5BFont13DrawTextFieldEiiiiiPciiii",6,4,-1,0},
      {"_ZN5BFont12DrawTextLineEiiiiiPcii",6,4,-1,0},
      {"_ZN5BFont12GetLineCountEPcii",1,2,-1,0},
      {"_ZN5BFont19GetTextFieldPageLenEiiPc",3,1,-1,0},
      {"_ZN5BFont23IsTextFieldDrawCompleteEiiPciii",3,1,-1,0},
      {"_ZN5BFont8GetWidthEPci",1,-1,2,0}
    };
    for(auto& rule:rules){
        uint32_t entry=g_elf_loader.find_symbol(rule.symbol);
        if(entry && uc_hook_add(g_native_engine.uc_,&rule.hook,UC_HOOK_CODE,(void*)localize_font_text,&rule,entry,entry)!=UC_ERR_OK)
            throw std::runtime_error("Cannot install display text hook");
    }
    static uc_hook metrics[2];
    const char* names[]={"_ZN5BFont8GetWidthEPciii","_ZN5BFont19GetByteLenPrintableEPciiii"};
    for(unsigned i=0;i<2;++i){uint32_t entry=g_elf_loader.find_symbol(names[i]);
        if(!entry || uc_hook_add(g_native_engine.uc_,metrics+i,UC_HOOK_CODE,(void*)accelerate_font_metrics,i?(void*)1:nullptr,entry,entry)!=UC_ERR_OK)
            throw std::runtime_error("Cannot install verified font metrics hook");}
}
#endif
