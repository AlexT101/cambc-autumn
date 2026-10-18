#pragma once
#include <cambc.h>
#include <array>
#include <cstdint>
#include <deque>
#include <memory>
#include <optional>
#include <vector>
#include "champions.h"
#include "draft.h"
#include "params.h"
#include "util.h"

namespace aph {

// Derived static parts are built on first use: all at once costs too much fuel on large maps.
// WASM loops, sorting and hashing are costly; host bitboard and field calls are cheap.

struct StaticMap;

// For start-up data kept to the end: a bump allocator over static storage, which starts zeroed
// for free, where each malloc costs ~130 fuel. Nothing is freed.
void* static_alloc(std::size_t bytes, std::size_t align);
template <class T> struct StaticAlloc {
    using value_type = T;
    StaticAlloc() = default;
    template <class U> constexpr StaticAlloc(const StaticAlloc<U>&) noexcept {}
    T* allocate(std::size_t n) { return static_cast<T*>(static_alloc(n * sizeof(T), alignof(T))); }
    void deallocate(T*, std::size_t) noexcept {}
    template <class U> bool operator==(const StaticAlloc<U>&) const noexcept { return true; }
};
template <class T> using StaticVector = std::vector<T, StaticAlloc<T>>;

struct Altar {
    vec2 pos;
    int mirror = -1; // index of the symmetric altar (itself if on the axis)

    const bitboard& tribute_tiles() const; // walkable for us within tribute range (1)
    const bitboard& lock_tiles() const;    // walkable for us within 2: where a lock can be placed from

private:
    friend class World;
    friend struct StaticMap;
    const StaticMap* map_ = nullptr;
    mutable std::optional<bitboard> tribute_, lock_;
};

struct CampMember {
    std::uint32_t handle; // engine camp id
    vec2 pos;
    cambc::camp_type type;
    float max_health;
    float strength;
};

struct CampGroup {
    std::uint32_t handle; // engine camp-group id
    StaticVector<CampMember> members;
    vec2 centre;        // the member tile nearest the members' mean position
    int gold = 0, gems = 0;
    int respawn = 0;    // rounds from capture payout to return
    float strength = 0; // damage per camp phase from all members while awake
    int mirror = -1;
    bool has_monolith = false;

    cambc::camp camp(int member) const;
    const bitboard& tiles() const;    // camp tiles: stand on one, with no enemy on any, to capture
    const bitboard& adjacent() const; // walkable tiles within 1 of a camp tile, camp tiles excluded
    const bitboard& threat() const;   // tiles within 3 of a camp tile, where its monsters attack

private:
    friend class World;
    friend struct StaticMap;
    const StaticMap* map_ = nullptr;
    mutable std::optional<bitboard> tiles_, adjacent_, threat_;
};

// An edge-connected set of bush tiles (diagonal bushes are separate clusters). From inside a
// cluster it is see-through, within the usual vision square; from outside you see none of it.
struct BushCluster {
    bitboard tiles;
    int size = 0;
};

struct StaticMap {
    // From the engine's map, with the draft's analysis if it wrote one for this map.
    static std::unique_ptr<StaticMap> build();

    int width = 0, height = 0;
    cambc::symmetry symmetry{};
    bool team_a = true; // team A starts odd rounds; B starts even rounds and wins a full tie

    // The SDK's own boards, read once at start-up.
    const bitboard& walls = cambc::map::walls();
    const bitboard& holes = cambc::map::holes();
    const bitboard& bushes = cambc::map::bushes();
    const bitboard& altar_tiles = cambc::map::altars();
    const bitboard& ally_spawn = cambc::map::spawn_region(team::ally);
    const bitboard& enemy_spawn = cambc::map::spawn_region(team::enemy);
    bitboard camp_tiles;
    std::vector<vec2> ally_spawn_tiles, enemy_spawn_tiles;
    vec2 ally_spawn_centre, enemy_spawn_centre;

    // Written whole by World::build_static, so not cleared first.
    bitboard impassable{cambc::uninitialized};       // walls | holes | altars: nobody walks or lands there
    bitboard passable{cambc::uninitialized};         // ~impassable
    bitboard blocked_for_us{cambc::uninitialized};   // impassable | enemy spawn: static walls for our walking
    bitboard blocked_for_them{cambc::uninitialized}; // impassable | our spawn
    bitboard open_for_us{cambc::uninitialized};      // ~blocked_for_us
    bitboard open_for_them{cambc::uninitialized};    // ~blocked_for_them
    bitboard near_enemy_spawn; // within 1 of an enemy spawn tile
    bitboard walls_and_bushes{cambc::uninitialized};
    bitboard standable{cambc::uninitialized}; // ~(camp_tiles | blocked_for_us)

    std::vector<Altar> altars;
    std::vector<CampGroup> groups;

