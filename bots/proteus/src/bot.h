#pragma once
#include "util.h"

namespace aph {

class World;
class Pathing;

struct Memory {
    int round = -1;    // of our previous turn
    float health = 0;  // at its end
    float damage = 0;  // taken since, as of this turn's start (net of heals)
    bool banking = false; // our bag headed for an altar rather than another capture last turn
    int farm_group = -1;  // farm's latest choice: kept when near tied, walked to on short fuel
    int recall_farm = -1; // farm_group, while a recall reaches it sooner by way of spawn (recall_to_farm)
    int claim = -1;       // the group we told allies we work towards, or -1
    int live_claim = -1;  // our claim observed alive at the start of our previous turn
    bool crew = false;    // joining an ally's claim rather than our own
    float camp_fled = -1; // our health when camp fire last sent us home: we keep going until healed above it or home
    bool siege = false;   // our claim is a Monolith or a group sealing the altars (seals()), attacked by the team together
    int staged_since = -1; // round we started waiting near it for the others
    int wait_altar = -1, wait_since = -1;   // the altar we wait at for a safe tribute, since when
    int avoid_altar = -1, avoid_until = -1; // one we gave up waiting at, skipped until that round
    bool wants_crystal = false; // once a crystal hop to an altar would have beaten walking to bank: kept all game
    int hop_refused = -1, hop_refused_until = -1; // a farm hop no safe landing was found for, skipped until then
    // The protected mate's (Prism's) stops beside Willow for heals (support.cc): the current one's
    // start, turns, farm group and latest health; the last closed one's group and health, -1 for
    // none; and whether to retreat until fit for work while that group stays our farm choice.
    int recovery_start = -1, recovery_turns = 0;
    int recovery_group = -1, recovery_closed_group = -1;
    bool recovery_reentry = false;
    float recovery_health = 0, recovery_closed_health = -1;
    // Willow's wait beside its mate with no heal or progress to work: since when, and turns.
    int formation_start = -1, formation_turns = 0;
    // Our operation on a strong group with an expected crew (farm, economy/crew.cc): the group, the
    // round we came within its reach (-1 until then), and per group the round before which it is
    // not proposed again.
    int crew_proposed = -1, crew_reached = -1;
    std::array<int, 256> crew_ban{};
    // Farm's Monolith operation we work (farm_monolith), -1 for none; since when we stand staged out
    // of its reach for the crew; the crew's output as last priced; for the traces, since when we
    // work it and the damage taken since.
    int mono_group = -1, mono_staged = -1, mono_since = -1;
    float mono_output = 0, mono_taken = 0;
    vec2 ward{-1, -1};    // our latest ward
    vec2 bushes_watched{-1, -1}; // a tile whose bushes in ward reach are all in our cluster or our ward's
};

// `world` is as of the turn's start, observed again after a ward; ask cambc for anything that
// changes after acting.
void play_turn(World& world, Pathing& pathing, Memory& memory);
// With the turn's spare fuel, each step only while more than `fuel_floor` would remain: the walk
// to our farm choice from where we ended, the farm loop's order and the altar walk.
void prepare_next_turn(const World& world, Pathing& pathing, const Memory& memory, std::uint64_t fuel_floor);

} // namespace aph
