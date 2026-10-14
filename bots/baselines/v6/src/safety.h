// Danger before our next turn: what each enemy (seen, or unseen through `possible`) and each
// awake camp could do to a tile, and whether a local fight is won. Built on first query each
// turn from host bitboard and field calls.
//
// Unseen enemies are weighted by the uniform chance that they stand within reach of a tile:
// |square(tile, reach) & possible| / |possible|. Over 1200 ladder games (per-champion vision,
// rounds since the attacker was last seen): visible enemies dealt 92% of champion hits; within
// reach of the uniformly weighted possible set, being in reach ran at 0.6-0.9x that chance and
// a hit at 0.15-0.25x; the hit rate inside the dilated set fell from 5% a round one round after
// losing sight to 1% after four and 0.3% after eight, as the set grows. So the weight shrinks
// with staleness by itself, and an enemy whose best weight is below `credible_weight` is left
// out. Typical cost: 1-5k fuel a turn, ~1.5-3k more per unseen credible enemy.
#pragma once
#include <cambc.h>
#include <array>
#include <optional>
#include <vector>
#include "util.h"

namespace aph {

class World;
struct ChampionBelief;

namespace safety_params {
// Ladder: a visible enemy within reach hit that champion in 23-27% of rounds.
inline constexpr float hit_given_reach = 0.25f;
// A recall is kept while the chance of damage before our next turn is below this: a visible
// enemy in reach is enough on its own; an unseen one needs a weight near 1.
inline constexpr float recall_risk = 0.2f;
// Unseen enemies with a lower best weight are left out entirely. From 0.5 being in reach ran at
// 33% or more and a hit at 4.6% a round, six times the rate outside the dilated set.
inline constexpr float credible_weight = 0.5f;
// An awake camp we have not watched for 2 rounds may have fallen asleep.
inline constexpr float unknown_camp_weight = 0.5f;
inline constexpr int camp_attack_range = 3;
inline constexpr int fight_ally_radius = 4;
// Routing around danger farther than this is left to later turns: routes are replanned each turn.
inline constexpr int avoid_radius = 8;
} // namespace safety_params

// The most an enemy can do on its next turn to a tile at each Chebyshev distance from where it
// stands: walk, dash, attack, reset and damage spells, by the rules' action allowances. Walls,
// line of sight and items (Durability, shields) are ignored, so this is an upper bound.
struct Strike {
    static constexpr int max_reach = 5;
    std::array<float, max_reach + 1> damage{};
    std::array<bool, max_reach + 1> stuns{};
    int reach = -1; // farthest distance it can damage or stun; -1: nothing

    float at(int d) const { return d >= 0 && d <= reach ? damage[d] : 0.0f; }
    bool hits(int d) const { return d >= 0 && d <= reach; }
};

// From its facts, last-read Strength and Focus and the cooldowns projected to `turn_round`.
Strike strike(const ChampionBelief& c, int turn_round);
// The round of the enemy's next turn: later this round if it acts after us, else next round.
int next_turn_round(const World& world, const ChampionBelief& c);

struct Threat {
    int enemy = -1; // index into World::enemies
    bool visible = false;
    vec2 pos{-1, -1}; // visible only
    int tiles = 1;    // possible tiles
    // Best chance over tiles that it can reach one: 1 if visible, else min(1, reach area / tiles).
    float weight = 1;
    Strike strike;
    // Tiles it can damage or stun; unseen, only those near or above `credible_weight`.
    bitboard area;
    std::optional<cambc::distance_field> steps; // unseen: distance from `possible`, capped at the reach

    int distance(vec2 p) const;
    bool credible() const { return visible || weight >= safety_params::credible_weight; }
};

// A pooled fight: each side's health summed, damage focused, sides alternating turns. Stuns
// skip the strongest opponent's turn; heals and shields add to the pool once when ready.
// Ignores items, positioning, overkill and the order within a side.
struct Trade {
    bool lost = false;          // they win when they strike first
    bool lost_anyway = false;   // they win even when we strike first
    int turns_to_kill_us = 0;   // their turns, when they strike first; 0: not within the horizon
    int turns_to_kill_them = 0; // ours
    float our_health = 0, their_health = 0;
    int allies = 0, enemies = 0;
};

class Safety {
public:
    explicit Safety(const World& world);

    const std::vector<Threat>& threats();
    const Threat* threat(int enemy);

    // Chance the threat could be within reach of p; uniform over its possible tiles.
    float chance_in_reach(const Threat& t, vec2 p);
    float camp_damage(vec2 p, bool worst = true);
    // Every credible threat at full damage, plus camps.
    float worst_damage(vec2 p);
    // Each threat by chance in reach times `hit_given_reach`, plus camps.
    float expected_damage(vec2 p);
    // Chance of taking any damage or a stun at p before our next turn (cancelling a recall).
    float hit_chance(vec2 p);
    bool threatened(vec2 p) { return hit_chance(p) >= safety_params::recall_risk; }

    const bitboard& camp_area();      // within 3 of a live member of an awake (or maybe awake) group
    const bitboard& enemy_area();     // within a credible threat's reach
    const bitboard& contested_area(); // within reach of two or more credible threats
    // Tiles to keep off while routing: camps and credible enemies, never our own tile.
    bitboard avoid();

    // Us and the allies we see within `fight_ally_radius`, against every credible threat that
    // could hit p.
    Trade fight(vec2 p);
    // Us alone against one enemy.
    Trade duel(int enemy);
    // Their turns for the visible enemies to kill us at p if we never act (channelling), each
    // walking a step a turn until in reach; 0 if not within `horizon` turns.
    int turns_to_kill_idle(vec2 p, int horizon);
    // Could the credible threats and camps kill us at p before our next turn?
    bool lethal(vec2 p);
    // Off spawn, and below the recall line, or somewhere lethal in a fight we lose. Retreating
    // from every lost fight cost tempo in testing (6-7 of 18 against v0) for few deaths saved.
    bool should_retreat();

private:
    struct CampHit {
        vec2 pos;
        float strength;
        float weight;
    };
    const std::vector<CampHit>& awake_members();
    void build();

    const World& world_;
    bool built_ = false;
    std::vector<Threat> threats_;
    std::optional<std::vector<CampHit>> members_;
    std::optional<bitboard> camp_area_, enemy_area_, contested_area_;
};

} // namespace aph
