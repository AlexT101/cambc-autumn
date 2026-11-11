#pragma once
#include "../common/common.h"
#include "word.h"
#include <algorithm>

// Where each ally ended its last turn. Between two end-of-turn writes an ally moves at
// most 6 tiles (teleport 3, walk 1, dash 2), so it sends its position mod 13; a recall
// or respawn lands on spawn, so then it sends its tile in the box 3 out from the spawn.
namespace comms::ally_position {
    constexpr i32 reach = 6, mod = 2 * reach + 1;

    enum kind : u32 { near, home, dead };
    inline radix::sum kinds;

    inline vec2 box_min;
    inline i32 box_w, box_h;
    inline u32 first_field, my_field;

    inline vec2 pos[champs::max_champs]; // x = -1 dead
    inline vec2 written{-1, -1};

    inline i32 near_axis(i32 last, i32 r) {
        return last - reach + ((r - last + reach) % mod + mod) % mod;
    }

    inline void init() {
        i32 x0 = g::W, y0 = g::H, x1 = 0, y1 = 0;
        for (const vec2 p : map_info::ally_spawn.positions())
            x0 = std::min(x0, p.x), y0 = std::min(y0, p.y), x1 = std::max(x1, p.x),
            y1 = std::max(y1, p.y);

        box_min = {std::max(x0 - 3, 0), std::max(y0 - 3, 0)};
        box_w = std::min(x1 + 3, g::maxX) - box_min.x + 1;
        box_h = std::min(y1 + 3, g::maxY) - box_min.y + 1;

        kinds.add(mod * mod), kinds.add(u64(box_w * box_h)), kinds.add(1);
        first_field = layout.n;
        for (u32 k = 0; k < champs::n_allies; ++k) {
            layout.add(kinds.count);
            if (champs::allies[k] == champs::my_id)
                my_field = first_field + k;
        }

        std::fill_n(pos, champs::n, vec2{(x0 + x1) / 2, (y0 + y1) / 2});
    }

    inline void start_turn() {
        for (u32 k = 0; k < champs::n_allies; ++k) {
            const u64 v = fields[first_field + k];
            vec2& p = pos[champs::allies[k]];
            switch (kinds.tag(v)) {
                case near:
                    p = {near_axis(p.x, i32(v % mod)), near_axis(p.y, i32(v / mod))};
                    break;
                case home: {
                    const u64 c = kinds.unwrap(home, v);
                    p = {box_min.x + i32(c % u64(box_w)),
                         box_min.y + i32(c / u64(box_w))};
                    break;
                }
                default:
                    p = {-1, -1};
            }
        }
    }

    inline void end_turn() {
        const vec2 p = g::me().position();
        const i32 bx = p.x - box_min.x, by = p.y - box_min.y;
        const bool in_box = u32(bx) < u32(box_w) && u32(by) < u32(box_h);
        u64& v = fields[my_field];
        if (p.x < 0)
            v = kinds.wrap(dead, 0);
        else if (in_box && (written.x < 0 || util::chebyshev(p, written) > reach))
            v = kinds.wrap(home, u64(by * box_w + bx));
        else
            v = kinds.wrap(near, u64(p.y % mod * mod + p.x % mod));
        written = p;
    }
} // namespace comms::ally_position
