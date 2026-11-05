#pragma once
#include "../common/common.h"
#include "../path/dash.h"

namespace farm {
    inline cambc::bitboard goals, off_camp_goals;

    // Next to monsters not seen dead (all, while waiting); off camp tiles if any.
    template <class Out>
    void walk_next_to(Out& out, const camp_info::group& grp) {
        goals.clear();
        for (const camp_info::monster& m : camp_info::members(grp))
            if (!camp_info::seen_dead(m))
                goals.draw_chebyshev(m.pos, 1);
        if (goals.is_empty())
            for (const camp_info::monster& m : camp_info::members(grp))
                goals.draw_chebyshev(m.pos, 1);
        bb::and_into(goals, camp_info::off_camps, off_camp_goals);
        path::walk_or_dash_to(out, off_camp_goals.is_empty() ? goals : off_camp_goals);
    }
} // namespace farm
