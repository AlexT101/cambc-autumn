#pragma once
#include "channel.h"
#include "globals.h"
#include "map_info.h"
#include "rng.h"
#include "types.h"
#include <algorithm>
#include <cambc.h>

namespace util {
    inline bool on_spawn() {
        return map_info::ally_spawn.is_set(g::my_pos);
    }

    inline vec2 sym_pos(vec2 p) {
        using cambc::symmetry;
        const symmetry s = cambc::map::symmetry();
        return {s == symmetry::vertical ? p.x : g::maxX - p.x,
                s == symmetry::horizontal ? p.y : g::maxY - p.y};
    }

    inline bool can_recall() {
        const cambc::champion& me = g::me();

        using cs = cambc::champion_state;
        constexpr u32 mask = (cs::alive | cs::recalling | cs::submitting_gems |
                              cs::teleporting | cs::recall_started)
                                 .bits();

        return (channel::state().bits() & mask) == cs::alive.bits() &&
               me.restrictions().is_empty();
    }

    // whether c has a family's passive: any of its emblems (strength, focus and health, two
    // items apart; the passive comes with the first)
    inline bool has_passive(const champ_info& c, cambc::item_type strength_emblem) {
        const auto* held = c.items.ptr() + u32(strength_emblem);
        return held[0] || held[2] || held[4];
    }

    inline i32 manhattan(vec2 a, vec2 b) {
        return std::abs(a.x - b.x) + std::abs(a.y - b.y);
    }

    inline i32 chebyshev(vec2 a, vec2 b) {
        return std::max(std::abs(a.x - b.x), std::abs(a.y - b.y));
    }

    inline vec2 rand_pos() {
        return vec2(rng::next(g::W), rng::next(g::H));
    }

    inline void require(bool cond, const char* what = "assertion failed") {
        if (!cond) {
            throw std::logic_error(what);
        }
    }
} // namespace util
