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
class Safety;
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
// sight (walls and bushes block it; a bush tile is seen only from its own cluster) or its own
// ward's, when we see that ward, or a ground spell at any tile within 5; Varg's basic attacks also
// at a unit beside the tile. Damage as Strike's.
class Reach {
public:
    // Its next turn, or with `twice` its next two: a walk first, or a second basic attack. The second
    // turn falls in turn_round + 1, so a slot coming ready then counts for it.
    void build(const World& world, const ChampionBelief& e, int turn_round, bool twice);
    Blow at(vec2 p) const;
    int reach() const { return reach_; } // Chebyshev bound on the tiles it can affect

    // The tiles within `radius` around the enemy, bit at(x, y) for the offset (x, y), in two words
    // (128-bit shifts are library calls in WASM).
    struct Window {
        static constexpr int radius = 4, width = 2 * radius + 1, cells = width * width;
        static_assert(cells > 64 && cells <= 128);
        static constexpr std::uint64_t hi_mask = (std::uint64_t{1} << (cells - 64)) - 1;
        static constexpr int at(int x, int y) { return width * (y + radius) + x + radius; }
        std::uint64_t lo = 0, hi = 0;
        static constexpr Window bit(int i) { return i < 64 ? Window{std::uint64_t{1} << i, 0} : Window{0, std::uint64_t{1} << (i - 64)}; }
        friend constexpr Window operator&(Window a, Window b) { return {a.lo & b.lo, a.hi & b.hi}; }
        friend constexpr Window operator|(Window a, Window b) { return {a.lo | b.lo, a.hi | b.hi}; }
        constexpr Window operator~() const { return {~lo, ~hi & hi_mask}; }
        constexpr Window& operator&=(Window b) { return *this = *this & b; }
        constexpr Window& operator|=(Window b) { return *this = *this | b; }
        constexpr explicit operator bool() const { return (lo | hi) != 0; }
        // 0 <= k < cells
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
    // Tiles it can act from: here, after a walk, after a dash; and each after a further walk.
    enum Tiles : std::uint8_t { here, walked1, dashed, walked2, dashed_walked, tile_sets };
    struct Way {
        float damage;
        Tiles from;
        std::int8_t range;
        std::uint8_t key; // its tiles, range, sight and turn: ways with equal keys merge
        bool sight, stuns, walked;
        std::int8_t bound; // extent_[from] + range: the farthest tile it reaches
    };
    // Returns the way's index: one already there with the same key takes the larger damage.
    int add(Tiles from, int range, bool sight, float damage, bool stuns, bool walked);
    void set_reach();
    // The ways from the tile sets, unless the recipe is unchanged.
    // ready2: the slots ready on its second turn (ready's, unless twice).
    void build_ways(const ChampionBelief& e, std::array<bool, 2> ready, std::array<bool, 2> ready2, bool twice);
    std::array<Window, tile_sets> tiles_;
    std::array<std::int8_t, tile_sets> extent_; // farthest tile of each from the enemy
    const World* world_ = nullptr;
    vec2 origin_{-1, -1};
    int owner_ = -1; // its index among the enemies
    // Its own ward, the only one that lends it sight, when we see it; else -1. Looked up on first need.
    static constexpr int unknown_ward = -2;
    mutable int ward_ = unknown_ward;
    // What tiles_ were worked out for: kept while it stays put, our champions around it stay put
    // and no camp lies in its window.
    vec2 sets_origin_{-1, -1};
    Window sets_occupied_;
    std::uint8_t sets_kind_ = 0;
    bool sets_reusable_ = false;
    // The ways depend only on what the recipe holds: kept between builds while it is unchanged,
    // one set for each ready slots and number of turns, as cooldowns run out and come back.
    struct Recipe {
        cambc::champion_type type{};
        std::uint32_t strength = 0, focus = 0;
        std::uint8_t slots = 0; // bits 0-1 ready, 2-3 ready on the second turn
        bool twice = false, valid = false;
        bool operator==(const Recipe&) const = default;
    };
    struct Ways {
        Recipe recipe;
        std::array<Way, 14> way;
        int count = 0;
        int basic = -1; // the plain basic attack's way
    };
    // By each slot's turns ready (0-2) and twice.
    std::array<Ways, 18> ways_by_;
    Ways* ways_ = &ways_by_[0];
    float strength_ = 0;
    bool twice_ = false;
    // Varg: its basic attacks also hit within 1 of the target, so they reach a tile through the
    // units beside it (`units_`: our visible champions but us, and live camp members).
    bool splash_ = false;
    Window units_;
    // The units its basic attack at `range` can hit from tiles_[from]; all its basic attacks share
    // the range. Worked out on first need each build.
    const Window& splash_targets(Tiles from, int range) const;
    mutable std::array<Window, tile_sets> splash_units_;
    mutable std::uint8_t splash_known_ = 0;
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

// Tiles within `range` (at most 4) of `target` from which our basic attack or unit cast sees it, as
// a Reach::Window around it: exact, but for viewers in bushes beyond a step, who are left out.
// `store`: keep the terrain's sight mask for the game (debug checks pass false).
Reach::Window attack_viewers(const World& world, vec2 target, int range, bool store = true);

// With fuel above `fuel_floor` at the turn's end: Reach's static terrain around the tiles visible
// enemies may step to, so fights find it ready. Sight masks are not warmed: in bench games only 1
// in 20 of those warmed was ever read.
void warm_reach(const World& world, std::uint64_t fuel_floor);
// The static window and far sight mask at p (not a wall), as a miss would fill them.
void warm_reach_tile(const World& world, vec2 p);

// From its facts, last-read Strength and Focus and the cooldowns projected to `turn_round`.
const Strike& strike(const ChampionBelief& c, int turn_round);
// An enemy in sight loses its next turn to a stun (rules: abilities.stun).
bool turn_lost(const ChampionBelief& c);
// The round of the enemy's next turn: later this round if it acts after us, else next round; one
// later if a stun takes it.
int next_turn_round(const World& world, const ChampionBelief& c);
// Its turns before our next one: later this round, and next round before us, less one a stun takes.
int turns_before_ours(const World& world, const ChampionBelief& c);
// strike(), widened when it has two turns before our next: a walk then the strike, or the strike
// and a second basic attack.
const Strike& threat_strike(const World& world, const ChampionBelief& c);
// A visible enemy within `margin` of our `reach` from p, or of its own strike before our next turn:
// a fight may open there that wants what we would spend now.
bool engagement_near(const World& world, vec2 p, int reach, int margin = 1);

// dist(p, c) <= r for r >= 0, without the distance.
[[gnu::always_inline]] inline bool in_square(vec2 p, vec2 c, int r) {
    const auto side = 2 * static_cast<unsigned>(r);
    return (static_cast<unsigned>(p.x - c.x + r) <= side) & (static_cast<unsigned>(p.y - c.y + r) <= side);
}

struct Threat {
    int enemy = -1; // index into World::enemies
    bool visible = false;
    vec2 pos{-1, -1}; // visible only
    int tiles = 1;    // possible tiles
    Strike strike;
    // Unseen: tiles it can damage or stun, only those near or above `credible_weight`. Visible
    // threats' are drawn by enemy_area().
    bitboard area;
    // Unseen: Chebyshev distance from `possible`, as Strike's, capped at unseen_radius(); reused
    // by the next build.
    const cambc::distance_field* steps = nullptr;
    // Visible: whose blow() places it on the map, its Reach built on first need.
    Safety* owner = nullptr;
    const ChampionBelief* belief = nullptr;

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
    bool falls_known = true;    // self_falls is: a fight asked without it can end once it cannot be lost
    float our_health = 0, their_health = 0; // debug_fights only
    int allies = 0, enemies = 0;
    std::array<float, 4> dealt{}; // debug_fights only: see simulate()
};

class Safety {
public:
    explicit Safety(const World& world);

