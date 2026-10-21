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
// sight (walls and bushes block it; a bush tile is seen only from its own cluster, or by a visible
// enemy ward), or a ground spell at any tile within 5; Varg's basic attacks also at a unit beside
// the tile. Damage as Strike's.
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
    void build_ways(const ChampionBelief& e, std::array<bool, 2> ready, bool twice);
    std::array<Window, tile_sets> tiles_;
    std::array<std::int8_t, tile_sets> extent_; // farthest tile of each from the enemy
    const World* world_ = nullptr;
    vec2 origin_{-1, -1};
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
        std::uint8_t slots = 0;
        bool twice = false, valid = false;
        bool operator==(const Recipe&) const = default;
    };
    struct Ways {
        Recipe recipe;
        std::array<Way, 14> way;
        int count = 0;
        int basic = -1; // the plain basic attack's way
    };
    std::array<Ways, 8> ways_by_;
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

// From its facts, last-read Strength and Focus and the cooldowns projected to `turn_round`.
const Strike& strike(const ChampionBelief& c, int turn_round);
// The round of the enemy's next turn: later this round if it acts after us, else next round.
int next_turn_round(const World& world, const ChampionBelief& c);
// Its turns before our next one: later this round, and next round before us.
int turns_before_ours(const World& world, const ChampionBelief& c);
// strike(), widened when it has two turns before our next: a walk then the strike, or the strike
// and a second basic attack.
const Strike& threat_strike(const World& world, const ChampionBelief& c);

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
    // Unseen: distance from `possible` around walls, capped at the reach; reused by the next build.
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
    bool cut = false;           // set in trade() on fight-cut; never memoised
    float our_health = 0, their_health = 0; // debug_fights only
    int allies = 0, enemies = 0;
    std::array<float, 4> dealt{}; // debug_fights only: see simulate()
};

// What could hit one tile before our next turn. Bit i of a mask: enemies[i].
struct TileDanger {
    std::uint16_t vis_mask = 0, stun_mask = 0, unseen_mask = 0;
    float vis = 0, vis_unacted = 0, unseen = 0, camp_exp = 0, camp_worst = 0;
    float worst() const { return vis + unseen + camp_worst; }
};

// Own turns a fight is played for: every slot ready at the start is cast on turns 0, 8 and 16.
// Measured at 100M on the worst maps, kills land just after those casts (peaks on turns 9 and 17),
// and the 8% of fights still undecided at 24 turns cost 20% of the simulation fuel.
inline constexpr int fight_horizon = 17; // 2 * ability_cooldown + 1, asserted in safety.cpp

// What Safety::engage() simulates at a tile: COMBAT-MERGE.md's per-mode rule table.
struct Engage {
    enum class Mode : std::uint8_t { stand, pursue, idle };
    Mode mode = Mode::stand;
    int approach = 0;          // pursue/idle
    int horizon = fight_horizon;
    int with_enemy = -1;       // always in the key (prey); never no_fight
};

// Whether ending the turn on a tile loses its fight there.
struct Verdict {
    bool lost = false, falls = false;
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
    // tile(p).worst(), with each visible enemy yet to act counted twice when `double_unacted`.
    float damage_bound(vec2 p, bool double_unacted = false);
    // At least damage_bound(p), counting every unseen threat at its most: no host queries or
    // strikes for them.
    float damage_ceiling(vec2 p, bool double_unacted = false);
    float camp_damage(vec2 p, bool worst = true);
    // Where a live member of an awake (or maybe awake) group would attack us: within its range, and
    // no visible champion nearer it (or as near and acting first).
    const bitboard& camp_area();
    // Chance of taking any damage or a stun at p before our next turn (cancelling a recall).
    bool threatened(vec2 p);

    const bitboard& enemy_area(); // within a credible threat's reach
    // Tiles to keep off while routing: camps and credible enemies. Our own tile is included when
    // in danger, so routing can free the region we stand in.
    bitboard avoid();
    // any_within(avoid(), p, r), without building the threats.
    bool avoid_within(vec2 p, int r);
    // Each threat as threats() would list it, with its blow at p as tile(p) counts it. Returns the
    // count.
    struct ThreatAt {
        int enemy;
        Blow blow;
    };
    int threats_at(vec2 p, std::array<ThreatAt, 16>& out);