    vec2 mirror(vec2 p) const;
    bitboard mirror(const bitboard& b) const;
    int group_at(vec2 p) const; // group whose camp tile this is, or -1
    int altar_at(vec2 p) const; // altar on this tile, or -1
    bool walkable(vec2 p) const { return in_bounds(p) && !blocked_for_us.is_set(p); }

    // Walking steps over static terrain (camps and units ignored).
    const Field& from_ally_spawn() const;
    bool from_ally_spawn_ready() const { return ally_field_.has_value(); }
    const Field& from_enemy_spawn() const;
    const BushCluster& bush_cluster(vec2 p) const;
    const bitboard& near_bushes() const; // tiles with a bush within ward placement range (2)
    // Find every cluster viewers(p, radius) needs while more than `fuel_floor` fuel remains; true
    // once all are. A large cluster can take ~100k, so the work carries over between calls.
    bool find_bush_clusters(vec2 p, int radius, std::uint64_t fuel_floor) const;
    // Tiles from which p is in sight within Chebyshev `radius`: the engine's shadowcast, with
    // walls and every bush cluster but the viewer's own opaque.
    bitboard viewers(vec2 p, int radius) const;

    // Compute derived parts while more than `fuel_floor` fuel remains; true once all are done.
    bool warm_up(std::uint64_t fuel_floor) const;

    // Walking steps to a group's centre from our spawn and from theirs: the spawn fields' values.
    int ally_steps(int group) const;
    int enemy_steps(int group) const;
    // From the draft, when it has them: the steps to a group's centre from the tribute tiles of
    // every altar, and from one of our spawn tiles; a member's attack tiles (Pathing).
    std::optional<int> drafted_altar_steps(int group) const;
    std::optional<int> drafted_spawn_steps(vec2 tile, int group) const;
    bool drafted() const { return plan_ != nullptr; }
    bool spawn_steps_drafted() const { return plan_ && plan_->spawn_tiles > 0; }
    bool attack_tiles_drafted(int group, int range) const;
    bitboard drafted_attack_tiles(int group, int member, int range) const;

private:
    friend class World;
    const DraftPlan* plan_ = nullptr; // matching this map
    mutable std::vector<int> attack_bit_; // per drafted group: its members' first bit in plan_->data
    int drafted_steps(int group, int which) const;
    // Per tile, row-major, in static storage, which starts zeroed for free: filling a vector costs
    // ~1 fuel a byte. One map per process.
    static constexpr int max_tiles = 100 * 100;
    inline static std::array<std::uint16_t, max_tiles> group_lookup_{}; // group index + 1, or 0
    inline static std::array<std::uint16_t, max_tiles> altar_lookup_{}; // altar index + 1, or 0
    mutable std::optional<Field> ally_field_, enemy_field_;
    mutable std::deque<BushCluster> bush_clusters_; // found so far; references stay valid
    mutable bitboard clustered_;                     // their tiles
    inline static std::array<std::uint16_t, max_tiles> cluster_of_{}; // cluster index + 1, or 0
    struct Growth {
        bitboard tiles;        // the 8-connected flood
        bool diagonal = false; // the flood joins bushes only diagonally somewhere: grow by edges
    };
    mutable std::optional<Growth> growth_; // a flood whose cluster was not found for lack of fuel
    // The cluster grown from p; null if the fuel fell to the floor first.
    const BushCluster* grow_cluster(vec2 p, std::uint64_t fuel_floor) const;
    mutable std::optional<bitboard> diagonal_links_, near_bushes_;
    const bitboard& diagonal_links() const; // bushes with a bush diagonal neighbour joined only diagonally
};

enum class Source : std::uint8_t {
    none,
    seen,
    comms,
    inferred, // the rules (respawn on spawn, recall arrival, ...)
};

enum class Channel : std::uint8_t { none, recall, tribute, teleport };

// A point in the turn order: after the turn in `slot` of `round` (-1: the round's start).
struct Moment {
    int round = 0;
    int slot = -1;
    auto operator<=>(const Moment&) const = default;
};

inline constexpr int home_recall_time = 3;       // turn ends, with a Home emblem
inline constexpr int teleport_crystal_range = 3; // Chebyshev, terrain ignored
inline constexpr int ability_cooldown = 8;        // rounds from a cast to the slot's next

struct ChampionBelief {
    cambc::handle_champion_t handle{};
    cambc::champion_type type{};
    team side = team::enemy;
    int index = 0; // position among its team's champions (handle order = pick order)
    bool is_self = false;

    bool alive = true;
    int died_round = -1;       // round we first saw it dead
    int respawn_earliest = -1; // window for its respawn round while dead
    int respawn_latest = -1;
    int respawned_round = -1; // its respawn turn's round, when known to be this round's