    std::span<const Threat> threats();
    // Bit i: enemies[i] is alive and visible (seen) or alive, unseen and tracked (unseen).
    // Beliefs are fixed for the turn, so these are listed once.
    std::uint32_t seen_enemies() {
        if (!listed_) list_enemies();
        return seen_;
    }
    std::uint32_t live_enemies() {
        if (!listed_) list_enemies();
        return seen_ | unseen_;
    }
    void list_enemies();
    bool any_threat(); // threats() is not empty, without building it
    // Without building the threats: at least worst_damage(p), and at least their sum with each
    // visible enemy yet to act counted twice when `double_unacted`.
    float damage_bound(vec2 p, bool double_unacted = false);
    // At least damage_bound(p), counting every unseen threat at its most: no host queries or
    // strikes for them.
    float damage_ceiling(vec2 p, bool double_unacted = false);
    // damage_bound(p) without and with `double_unacted`, whether a blow reaches p or stuns, and
    // threat: threatened(p)'s chance from enemies alone, without building the threats, in one pass.
    struct Bound {
        float damage = 0, doubled = 0;
        bool hits = false, stuns = false, threat = false;
    };
    Bound bound(vec2 p);
    // `next`: in the next camp phase only, which a stunned member skips (rules: abilities.stun);
    // else in each camp phase while we stay.
    float camp_damage(vec2 p, bool worst = true, bool next = false);
    // Where a live member of an awake (or maybe awake) group would attack us: within its range, and
    // no visible champion nearer it (or as near and acting first).
    const bitboard& camp_area();
    // Chance of taking any damage or a stun at p before our next turn (cancelling a recall).
    bool threatened(vec2 p);

