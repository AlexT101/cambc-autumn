#pragma once
#include "types.h"

namespace rng {
    inline u64 state = 0;

    inline void seed(u64 value) {
        state = value;
    }

    // splitmix64: about 15 fuel
    inline u64 next() {
        u64 z = (state += 0x9e3779b97f4a7c15ull);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
        return z ^ (z >> 31);
    }

    inline u32 next(u32 limit) {
        return u32(next() % limit);
    }
} // namespace rng