    // The tile table: each tile's danger numbers. A row stays put until generation() changes, but
    // tiles outside the 7x7 around the turn-start tile share 4 slots: copy a row to keep it across
    // other tile() calls. Like blow(), it throws for a wall tile in a visible enemy's reach.
    // The one unseen rule: an unseen credible threat's blow is its Threat::at(p), so that threat
    // alone is built once `possible` comes within its field's radius of the window (or of p, outside it).
    // camp_damage() and exit_rounds() fill only the camp columns, and never throw.
    const TileDanger& tile(vec2 p);
    // The visible threats' Strike bounds at p, without building their Reach; `mask` gets their bits.
    float strike_sum(vec2 p, std::uint16_t* mask = nullptr);
    // Rounds of walking from p until no awake camp member can pick us: the least r with
    // any_within(standable & ~camp_area(), p, r), at most one more than the longest camp reach;
    // 0 if none can pick us at p.
    int exit_rounds(vec2 p);
    // Chance an unseen threat hits p: 1 - prod(1 - near / tiles * hit_given_reach) over
    // tile(p).unseen_mask.
    float unseen_chance(vec2 p);

    // engage(p) stand: us and the allies we see within `fight_ally_radius`, against every credible
    // threat that could hit p. Cut short (Trade::cut) rather than spend the turn's last `end_reserve`.
    Trade fight(vec2 p);
    // Who would fight at p: bit i of the low half for allies[i], of the high half for enemies[i];
    // no_fight if no threat hits p.
    static constexpr std::uint32_t no_fight = ~0u;
    std::uint32_t fight_key(vec2 p);
    // fight_key(p) given `visible`: the bits of every visible threat that hits p, at least one.
    std::uint32_t fight_key_with(vec2 p, std::uint32_t visible);
    // The stand fight of a key with no camp charge, memoised.
    Trade fight_of(std::uint32_t key);
    // fight_of(key) if memoised, else null.
    const Trade* known_fight_of(std::uint32_t key) const { return memo(uint_key(key)); }
    // fight_of(key) when known_fight_of(key) is null.
    Trade new_fight(std::uint32_t key);
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
    // engage(p) pursue: lost means they win even if we stand and fight.
    Trade pursuit(vec2 p, int approach);
    // engage(p) idle: their turns for the visible enemies and camps to kill us at p if we never act
    // (channelling); 0 if not within `horizon` turns.
    int turns_to_kill_idle(vec2 p, int horizon);
    // Could the credible threats and camps kill us at p before our next turn?
    bool lethal(vec2 p);

    // The one simulation entry, by COMBAT-MERGE.md's rule table. Stand: us and the allies near p,
    // they first, against tile(p)'s visible and credible unseen threats (and with_enemy). Pursue:
    // we first, against the visible enemies off their spawn within `approach` walks, each joining
    // as it arrives. Both are charged the camps' expected damage at p, less the claimed group, for
    // exit_rounds(p) of their turns. Idle: we never act (a channel) against the visible enemies
    // arriving within the horizon, charged the camps for all of it; turns_to_kill_us, with lost
    // and self_falls set when it is not 0. Memoised by who fights, arrivals, camp charge and mode,
    // across invalidate(); a stand fight may be settled by a memoised won one at least as hard or
    // lost one at most as hard.
    Trade engage(vec2 p, Engage e);
    int idle_turns(vec2 p, int horizon);
    void set_claimed(int group); // camp group our farm/siege budgets; skipped in stand/pursue camp charge
    Verdict verdict(vec2 q);       // engage(q) stand's lost and self_falls
    bool guarded(vec2 q);          // false if no visible foe reaches q (strike_sum) or q no worse than here (mask ⊆, damage ≤);
                                   // else v.lost || (v.falls && (linked || tile(q).worst() >= health)). Radius 3 only.
                                   // Here is the turn-start tile; answers are kept for the generation.
    // The tiles guarded() has answered true this generation, drawn when asked; null: none. Tiles
    // nobody asked about are left out: callers ask guarded() of the tiles they would end on.
    const bitboard* guarded_board();
    std::uint32_t guard_stamp() const; // generation << 8 | guarded count (KeptRoute key)
    // fight/pursuit/turns_to_kill_idle stay as wrappers until W4.

