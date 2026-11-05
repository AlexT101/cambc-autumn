#pragma once
#include "../common/common.h"
#include "../comms/comms.h"
#include "../path/dash.h"
#include <algorithm>
#include <cmath>
#include <vector>

// Home the sooner way, on foot or by recall, when health runs low: in a camp fight we cannot win,
// at the last round we could still walk out of the monsters' reach; elsewhere below `below`.
// Ending a turn on our own spawn heals to full.
//
//   should_go_home()   whether this turn heads home
//   rounds_home()      rounds until we start a turn on spawn, the sooner way
//   go_home(out)       this turn's part of getting there
namespace recall {
    constexpr f32 below = 0.5f;           // of max health, out of every awake monster's reach
    constexpr f32 margin = 0.033f;        // of max health, kept on top in a camp fight
    constexpr i32 home_emblem_rounds = 3; // a recall with a Home emblem (a second changes nothing)

    // rounds until a recall puts us on spawn at a turn start: what a running one has left, or a
    // new one's length
    inline i32 recall_rounds() {
        const champ_info& me = champs::my_info();
        if (channel::on.contains(cambc::champion_state::recalling))
            return me.channel;
        return util::has_passive(me, cambc::item_type::home_emblem_of_strength)
                   ? home_emblem_rounds
                   : cambc::constants::recall_time;
    }

    // a step a round over fixed ground; a dash only makes it sooner
    inline i32 walk_rounds() {
        return map_info::to_spawn.ptr()[map_info::cell(g::my_pos)];
    }

    inline i32 rounds_home() {
        return std::min(recall_rounds(), walk_rounds());
    }

    inline bool heading_home = false; // decided on an earlier turn, until healed

    // the awake monsters that reach us
    struct threat {
        f32 incoming = 0;  // their hits a round
        i32 steps_out = 0; // walking, to the nearest tile out of every monster's reach (7: none
                           // within 6)
        f32 group_hp = 0;  // left in their groups, as read now (unseen: full)
        f32 dealt = 0;     // a round on them, by us and the allies within 4 of them
    };

    inline threat threat_here(const cambc::bitboard& aggro) {
        using it = cambc::item_type;
        threat t;
        const champ_info& me = champs::my_info();
        const f32 taken = (util::has_passive(me, it::jungle_emblem_of_strength) ? 0.7f : 1) *
                          (util::has_passive(me, it::durability_emblem_of_strength) ? 0.9f : 1);
        static cambc::bitboard awake;
        static std::vector<vec2> at(camp_info::monsters.size());
        cambc::vision::awake_camp_tiles_into(awake);
        const u32 n = awake.positions_into(at);
        static std::vector<const camp_info::group*> groups; // theirs
        groups.clear();
        for (u32 i = 0; i < n; ++i) {
            const i32 kind = i32(camp_info::kind_at[at[i].y * g::W + at[i].x]);
            const cambc::camp_stats& s = camp_info::stats[kind];
            if (s.base_strength == 0 || util::chebyshev(at[i], g::my_pos) > s.base_attack_range)
                continue;
            t.incoming += s.base_strength * taken;
            if (const camp_info::group* grp = camp_info::group_on(at[i]);
                std::find(groups.begin(), groups.end(), grp) == groups.end())
                groups.push_back(grp);
        }
        // the nearest tile out of reach, within 6
        static cambc::bitboard safe, square;
        bb::or_into(aggro, map_info::fixed, safe), safe |= camp_info::tiles;
        bb::not_into(safe, safe);
        square.clear(), square.draw_chebyshev(g::my_pos, 6);
        safe &= square;
        static std::vector<vec2> tiles(13 * 13);
        const u32 k = safe.positions_into(tiles);
        const u16* const from_me = map_info::from_me.ptr();
        t.steps_out = 7;
        for (u32 i = 0; i < k; ++i)
            t.steps_out = std::min<i32>(t.steps_out, from_me[map_info::cell(tiles[i])]);
        // what is left of them, and who hits them
        t.dealt = me.strength * (util::has_passive(me, it::monster_emblem_of_strength) ? 1.1f : 1);
        for (const camp_info::group* grp : groups)
            for (const camp_info::monster& m : camp_info::members(*grp)) {
                f32 hp;
                const f32 full = camp_info::stats_of(m).base_health;
                t.group_hp += camp_info::health(m, hp) ? std::max(hp, 0.f) : full;
            }
        for (u32 a = 0; a < champs::n_allies; ++a) {
            const u32 ally = champs::allies[a];
            const vec2 p = comms::ally_position::pos[ally];
            if (ally == champs::my_id || p.x < 0)
                continue;
            bool near_any = false;
            for (const camp_info::group* grp : groups)
                for (const camp_info::monster& m : camp_info::members(*grp))
                    near_any |= util::chebyshev(p, m.pos) <= 4;
            if (near_any)
                t.dealt += champs::info[ally].strength;
        }
        return t;
    }