    const bitboard& enemy_area(); // within a credible threat's reach
    // Tiles to keep off while routing: camps and credible enemies. Our own tile is included when
    // in danger, so routing can free the region we stand in. A scratch board, valid until the next call.
    const bitboard& avoid();
    // any_within(avoid(), p, r), without building the threats.
    bool avoid_within(vec2 p, int r);
    // Each threat as threats() would list it, with its blow at p, without building them: an
    // unseen threat's distance is searched out to its radius only. Returns the count.
    struct ThreatAt {
        int enemy;
        Blow blow;
    };
    int threats_at(vec2 p, std::array<ThreatAt, 16>& out);
    // Whether a threat threats_at() lists may hit within `radius` of p: false spares its searches
    // for every tile that close.
    bool credible_enemy_may_hit_within(vec2 p, int radius);

    // Us and the allies we see within `fight_ally_radius`, against every credible threat that
    // could hit p. Cut short (Trade::cut) rather than spend the turn's last `end_reserve`.
    // Without `falls` the fight may end once it cannot be lost, leaving self_falls unknown.
    Trade fight(vec2 p, bool falls = true);
    // Optional chase only: the same roster, with unavailable first activations delayed on copies.
    // `late` as late() gives: enemies who walk into the fight.
    Trade chase_trade(std::uint32_t key, std::uint32_t delayed, const std::array<int, 2>& self_cooldowns, bool can_cast, bool falls = true,
                      std::uint32_t late = 0);
    // Who would fight at p: bit i of the low half for allies[i], of the high half for enemies[i];
    // no_fight if no threat hits p.
    static constexpr std::uint32_t no_fight = ~0u;
    std::uint32_t fight_key(vec2 p);
    // fight_key(p) given `visible`: the bits of every visible threat that hits p, at least one.
    std::uint32_t fight_key_with(vec2 p, std::uint32_t visible);
    // The fight of a key, joined by the `late` enemies, memoised.
    Trade fight_of(std::uint32_t key, bool falls = true, std::uint32_t late = 0);
    // fight_of(key, late) if memoised, else null.
    const Trade* known_fight_of(std::uint32_t key, std::uint32_t late = 0) const { return memo(key, late, true); }
    // fight_of(key, late) when known_fight_of(key, late) is null.
    Trade new_fight(std::uint32_t key, bool falls = true, std::uint32_t late = 0);
    // The visible enemies outside `key` who walk into reach of p within pursuit_steps turns, off their
    // spawn: 2 bits each by enemy index, their turns of walking (1-3), after which they join the fight.
    std::uint32_t late(vec2 p, std::uint32_t key);
    // threat_strike(), kept for the turn.
    const Strike& strike_of(const ChampionBelief& e) { return struck(e).strike; }
    // What a visible enemy could do to p before our next turn (threat_strike placed on the map).
    Blow blow(const ChampionBelief& e, vec2 p);
    // A visible enemy's turns of walking before it can strike p: 0 if it can now, else at least 1
    // and at least its Chebyshev distance past its reach.
    int approach(const ChampionBelief& e, vec2 p);
    // Enough for most fights, by the champions in sight and this turn's costliest simulation;
    // plus query_cost_estimate().
    std::uint64_t fight_cost_estimate();
    // The threat build and the visible threats' Reach builds still pending.
    std::uint64_t query_cost_estimate();
    // At most what building the threats costs, 0 once built.
    std::uint64_t build_cost_estimate();
    // The fight if we stay at p: us and the allies near p against the enemies who can strike p
    // now (the unseen ones only if a visible one can, or `unseen`), joined by every visible enemy
    // within `approach` steps of its reach once it has walked into reach, while the camps in reach
    // of p keep hitting us. `falls` as for fight(); without walkers or camps it is fight(p).
    // Once a visible enemy hits p, those within `joined` steps join too.
    Trade stand(vec2 p, int approach, bool falls, bool unseen, int joined = 0);
    // Their turns for the visible enemies and camps to kill us at p if we never act (channelling),
    // each enemy walking a step a turn until in reach; 0 if not within `horizon` turns.
    int turns_to_kill_idle(vec2 p, int horizon);
    // Could the credible threats and camps kill us at p before our next turn? Against our health
    // and shield now: Ren's retaliation and our shield cast this turn count once refreshed.
    bool lethal(vec2 p);

