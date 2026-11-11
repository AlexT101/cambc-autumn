#pragma once
#include "constants.h"
#include "globals.h"
#include "types.h"
#include <iostream>

// DBG(a << b): prints a line in debug builds, at no fuel; release builds leave it out
#define DBG(...) debug_block({ std::cout << __VA_ARGS__ << '\n'; })

namespace dbg {
    constexpr u32 white = 0xFFFFFF;

    inline void dot(vec2 tile, u32 rgb = white) {
        if constexpr (constants::debug)
            cambc::debug::draw_dot(tile, rgb);
    }

    inline void line(vec2 from, vec2 to, u32 rgb = white) {
        if constexpr (constants::debug)
            cambc::debug::draw_line(from, to, rgb);
    }

    inline void line(vec2 to, u32 rgb = white) {
        if constexpr (constants::debug)
            cambc::debug::draw_line(g::my_pos, to, rgb);
    }
} // namespace dbg
