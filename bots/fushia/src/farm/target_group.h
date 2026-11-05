#pragma once
#include "../common/common.h"
#include "../path/dash.h"
#include "../recall/recall.h"
#include <algorithm>

// Which camp group to farm: the one we can start hitting soonest, never one with a monolith.
// Soonest by the quicker way there: from here, or recalling first and going from spawn.
namespace farm {
    // a group, through one of its monsters
    struct group_candidate {
        const camp_info::monster* monster;
        u32 steps; // rounds to its tile
        u32 score; // max(steps, group's wait): rounds until we can hit it
        bool via_spawn = false; // sooner by recalling first

        bool is_better_than(const group_candidate& o) const {
            return score < o.score || (score == o.score && steps < o.steps);
        }
    };

    // score >= never: can't farm (unreachable: 65535 steps; reward waiting: UINT32_MAX)
    constexpr u32 never = cambc::distance_field::unreachable;

    inline group_candidate score_group(const camp_info::monster& m, u32 steps, bool via_spawn) {
        return {&m, steps, std::max(steps, camp_info::wait(camp_info::group_of(m))), via_spawn};
    }

    inline cambc::distance_field dash_from_me, dash_from_spawn; // the crossable holes open
    inline vec2 dash_from_me_at{-1, -1};

    // path/dash.h's eta: walking, or the dash route (null: none) with the dash `wait` rounds
    // away at the first hole
    inline u32 eta(const u16* walk, const u16* dash, i32 wait, i32 cell) {
        return dash ? std::min<u32>(walk[cell], dash[cell] + u32(wait)) : walk[cell];
    }

    // Rounds until we stand on each tile (cell()): from here, or by recall and then from spawn,
    // each by path/dash.h's eta. Dash routes only where a dash crosses a hole. On a capture we
    // leave at the payout, and a recall lands with it.
    struct eta_from_me {
        const u16 *walk = map_info::from_me.ptr(), *dash = nullptr;
        const u16 *spawn_walk = map_info::to_spawn.ptr(), *spawn_dash = nullptr;
        i32 wait = 0, spawn_wait = 0;
        u32 recall = never; // rounds until a recall puts us on spawn; never: no recall now
        u32 payout = u32(camp_info::payout_in());

        eta_from_me() {
            using namespace path::dashing;
            if (util::can_recall())
                recall = u32(recall::recall_rounds());
            if (!steps_to_hole)
                return;
            if (g::my_pos != dash_from_me_at) {
                static cambc::bitboard roots;
                roots.clear(), roots.set(g::my_pos);
                dash_from_me.compute(open_holes, roots, path::visited);
                dash_from_me_at = g::my_pos;
            }
            static bool spawn_done = false; // spawn never moves
            if (!spawn_done)
                dash_from_spawn.compute(open_holes, map_info::ally_spawn, path::visited),
                    spawn_done = true;
            dash = path::values(dash_from_me), spawn_dash = path::values(dash_from_spawn);
            const i32 cooldown = i32(move_manager::dash_ability->cooldown());
            wait = std::max(0, cooldown - i32(steps_to_hole[map_info::cell(g::my_pos)]));
            spawn_wait = std::max(0, cooldown - i32(recall) -
                                         i32(steps_to_hole[map_info::cell(g::my_spawn_pos)]));
        }
        u32 here(i32 cell) const {
            return payout + eta(walk, dash, wait, cell);
        }
        u32 via_spawn(i32 cell) const {
            return std::max(payout, recall) + eta(spawn_walk, spawn_dash, spawn_wait, cell);
        }
    };

    inline group_candidate choose_target_group(const camp_info::monster* last) {
        const eta_from_me rounds;
        group_candidate best{nullptr, 0, never};

        // clever(?) move-ordering trick: use last turn's target first (it usually wins)
        if (last) {
            const u32 here = rounds.here(last->cell), spawn = rounds.via_spawn(last->cell);
            if (const group_candidate c = score_group(*last, std::min(here, spawn), spawn < here);
                c.score < never)
                best = c;
        }

        for (const camp_info::monster& m : camp_info::monsters) {
            const u32 here = rounds.here(m.cell), spawn = rounds.via_spawn(m.cell);
            const u32 d = std::min(here, spawn);
            if (d >= best.score || camp_info::group_of(m).kinds[i32(cambc::camp_type::monolith)])
                continue; // never a group with a monolith
            if (const group_candidate c = score_group(m, d, spawn < here); c.is_better_than(best))
                best = c;
        }
        return best;
    }
} // namespace farm
