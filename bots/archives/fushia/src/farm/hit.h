#pragma once
#include "../common/common.h"

namespace farm {
    struct hit_candidate {
        const camp_info::monster* monster;
        f32 hp;

        bool is_better_than(const hit_candidate& o) const {
            return hp < o.hp; // finish kills first
        }
    };

    // null monster if none is in range and in sight
    inline hit_candidate weakest_in_range(const camp_info::group& grp) {
        const i32 range = g::me().attack_range();
        hit_candidate best{nullptr, 0};
        for (const camp_info::monster& m : camp_info::members(grp)) {
            f32 hp;
            if (util::chebyshev(m.pos, g::my_pos) > range || !camp_info::health(m, hp))
                continue;
            if (const hit_candidate h{&m, hp}; !best.monster || h.is_better_than(best))
                best = h;
        }
        return best;
    }
} // namespace farm
