// Danger before our next turn: what each enemy (seen, or unseen through `possible`) and each
// awake camp could do to a tile, and whether a local fight is won. Built on first query each
// turn from host bitboard and field calls.
//
// Unseen enemies are weighted by the uniform chance that they stand within reach of a tile:
// |square(tile, reach) & possible| / |possible|. The weight shrinks with staleness as the set
// grows, and an enemy whose best weight is below `credible_weight` is left out.
#pragma once
#include <cambc.h>
#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <vector>
#include "util.h"

namespace aph {

class World;
struct ChampionBelief;

namespace safety_params {
// Chance a round that an enemy within reach hits us.
inline constexpr float hit_given_reach = 0.25f;
// A recall is kept while the chance of damage before our next turn is below this: a visible
// enemy in reach is enough on its own; an unseen one needs a weight near 1.
inline constexpr float recall_risk = 0.2f;
// Unseen enemies with a lower best weight are left out entirely.
inline constexpr float credible_weight = 0.5f;
// An awake camp we have not watched for 2 rounds may have fallen asleep.
inline constexpr float unknown_camp_weight = 0.5f;
inline constexpr int fight_ally_radius = 4;
} // namespace safety_params

// The most an enemy can do on its next turn to a tile at each Chebyshev distance from where it
// stands: walk, dash, attack, reset and damage spells, by the rules' action allowances. Walls,
// line of sight and items (Durability, shields) are ignored, so this is an upper bound.
struct Strike {
    static constexpr int max_reach = 6; // a dash, or a walk on the first of two turns
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
// Its turns before our next one: later this round, and next round before us.
int turns_before_ours(const World& world, const ChampionBelief& c);
// strike(), widened when it has two turns before our next: a walk then the strike, or the strike
// and a second basic attack.
Strike threat_strike(const World& world, const ChampionBelief& c);

struct Threat {
    int enemy = -1; // index into World::enemies
    bool visible = false;
    vec2 pos{-1, -1}; // visible only
    int tiles = 1;    // possible tiles
    Strike strike;
    // Tiles it can damage or stun; unseen, only those near or above `credible_weight`.
    bitboard area;
    // Unseen: distance from `possible`, capped at the reach; reused by the next build.
    const cambc::distance_field* steps = nullptr;

    int distance(vec2 p) const;
};

// A fight with sides alternating turns, each side's damage focused on the other's weakest member
// and spilling over, so the fallen stop dealing damage (Cassi and Issac fall together).
// Stuns skip the strongest opponent's turn; a heal goes to the weakest hurt ally other than the
// caster, a shield to its caster until it expires; Ren hits back while Ren is the one hit.
// Ignores items, positioning and the order within a side.
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

    std::span<const Threat> threats();
    bool built() const { return built_; }
    bool any_threat(); // threats() is not empty, without building it
    // Without building the threats: at least worst_damage(p), and at least their sum with each
    // visible enemy yet to act counted twice when `double_unacted`.
    float damage_bound(vec2 p, bool double_unacted = false);
    float camp_damage(vec2 p, bool worst = true);
    // Each threat by chance in reach times `hit_given_reach`, plus camps.
    float expected_damage(vec2 p);
    // Chance of taking any damage or a stun at p before our next turn (cancelling a recall).
    bool threatened(vec2 p);

    const bitboard& enemy_area(); // within a credible threat's reach
    // Tiles to keep off while routing: camps and credible enemies. Our own tile is included when
    // in danger, so routing can free the region we stand in.
    bitboard avoid();
    // any_within(avoid(), p, r), without building the threats.
    bool avoid_within(vec2 p, int r);
    // Each threat as threats() would list it, with its distance(p), without building them: an
    // unseen threat's distance is searched out to its radius only. Returns the count.
    struct ThreatAt {
        int enemy;
        const Strike* strike;
        int distance;
    };
    int threats_at(vec2 p, std::array<ThreatAt, 16>& out);

