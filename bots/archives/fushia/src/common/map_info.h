#pragma once
#include "bb.h"
#include "globals.h"
#include "types.h"
#include <cambc.h>

namespace map_info {
    inline const cambc::bitboard& walls = cambc::map::walls();
    inline const cambc::bitboard& holes = cambc::map::holes();
    inline const cambc::bitboard& altars = cambc::map::altars();
    inline const cambc::bitboard& ally_spawn =
        cambc::map::spawn_region(cambc::team::ally);
    inline const cambc::bitboard& enemy_spawn =
        cambc::map::spawn_region(cambc::team::enemy);

    inline cambc::bitboard altar_adj;

    inline cambc::bitboard fixed;
    inline cambc::distance_field to_spawn; // steps home over fixed ground
    inline cambc::distance_field from_me; // steps from the champion: from_me.get(tile)
    inline vec2 from_me_at{-1, -1};
    inline i32 row_cell[100], column_cell[100]; // cell() = row_cell[y] + column_cell[x]

    inline void init() {
        bb::or_into(walls, holes, fixed), fixed |= altars, fixed |= enemy_spawn;

        static cambc::bitboard row, temp;
        altars.shift_right_into(1, temp), bb::or_into(altars, temp, row);
        altars.shift_right_into(-1, temp), row |= temp;
        row.shift_up_into(1, temp), bb::or_into(row, temp, altar_adj);
        row.shift_up_into(-1, temp), altar_adj |= temp;
        bb::and_into(altar_adj, fixed, temp), altar_adj ^= temp;
        to_spawn.compute(fixed, ally_spawn, temp);

        const i32 chunk_columns = (g::W + 7) / 8;
        for (i32 y = 0; y < g::H; ++y)
            row_cell[y] = (y >> 3) * chunk_columns * 64 + (y & 7) * 8;
        for (i32 x = 0; x < g::W; ++x)
            column_cell[x] = (x >> 3) * 64 + (x & 7);
    }

    // Index of `tile` in a distance field's buffer: 8x8 chunks, rows inside a chunk,
    // chunks row by row (docs/ours/compute.md). Fields are read in place with it
    // instead of being exported.
    inline i32 cell(vec2 tile) {
        return row_cell[tile.y] + column_cell[tile.x];
    }

    inline void start_turn() {
        if (!g::alive || g::my_pos == from_me_at)
            return;
        static cambc::bitboard roots, visited;
        roots.clear(), roots.set(g::my_pos);
        from_me.compute(fixed, roots, visited);
        from_me_at = g::my_pos;
    }
} // namespace map_info