    // Live members of awake (or maybe awake) groups, bar those read asleep that nobody else is near
    // enough to wake, with where they would attack us from.
    struct CampHit {
        vec2 pos;
        float strength; // softened by our emblems: its damage to us
        float weight;
        int reach; // farthest distance at which it would pick us
        std::int16_t group;
    };
    std::span<const CampHit> awake_members();

    // After our attacks and casts: invalidate() only if a visible enemy or camp member died.
    void refresh();
    // Changes whenever cached answers may. Unique across Safety instances, so a stamp left in
    // uninitialised storage by an earlier one never matches.
    std::uint32_t generation() const { return generation_; }
    // After world.observe(): true if Safety was kept, dropping only what unseen enemies decide;
    // false if it must be rebuilt.
    bool reobserve();
    ~Safety(); // debug: the MEMO line

    // A visible enemy's Reach, built on first use this turn: blow(e, p) where its strike reaches p.
    const Reach& reach_of(const ChampionBelief& e);

private:
    bool may_be_hit(vec2 p); // false only if no threat hits p
    // Every credible threat at full damage, plus camps.
    float worst_damage(vec2 p);
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
    };
    Foe& foe(const ChampionBelief& e);
    // foe(e) with only its strike worked out: an unseen enemy's tiles and weight count its
    // possible set, a whole-board host operation.
    Foe& struck(const ChampionBelief& e);
    void strike_foe(const ChampionBelief& e, Foe& x);
    void count_foe(const ChampionBelief& e, Foe& x);
    // Appends the threats of the enemies in `which` that have none yet.
    void build_threats(std::uint32_t which);
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
    std::uint16_t threat_mask_ = 0; // bit i: enemies[i] is one of them
    std::vector<CampHit>& members_; // likewise, the first `member_count_`; valid once `members_known_`
    int member_count_ = 0;
    bool members_known_ = false;
    float camp_factor_ = 0; // camp_hit_factor(), read on first need: CampHit strengths carry it
    // The tile table: slot 7 * (y - centre_.y + 3) + x - centre_.x + 3 for the 7x7 window, then 4
    // ring slots for tiles outside it, reused in turn. A row's columns fill lazily in groups, each
    // with a known bit per slot (bit s: slot s); the bits are dropped at a new generation and the
    // rows are left uninitialised.
    static constexpr int window_slots = 49, table_slots = window_slots + 4;
    void sync_table();
    int window_slot(vec2 p) const; // -1 outside the window
    int slot_of(vec2 p);           // -1 if p has no slot yet
    int claim_slot(vec2 p);        // outside the window, takes the next ring slot
    int threat_slot(vec2 p);       // claim_slot(p) with the row's columns filled
    void fill_threats(vec2 p, TileDanger& row);
    void fill_camps(vec2 p, TileDanger& row);
    // The one unseen rule for an unseen credible enemy (see tile()).
    Blow unseen_blow(const ChampionBelief& e, const Foe& x, vec2 p, bool window);
    // Inside debug_block only: the distance-0 rule the table replaced (each credible unseen threat
    // at its strike's damage at 0 when `possible` is within its reach of p); `near`: any did.
    float debug_old_unseen(vec2 p, bool* near);
    vec2 centre_;
    std::uint32_t table_generation_ = 0;
    std::uint64_t threats_known_ = 0, camps_known_ = 0, chances_known_ = 0;
    // By enemy, this generation: whether `possible` comes within an unseen threat's field of the window.
    std::uint16_t gate_asked_ = 0, gate_near_ = 0;
    std::uint8_t ring_used_ = 0, ring_next_ = 0;
    std::uint32_t exits_generation_ = 0; // of exit_rounds()' field
    union {
        std::array<vec2, 4> ring_at_;
    };
    union {
        std::array<TileDanger, table_slots> rows_;
    };
    struct Lazy {
        float chance; // unseen_chance()
    };
    union {
        std::array<Lazy, table_slots> lazy_;
    };
    std::optional<bitboard> camp_area_, enemy_area_;
    // An engage() fight, all its simulation depends on: who fights (fight_key()'s bits), each
    // enemy's arrival turn (3 bits at 3 * i), the camp charge each of their turns in camp_step
    // units for their first `camp_turns` turns, the mode and the horizon.
    struct FightKey {
        std::uint32_t who;
        std::uint64_t arrive;
        std::uint16_t camp_q;
        std::uint8_t camp_turns, mode, horizon;
        bool operator==(const FightKey&) const = default;
    };
    // A uint32 key's: stand, no camp charge.
    static constexpr FightKey uint_key(std::uint32_t who) {
        return {who, 0, 0, 0, static_cast<std::uint8_t>(Engage::Mode::stand), static_cast<std::uint8_t>(fight_horizon)};
    }
    // False if there is no fight: no enemy (and, idle, no camp charge).
    bool shape(vec2 p, const Engage& e, FightKey& k);
    // The memo's trade, or a fight it settles, else a new one.
    Trade play(const FightKey& k);
    // 1: k's memoised trade; 2: a stand key settled by a memoised stand fight with its camp charge,
    // a won one with at least its enemies and at most its allies, or a lost one the reverse
    // (lost and self_falls only); 0: neither.
    int recall(const FightKey& k, Trade& out);
    // Simulates k with `enemies` as its enemies and memoises it, unless cut.
    Trade run(const FightKey& k, std::uint32_t enemies);
    void note_linked();
    std::uint32_t linked_who_ = 0; // Cassi and Issac, as FightKey::who bits
    bool linked_known_ = false;
    // A memo: past `max_fights` the oldest is replaced. Kept across generations: a key's trade
    // depends only on its fighters, made once a turn.
    struct FightMemo {
        FightKey key;
        Trade trade;
    };
    static constexpr int max_fights = 48;
    const Trade* memo(const FightKey& key) const;
    // Forgets the fights of keys naming any of `enemies` (bit i: enemies[i]).
    void drop_fights(std::uint32_t enemies);
    std::uint32_t generation_;
    int fight_count_ = 0;
    union {
        std::array<FightMemo, max_fights> fights_;
    };
    // What reobserve() compares: the champions in view and the camps at construction.
    void note_view();
    struct Viewed {
        vec2 pos;
        float health;
    };
    std::uint16_t viewed_enemies_ = 0, viewed_allies_ = 0; // bit i: alive and visible
    std::uint32_t viewed_camps_ = 0;                        // World::camps_version
    union {
        std::array<Viewed, 16> viewed_; // by enemy index, for viewed_enemies_
    };
    // The verdict section (W2-A).
    int claimed_ = -1; // set_claimed()
    // camp_damage(p, false) less the claimed group's members.
    float stand_camp(vec2 p);
    Verdict judge(const FightKey& k);
    bool guard_rule(Verdict v, bool dies) const;
    // Whether guarded(q) needs a verdict, with its key and whether tile(q) can kill us.
    bool exposed(vec2 q, FightKey& k, bool& dies);
    // guarded()'s answers (bit s: window slot s) for guarded_generation_, and the true ones
    // guarded_board() has drawn for board_generation_.
    void sync_guard();
    std::uint32_t guarded_generation_ = 0, board_generation_ = 0;
    std::uint64_t guard_asked_ = 0, guard_true_ = 0, board_bits_ = 0;
    std::uint64_t costliest_fight_ = 0;
    // Bit i: query_cost_estimate() counts enemies[i]'s Reach until built (reached_), as found
    // once refreshed: reached_ only gains bits meanwhile, and gone() keeps its answers.
    std::uint16_t reachable_ = 0;
    bool reachable_known_ = false;
    int champions_ = -1;            // in sight, for fight_cost_estimate(); beliefs are fixed for the turn
    std::uint64_t build_cost_ = 0;  // build_cost_estimate() until built, refreshed or invalidated; 0: unknown
};

} // namespace aph
