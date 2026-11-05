#pragma once
#include "unit.h"

// The one-round threat map: on each tile of the 7x7 window around us (every tile a move can
// end on), the damage we expect to take before our next turn. Each enemy deals its most
// damage at its distance, times its share; each awake monster in range hits us if no other
// champion stands nearer it (a monster hits the nearest champion in its range).
namespace fight {
    constexpr i32 window = 3; // tiles from us: dash 2, and a walk after it

    inline i32 window_index(vec2 t) {
        return (t.y - g::my_pos.y + window) * (2 * window + 1) + (t.x - g::my_pos.x + window);
    }

    // Enemy f's threat on a tile d away.
    inline f32 threat_of(const unit& f, i32 d) {
        return d < max_d ? f.share * f.dmg[d] : 0;
    }

    inline void add_monster_threat(f32* out) {
        constexpr i32 side = 2 * window + 1;
        static cambc::bitboard awake, near;
        static vec2 at[64];
        cambc::vision::awake_camp_tiles_into(awake);
        near.clear(), near.draw_chebyshev(g::my_pos, f32(window + 5));
        awake &= near;
        const u32 n = std::min(awake.positions_into(at), u32(std::size(at)));
        for (u32 i = 0; i < n; ++i) {
            const cambc::camp_stats& s =
                camp_info::stats[i32(camp_info::kind_at[at[i].y * g::W + at[i].x])];
            if (s.base_strength <= 0)
                continue;
            // it hits us where no other champion stands nearer it
            i32 r = s.base_attack_range;
            for (u32 j = 0; j < n_friends; ++j)
                r = std::min(r, util::chebyshev(friends[j], at[i]));
            for (u32 j = 0; j < n_foes; ++j)
                r = std::min(r, util::chebyshev(foes[j].pos, at[i]));
            const i32 cx = at[i].x - g::my_pos.x + window, cy = at[i].y - g::my_pos.y + window;
            const i32 x0 = std::max(cx - r, 0), x1 = std::min(cx + r, side - 1);
            for (i32 y = std::max(cy - r, 0); y <= std::min(cy + r, side - 1); ++y)
                for (i32 x = x0; x <= x1; ++x)
                    out[y * side + x] += s.base_strength;
        }
    }

    inline void threat_into(f32* out) {
        constexpr i32 side = 2 * window + 1;
        std::fill_n(out, side * side, 0.f);
        for (u32 f = 0; f < n_foes; ++f) {
            const unit& u = foes[f];
            const i32 fx = u.pos.x - g::my_pos.x, fy = u.pos.y - g::my_pos.y;
            for (i32 y = -window, i = 0; y <= window; ++y) {
                const i32 dy = std::abs(y - fy);
                for (i32 x = -window; x <= window; ++x, ++i)
                    out[i] += threat_of(u, std::max(std::abs(x - fx), dy));
            }
        }
        add_monster_threat(out);
    }
} // namespace fight