    // Live members of awake (or maybe awake) groups, bar those read asleep that nobody else is near
    // enough to wake, with where they would attack us from.
    struct CampHit {
        vec2 pos;
        float strength; // softened by our emblems: its damage to us
        float weight;
        int reach; // farthest distance at which it would pick us
        std::uint32_t handle;
        bool stunned; // in sight and stunned: it skips the next camp phase
    };
    std::span<const CampHit> awake_members();

    // After our attacks and casts: invalidate() only if a visible enemy or camp member died.
    void refresh();

    // A visible enemy's Reach, built on first use this turn: blow(e, p) where its strike reaches p.
    const Reach& reach_of(const ChampionBelief& e);

private:
    bool may_be_hit(vec2 p); // false only if no threat hits p
    bool threatened_now(vec2 p);
    // Every credible threat at full damage, plus camps.
    float worst_damage(vec2 p);
    // Its strike's reach; for one whose stun leaves it no turn before our next, its first turn's,
    // as it still fights from then on.
    int fight_reach(const ChampionBelief& e);
    // Key bits of the lost_mask_ enemies whose fight_reach() covers p.
    std::uint32_t lost_in_reach(vec2 p);
    // Drop everything cached, after something this turn changed the fight: a kill or a camp kill.
    // Later queries recheck the engine for champions and monsters that died; stuns are not read.
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
    // foe(e) with only its strike worked out: an unseen enemy's tiles and weight count its
    // possible set, a whole-board host operation.
    Foe& struck(const ChampionBelief& e);
    void strike_foe(const ChampionBelief& e, Foe& x);
    void count_foe(const ChampionBelief& e, Foe& x);
    void build_threats();
    void find_members();
    void count_champions();
    void list_reachable();
    std::uint64_t estimate_build();
    bool still_alive(const ChampionBelief& c);
    void build_reach(const ChampionBelief& e, Reach& r);
    void build();
    template <class F> void each_threat(vec2 p, F&& f);
    // Seen alive at turn start but dead now, once refreshed.
    bool gone(const ChampionBelief& c);

