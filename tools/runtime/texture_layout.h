#ifndef HL5_TEXTURE_LAYOUT_H
#define HL5_TEXTURE_LAYOUT_H
#include <stdint.h>

namespace hl5 {
// GLES 1 defaults to GL_UNPACK_ALIGNMENT=4. Include padding between rows,
// but never read past the last pixel of the last row.
static inline uint32_t texture_upload_bytes(int32_t width, int32_t height,
                                             uint32_t format, uint32_t type) {
    if (width <= 0 || height <= 0) return 0;
    uint32_t bpp = 0;
    if (type == 0x8363 && format == 0x1907) bpp = 2; // RGB565
    if ((type == 0x8033 || type == 0x8034) && format == 0x1908) bpp = 2;
    if (type == 0x1401) {
        if (format == 0x1908) bpp = 4;
        if (format == 0x1907) bpp = 3;
        if (format == 0x1906 || format == 0x1909) bpp = 1;
        if (format == 0x190A) bpp = 2;
    }
    if (!bpp) return 0;
    uint64_t row = uint64_t(width) * bpp;
    uint64_t stride = (row + 3) & ~uint64_t(3);
    uint64_t bytes = stride * (height - 1) + row;
    return bytes <= 64 * 1024 * 1024 ? static_cast<uint32_t>(bytes) : 0;
}
}
#endif
