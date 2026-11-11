#pragma once
#include "../common/common.h"
#include "../farm/target_group.h"
#include "../path/dash.h"
#include "../recall/recall.h"
#include <algorithm>
#include <vector>

// A dead group pays whoever stands on its tiles for capture_time round starts, split
// between them, so one ally goes. Every ally scores the allies it sees on the reward
// groups in view the same way and gives them out best first, so they agree without
// talking. An ally on a group's tiles keeps it (no handoffs). After the payout,
// farming steps off (a champion on a tile holds back the respawn).
namespace capture {
    // An ally capturing a reward group. One on the group's tiles (0 steps) comes first: it
    // keeps it.
    struct capture_candidate {
        u32 ally;  // id
        u32 group; // index in camp_info::groups
        u32 steps; // to the group's nearest tile
        f32 score; // value per round of walking and holding

        bool is_better_than(const capture_candidate& o) const {
            if ((steps == 0) != (o.steps == 0))
                return steps == 0;
            if (score != o.score)
                return score > o.score;
            return ally != o.ally ? ally < o.ally : group < o.group;
        }
    };

    // g's pay, in gold, to champion c
    inline f32 value(const camp_info::group& g, const champ_info& c) {
        using namespace cambc::constants::passive_abilities;
        using ct = cambc::champion_type;
        const f32 gold_bonus =
            c.type == ct::vesper_vale ? vesper_vale_bonus_gold_percent : 0;
        const f32 tribute_gold =
            c.type == ct::marcella ? marcella_tribute_gold_per_gem : 0;
        return g.gold * (1 + gold_bonus / 100) +
               g.gems * (economy::gem_worth_in_gold() + tribute_gold);
    }

    // wealth at which an ally's claim counts half: the poorer ally gets the gold
    constexpr f32 spread_gold = 2294;

    // c capturing g from `steps` away: g's pay per round of walking there, then waiting
    // on a tile, scaled down by c's wealth to spread gold across the team
    inline f32 score_candidate(const camp_info::group& g, const champ_info& c, u32 steps) {
        return value(g, c) / f32(steps + constants::capture_time) * spread_gold /
               (spread_gold + c.wealth());
    }

    // in sight this round, alive, not recalling or tributing
    inline bool can_capture(const champ_info& c) {
        using cs = cambc::champion_state;
        constexpr u32 busy = (cs::alive | cs::recalling | cs::submitting_gems).bits();
        return c.vision_observed == g::round && (c.state.bits() & busy) == cs::alive.bits();
    }

    // low max distance limit in distance_field
    constexpr u16 search_limit = 10;

    // g's candidates: every ally that can capture (us among them), with its steps from g's
    // tiles (path, the same on every ally) and score_candidate.
    inline void add_candidates(const camp_info::group& g,
                               std::vector<capture_candidate>& candidates) {
        static cambc::bitboard roots, at, visited;
        static cambc::distance_field field;
        at.clear();

        u32 capturers[champs::max_champs / 2];
        u32 n = 0;
        for (u32 i = 0; i < champs::n_allies; ++i) {
            const u32 ally = champs::allies[i];
            if (can_capture(champs::info[ally]))
                capturers[n++] = ally, at.set(champs::info[ally].pos);
        }

        roots.clear();
        for (const camp_info::monster& m : camp_info::members(g))
            roots.set(m.pos);

        field.compute_to(map_info::fixed, roots, at, visited, search_limit);

        const u16* const steps = field.ptr();

        bool any_near = false;
        for (u32 i = 0; i < n; ++i)
            any_near |= steps[map_info::cell(champs::info[capturers[i]].pos)] !=
                        cambc::distance_field::unreachable;

        const u32 group = u32(&g - camp_info::groups.data());
        for (u32 i = 0; i < n; ++i) {
            const champ_info& c = champs::info[capturers[i]];

            i32 d = steps[map_info::cell(c.pos)];
            if (d == cambc::distance_field::unreachable) {
                if (any_near)
                    continue;

                // fall back to chebyshev if no one can reach within search limit
                d = INT32_MAX;
                for (const camp_info::monster& m : camp_info::members(g))
                    d = std::min(d, util::chebyshev(m.pos, c.pos));
            }

            candidates.push_back({capturers[i], group, u32(d), score_candidate(g, c, u32(d))});
        }
    }

    // The reward group ours to capture, or null: the candidates on the groups in view, best
    // first, each ally and each group given out once (a greedy assignment).
    inline const camp_info::group* assigned() {
        static std::vector<capture_candidate> candidates;
        candidates.clear();
        for (const camp_info::group* grp : camp_info::groups_in_view)
            if (grp->state == camp_info::group_state::reward)
                add_candidates(*grp, candidates);
        std::sort(candidates.begin(), candidates.end(),
                  [](const capture_candidate& a, const capture_candidate& b) {
                      return a.is_better_than(b);
                  });

        bool ally_out[champs::max_champs] = {};
        u32 groups_out[champs::max_champs / 2], n_out = 0; // one ally each
        for (const capture_candidate& c : candidates) {
            if (ally_out[c.ally] ||
                std::find(groups_out, groups_out + n_out, c.group) != groups_out + n_out)
                continue;
            if (c.ally == champs::my_id)
                return &camp_info::groups[c.group];
            ally_out[c.ally] = true, groups_out[n_out++] = c.group;
        }
        return nullptr;
    }

    template <class Out>
    void walk_to_nearest_tile(Out& out, const camp_info::group& g) {
        const u16* const steps = map_info::from_me.ptr();
        const camp_info::monster* nearest = nullptr;
        for (const camp_info::monster& m : camp_info::members(g))
            if (!nearest || steps[m.cell] < steps[nearest->cell])
                nearest = &m;
        path::walk_to(out, nearest->pos);
    }

    // false when no reward is ours
    template <class Out>
    bool step(Out& out) {
        const camp_info::group* grp = assigned();
        if (!grp)
            return false;
        if (camp_info::group_on(g::my_pos) != grp) {
            walk_to_nearest_tile(out, *grp);
            camp_info::heading = grp, camp_info::heading_round = g::round;
        } else if (camp_info::all_in_sight(*grp) &&
                   farm::choose_target_group(nullptr).via_spawn &&
                   !recall::aggro_near().is_set(g::my_pos))
            recall::go_home(out); // on it, every tile seen, out of monsters' reach, and the next
                                  // group is sooner by recall: it lands with the payout
        return true;
    }
} // namespace capture