    // Last observation. `visible` means in our vision now; the rest may be stale.
    bool visible = false;
    vec2 pos{-1, -1};
    int pos_round = -1;
    Source pos_source = Source::none;
    float health = 0, max_health = 0, strength = 0, focus = 0;
    int stats_round = -1;
    int gems = 0;
    int gems_round = -1;
    bool fast_recall = false; // a Home emblem, when last seen (enemies; we never buy one): recall takes home_recall_time turn ends
    bool acted = false; // had completed its turn when last read this round
    // Turn-order priority for priority_round, and from the round after it.
    int priority = 0, next_priority = 0, priority_round = -1;
    int rank = 0; // place in its team's turn order, from the priorities last read
    int prev_rank = 0; // its rank in the round of our previous update

    // Abilities: the earliest round each slot could be cast. Exact while visible (read from the
    // engine); through fog, projected with the cooldown rule assuming no unseen cast, so the real
    // round can be later, never earlier, except that a Vendetta kill readies both.
    std::array<int, 2> ready_round{0, 0};
    std::array<int, 2> last_cast_round{-1, -1}; // inferred from the cooldown jumping up

    Channel channel = Channel::none;
    int channel_end_round = -1;

    // Enemies only: every tile it could be on, from what we have seen and how champions move.
    // Teleport crystals are not modelled. Empty while dead; anywhere while !tracked. Left
    // uninitialised until the first fix, so never set for allies.
    bitboard possible{cambc::uninitialized};
    // Dashers only: the part of `possible` reached by walking alone since the fix. A dash moves
    // 2 more only once per cooldown, so the rest of `possible` is this widened by one dash.
    bitboard undashed{cambc::uninitialized};
    bool undashed_all = false; // undashed == possible
    bool tracked = false;
    // Nonzero lineages: possible and undashed equal those of every enemy with the same one.
    std::uint32_t lineage = 0;
    Moment fixed, at; // when `possible` was last known exactly, and when it describes
    int turns_since_fixed = 0;

    const ChampionFacts& facts() const { return aph::facts(type); }
    bool ability_ready(int slot, int round) const { return alive && round >= ready_round[slot]; }
    // No walking, attacking or casting on the respawn turn.
    bool can_act(int round) const { return alive && round != respawned_round; }
    // Damage back to whoever hits it (Ren), even as it dies.
    float retaliation() const { return facts().passive == Passive::retaliation ? retaliation_share * focus : 0.0f; }
    // True if an unseen reset could make the abilities ready earlier than ready_round says.
    bool cooldowns_uncertain() const { return !visible && facts().passive == Passive::reset_on_kill; }
    int age(int round) const { return pos_round < 0 ? 1 << 20 : round - pos_round; }
};

enum class CampState : std::uint8_t {
    alive,      // at least one monster alive
    cleared,    // every monster dead; the reward waits for a capture
    respawning, // captured; returns at respawn_round (later while a camp tile is occupied)
};

enum class Awake : std::uint8_t { asleep, awake, unknown };

struct CampBelief {
    CampState state = CampState::alive;
    int state_round = 0;     // last round the state was seen; 0 = the start-of-game assumption
    int respawn_round = -1;  // while respawning
    StaticVector<float> health;     // per member, last seen; 0 = dead
    StaticVector<int> health_round; // per member: the last round its health was known
    // Groups sleep until damaged and fall asleep after 2 camp phases with no champion within 3.
    Awake awake = Awake::asleep;
    int last_damaged_round = -1; // a health drop we saw
    int quiet_rounds = 0;        // consecutive fully observed rounds with no champion within 3
    // Capture in progress: who holds the cleared group's tiles, and the round the hold began
    // (payout at held_since + capture_time + 1).
    std::optional<team> holder;
    int held_since = -1;
    // Who stood on its tiles when last fully seen: bit i for allies[i], 16 + i for enemies[i].
    std::uint32_t occupants = 0;
    int told_respawn = -1; // the respawn round the team was told through comms
    int cleared_by_us = -1; // the round our own turn killed its last member while we stood on it
};

struct AltarBelief {
    bool ally_lock = false, enemy_lock = false;
    int ally_lock_hits = 0, enemy_lock_hits = 0;
    int seen_round = -1;
};

struct WardSighting {
    vec2 pos;
    int round;
};

struct Scores {
    int ally = 0, enemy = 0;             // tributed gems
    int ally_delta = 0, enemy_delta = 0; // change since our previous turn
    int enemy_tribute_round = -1;        // round we saw the enemy's latest tribute land
    int enemy_tribute_amount = 0;
};

class World {
public:
    // Start of each play turn. The first call also builds the static map.
    void update();
    void observe();
    // After our actions: note a group we cleared standing on it, so held from this round.
    void note_turn_end();
    std::uint64_t observe_cost_estimate() const { return 1000 * (allies.size() + enemies.size()); }

