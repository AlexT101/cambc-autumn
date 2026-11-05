#pragma once
#include "../common/common.h"
#include <array>

// The target group's best (monster, tile to stand on) pair.
namespace farm {
    struct monster_candidate {
        const camp_info::monster* monster;
        vec2 stand_at; // in range and in sight of monster
        u32 steps;     // to stand_at
        f32 hp;        // full when unseen

        bool is_better_than(const monster_candidate& o) const {
            if (steps != o.steps)
                return steps < o.steps; // hit sooner
            return hp < o.hp;           // finish kills first
        }
    };

    // Monsters not seen dead (all, while waiting for the respawn); null if no pair.
    inline monster_candidate choose_target_monster(const camp_info::group& grp) {
        bool any_open = false;
        for (const camp_info::monster& m : camp_info::members(grp))
            any_open |= !camp_info::seen_dead(m);

        // standable: not fixed, no other champion, no maybe-alive monster, not another
        // group's tile (one there blocks its respawn, or waits on its reward); off camp
        // tiles while waiting. static: boards allocate
        static cambc::bitboard free, around, square;
        polyfill::champion_tiles_into(free);
        free.set(g::my_pos, false);
        free |= camp_info::maybe_alive, free |= map_info::fixed;
        if (any_open) {
            static cambc::bitboard others;
            bb::copy_into(camp_info::tiles, others);
            for (const camp_info::monster& m : camp_info::members(grp))
                others.set(m.pos, false);
            free |= others;
        } else
            free |= camp_info::tiles;
        bb::not_into(free, free);

        const f32 range = f32(g::me().attack_range());
        const u16* const steps = map_info::from_me.ptr();
        std::array<vec2, 49> tiles; // 7x7: attack range is 1 or 3
        monster_candidate best{nullptr, {}, 0, 0};
        for (const camp_info::monster& m : camp_info::members(grp)) {
            if (any_open && camp_info::seen_dead(m))
                continue;
            f32 hp = camp_info::stats_of(m).base_health;
            camp_info::health(m, hp);
            // sight is symmetric, except bush tiles, which drop out
            g::me().visible_tiles_from_into(m.pos, around);
            square.clear(), square.draw_chebyshev(m.pos, range);
            around &= square, around &= free;
            const u32 n = around.positions_into(tiles);
            for (u32 i = 0; i < n; ++i) {
                const u32 d = steps[map_info::cell(tiles[i])];
                if (d == cambc::distance_field::unreachable)
                    continue;
                if (const monster_candidate c{&m, tiles[i], d, hp};
                    !best.monster || c.is_better_than(best))
                    best = c;
            }
        }
        return best;
    }
} // namespace farm