    const World& world_;
    std::uint16_t reached_ = 0; // bit i: reach_pool()[i] is built for enemies[i] this turn
    bool built_ = false;
    bool refresh_ = false;
    float own_health_ = -1; // lethal()'s health and shield, read on first need since the last refresh
    std::array<std::int8_t, 16> gone_{}; // by enemy index: 0 unknown, 1 alive, 2 dead
    bool listed_ = false;
    std::uint32_t seen_ = 0, unseen_ = 0;
    // Left uninitialised: the engine charges for every byte written. Bit i: foes_[i] is set.
    std::uint16_t known_ = 0;
    std::uint16_t counted_ = 0; // bit i: foes_[i] has its tiles and weight
    std::uint32_t made_ = 0; // fighters made for the fights this turn: bit i for allies[i], 16 + i for enemies[i]
    union {
        std::array<Foe, 16> foes_;
    };
    // The first `threat_count_` of a pool kept across turns (one Safety lives at a time): growing a
    // vector reallocates at ~300 fuel a time, and each Threat allocates a bitboard.
    std::vector<Threat>& threats_;
    int threat_count_ = 0;
    // Bit i: enemies[i] is one of them, or fights though a stun leaves it no turn before our next (lost_mask_).
    std::uint16_t threat_mask_ = 0, lost_mask_ = 0;
    std::vector<CampHit>& members_; // likewise, the first `member_count_`; valid once `members_known_`
    int member_count_ = 0;
    bool members_known_ = false;
    float camp_factor_ = 0; // camp_hit_factor(), read on first need: CampHit strengths carry it
    struct CampMemo {
        vec2 p;
        float damage;
        bool valid;
    };
    // camp_damage() by `worst`, and worst for the next phase: the last tile asked. Reset whenever the
    // members are found or a stun is read.
    union {
        std::array<CampMemo, 3> camp_memo_;
    };
    // camp_area() and enemy_area() are kept in scratch boards: allocating one each turn costs ~550.
    bool camp_area_known_ = false, enemy_area_known_ = false;
    // threatened()'s last tile and answer: callers on a recall or shop turn ask about our tile again.
    vec2 threatened_at_{-1, -1};
    bool threatened_ = false;
    // By fight_key(). A memo: past `max_fights` the oldest is replaced.
    struct FightMemo {
        std::uint32_t key, late;
        Trade trade;
    };
    static constexpr int max_fights = 32;
    // `falls`: only one whose self_falls is known.
    const Trade* memo(std::uint32_t key, std::uint32_t late, bool falls) const;
    int fight_count_ = 0;
    std::uint32_t unknown_falls_ = 0; // bit i: fights_[i] was asked without self_falls and does not know it
    union {
        std::array<FightMemo, max_fights> fights_;
    };
    std::uint64_t costliest_fight_ = 0;
    // Bit i: query_cost_estimate() counts enemies[i]'s Reach until built (reached_), as found
    // once refreshed: reached_ only gains bits meanwhile, and gone() keeps its answers.
    std::uint16_t reachable_ = 0;
    bool reachable_known_ = false;
    int champions_ = -1;            // in sight, for fight_cost_estimate(); beliefs are fixed for the turn
    std::uint64_t build_cost_ = 0;  // build_cost_estimate() until built, refreshed or invalidated; 0: unknown
};

} // namespace aph
