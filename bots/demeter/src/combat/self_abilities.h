// Attack resets, dashes, heals and shields. Each casts at most once and returns true if it did;
// only one cast succeeds per turn, so call the most valuable first.
#pragma once
#include <array>
#include <optional>
#include "../util.h"

namespace aph {

class World;
class Pathing;
class Safety;
struct ChampionBelief;

// The enemy a basic attack from here should hit, read live as vision changes when we move: the
// biggest kill, else the weakest, or for Varg the most value counting splash. Never one whose
// retaliation would kill us, nor one on its spawn (it heals at its turn end) unless the hit kills
// it or, with `stunnable_only`, stuns it; with that flag, only enemies a stun affects.
std::optional<cambc::handle_champion_t> attack_target(const World& world, bool stunnable_only = false);

// With the basic attack spent (by attacking, or by a ranged champion's walk), reset it and attack
// again. Enemies: attack_target's, unless Varg's shield wants the cast and the hit does not kill.
// Camps: the member nearest death (a Vendetta kill readies both abilities), held back while an
// enemy is close enough to want the reset for a fight.
// `stunning_only`: only a reset whose attack stuns (Marcella), on an enemy it would stun; call it
// before abilities.cc's casts, which share the one cast per turn, and the plain one after.
// `group`: only that group's camps.
bool reset_and_attack_enemy(const World& world, bool stunning_only = false);
bool reset_and_attack_camp(const World& world, int group);
// A camp tile lies within `range` of p.
bool camp_in_reach(const World& world, vec2 p, int range);

// Travel: dash to the landing nearest the goals if it gains at least 2 steps and no enemy is near
// enough to want the dash for a fight or an escape. Goals more than `max_steps` away are not searched
// for, and a search that finds no gain pauses this overload for a few rounds, whatever the goals.
// On success, follow receives the search field, valid until the next call to this overload.
bool dash_towards(const World& world, Pathing& pathing, const bitboard& goals, int max_steps = unreachable, const Field** follow = nullptr);
bool dash_towards(const World& world, Pathing& pathing, const Field& field);
// Over a hole or altar line beside us (StaticMap::crossable) where `field` gains: unlike a travel
// dash, with enemies near, as long as the landing is no deeper in their reach.
bool dash_across(const World& world, Pathing& pathing, const Field& field);
// Into attack range of `target`, else of a visible enemy we can finish or are beating; attack after it.
bool dash_to_attack(const World& world, Pathing& pathing, const ChampionBelief* target = nullptr);
// Out of the reach of visible enemies and awake camps, tie-broken towards `home`. `dead`: the
// tile of an enemy we killed this turn, which the beliefs still hold alive.
bool dash_away(const World& world, Pathing& pathing, const Field& home, vec2 dead = {-1, -1});
// dash_away's choice, quoted without casting: its first landings, best first, from `from`.
// `clears`: the first lands out of every threat's reach.
struct EscapeDashQuote {
    int slot = -1, count = 0;
    vec2 from{-1, -1};
    std::array<vec2, 3> tiles{};
    bool clears = false;
};
EscapeDashQuote quote_escape_dash(const World& world, Pathing& pathing, const Field& home, vec2 dead);
// The quote's first landing only, if we are still where it was made and its slot is ready.
bool cast_escape_dash(const World& world, Pathing& pathing, const EscapeDashQuote& quote);
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
// Varg or Heart of Ruin: before damage from an awake camp, a camp we are hitting or an enemy in
// reach. `farmed`: the group farm chose, which we hit from attack range; another group's camp in
// attack range is hit only if our attack is spent.
bool shield_if_needed(const World& world, Safety& safety, int farmed);

} // namespace aph
