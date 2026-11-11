#pragma once
#include "word.h"

// The last camp payout one of us saw: its group and round (mod 4, so up to 3 rounds old). The
// others take the group's respawn from it, so they don't head for a group they last saw alive.
// One field: of two payouts sent in a round, the later one is kept.
namespace comms::captures {
    constexpr u32 rounds = 4; // the payout round is sent mod this
    inline u32 field = 0;
    inline bool on = false; // the field fits in the word
    inline u64 last = 0;    // the value last read or written; 0: none yet

    inline void init() {
        u32 groups;
        cambc::detail::check(cambc::detail::sdk_map_num_camp_groups(&groups));
        const u128 values = u128(groups) * rounds + 1;
        if ((on = radix::fits(radix::times(layout.count, values))))
            field = layout.add(values);
    }

    // before camp_info::start_turn, which then reads the groups in view
    inline void start_turn() {
        if (!on || fields[field] == last)
            return;
        last = fields[field];
        const u32 r = u32((last - 1) % rounds);
        const i32 paid = g::round - i32((u32(g::round) - r) % rounds);
        camp_info::group& grp = camp_info::groups[(last - 1) / rounds];
        grp.state = camp_info::group_state::respawning, grp.back = paid + grp.respawn;
    }

    inline void end_turn() {
        if (!on || camp_info::paid_group < 0)
            return;
        fields[field] = last = 1 + u64(camp_info::paid_group) * rounds +
                               u64(camp_info::paid_round) % rounds;
        camp_info::paid_group = -1;
    }
} // namespace comms::captures
