#pragma once
#include "../common/common.h"
#include "../path/dash.h"

namespace tribute {
    constexpr u32 at_gems = 30;

    template <class Out>
    bool step(Out& out) {
        if (champs::my_info().gems < at_gems)
            return false;
        if (!map_info::altar_adj.is_set(g::my_pos)) {
            path::walk_to(out, map_info::altar_adj);
            return true;
        }
        for (const vec2 dir : path::DIRS) // the altar next to us
            if (const vec2 pos = g::my_pos + dir;
                polyfill::is_in_bounds(pos) && polyfill::is_set(map_info::altars, pos)) {
                out.submit_gems(pos);
                return true;
            }
        return true;
    }
} // namespace tribute
