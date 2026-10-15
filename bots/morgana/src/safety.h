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
#include <cstdint>
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
    // Unseen: distance from `possible`, capped at the reach; reused by the next build.
    const cambc::distance_field* steps = nullptr;

    int distance(vec2 p) const;
    bool credible() const { return visible || weight >= safety_params::credible_weight; }
};

// A fight with sides alternating turns, each side's damage focused on the other's weakest member
// and spilling over, so the fallen stop dealing damage (Cassi and Issac fall together). Pooled
// health hid this: we died in 17% of won fights where we were the weakest, 4-7% otherwise.
// Stuns skip the strongest opponent's turn; a heal goes to the weakest hurt ally other than the
// caster, a shield to its caster until it expires; Ren hits back while she is the one hit.
// An ally joins once it could walk into reach of the nearest enemy, and is out of their reach
// until then. Ignores items, other positioning and the order within a side.
struct Trade {
    bool lost = false;          // they win when they strike first
    int turns_to_kill_us = 0;   // their turns, when they strike first; 0: not within the horizon
    int turns_to_kill_them = 0; // ours
    bool self_falls = false;    // we die before their side does, when they strike first
    float our_health = 0, their_health = 0;
    int allies = 0, enemies = 0;
    std::array<float, 4> dealt{}; // debug_fights only: see simulate()
};

class Safety {
public:
    explicit Safety(const World& world);

    const std::vector<Threat>& threats();
    const Threat* threat(int enemy);
    bool built() const { return built_; }
    bool any_threat(); // threats() is not empty, without building it
    // Without building the threats: at least worst_damage(p), and at least their sum with each
    // visible enemy yet to act counted twice when `double_unacted`.
    float damage_bound(vec2 p, bool double_unacted = false);
    bool may_be_hit(vec2 p); // false only if no threat hits p

    // Chance the threat could be within reach of p; uniform over its possible tiles.
    float chance_in_reach(const Threat& t, vec2 p);
    float camp_damage(vec2 p, bool worst = true);
    // Every credible threat at full damage, plus camps.
    float worst_damage(vec2 p);
    // Each threat by chance in reach times `hit_given_reach`, plus camps.
    float expected_damage(vec2 p);
    // Chance of taking any damage or a stun at p before our next turn (cancelling a recall).
    bool threatened(vec2 p);

    // Where a live member of an awake (or maybe awake) group would attack us: within 3, and no
    // visible champion nearer it (or as near with a lower id).
    const bitboard& camp_area();
    const bitboard& enemy_area(); // within a credible threat's reach
    // Tiles to keep off while routing: camps and credible enemies. Our own tile is included when
    // in danger, so routing can free the region we stand in.
    bitboard avoid();

    // Us and the allies we see within `fight_ally_radius`, against every credible threat that
    // could hit p.
    Trade fight(vec2 p);
    // Generous for one fight(): a simulation grows with the fighters (1v1 ~6k, 4v4 ~17k, up to
    // 26k) and this turn's costliest one; building the threats 2-16k.
    std::uint64_t fight_cost_estimate() const;
    // Us alone against one enemy.
    Trade duel(int enemy);
    // Their turns for the visible enemies and camps to kill us at p if we never act (channelling),
    // each enemy walking a step a turn until in reach; 0 if not within `horizon` turns.
    int turns_to_kill_idle(vec2 p, int horizon);
    // Could the credible threats and camps kill us at p before our next turn?
    bool lethal(vec2 p);
    // Off spawn, and below the recall line, or somewhere lethal in a fight we lose. Retreating
    // from every lost fight cost tempo in testing (6-7 of 18 against an early baseline) for few deaths saved.
    bool should_retreat();

    // Drop everything cached, after something this turn changed the fight: a kill, a stun or a
    // camp kill. Later queries recheck the engine for champions and monsters that died.
    void invalidate();
    // After our attacks and casts: invalidate() only if a visible enemy or camp member died.
    void refresh();

private:
    struct CampHit {
        vec2 pos;
        float strength;
        float weight;
        int reach; // farthest distance at which it would pick us
    };
    const std::vector<CampHit>& awake_members();
    void build();
    template <class F> void each_threat(vec2 p, F&& f);
    // Seen alive at turn start but dead now, once refreshed.
    bool gone(const ChampionBelief& c);

    const World& world_;
    bool built_ = false;
    bool refresh_ = false;
    std::array<std::int8_t, 16> gone_{}; // by enemy index: 0 unknown, 1 alive, 2 dead
    std::vector<Threat> threats_;
    std::optional<std::vector<CampHit>> members_;
    std::optional<bitboard> camp_area_, enemy_area_;
    // By who fights: bit i of the low half for allies[i], of the high half for enemies[i].
    std::vector<std::pair<std::uint32_t, Trade>> fights_;
    std::uint64_t costliest_fight_ = 0;
};

} // namespace aph
