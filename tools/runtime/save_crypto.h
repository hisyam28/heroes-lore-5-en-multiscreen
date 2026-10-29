#pragma once
#include <cstdint>
namespace hl5 {
// Target desRound (0x33e58): 16 rounds over 32 unpacked bits per half.
// Use the target's live key and its own E/P/S-box data, never a new save format.
static inline bool des_round_bits(uint32_t* left, uint32_t* right,
    const uint8_t* key, const uint8_t* expansion, const uint8_t* permutation,
    const uint8_t* sbox) {
    for (unsigned i=0;i<32;++i)
        if (left[i]>1 || right[i]>1 || permutation[i]<1 || permutation[i]>32) return false;
    for (unsigned i=0;i<48;++i) if (expansion[i]<1 || expansion[i]>32) return false;
    for (unsigned i=0;i<768;++i) if (key[i]>1) return false;
    for (unsigned i=0;i<512;++i) if (sbox[i]>15) return false;
    for (unsigned round=0;round<16;++round) {
        uint32_t old_right[32], expanded[48], substituted[32];
        for (unsigned i=0;i<32;++i) old_right[i]=right[i];
        for (unsigned i=0;i<48;++i) expanded[i]=right[expansion[i]-1]^key[round*48+i];
        for (unsigned box=0;box<8;++box) {
            const uint32_t* x=expanded+box*6;
            unsigned row=x[0]*2+x[5], col=x[1]*8+x[2]*4+x[3]*2+x[4];
            unsigned value=sbox[box*64+row*16+col];
            for (unsigned bit=0;bit<4;++bit) substituted[box*4+bit]=(value>>(3-bit))&1;
        }
        for (unsigned i=0;i<32;++i) right[i]=left[i]^substituted[permutation[i]-1];
        for (unsigned i=0;i<32;++i) left[i]=old_right[i];
    }
    return true;
}
}
