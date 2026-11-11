#pragma once
#include "../common/types.h"
#include <algorithm>

// optimal encoding

namespace radix {
    constexpr u32 max_parts = 16;
    constexpr u128 word_count = u128(1) << 64;
    constexpr u128 too_many = word_count + 1;

    inline bool fits(u128 count) {
        return count <= word_count;
    }

    inline u128 times(u128 a, u128 b) {
        u128 c;
        return __builtin_mul_overflow(a, b, &c) ? too_many : std::min(c, too_many);
    }

    // field i holds a value in [0, size[i]); field 0 is the lowest digit
    struct product {
        u64 size[max_parts];
        u128 count = 1;
        u32 n = 0;

        // appends a field of r < 2^64 values, returns its index
        u32 add(u128 r) {
            size[n] = u64(r), count = times(count, r);
            return n++;
        }

        u64 pack(const u64* x) const {
            u64 v = 0;
            for (u32 i = n; i--;)
                v = v * size[i] + x[i];
            return v;
        }

        void unpack(u64 v, u64* x) const {
            for (u32 i = 0; i < n; ++i)
                x[i] = v % size[i], v /= size[i];
        }
    };

    // alternative t holds a value in [0, its count), numbered from start[t]
    struct sum {
        u64 start[max_parts];
        u128 count = 0;
        u32 n = 0;

        // appends an alternative of c values, returns its tag
        u32 add(u128 c) {
            start[n] = u64(count), count = std::min(count + c, too_many);
            return n++;
        }

        // scans the alternatives in order, so put the common ones first
        u32 tag(u64 v) const {
            u32 t = 0;
            while (t + 1 < n && v >= start[t + 1])
                ++t;
            return t;
        }

        u64 wrap(u32 t, u64 x) const {
            return start[t] + x;
        }

        u64 unwrap(u32 t, u64 v) const {
            return v - start[t];
        }
    };
} // namespace radix
