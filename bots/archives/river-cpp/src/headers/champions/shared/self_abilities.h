#pragma once

#include "../../../params.h"
#include <optional>
#include <algorithm>
#include <array>
#include <vector>
#include "../../comms.h"
#include "../cassi/states/assess.h"

namespace aph {
struct ChampionBelief;
class World;
class Pathing;
struct Field;
enum class AbilityKind : std::uint8_t;
class Safety;
struct HealTarget;
}
namespace aph {
namespace {
struct Hazard;
struct Landings;
}
}

namespace aph {
class World;

class Pathing;

class Safety;

struct ChampionBelief;

// The enemy a basic attack from here should hit, read live as vision changes when we move: the
// weakest, or for Varg the most value counting splash. Never one whose retaliation would kill us,
// nor one on its spawn (it heals at its turn end) unless the hit kills it or, with
// `stunnable_only`, stuns it; with that flag, only enemies a stun affects.
std::optional<cambc::handle_champion_t> attack_target(const World& world, bool stunnable_only = false);

// With the basic attack spent (by attacking, or by a ranged champion's walk), reset it and attack
// again. Enemies: the weakest in range. Camps: the member nearest death (a Vendetta kill readies
// both abilities), held back while an enemy is close enough to want the reset for a fight.
// `stunning_only`: only a reset whose attack stuns (Marcella), on an enemy it would stun; call it
// before abilities.cpp's casts, which share the one cast per turn, and the plain one after.
// `group`: only that group's camps.
bool reset_and_attack_enemy(const World& world, bool stunning_only = false);

bool reset_and_attack_camp(const World& world, int group);

// A camp tile lies within `range` of p.
bool camp_in_reach(const World& world, vec2 p, int range);

// Travel: dash to the landing nearest the goals if it gains at least 2 steps and no enemy is near
// enough to want the dash for a fight or an escape. Goals more than `max_steps` away are not searched for.
// On success, follow receives the search field, valid until the next call to this overload.
bool dash_towards(const World& world, Pathing& pathing, const bitboard& goals, int max_steps = unreachable, const Field** follow = nullptr);

bool dash_towards(const World& world, Pathing& pathing, const Field& field);

// Into attack range of `target`, else of a visible enemy we can finish or are beating; attack after it.
bool dash_to_attack(const World& world, Pathing& pathing, const ChampionBelief* target = nullptr);

// Out of the reach of visible enemies and awake camps, tie-broken towards `home`. `dead`: the
// tile of an enemy we killed this turn, which the beliefs still hold alive.
bool dash_away(const World& world, Pathing& pathing, const Field& home, vec2 dead = {-1, -1});

// A ready dash could land out of every visible enemy's and awake camp's reach, `dead` aside.
bool dash_clears(const World& world, Pathing& pathing, vec2 dead);

// Onto one of `tiles` (landings the caller accepts), nearest our spawn.
bool dash_onto(const World& world, Pathing& pathing, const bitboard& tiles);

// Willow: the ally the heal restores most, if it restores enough or the ally is low.
bool heal_ally(const World& world);

// A heal restoring `gain` of `amount` to an ally at `fraction` of its health is worth the cooldown.
bool worth_healing(float amount, float gain, float fraction);

// A visible healer, us or an ally, could heal now, restoring `amount`: an ally's cooldowns are not
// in its belief, so this reads them live.
bool heal_ready(const World& world, const ChampionBelief& healer, float& amount);

struct HealTarget {
    const ChampionBelief* ally;
    vec2 pos;
    float gain, fraction; // what the heal restores, and the ally's health fraction before it
};

// A visible ally off its spawn that a heal of `amount` is worth casting on. One keeping a recall
// going will reach spawn and heal there.
std::optional<HealTarget> heal_target(const World& world, const ChampionBelief& a, float amount);

// Varg: before damage from an awake camp, a camp we are hitting or an enemy in reach. `farmed`:
// the group farm chose, which we hit from attack range; another group's camp in attack range is
// hit only if our attack is spent.
bool shield_if_needed(const World& world, Safety& safety, int farmed);

}
namespace aph {
namespace {
constexpr int self_dash_steps = 2;

constexpr int reset_hold_margin = 2;

constexpr int travel_dash_clearance = 10;

constexpr float heal_min_share = 0.6f;

constexpr float heal_low_health = 0.5f;

constexpr float dash_min_health = 0.5f;

constexpr float chase_health = 0.4f;

constexpr int failed_search_pause = 4;

// The slot of `kind` if it can be cast now, else -1.
int ready(const World& world, AbilityKind kind);

bool self_cast(int slot, vec2 tile = {-1, -1});

struct Hazard {
    vec2 pos;
    int reach;
    bool camp;
};

// Enemies and awake monsters that could reach a tile within a dash of `here` before our next turn.
// A scratch vector, valid until the next call: allocating costs more than the work.
// `dead`: an enemy we killed this turn, still alive in the beliefs.
const std::vector<Hazard>& threats_near(const World& world, vec2 here, vec2 dead = {-1, -1});

// How deep a tile sits inside the threats' reach.
int danger(const std::vector<Hazard>& threats, vec2 p);

// A hidden unit on a landing fails the cast without spending it, so a few are tried.
struct Landings {
    static constexpr int tries = 3;
    std::array<vec2, tries> tiles;
    int count = 0;
};

// The first landings in increasing `score`, ties in board order, keeping only those `keep` accepts.
template <class Score, class Keep> Landings ranked(const bitboard& landings, Score score, Keep keep);

// Heart of Ruin's landing hits camps beside it: keep it off sleeping groups that strike.
bool wakes_camp(const World& world, vec2 p);

// Heart of Ruin's landing hits enemies beside it, unseen ones too, and Ren strikes back even while
// dying: keep it off any whose retaliation would kill us. `dead`: as threats_near's.
bool landing_suicidal(const World& world, vec2 p, vec2 dead = {-1, -1});

bool dash_to_first(int dash, Pathing& pathing, const Landings& landings);

int travel_dash_ready(const World& world);

bool travel_dash(const World& world, Pathing& pathing, int dash, int here_steps, auto steps_at);

// Varg's shield, cast at the turn's end, absorbs more than a hit that does not kill.
bool shield_wanted(const World& world);

}
}
namespace aph {
std::optional<cambc::handle_champion_t> attack_target(const World& world, bool stunnable_only);

bool reset_and_attack_enemy(const World& world, bool stunning_only);

// Monsters never move: the tiles within each range of a camp tile are kept.
bool camp_in_reach(const World& world, vec2 p, int range);

bool reset_and_attack_camp(const World& world, int group);

bool dash_towards(const World& world, Pathing& pathing, const Field& field);

bool dash_towards(const World& world, Pathing& pathing, const bitboard& goals, int max_steps, const Field** follow);

bool dash_to_attack(const World& world, Pathing& pathing, const ChampionBelief* target);

bool dash_away(const World& world, Pathing& pathing, const Field& home, vec2 dead);

bool dash_clears(const World& world, Pathing& pathing, vec2 dead);

bool dash_onto(const World& world, Pathing& pathing, const bitboard& tiles);

bool worth_healing(float amount, float gain, float fraction);

bool heal_ready(const World& world, const ChampionBelief& healer, float& amount);

std::optional<HealTarget> heal_target(const World& world, const ChampionBelief& a, float amount);

bool heal_ally(const World& world);

bool shield_if_needed(const World& world, Safety& safety, int farmed);

}
