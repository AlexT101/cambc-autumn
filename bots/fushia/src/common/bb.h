#pragma once
#include <cambc.h>

// out = a op b in one engine call; out may be a or b. The SDK only has in-place ops.
// Unchecked: the engine fails these only for a bad pointer.

namespace bb {
    using cambc::bitboard;
    namespace d = cambc::detail;

    inline void copy_into(const bitboard& a, bitboard& out) {
        d::sdk_Bitboard_Union(a.ptr(), a.ptr(), out.ptr());
    }
    inline void not_into(const bitboard& a, bitboard& out) {
        d::sdk_Bitboard_Not(a.ptr(), out.ptr());
    }

    inline void or_into(const bitboard& a, const bitboard& b, bitboard& out) {
        d::sdk_Bitboard_Union(a.ptr(), b.ptr(), out.ptr());
    }
    inline void and_into(const bitboard& a, const bitboard& b, bitboard& out) {
        d::sdk_Bitboard_Intersect(a.ptr(), b.ptr(), out.ptr());
    }
    inline void xor_into(const bitboard& a, const bitboard& b, bitboard& out) {
        d::sdk_Bitboard_Xor(a.ptr(), b.ptr(), out.ptr());
    }
} // namespace bb