    // Whether this turn heads home. In reach of awake monsters: when we cannot finish them (their
    // hits until the last one dies would leave less than `margin`) and one more round's hits
    // would leave no more than walking out of their reach costs, plus `margin`; elsewhere, below
    // `below`. Once decided, until healed.
    inline bool should_go_home() {
        const champ_info& me = champs::my_info();
        if (me.health >= me.max_health)
            heading_home = false;
        if (heading_home)
            return true;
        static cambc::bitboard aggro, near;
        near.clear(), near.draw_chebyshev(g::my_pos, 13);
        camp_info::aggro_into(near, aggro);
        const threat t = aggro.is_set(g::my_pos) ? threat_here(aggro) : threat{};
        if (t.incoming == 0)
            return heading_home = me.health < below * me.max_health;
        if (me.health - t.incoming * (std::ceil(t.group_hp / t.dealt) - 1) > margin * me.max_health)
            return false; // we finish them first
        return heading_home = me.health <= f32(t.steps_out) * t.incoming + margin * me.max_health;
    }

    // tiles that monsters near us may hit: within 8 + the longest reach, 5
    inline const cambc::bitboard& aggro_near() {
        static cambc::bitboard aggro, near;
        near.clear(), near.draw_chebyshev(g::my_pos, 13);
        camp_info::aggro_into(near, aggro);
        return aggro;
    }

    // Home the sooner way: already there, stay (ending the turn on spawn heals); on foot when
    // that is no slower (a hit does not stop it, and it heals a turn sooner); else out of reach
    // of every awake monster (any hit cancels a recall), then recall. On a capture, a walk
    // waits for the payout and a recall starts so that it lands with it.
    template <class Out>
    void go_home(Out& out) {
        if (util::on_spawn())
            return;
        const i32 payout = camp_info::payout_in();
        if (payout + walk_rounds() <= std::max(payout, recall_rounds())) {
            if (payout == 0)
                path::walk_to(out, map_info::ally_spawn);
            return;
        }

        static cambc::bitboard blocked, safe;
        const cambc::bitboard& aggro = aggro_near();
        if (aggro.is_set(g::my_pos)) {
            // the nearest tile in sight out of reach (a walk still leaves the recall)
            bb::or_into(aggro, map_info::fixed, blocked), blocked |= camp_info::tiles;
            bb::not_into(blocked, safe);
            static cambc::bitboard square;
            square.clear(), square.draw_chebyshev(g::my_pos, 8);
            safe &= square;
            if (!safe.is_empty())
                path::walk_to(out, safe);
        }
        if (!aggro.is_set(g::my_pos) && util::can_recall() && payout <= recall_rounds())
            out.recall();
    }

    // false when not heading home
    template <class Out>
    bool step(Out& out) {
        if (!should_go_home())
            return false;
        go_home(out);
        return true;
    }
} // namespace recall
