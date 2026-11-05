#pragma once
#include "../common/common.h"
#include "move_manager.h"

//   cell(tile)  where a tile is in a distance field's buffer (map_info::cell)
// Moving towards a goal (walk_to, walk_or_dash_to) is in dash.h.

namespace path {
    constexpr vec2 DIRS[8] = {vec2::north,      vec2::north_east, vec2::east,
                              vec2::south_east, vec2::south,      vec2::south_west,
                              vec2::west,       vec2::north_west};

    inline const cambc::bitboard& fixed = map_info::fixed; // built by map_info::init()
    inline cambc::bitboard visited, blocked, stop_at, scratch;
    inline cambc::distance_field field;
    using map_info::cell;

    // A field's buffer, once a search has written it.
    inline const u16* values(const cambc::distance_field& f) { return f.ptr(); }

    // step to a neighbour `closer` accepts, tiebreak by distance (L2) to `aim`
    // asks `free` when a move is tried; moves through `out`. true if move succeeds.
    template <class Out>
    bool step_nearest(Out& out, vec2 from, vec2 aim, auto closer, auto free) {
        struct candidate {
            vec2 tile;
            i32 dist2;
        };
        candidate candidates[8];
        i32 count = 0;
        for (vec2 direction : DIRS)
            if (const vec2 next = from + direction; closer(next)) {
                const i32 dx = aim.x - next.x, dy = aim.y - next.y;
                candidates[count++] = {next, dx * dx + dy * dy};
            }

        while (count > 0) {
            i32 best = 0;
            for (i32 i = 1; i < count; ++i)
                if (candidates[i].dist2 < candidates[best].dist2)
                    best = i;
            const vec2 tile = candidates[best].tile;
            candidates[best] = candidates[--count];
            if (free(tile) && out.walk(tile))
                return true;
        }
        return false;
    }
} // namespace path
