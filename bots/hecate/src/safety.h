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

// What an enemy could do to one tile before our next turn.
struct Blow {
    float damage = 0;
    bool hits = false; // damage or a stun
    bool stuns = false;
};

// The most an enemy can do on its next turn to a tile at each Chebyshev distance from where it
// stands: walk, dash, attack, reset and damage spells, by the rules' action allowances. Walls,
// line of sight and items (Durability, shields) are ignored, so this is an upper bound; Reach
// places the same actions on the map.
struct Strike {
    static constexpr int max_reach = 6; // a dash, or a walk on the first of two turns
    std::array<float, max_reach + 1> damage{};
    std::array<bool, max_reach + 1> stuns{};
    int reach = -1; // farthest distance it can damage or stun; -1: nothing

    float at(int d) const { return d >= 0 && d <= reach ? damage[d] : 0.0f; }
    bool hits(int d) const { return d >= 0 && d <= reach; }
    Blow blow(int d) const { return hits(d) ? Blow{damage[d], true, stuns[d]} : Blow{}; }
};

// A visible enemy's actions before our next turn on the map: the tiles it can walk to (over tiles
// open to it, past visible allies of ours) or dash to (2 king steps over anything but walls and
// live camps, onto a free tile), and from there a basic attack or unit spell at a target in its
// sight (walls and bushes block it; a bush tile is seen only from its own cluster, or by a visible
// enemy ward), or a ground spell at any tile within 5. Damage as Strike's.
class Reach {
public:
    // Its next turn, or with `twice` its next two: a walk first, or a second basic attack.
    void build(const World& world, const ChampionBelief& e, int turn_round, bool twice);
    Blow at(vec2 p) const;
    int reach() const { return reach_; } // Chebyshev bound on the tiles it can affect

    // Bit 9 * (y + 4) + x + 4: the 9x9 tiles around the enemy, in two words (128-bit shifts are
    // library calls in WASM).
    struct Window {
        static constexpr std::uint64_t hi_mask = (std::uint64_t{1} << 17) - 1;
        std::uint64_t lo = 0, hi = 0;
        static constexpr Window bit(int i) { return i < 64 ? Window{std::uint64_t{1} << i, 0} : Window{0, std::uint64_t{1} << (i - 64)}; }
        friend constexpr Window operator&(Window a, Window b) { return {a.lo & b.lo, a.hi & b.hi}; }
        friend constexpr Window operator|(Window a, Window b) { return {a.lo | b.lo, a.hi | b.hi}; }
        constexpr Window operator~() const { return {~lo, ~hi & hi_mask}; }
        constexpr Window& operator&=(Window b) { return *this = *this & b; }
        constexpr Window& operator|=(Window b) { return *this = *this | b; }
        constexpr explicit operator bool() const { return (lo | hi) != 0; }
        // 0 <= k < 81
        constexpr Window shl(int k) const {
            if (k == 0) return *this;
            if (k < 64) return {lo << k, ((hi << k) | (lo >> (64 - k))) & hi_mask};
            return {0, (lo << (k - 64)) & hi_mask};
        }
        constexpr Window shr(int k) const {
            if (k == 0) return *this;
            if (k < 64) return {(lo >> k) | (hi << (64 - k)), hi >> k};
            return {hi >> (k - 64), 0};
        }
    };
private:
    struct Way {
        Window from; // where it acts from
        float damage;
        std::int8_t range, far; // far: its farthest tile's distance from the enemy
        bool sight, stuns, walked;
    };
    // Returns the way's index: one already there with the same tiles, range and sight takes the
    // larger damage.
    int add(Window from, int range, bool sight, float damage, bool stuns, bool walked);
    const World* world_ = nullptr;
    const bitboard* wards_ = nullptr; // what visible enemy wards see this round, if any
    vec2 origin_{-1, -1};
    std::array<Way, 14> ways_;
    int count_ = 0;
    int basic_ = -1; // the plain basic attack's way
    float strength_ = 0;
    bool twice_ = false;
    int reach_ = -1;
    // By the low 3 bits of x and y, so the tiles of any 8x8 square never collide; valid when its
    // stamp is this build's.
    struct Memo {
        vec2 p;
        Blow blow;
        std::uint32_t stamp = 0;
    };
    mutable std::array<Memo, 64> memo_;
    std::uint32_t stamp_ = 0;
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
    // Tiles it can damage or stun (visible: a superset); unseen, only those near or above
    // `credible_weight`.
    bitboard area;
    // Unseen: distance from `possible` around walls, capped at the reach; reused by the next build.
    const cambc::distance_field* steps = nullptr;
    const Reach* reach = nullptr; // visible

    Blow at(vec2 p) const;
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
    // Each threat as threats() would list it, with its blow at p, without building them: an
    // unseen threat's distance is searched out to its radius only. Returns the count.
    struct ThreatAt {
        int enemy;
        Blow blow;
    };
    int threats_at(vec2 p, std::array<ThreatAt, 16>& out);

    // Us and the allies we see within `fight_ally_radius`, against every credible threat that
    // could hit p. Cut short (Trade::cut) rather than spend the turn's last `end_reserve`.
    // `exclude`: an enemy (by index) left out, as when our hit kills it first.
    Trade fight(vec2 p, int exclude = -1);
    // Who would fight at p: bit i of the low half for allies[i], of the high half for enemies[i];
    // no_fight if no threat hits p.
    static constexpr std::uint32_t no_fight = ~0u;
    std::uint32_t fight_key(vec2 p, int exclude = -1);
    // The fight of a key, memoised.
    Trade fight_of(std::uint32_t key);
    bool known_fight_of(std::uint32_t key) const { return memo(key) != nullptr; }
    // fight(p) if it needs no simulation, else null.
    const Trade* known_fight(vec2 p);
    // threat_strike(), kept for the turn.
    const Strike& strike_of(const ChampionBelief& e) { return foe(e).strike; }
    // What a visible enemy could do to p before our next turn (threat_strike placed on the map).
    Blow blow(const ChampionBelief& e, vec2 p);
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
    // Its turns of walking before it can strike p: 0 if it can now, else at least 1 and at least
    // its Chebyshev distance past its reach.
    int approach(const ChampionBelief& e, vec2 p);
    const Reach& reach_of(const ChampionBelief& e);
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
    std::uint16_t reached_ = 0; // bit i: reach_pool()[i] is built for enemies[i] this turn
    bool built_ = false;
    bool refresh_ = false;
    std::array<std::int8_t, 16> gone_{}; // by enemy index: 0 unknown, 1 alive, 2 dead
    // Left uninitialised: the engine charges for every byte written. Bit i: foes_[i] is set.
    std::uint16_t known_ = 0;
    std::uint32_t made_ = 0; // fighters made for the fights this turn: bit i for allies[i], 16 + i for enemies[i]
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
    // By fight_key(). A memo: past `max_fights` the oldest is replaced.
    struct FightMemo {
        std::uint32_t key;
        Trade trade;
    };
    static constexpr int max_fights = 32;
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