    // Merge a teammate's sighting (from comms), with health as a share of max; ignored if not
    // fresher than ours.
    void note_sighting(int enemy_index, vec2 pos, int round, float health);
    // A teammate saw the group captured, returning at `respawn_round`.
    void note_capture(int group, int respawn_round);

    void debug_output() const;
    void dump_beliefs() const;

    bool ready() const { return static_ != nullptr && self_index < static_cast<int>(allies.size()) && allies[self_index].is_self; }
    const StaticMap& map() const { return *static_; }
    // True if the bot ran out of fuel and resumed in a later round: beliefs are a round old.
    bool is_stale() const { return cambc::round_number() != static_cast<std::uint32_t>(round); }

    const ChampionBelief& me() const { return allies[self_index]; }
    // Index of the champion's turn in `round`, by its rank then: the current one for this round,
    // that of our previous update for earlier rounds.
    int slot(const ChampionBelief& c, int round) const;
    Moment now() const { return {round, slot(me(), round)}; }
    // Turns the champion takes strictly between two moments.
    int turns_between(const ChampionBelief& c, Moment from, Moment to) const;
    int round = 0;
    int first_round = 0; // this instance's first play round

    std::vector<ChampionBelief> allies; // in handle order, self included
    std::vector<ChampionBelief> enemies;
    int self_index = 0;

    std::vector<CampBelief> camps; // parallel to map().groups
    std::vector<AltarBelief> altars; // parallel to map().altars
    std::vector<WardSighting> enemy_wards;
    Scores score;
    bitboard visible; // this turn's vision (ours and our ward's)
    // An enemy was seen changing priority: its team's order for next round can change until each
    // has acted, and unseen ones' ranks are guesses.
    bool enemy_priorities_change = false;

private:
    void init_beliefs();
    void rank_turns();
    // Also keeps each champion's rank of the previous round when a new one starts.
    void read_priorities(bool new_round);
    void prune(ChampionBelief& b) const;
    static void note_emptied(ChampionBelief& b);
    void update_champions(bool full);
    void update_champion(ChampionBelief& b, bool full);
    void read_vision(); // visible and unseen_, overwritten in place
    // Each overwrites `possible` in place: assigning a new board would allocate.
    static void fix_at_spawn(ChampionBelief& b, const bitboard& spawn, Moment when);
    static void fix(ChampionBelief& b, vec2 tile, Moment when);
    static void fix_nowhere(ChampionBelief& b, Moment when);
    static void mark_fixed(ChampionBelief& b, Moment when);
    void advance(ChampionBelief& b);
    // advance() then prune(), with the prune folded into the growth.
    void advance_and_prune(ChampionBelief& b);
    // Adds `turns` of movement to `possible`, ending on `land`; returns whether a dash widened it.
    bool grow(ChampionBelief& b, int turns, const bitboard& land);
    // Where a growth pruned straight after can end: open to them and out of sight.
    const bitboard& landing();
    // advance and prune an enemy of a lineage, or copy the result of one of the same lineage and
    // inputs tracked earlier in this pass.
    void track(ChampionBelief& b);
    static void walk(bitboard& tiles, const StaticMap& s, int steps, const bitboard& land);
    static void widen_by_dash(const bitboard& from, bitboard& out, const StaticMap& s, int steps, const bitboard& land);
    // Every change to `possible` but growth goes to `undashed` too.
    static void also_undashed(ChampionBelief& b, const bitboard& tiles);
    void update_camps();
    int hold_start(const CampGroup& G, team holder, int earliest, bool cleared_by_us) const;
    void update_altars();
    void update_wards();
    std::uint32_t tributing_enemies() const; // bit i: enemies[i] is believed to be tributing
    void update_scores(std::uint32_t tributing);

    std::unique_ptr<StaticMap> static_;
    bitboard unseen_; // ~visible
    bitboard landing_{cambc::uninitialized}; // open_for_them & unseen_, once landing_ready_
    bool landing_ready_ = false;
    std::vector<std::uint8_t> group_visible_; // update_camps() scratch
    // Per group: unseen, update_camps() could still change it (a hold paying out, a return, an
    // awake group's wakefulness going unknown).
    std::vector<std::uint8_t> camps_pending_;
    struct Tracked {
        std::uint32_t before, after;
        int leader, turns, tsf;
        Moment fixed, at;
        bool dasher, dash, fast_recall;
    };
    std::array<Tracked, 8> tracked_{}; // this pass's track() results
    int tracked_count_ = 0;
    std::uint32_t lineages_ = 0;
    bool ranks_stale_ = true;
    int ranked_round_ = -1;
    int updated_round_ = -1;
};

} // namespace aph
