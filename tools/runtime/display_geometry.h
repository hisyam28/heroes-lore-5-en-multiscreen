#ifndef HL5_DISPLAY_GEOMETRY_H
#define HL5_DISPLAY_GEOMETRY_H

#include <stdint.h>

namespace hl5 {
struct DisplayGeometry {
    int32_t logical_width = 400;
    int32_t logical_height = 240;
    int32_t x = 0, y = 0, width = 0, height = 0;
};

static inline int32_t logical_width_for_surface(int32_t width, int32_t height) {
    if (width <= 0 || height <= 0) return 400;
    int64_t logical = (240LL * width + height - 1) / height;
    if (logical < 400) logical = 400;
    return static_cast<int32_t>((logical + 1) & ~1LL);
}
static inline int32_t logical_height_for_surface(int32_t width, int32_t height) {
    if (width <= 0 || height <= 0) return 240;
    int64_t logical = (400LL * height + width - 1) / width;
    if (logical < 240) logical = 240;
    return static_cast<int32_t>((logical + 1) & ~1LL);
}

static inline DisplayGeometry cover_display(int32_t width, int32_t height,
                                           int32_t logical_width, int32_t logical_height) {
    DisplayGeometry result;
    result.logical_width = logical_width;
    result.logical_height = logical_height;
    if (width <= 0 || height <= 0 || logical_width <= 0 || logical_height <= 0) return result;
    // One uniform scale covers every edge. Rounding the logical width to an
    // even pixel may overscan a few physical pixels; it must not create bars.
    if (int64_t(width) * logical_height < int64_t(height) * logical_width) {
        result.height = height;
        result.width = (int64_t(height) * logical_width + logical_height - 1) / logical_height;
        result.x = (width - result.width) / 2;
    } else {
        result.width = width;
        result.height = (int64_t(width) * logical_height + logical_width - 1) / logical_width;
        result.y = (height - result.height) / 2;
    }
    return result;
}

static inline int32_t map_display_coordinate(int32_t coordinate, int32_t origin,
                                             int32_t extent, int32_t logical_extent) {
    if (extent <= 0 || logical_extent <= 0) return 0;
    int64_t mapped = (int64_t(coordinate) - origin) * logical_extent / extent;
    if (mapped < 0) return 0;
    if (mapped >= logical_extent) return logical_extent - 1;
    return static_cast<int32_t>(mapped);
}
} // namespace hl5
#endif
