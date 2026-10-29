#ifndef HL5_RASTER_RGB565_H
#define HL5_RASTER_RGB565_H
#include "framebuffer_copy.h"

namespace hl5 {
struct RasterRect {
    int32_t x = 0, y = 0, width = 0, height = 0;
};
static inline bool valid_packed565(const GuestFramebuffer& fb) {
    return fb.bits == 16 && fb.width > 0 && fb.height > 0 &&
        fb.width <= 16384 && fb.height <= 16384 && fb.stride >= fb.width * 2 &&
        fb.stride <= 65536 && fb.stride / fb.width == 2 && fb.pixels >= 0x10000 &&
        uint64_t(fb.stride) * fb.height <= 16 * 1024 * 1024 &&
        uint64_t(fb.pixels) + uint64_t(fb.height) * fb.stride <= 0xffffffffULL;
}
static inline bool plan_alpha_fill565(const GuestFramebuffer& fb, uint32_t rgb_type,
    int32_t x, int32_t y, int32_t width, int32_t height, RasterRect& rect) {
    rect = RasterRect{};
    if (rgb_type != 1 || !valid_packed565(fb) || x < -16384 || y < -16384 ||
        x > 16384 || y > 16384 || width < -16384 || height < -16384 ||
        width > 16384 || height > 16384) return false;
    if (x < 0) { width += x; x = 0; }
    if (y < 0) { height += y; y = 0; }
    width = copy_min(width, fb.width - x);
    height = copy_min(height, fb.height - y);
    if (width <= 0 || height <= 0) return true;
    rect.x = x; rect.y = y; rect.width = width; rect.height = height;
    return true;
}
// This deliberately preserves the target's /256 truncation and 255-alpha
// inverse. Alpha=255 is not replaced by an exact-color fill.
static inline uint16_t alpha_fill_pixel565(uint16_t pixel, uint32_t color, uint32_t alpha) {
    alpha &= 255;
    if (!alpha) return pixel;
    uint32_t inverse = 255 - alpha;
    uint32_t red = ((pixel & 0xf800) >> 8) * inverse + ((color >> 16) & 255) * alpha;
    uint32_t green = ((pixel & 0x07e0) >> 3) * inverse + ((color >> 8) & 255) * alpha;
    uint32_t blue = ((uint32_t(pixel) << 3) & 255) * inverse + (color & 255) * alpha;
    return static_cast<uint16_t>((red & 0xf800) | ((green >> 5) & 0x07e0) | (blue >> 11));
}
static inline void alpha_fill_row565(uint16_t* pixels, uint32_t count, uint32_t color, uint32_t alpha) {
    for (uint32_t x = 0; x < count; ++x) pixels[x] = alpha_fill_pixel565(pixels[x], color, alpha);
}

static inline uint16_t table_blend_pixel565(uint16_t pixel, uint32_t color,
    uint32_t alpha, const uint8_t* table) {
    alpha &= 255;
    if (!alpha) return pixel;
    uint32_t red = pixel >> 11;
    uint32_t green = (pixel & 0x07e0) >> 6;
    uint32_t blue = pixel & 31;
    uint32_t result_red = table[((color >> 19) & 31) * 32 + red];
    uint32_t result_green = uint32_t(table[((color >> 11) & 31) * 32 + green]) * 2;
    uint32_t result_blue = table[((color >> 3) & 31) * 32 + blue];
    uint32_t amount = alpha >> 3;
    if (amount <= 30) {
        result_red = (result_red * amount + red * (31 - amount)) >> 5;
        result_blue = (result_blue * amount + blue * (31 - amount)) >> 5;
        result_green = (result_green * (amount * 2) + green * 2 * (62 - amount * 2)) >> 6;
    }
    return static_cast<uint16_t>((result_blue & 31) | (result_red << 11) | ((result_green << 5) & 0x07e0));
}
static inline void table_blend_row565(uint16_t* pixels, uint32_t count,
    uint32_t color, uint32_t alpha, const uint8_t* table) {
    for (uint32_t x = 0; x < count; ++x)
        pixels[x] = table_blend_pixel565(pixels[x], color, alpha, table);
}
static inline uint16_t palette_blend_pixel565(uint16_t original,uint32_t color,
    uint32_t alpha,bool first_original,bool second_original,const uint8_t* table){
    uint16_t fixed=static_cast<uint16_t>(((color>>8)&0xf800)|((color>>5)&0x07e0)|((color>>3)&31));
    alpha&=255;
    if(!alpha)return first_original||second_original?original:fixed;
    uint32_t r=original>>11,g=(original&0x07e0)>>6,b=original&31;
    uint32_t cr=fixed>>11,cg=(fixed&0x07e0)>>6,cb=fixed&31;
    uint32_t ar=second_original?r:(first_original?cr:r);
    uint32_t ag=second_original?g:(first_original?cg:g);
    uint32_t ab=second_original?b:(first_original?cb:b);
    uint32_t br=second_original?r:(first_original?r:cr);
    uint32_t bg=second_original?g:(first_original?g:cg);
    uint32_t bb=second_original?b:(first_original?b:cb);
    uint32_t nr=table[ar*32+br],ng=uint32_t(table[ag*32+bg])*2,nb=table[ab*32+bb];
    uint32_t amount=alpha>>3;
    if(amount<=30){
        uint32_t base_r=first_original||second_original?r:cr;
        uint32_t base_g=first_original||second_original?g:cg;
        uint32_t base_b=first_original||second_original?b:cb;
        nr=(nr*amount+base_r*(31-amount))>>5;
        nb=(nb*amount+base_b*(31-amount))>>5;
        ng=(ng*(amount*2)+base_g*2*(62-amount*2))>>6;
    }
    return static_cast<uint16_t>((nr<<11)|((ng<<5)&0x07e0)|(nb&31));
}
static inline void palette_blend565(uint16_t* destination,const uint16_t* backup,
    uint32_t count,uint32_t color,uint32_t alpha,bool first_original,bool second_original,
    uint32_t skip_color,const uint8_t* table){
    for(uint32_t i=0;i<count;++i)if(backup[i]!=skip_color)
        destination[i]=palette_blend_pixel565(backup[i],color,alpha,first_original,second_original,table);
}
static inline bool plan_context_fill565(const GuestFramebuffer& fb, int32_t x,
    int32_t y, int32_t width, int32_t height, const int32_t* context, RasterRect& rect) {
    rect = RasterRect{};
    if (!valid_packed565(fb) || context[8] < 255 || context[11] ||
        x < -16384 || y < -16384 || x > 16384 || y > 16384 ||
        width < -16384 || height < -16384 || width > 16384 || height > 16384) return false;
    if (width < 0) { x += width; width = -width; }
    if (height < 0) { y += height; height = -height; }
    if (x < 0) { width += x; x = 0; }
    if (y < 0) { height += y; y = 0; }
    int32_t right = copy_min(copy_min(x + width, fb.width), context[3]);
    int32_t bottom = copy_min(copy_min(y + height, fb.height), context[4]);
    x = copy_max(x, context[1]); y = copy_max(y, context[2]);
    if (x >= right || y >= bottom) return true;
    rect.x = x; rect.y = y; rect.width = right - x; rect.height = bottom - y;
    return true;
}

// Verified from target GbmImage getters, not the reference source layout.
struct GuestIndexedImage {
    uint8_t type, palette_size;
    uint16_t width, height, reserved;
    uint32_t palette, pixels;
};
static_assert(sizeof(GuestIndexedImage) == 16, "Target image layout");
struct IndexedBlitPlan {
    RasterRect destination;
    int32_t sx = 0, sy = 0;
    uint32_t source_stride = 0;
    uint32_t bits = 0, flip_x = 0, flip_y = 0;
};
static inline bool plan_indexed_blit565(const GuestFramebuffer& fb, const int32_t* clip,
    int32_t x, int32_t y, int32_t width, int32_t height, const GuestIndexedImage& image,
    int32_t sx, int32_t sy, uint32_t mirror, uint32_t anchor, IndexedBlitPlan& plan) {
    plan = IndexedBlitPlan{};
    uint32_t bits = image.type & 15;
    if (!valid_packed565(fb) || fb.stride != fb.width * 2 || (bits != 4 && bits != 8) ||
        image.width == 0 || image.height == 0 || image.width > 16384 || image.height > 16384 ||
        width <= 0 || height <= 0 || width > 16384 || height > 16384 ||
        x < -16384 || y < -16384 || x > 16384 || y > 16384 ||
        sx < 0 || sy < 0 || sx > image.width || sy > image.height ||
        width > image.width - sx || height > image.height - sy ||
        image.palette < 0x10000 || image.pixels < 0x10000 ||
        (mirror != 0x10 && mirror != 8 && mirror != 4 && mirror != 12)) return false;
    if (anchor & 0x10) x -= width >> 1;
    else if (anchor & 0x20) x -= width;
    if (anchor & 2) y -= height >> 1;
    else if (anchor & 4) y -= height;
    // Keep all edge/clipping cases in the original implementation. Fully
    // contained rectangles leave CalcClipLCD's inputs unchanged in every mode.
    if (x < 0 || y < 0 || x < clip[0] || y < clip[1] ||
        x + width > fb.width || y + height > fb.height ||
        x + width > clip[2] || y + height > clip[3]) return false;
    uint32_t stride = bits == 4 ? (image.width + 1) / 2 : image.width;
    if (uint64_t(stride) * image.height > 16 * 1024 * 1024) return false;
    uint64_t source_end = uint64_t(image.pixels) + uint64_t(stride) * image.height;
    uint64_t palette_end = uint64_t(image.palette) + (bits == 4 ? 32 : 512);
    uint64_t destination_start = uint64_t(fb.pixels) + y * fb.stride + x * 2;
    uint64_t destination_end = destination_start + uint64_t(height - 1) * fb.stride + width * 2;
    if (source_end > 0xffffffffULL || palette_end > 0xffffffffULL ||
        (destination_start < source_end && uint64_t(image.pixels) < destination_end) ||
        (destination_start < palette_end && uint64_t(image.palette) < destination_end)) return false;
    plan.destination.x = x; plan.destination.y = y;
    plan.destination.width = width; plan.destination.height = height;
    plan.sx = sx; plan.sy = sy; plan.source_stride = stride; plan.bits = bits;
    plan.flip_x = mirror == 8 || mirror == 12;
    plan.flip_y = mirror == 4 || mirror == 12;
    return true;
}
static inline void indexed_blit_row565(uint16_t* destination, const uint8_t* source,
    const uint16_t* palette, uint32_t sx, uint32_t width, uint32_t bits,
    bool flip_x, uint32_t skip_color) {
    for (uint32_t x = 0; x < width; ++x) {
        uint32_t position = sx + x;
        uint32_t index = bits == 4 ? ((position & 1) ? source[position / 2] & 15
                                                               : source[position / 2] >> 4)
                                  : source[position];
        uint16_t color = palette[index];
        if (color != skip_color) destination[flip_x ? width - 1 - x : x] = color;
    }
}
}
#endif