    // Us and the allies we see within `fight_ally_radius`, against every credible threat that
    // could hit p. Cut short (Trade::cut) rather than spend the turn's last `end_reserve`.
    // `exclude`: an enemy (by index) left out, as when our hit kills it first.
    Trade fight(vec2 p, int exclude = -1);
    // fight(p) if it needs no simulation, else null.
    const Trade* known_fight(vec2 p);
    // threat_strike(), kept for the turn.
    const Strike& strike_of(const ChampionBelief& e) { return foe(e).strike; }
    // Enough for most fights, by the champions in sight and this turn's costliest simulation;
    // plus build_cost_estimate().
    std::uint64_t fight_cost_estimate();
    // At most what building the threats costs, 0 once built.
    std::uint64_t build_cost_estimate();
    // Us and the allies we see near p, striking first, against every visible enemy within
    // `approach` steps of its reach, each joining once it has walked into reach, while the camps
    // in reach of p keep hitting us: lost means they win even if we stand and fight.
    Trade pursuit(vec2 p, int approach);
    // Their turns for the visible enemies and camps to kill us at p if we never act (channelling),
    // each enemy walking a step a turn until in reach; 0 if not within `horizon` turns.
    int turns_to_kill_idle(vec2 p, int horizon);
    // Could the credible threats and camps kill us at p before our next turn?
    bool lethal(vec2 p);

    // Live members of awake (or maybe awake) groups, with where they would attack us from.
    struct CampHit {
        vec2 pos;
        float strength;
        float weight;
        int reach; // farthest distance at which it would pick us
    };
    const std::vector<CampHit>& awake_members();

    // After our attacks and casts: invalidate() only if a visible enemy or camp member died.
    void refresh();

private:
    bool may_be_hit(vec2 p); // false only if no threat hits p
    // Chance the threat could be within reach of p; uniform over its possible tiles.
    float chance_in_reach(const Threat& t, vec2 p);
    // Every credible threat at full damage, plus camps.
    float worst_damage(vec2 p);
    // Where a live member of an awake (or maybe awake) group would attack us: within 3, and no
    // visible champion nearer it (or as near with a lower id).
    const bitboard& camp_area();
    // Drop everything cached, after something this turn changed the fight: a kill, a stun or a
    // camp kill. Later queries recheck the engine for champions and monsters that died.
    void invalidate();

    static std::vector<CampHit>& member_pool();
    // An enemy's strike for its next turn and, unseen, its possible tiles and weight (0: not
    // credible), worked out on first use: beliefs are fixed for the turn.
    struct Foe {
        Strike strike;
        int tiles;
        float weight;
        vec2 asked; // unseen: the last tile asked about, and whether `possible` is within reach of it
        bool near;
    };
    Foe& foe(const ChampionBelief& e);
    void build();
    template <class F> void each_threat(vec2 p, F&& f);
    // Seen alive at turn start but dead now, once refreshed.
    bool gone(const ChampionBelief& c);

    const World& world_;
    bool built_ = false;
    bool refresh_ = false;
    std::array<std::int8_t, 16> gone_{}; // by enemy index: 0 unknown, 1 alive, 2 dead
    // Left uninitialised: the engine charges for every byte written. Bit i: foes_[i] is set.
    std::uint16_t known_ = 0;
    union {
        std::array<Foe, 16> foes_;
    };
    // The first `threat_count_` of a pool kept across turns (one Safety lives at a time): growing a
    // vector reallocates at ~300 fuel a time, and each Threat allocates a bitboard.
    std::vector<Threat>& threats_;
    int threat_count_ = 0;
    std::vector<CampHit>& members_; // likewise; valid once `members_known_`
    bool members_known_ = false;
    std::optional<bitboard> camp_area_, enemy_area_;
    // By who fights: bit i of the low half for allies[i], of the high half for enemies[i]. A memo:
    // past `max_fights` the oldest is replaced.
    struct FightMemo {
        std::uint32_t key;
        Trade trade;
    };
    static constexpr int max_fights = 32;
    static constexpr std::uint32_t no_fight = ~0u; // no threat hits the tile
    std::uint32_t fight_key(vec2 p, int exclude);
    const Trade* memo(std::uint32_t key) const;
    int fight_count_ = 0;
    union {
        std::array<FightMemo, max_fights> fights_;
    };
    std::uint64_t costliest_fight_ = 0;
    int champions_ = -1;            // in sight, for fight_cost_estimate(); beliefs are fixed for the turn
    std::uint64_t build_cost_ = 0;  // build_cost_estimate() until built, refreshed or invalidated; 0: unknown
};

} // namespace aph
