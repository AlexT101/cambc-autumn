#pragma once
#include "types.h"
#include "util.h"
#include <algorithm>
#include <cambc.h>
#include <variant>

namespace constants {
    // debug builds (`cambc run`) only: release builds, and so the platform, leave it all out
#ifdef CAMBC_DEBUG
    constexpr inline bool debug = true;
#else
    constexpr inline bool debug = false;
#endif

    // We hardcode engine constants because some of them are not constexpr.

    // rounds
    constexpr inline i32 capture_time = 5;    // on a dead group's tile before it pays
    constexpr inline i32 camp_sleep_time = 2; // unwatched, before a camp sleeps
    constexpr inline i32 respawn_time = 60;   // before a dead champion respawns
    constexpr inline i32 recall_time = 5;     // recall channel, before passives
    constexpr inline i32 tp_crystal_time = 3; // teleport-crystal channel
    constexpr inline u32 max_rounds = 2000;   // then tiebreakers decide
    constexpr inline u32 tile_reveal_rounds = 1; // collision reveal, this round too

    // tribute: ceil(gems * multiplier) + base rounds, at least minimum
    constexpr inline f64 submit_gem_duration_multiplier = 0.1;
    constexpr inline i32 submit_gem_base_duration = 0;
    constexpr inline i32 submit_gem_minimum_duration = 1;
    constexpr inline i32 submit_gems_range = 1; // Chebyshev tiles to the altar
    constexpr inline u32 winning_gems = 1000;   // tributed, to win

    // gold and health
    constexpr inline u32 kill_gold = 100;   // to the champion credited with a kill
    constexpr inline u32 assist_gold = 0;   // pool split among assists
    constexpr inline u32 passive_gold = 0;  // to each champion every round
    constexpr inline f32 spawn_healing = 1; // fraction of max health a round on spawn

    // wards
    constexpr inline u32 active_wards = 1;   // placed at once, per champion
    constexpr inline i32 ward_cooldown = 10; // rounds to recharge one
    constexpr inline i32 ward_lifetime = -1; // rounds; -1 never expires
    constexpr inline f32 ward_vision_radius = 6;
    constexpr inline f32 ward_placement_radius = 2;

    // altars and memory
    constexpr inline u32 altar_lock_hits = 5;       // attacks to destroy a lock
    constexpr inline u32 shared_memory_bytes = 8;   // per team, writable all game
    constexpr inline u32 draft_memory_bytes = 1024; // per team, frozen after the draft

    // Farthest Chebyshev distance a champion can hit from on its next turn, by
    // champion_type: its walk (1), dash (2), basic attack and spells.
    constexpr inline i32 reach[] = {
        5, // ryth: area stun, range 4 + radius 1
        5, // vesper_vale: dash 2, then attack 3
        4, // vendetta: walk 1 + dash 2 + attack 1
        5, // cassi: walk 1, then stun at 4
        4, // issac: walk 1 + dash 2 + attack 1
        5, // stellar: area damage, range 4 + radius 1
        5, // prism: area damage, range 4 + radius 1
        4, // marcella: damage spell, range 4
        3, // willow: attack 3 (her spell heals)
        4, // ren: stun at 4, or walk 1 + dash 2 + attack 1
        3, // varg: walk 1 + attack 1 + splash 1
        4, // tavi: stun at 4
        4, // heart_of_ruin: walk 1 + dash 2, landing hits radius 1
    };
    constexpr inline i32 max_reach = *std::max_element(std::begin(reach), std::end(reach));

    // ---===
    namespace test_helper {
        inline i32 design_reach(cambc::champion_type type) {
            const cambc::champion design{type};
            const i32 attack = design.base_stats().base_attack_range;
            const i32 walk = 1;
            i32 best = attack > 1 ? attack : walk + attack;
            if (type == cambc::champion_type::varg)
                best += i32(cambc::constants::passive_abilities::varg_splash_radius);
            for (const cambc::ability& a : design.abilities())
                if (a.info())
                    std::visit(
                        [&](const auto& x) {
                            using T = std::decay_t<decltype(x)>;
                            const i32 step = x.exclusive_with_movement ? 0 : walk;
                            if constexpr (std::is_same_v<T, cambc::ability_damage> ||
                                          std::is_same_v<T, cambc::ability_cc>)
                                best = std::max(best, step + i32(x.range));
                            else if constexpr (std::is_same_v<
                                                   T, cambc::ability_aoe_damage>)
                                best =
                                    std::max(best, step + i32(x.range) + i32(x.radius));
                            else if constexpr (std::is_same_v<T, cambc::ability_dash>)
                                best = std::max(
                                    best,
                                    i32(x.range) +
                                        std::max(x.radius > 0 ? walk + i32(x.radius)
                                                              : 0,
                                                 attack > 1 ? attack : walk + attack));
                        },
                        *a.info());
            return best;
        }
    } // namespace test_helper
    // ===---

    // throws naming the first setting the engine no longer agrees with
// ---===
    inline void test() {
#define SAME(name)                                                                     \
    util::require(name == cambc::constants::name,                                      \
                  "constants::" #name " differs from the engine")
        SAME(capture_time);
        SAME(camp_sleep_time);
        SAME(respawn_time);
        SAME(recall_time);
        SAME(tp_crystal_time);
        SAME(max_rounds);
        SAME(tile_reveal_rounds);
        SAME(submit_gem_duration_multiplier);
        SAME(submit_gem_base_duration);
        SAME(submit_gem_minimum_duration);
        SAME(submit_gems_range);
        SAME(winning_gems);
        SAME(kill_gold);
        SAME(assist_gold);
        SAME(passive_gold);
        SAME(spawn_healing);
        SAME(active_wards);
        SAME(ward_cooldown);
        SAME(ward_lifetime);
        SAME(ward_vision_radius);
        SAME(ward_placement_radius);
        SAME(altar_lock_hits);
        SAME(shared_memory_bytes);
        SAME(draft_memory_bytes);
#undef SAME
        for (i32 t = 0; t < i32(std::size(reach)); ++t)
            util::require(reach[t] ==
                              test_helper::design_reach(cambc::champion_type(t)),
                          "constants::reach differs from the engine's designs");
    }
// ===---
} // namespace constants
