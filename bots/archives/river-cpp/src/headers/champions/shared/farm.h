#pragma once

#include "../../../params.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <limits>
#include <memory>
#include <optional>
#include <span>
#include <vector>
#include "../../comms.h"
#include "../cassi/states/assess.h"
#include "self_abilities.h"

namespace aph {
struct CampGroup;
struct StaticMap;
struct ChampionBelief;
struct CampBelief;
class World;
struct CampFight;
class Pathing;
struct ChampionFacts;
}
namespace aph {
namespace {
struct CampAttackTarget;
struct CampAttackTargets;
struct CampLeft;
struct AreaProfile;
}
}
namespace aph {
class Safety;
struct Aims;
}

namespace aph {
namespace {
// Test switches, off: each beat river head to head but not astraeus (research/EXPERIMENTS.md).
// camp_area_model: the clear estimate counts area hits on the members a 3x3 covers and stuns as
// cancelled attacks. dealers_first: walk to tiles in range of the first target that hits back, out of
// the others' reach where possible, instead of hitting whatever is in range.
inline constexpr bool camp_area_model = false, dealers_first = false;

struct CampAttackTarget {
    int group, member;
    float score, health;
};

struct CampAttackTargets {
    std::array<CampAttackTarget, 16> found;
    int n = 0;
};

// Our basic hit's targets from `from`: members of the groups the fight allows, most Strength removed
// first (camp_hit_worth). A member an ally yet to act will kill with a weaker hit is left to it
// (ally_finishes). `reset`: Vendetta's reset hit follows, so the kill plan below applies.
CampAttackTargets camp_targets_at(const World& world, const CampFight& fight, vec2 from, bool reset);

// The fight a hit on groups `allowed` accepts joins: those, and every group already awake.
template <class Allowed> const CampFight& camp_fight_for(const World& world, vec2 centre, int radius, Allowed allowed, int fresh);

template <class Allowed> CampAttackTargets camp_attack_targets(const World& world, Allowed allowed);

bool attack_camp_target(const World& world, const CampAttackTarget& target);

int attack_camp_targets(const World& world, const CampAttackTargets& targets);

// A camp in range of a group `allowed` accepts; the group attacked, or -1. Removing the most
// damage per hit goes first; Varg's splash wants the most live members next to its target.
template <class Allowed> int attack_camp(const World& world, Allowed allowed);

// The turn's first camp hit and the tile it is struck from (research/river/CAMP-SCORE.md): here; a step
// (melee walks freely; a ranged step spends the attack, which the reset buys back); a dash; or a dash
// then a step (melee). A tile scores its best target's Strength removed, twice while the reset's hit
// still follows (the cast unspent, or a Vendetta kill readying it), plus what a landing removes and
// stuns, plus the next camp phase's damage it spares over standing here as one round of the fight.
// Moving goes only to hit groups `moves` accepts, never deeper into visible enemies' reach. The group
// hit, or -1.
template <class Allowed, class Moves>
int plan_camp_attack(const World& world, Pathing& pathing, Safety& safety, Allowed allowed, Moves moves, const bitboard* avoid);

// Damage a turn, spells (and dash landings) spread over their cooldown.
float raw_output(const ChampionFacts& f, float strength, float focus);

float output(const ChampionBelief& c);

// output(), at least 1: a divisor for clear times.
float floored_output(const ChampionBelief& c);

// A farm cycle's worth a round, falling faster than 1 / rounds for long cycles: gems taken sooner
// turn into shards sooner, and a long clear is more often contested or cut short. On a large map
// every walk is long, so the horizon grows with it.
constexpr float cycle_horizon = 100;

float rate(const World& world, float worth, float rounds);

// Rounds from the first hold of a cleared group to its payout.
int capture_rounds();

constexpr float stickiness = 1.2f;

struct CampLeft {
    float health, strength;
};

// Damage taken clearing a group alone at `strength` a turn (callers pass floored_output, spells
// included), killing the deadliest first; also the rounds it takes. `reflect`: damage each hit on us
// returns to its monster (Ren). `left`: the living members, deadliest first; the reflect path wears it down.
float min_camp_damage(CampLeft* left, int n, float strength, float* rounds, float reflect);

// A champion's damage a turn from area hits (ground casts and landings, each a 3x3), and the camp
// attacks a round its stuns cancel, per member a stun reaches: unit stuns, then area ones.
struct AreaProfile {
    float area = 0, unit_stuns = 0, area_stuns = 0;
};

AreaProfile area_profile(const ChampionBelief& c);

// The most live members one 3x3 covers: a member's tile and its neighbours. Kept per belief.
int area_cover(const World& world, int g);

// Kept per group and strength while the group's belief is unchanged; the sorted members, for the
// last group asked, while its belief is.
float min_camp_damage_base(const World& world, int g, float strength, float* rounds, float reflect);

// With an area profile: area hits land on area_cover members (strength counts them once), and
// stuns cancel attacks, taken off as a share of the attackers' half-life count.
float min_camp_damage(const World& world, int g, float strength, float* rounds, float reflect = 0, const AreaProfile& p = {});

float min_camp_damage_base(const World& world, int g, float strength, float* rounds, float reflect);

// A group's weight by its side of the map: 1 in our half, falling towards the enemy spawn. Kept
// per group.
float home_ground(const StaticMap& map, int g);

// Damage spells a turn, spread over their cooldown: they reach 4, past the camps' 3.
float spell_output(const ChampionBelief& c);

// Basic attacks a turn, with the reset spread over its cooldown.
float basic_output(const ChampionBelief& c);

// Bit i: member i deals no damage and a basic attack of `range` reaches it from a tile out of the
// reach of every member that does. Static, so kept per group.
std::uint32_t safe_targets(const StaticMap& map, int g, int range);

// Rounds to clear a group alone without taking a hit: damage spells from 4 on the members that
// attack, basic attacks on the others from out of the attackers' range, or once they are dead.
// Negative if no spell can reach an attacker, or one reaches as far as our spells. `spells` and `basic`: our spell_output and
// basic_output (at least 1), with `range` our attack range.
float spell_clear_rounds(const StaticMap& map, int g, const CampBelief& belief, int range, float spells, float basic);

// Kept per group while its belief and our output hold.
float spell_clear_rounds(const World& world, int g, int range, float spells, float basic);

// No clear is quicker than the group's health over our whole output. Kept per group while its
// belief and our output hold.
float fastest_clear(const World& world, int g, float strength);

bool ally_engaged(const World& world, int group);

// Pathing::attack_tiles once prepared, null if preparing could take the fuel below `floor()`.
// Member tiles are static once prepared, so the union is kept while the same members live.
template <class Floor>
[[gnu::noinline]] const bitboard* farm_attack_tiles(const World& world, Pathing& pathing, int group, int range, Floor floor);

// The tiles of `tiles` (farm_attack_tiles, prepared) in range of the group's first target by
// camp_attack_targets' order (Strength removed per health) if it is within two steps of range of
// `here`, out of the other monsters' reach where the tiles allow (the strongest avoided first), else
// of any live member that hits back within that. Null otherwise.
const bitboard* dealer_tiles(const World& world, Pathing& pathing, int group, int range, const bitboard& tiles, vec2 here);

// After our attack killed a group's last monster, walk onto a free camp tile of it within a step,
// unless allies in sight already hold it (holders: more would only split the gems).
bool step_onto_cleared(const World& world, Pathing& pathing, int g);

// With the walk to spare after hitting `group`'s camp. If next phase's hits would take us below the recall
// line (recall_line), the step to the tile with the fewest that keeps a live member in attack range with
// a sight line. Else, melee, the step that brings its farthest live member nearest (Chebyshev), into no
// more hits or enemy reach than here.
bool camp_spare_step(const World& world, Pathing& pathing, Safety& safety, int group, const bitboard* avoid);

// The approach to a farm choice: onto its tiles once cleared, else into attack range.
int walk_range(const World& world, int g);

// Farm's spell clear (spell_clear_rounds): from a tile within ability range of a live attacker of
// the group but out of every attacker's reach, casting at the attackers, with basic attacks on
// what cannot hit back. False with no such tile or way to one, for the usual approach.
bool spell_clear(const World& world, Pathing& pathing, int g, const bitboard* zone, int cap);

// Chebyshev steps from p to the group's nearest camp tile.
int steps_to(const CampGroup& G, vec2 p);

// Carrying gems, farming on chains a capture onto the bag: it saves the walk to the altar and
// back but keeps the bag at risk for longer. It goes ahead only if the next group, by the time it
// adds to the trip, beats the best cycle starting from the altar; false means bank instead.
[[gnu::flatten]] bool farm(World& world, Pathing& pathing, Safety& safety, Aims& aims);

// A live group, awake or maybe, whose monsters not read asleep reach p.
bool awake_over(const World& world, int g, vec2 p);

// Retreating from an awake camp takes its hits anyway, and the clear is lost. Every awake group in
// reach counts: a nearly cleared harmless one next to an elk that is hitting us is no reason to stay.
bool finishing_camp(const World& world);

// A farming turn's output lands on camps: in enemy health points, the gems it earns at the map's
// gems per camp health point.
float farm_step_value(const World& world);

}
}
