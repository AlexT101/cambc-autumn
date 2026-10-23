#pragma once

// Bounded, trace-build-only output for the canonical337f Big World branch witness. Callers pass
// values already read by the policy; this helper performs no SDK queries or policy evaluation.
#include "bot.h"
#include "comms.h"
#include "world.h"

namespace aph {
inline bool bigworld_witness_turn(const World& world) {
    const int actor = world.me().index;
    return world.round >= 35 && world.round <= 75 && (actor == 0 || actor == 3);
}

inline void bigworld_witness_turn_row(const World& world, const Memory& memory, const char* phase,
                                     char branch, bool owned, bool requested, bool offered, bool retreat) {
    if (!bigworld_witness_turn(world)) return;
    debug_block({
        const auto& me = world.me();
        std::printf("BW-TURN r=%d actor=%d phase=%s branch=%c belief_pos=%d,%d belief_hp=%.3f live=%d farm=%d claim=%d crew=%d bank=%d siege=%d "
                    "support=%d,%d,%d,%d rec=%d,%d,%d form=%d,%d,%d\n",
                    world.round, me.index, phase, branch, me.pos.x, me.pos.y, static_cast<double>(me.health),
                    static_cast<int>(me.alive), memory.farm_group, memory.claim, static_cast<int>(memory.crew),
                    static_cast<int>(memory.banking), static_cast<int>(memory.siege), static_cast<int>(owned),
                    static_cast<int>(requested), static_cast<int>(offered), static_cast<int>(retreat),
                    static_cast<int>(memory.recovery), memory.recovery_start, memory.recovery_group,
                    memory.formation_start, memory.formation_turns, memory.formation_group);
        for (const auto& ally : world.allies) {
            if (ally.is_self) continue;
            const int claim = comms::claim_of(world, ally.index);
            std::printf("BW-ALLY r=%d actor=%d ally=%d alive=%d visible=%d pos=%d,%d pos_source=%u pos_round=%d "
                        "stats_round=%d local_cached_claim=%d\n",
                        world.round, me.index, ally.index, static_cast<int>(ally.alive), static_cast<int>(ally.visible),
                        ally.pos.x, ally.pos.y, static_cast<unsigned>(ally.pos_source), ally.pos_round,
                        ally.stats_round, claim);
        }
    });
}

inline void bigworld_witness_farm_row(const World& world, const Memory& memory, const char* phase,
                                      const char* movement, int previous, int selected,
                                      int scan_iteration, int scan_limit, int shared, int help, int risky,
                                      int requested = -1, int result = -1) {
    if (!bigworld_witness_turn(world)) return;
    debug_block({
        std::printf("BW-FARM r=%d actor=%d phase=%s move=%s prev=%d selected=%d requested=%d result=%d claim=%d crew=%d scan_iteration=%d scan_limit=%d shared=%d help=%d risky=%d\n",
                    world.round, world.me().index, phase, movement, previous, selected, requested, result, memory.claim,
                    static_cast<int>(memory.crew), scan_iteration, scan_limit, shared, help, risky);
    });
}

inline void bigworld_witness_claim_row(const World& world, int old_claim, int posted_claim) {
    if (!bigworld_witness_turn(world)) return;
    debug_block({
        std::printf("BW-CLAIM-LOCAL r=%d actor=%d old_local=%d assigned_local=%d\n",
                    world.round, world.me().index, old_claim, posted_claim);
    });
}
} // namespace aph
