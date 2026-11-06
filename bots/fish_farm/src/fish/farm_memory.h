// Intercontinental Fish's camp memory (research/fish-2026-11-05/FISH_MODEL.md 7.2): each group's
// newest state sighting, our own and the team's (posted through the 8 shared bytes, model/comms.cc),
// and the actor's farming history that the destination logit reads (visits, transitions, last
// group, allies seen on a group). Fish's states, not World's beliefs: World infers returns out of
// sight, Fish remembers what was seen.
#pragma once
#include <array>
#include <cstdint>
#include <vector>
#include "../model/world.h"

namespace aph::fish {

enum : std::uint8_t { st_unknown = 0, st_alive = 1, st_empty = 2, st_respawning = 3 };

struct Sighting {
    int round = -1;         // -1: never
    std::uint8_t state = st_unknown;
    int respawn_round = -1; // while respawning: the round it returns
};

struct FarmMemory {
    bool ready = false;
    std::vector<Sighting> own, team; // by group
    std::vector<int> ally_last;      // by group: the last round we saw an ally on one of its camp tiles
    std::vector<std::uint16_t> visits;
    // (source + 1) << 16 | dest for each transition seen; route = any (origin, c).
    std::vector<std::uint32_t> routes;
    int source = -1, last_group = -1;
    bool was_home = true;
    int last_camp = -1; // the group of our latest basic attack on a camp (7.3's prev), kept across death
    // Groups worked this turn (hits, a held capture), for the transitions at its end.
    std::array<int, 6> touched{};
    int n_touched = 0;
    // The Fish farm's state (fish/farm_turn.cc): the destination, the route origin it was chosen
    // from, its union state then; a spawn exit still to decide; the payout forecast's home trip.
    int target = -1, origin = -1, target_state = st_unknown, target_round = -1;
    bool spawn_pending = true, home = false, redecide = false, was_alive = true;
    int exclude = -1; // with redecide: a group to leave out
    int timer = 0;    // our recall's turn-start timer, 0 without one
    // Last turn's end: where, on which group, whether it was cleared, and our purse.
    vec2 end_pos{-1, -1};
    int end_group = -1, end_round = -1;
    bool end_cleared = false;
    int end_gems = 0, end_gold = 0;
    void init(int groups) {
        own.assign(static_cast<std::size_t>(groups), Sighting{});
        team.assign(static_cast<std::size_t>(groups), Sighting{});
        ally_last.assign(static_cast<std::size_t>(groups), -1);
        visits.assign(static_cast<std::size_t>(groups), 0);
        ready = true;
    }
    bool route(int origin, int dest) const {
        const std::uint32_t key = static_cast<std::uint32_t>(origin + 1) << 16 | static_cast<std::uint32_t>(dest);
        for (const auto k : routes)
            if (k == key) return true;
        return false;
    }
    void touch(int g) {
        if (g < 0) return;
        for (int i = 0; i < n_touched; ++i)
            if (touched[static_cast<std::size_t>(i)] == g) return;
        if (n_touched < static_cast<int>(touched.size())) touched[static_cast<std::size_t>(n_touched++)] = g;
    }
};
inline FarmMemory farm_memory;

inline FarmMemory& memory_of(const World& world) {
    if (!farm_memory.ready) farm_memory.init(static_cast<int>(world.map().groups.size()));
    return farm_memory;
}

inline std::uint8_t state_code(const CampBelief& c) {
    return c.state == CampState::alive ? st_alive : c.state == CampState::cleared ? st_empty : st_respawning;
}

// Our own sightings: every group read in view this round (World sets state_round only then). Also
// allies seen standing on camp tiles (ally_recent). Turn start and turn end both call it.
inline void observe_camps(const World& world) {
    auto& m = memory_of(world);
    const int round = world.round;
    const auto& map = world.map();
    for (std::size_t g = 0; g < world.camps.size(); ++g) {
        const auto& c = world.camps[g];
        if (c.state_round != round) continue;
        auto& s = m.own[g];
        s.round = round;
        s.state = state_code(c);
        s.respawn_round = s.state == st_respawning ? c.respawn_round : -1;
    }
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || a.pos_round != round || !in_bounds(a.pos)) continue;
        if (const int g = map.group_at(a.pos); g >= 0) m.ally_last[static_cast<std::size_t>(g)] = round;
    }
}

// A teammate's sighting from comms, kept if newer than the team's last.
inline void note_team_sighting(const World& world, int g, std::uint8_t state, int round, int respawn_round) {
    auto& m = memory_of(world);
    if (g < 0 || g >= static_cast<int>(m.team.size())) return;
    auto& s = m.team[static_cast<std::size_t>(g)];
    if (round < s.round) return;
    s.round = round, s.state = state, s.respawn_round = state == st_respawning ? respawn_round : -1;
}

// The newest sighting of g by anyone (7.2's team union): the team's where it is newer than ours.
inline const Sighting& union_sighting(const FarmMemory& m, int g, bool& from_team) {
    const auto& own = m.own[static_cast<std::size_t>(g)];
    const auto& team = m.team[static_cast<std::size_t>(g)];
    from_team = team.round >= 0 && (team.round > own.round || own.round < 0);
    return from_team ? team : own;
}

} // namespace aph::fish
