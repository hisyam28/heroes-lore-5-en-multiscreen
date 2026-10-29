#ifndef HL5_ARM32_RELOCATIONS_H
#define HL5_ARM32_RELOCATIONS_H

#include <stdint.h>

namespace hl5 {

struct Arm32RelocationSymbol {
    uint32_t value = 0;
    uint32_t host_address = 0;
    bool defined = false;
    bool absolute = false;
    bool weak = false;
    bool null_entry = false;
    bool function = false;
    bool host_resolved = false;
};

// AAELF32: R_ARM_ABS32 = (S + A) | T. Unresolved weak S is zero.
static inline bool resolve_arm_abs32(const Arm32RelocationSymbol& symbol,
                                     uint32_t load_bias, uint32_t addend,
                                     uint32_t& result) {
    uint32_t address = 0;
    if (symbol.null_entry) {
        address = 0;
    } else if (symbol.defined) {
        address = symbol.absolute ? symbol.value : load_bias + symbol.value;
    } else if (symbol.host_resolved) {
        address = symbol.host_address;
    } else if (!symbol.weak) {
        return false;
    }
    const uint32_t thumb = symbol.function ? address & 1u : 0;
    result = ((address & ~thumb) + addend) | thumb;
    return true;
}

} // namespace hl5
#endif
