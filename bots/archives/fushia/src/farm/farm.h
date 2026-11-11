#pragma once
#include "approach.h"
#include "cast.h"
#include "hit.h"
#include "target_group.h"
#include "target_monster.h"

namespace farm {
    inline const camp_info::monster* last_target = nullptr;

    template <class Out>
    bool step(Out& out) {
        const group_candidate group = choose_target_group(last_target);
        last_target = group.monster;
        if (!group.monster)
            return false;
        if (group.via_spawn) { // sooner by recalling first
            recall::go_home(out);
            return true;
        }

        const camp_info::group& grp = camp_info::group_of(*group.monster);
        const monster_candidate pair = choose_target_monster(grp);

        if (pair.monster)
            path::walk_or_dash_to(out, pair.stand_at);
        else // no free tile to hit any of them from
            walk_next_to(out, grp);

        bool attacked = false;
        if (channel::state().contains(cambc::champion_state::can_attack))
            if (const hit_candidate hit = weakest_in_range(grp); hit.monster)
                out.attack_camp(*hit.monster), attacked = true;
        const bool walked = g::my_pos != champs::my_info().pos;
        if (const cast_choice c = choose_cast(grp, walked, attacked); c.slot >= 0) {
            out.cast(c.slot, c.on, c.at);
            if (c.resets)
                if (const hit_candidate hit = weakest_in_range(grp); hit.monster)
                    out.attack_camp(*hit.monster);
        }
        return true;
    }
} // namespace farm
