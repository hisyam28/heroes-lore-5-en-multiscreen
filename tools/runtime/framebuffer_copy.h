#ifndef HL5_FRAMEBUFFER_COPY_H
#define HL5_FRAMEBUFFER_COPY_H
#include <stdint.h>

namespace hl5 {
// Layout verified against the target's DWARF and internalGrpCopyFrameBuffer.
struct GuestFramebuffer {
    int32_t width, height, stride, bits;
    uint32_t pixels;
};
struct FramebufferCopyPlan {
    uint32_t source = 0, destination = 0;
    uint32_t source_stride = 0, destination_stride = 0;
    uint32_t row_bytes = 0, rows = 0;
};
static inline int32_t copy_min(int32_t a, int32_t b) { return a < b ? a : b; }
static inline int32_t copy_max(int32_t a, int32_t b) { return a > b ? a : b; }

// Unsupported paths return false and execute the original guest instructions.
// In particular, overlapping copies retain the original forward-pixel behavior.
static inline bool plan_opaque_framebuffer_copy(const GuestFramebuffer& dst,
    int32_t dx, int32_t dy, int32_t width, int32_t height,
    const GuestFramebuffer& src, int32_t sx, int32_t sy,
    const int32_t* context, uint32_t transparent, FramebufferCopyPlan& out) {
    out = FramebufferCopyPlan{};
    if (transparent || context[8] < 255 || context[11] != 0 ||
        dx < 0 || dy < 0 || sx < 0 || sy < 0 ||
        width < 0 || height < 0 || width > 16384 || height > 16384 ||
        dx > 16384 || dy > 16384 || sx > 16384 || sy > 16384 ||
        (dst.bits != 16 && dst.bits != 32) || src.bits != dst.bits) return false;
    int32_t bpp = dst.bits / 8;
    const GuestFramebuffer* frames[] = {&src, &dst};
    for (const GuestFramebuffer* fb : frames) {
        if (fb->width <= 0 || fb->height <= 0 || fb->width > 16384 || fb->height > 16384 ||
            fb->stride < fb->width * bpp || fb->stride > 65536 || fb->pixels < 0x10000 ||
            uint64_t(fb->pixels) + uint64_t(fb->height) * fb->stride > 0xffffffffULL) return false;
    }
    int32_t left = copy_max(dx, context[1]);
    int32_t top = copy_max(dy, context[2]);
    int32_t right = copy_min(copy_min(dx + width, dst.width), context[3]);
    int32_t bottom = copy_min(copy_min(dy + height, dst.height), context[4]);
    right = copy_min(right, dx + src.width - sx);
    bottom = copy_min(bottom, dy + src.height - sy);
    if (left >= right || top >= bottom) return true;
    out.source = src.pixels + (sy + top - dy) * src.stride + (sx + left - dx) * bpp;
    out.destination = dst.pixels + top * dst.stride + left * bpp;
    out.source_stride = src.stride;
    out.destination_stride = dst.stride;
    out.row_bytes = (right - left) * bpp;
    out.rows = bottom - top;
    uint64_t source_end = uint64_t(out.source) + uint64_t(out.rows - 1) * src.stride + out.row_bytes;
    uint64_t destination_end = uint64_t(out.destination) + uint64_t(out.rows - 1) * dst.stride + out.row_bytes;
    if (uint64_t(out.source) < destination_end && uint64_t(out.destination) < source_end) return false;
    return true;
}
}
#endif
