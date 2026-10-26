#pragma once
#include <cambc.h>
#include <array>
#include <cstdint>
#include <deque>
#include <memory>
#include <optional>
#include <type_traits>
#include <vector>
#include "champions.h"
#include "combat_priority.h"
#include "draft.h"
#include "params.h"
#include "util.h"

namespace aph {

// Derived static parts are built on first use: all at once costs too much fuel on large maps.
// WASM loops, sorting and hashing are costly; host bitboard and field calls are cheap.

struct StaticMap;

// For start-up data kept to the end: a bump allocator over static storage, where each malloc costs
// ~130 fuel. Nothing is freed.
void* static_alloc(std::size_t bytes, std::size_t align);
// A fixed-size array in it, its elements unwritten: a vector's reserve or resize cost ~150 fuel
// each, ~500 a camp group over its three. Copies share the elements.
template <class T> class StaticArray {
    static_assert(std::is_trivially_copyable_v<T> && std::is_trivially_destructible_v<T>);

public:
    StaticArray() = default;
    explicit StaticArray(std::size_t n) : data_{n ? static_cast<T*>(static_alloc(n * sizeof(T), alignof(T))) : nullptr}, size_{n} {}
    // n elements of a larger one's storage: one allocation for many arrays, ~50 fuel each.
    StaticArray(StaticArray& pool, std::size_t& used, std::size_t n) : data_{n ? pool.data_ + used : nullptr}, size_{n} { used += n; }
    std::size_t size() const { return size_; }
    bool empty() const { return size_ == 0; }
    T* data() { return data_; }
    const T* data() const { return data_; }
    T& operator[](std::size_t i) { return data_[i]; }
    const T& operator[](std::size_t i) const { return data_[i]; }
    const T& front() const { return data_[0]; }
    T* begin() { return data_; }
    T* end() { return data_ + size_; }
    const T* begin() const { return data_; }
    const T* end() const { return data_ + size_; }

private:
    T* data_ = nullptr;
    std::size_t size_ = 0;
};

struct Altar {
    vec2 pos;

    const bitboard& tribute_tiles() const; // walkable for us within tribute range (1)
    const bitboard& lock_tiles() const;    // walkable for us within altar_lock_range: where a lock can be placed from

private:
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
    int reach; // attack range
};

struct CampGroup {
    std::uint32_t handle; // engine camp-group id
    StaticArray<CampMember> members;
    vec2 centre;        // the member tile nearest the members' mean position
    int gold = 0, gems = 0;
    int cluster_gold = 0, cluster_gems = 0; // the gold and gem clusters' part, which a Prospector emblem adds to
    int respawn = 0;    // rounds from capture payout to return
    float strength = 0; // damage per camp phase from all members while awake
    int reach = 0;      // longest member reach
    bool has_monolith = false;

    cambc::camp camp(int member) const;
    const bitboard& tiles() const;    // camp tiles: stand on one, with no enemy on any, to capture
    const bitboard& adjacent() const; // walkable tiles within 1 of a camp tile, camp tiles excluded
    const bitboard& threat() const;   // tiles within a member's reach of it, where its monsters attack
    // No tile of threat() is farther than this from the centre.
    int threat_radius() const;

private:
    friend struct StaticMap;
    const StaticMap* map_ = nullptr;
    mutable std::optional<bitboard> tiles_, adjacent_, threat_;
    mutable int threat_radius_ = -1;
};

// An edge-connected set of bush tiles (diagonal bushes are separate clusters). From inside a
// cluster it is see-through, within the usual vision square; from outside you see none of it.
struct BushCluster {
    bitboard tiles;
};

struct StaticMap {
    // From the engine's map, with the draft's analysis if it wrote one for this map.
    static std::unique_ptr<StaticMap> build();

    int width = 0, height = 0;
    cambc::symmetry symmetry{};
    bool team_a = true; // team A starts odd rounds; B starts even rounds and wins a full tie
    bool monolith_only = false; // every gem source is a Monolith
    // Every gem source is a big group (params::big_gems) or a Monolith, and there is a big group:
    // stampede's shared block.
    bool shared_gems = false;
    int max_camp_reach = 0; // longest reach of any camp member on the map
    // Walkable from our spawn, every camp counted as cleared; the same through dash_walls and landing_dash_walls.
    const bitboard& foot() const { return foot_ ? *foot_ : make_foot(); }
    const bitboard& dash_foot() const { return dash_foot_ ? *dash_foot_ : make_dash_foot(); }
    const bitboard& landing_dash_foot() const { return landing_dash_foot_ ? *landing_dash_foot_ : make_landing_dash_foot(); }
    // A walk region off foot() that a teleport crystal reaches: from a source tile on foot to a
    // landing tile within its range, terrain ignored, then the walk. One per altar no walk reaches
    // (its `altar`), then one per other region holding a farmed group (`altar` -1).
    struct Hop {
        int altar = -1;
        bitboard sources, landings, pocket; // pocket: the region, camp tiles included
    };
    const std::vector<Hop>& hops() const { return hops_ ? *hops_ : make_hops(); }
    // The hop into the region of a farmed group no walk reaches, or -1. Their hops are added by the
    // warm-up, after the altars': -1 until then.
    int group_hop(int group) const { return group_hops_done_ ? group_hops_[group] : -1; }
    bool hops_ready() const { return group_hops_done_; }
    bool any_group_hop() const { return group_hops_done_ && any_group_hop_; }

    // The SDK's own boards, read once at start-up.
    const bitboard& walls = cambc::map::walls();
    const bitboard& holes = cambc::map::holes();
    const bitboard& bushes = cambc::map::bushes();
    const bitboard& altar_tiles = cambc::map::altars();
    const bitboard& ally_spawn = cambc::map::spawn_region(team::ally);
    const bitboard& enemy_spawn = cambc::map::spawn_region(team::enemy);
    bitboard camp_tiles;
    std::vector<vec2> ally_spawn_tiles;
    vec2 ally_spawn_centre, enemy_spawn_centre;

    // Written whole by StaticMap::build, so not cleared first.
    bitboard impassable{cambc::uninitialized};       // walls | holes | altars: nobody walks or lands there
    bitboard passable{cambc::uninitialized};         // ~impassable
    bitboard blocked_for_us{cambc::uninitialized};   // impassable | enemy spawn: static walls for our walking
    bitboard blocked_for_them{cambc::uninitialized}; // impassable | our spawn
    bitboard open_for_us{cambc::uninitialized};      // ~blocked_for_us
    bitboard open_for_them{cambc::uninitialized};    // ~blocked_for_them
    // Holes and altars with standable tiles on two opposite sides, which a dash jumps in its two steps.
    // This and the next three are built only for a champion with a dash, and the draft bot.
    bitboard crossable;
    bitboard near_crossable{cambc::uninitialized}; // within 1 of a crossable tile
    bitboard dash_walls{cambc::uninitialized}; // blocked_for_us without crossable: a dasher's static walls
    // dash_walls for a dash that hits where it lands: no crossing within 2 of a harmful camp, which
    // the landing could wake (dash_across refuses it).
    bitboard landing_dash_walls{cambc::uninitialized};
    bitboard near_enemy_spawn; // within 1 of an enemy spawn tile
    bitboard walls_and_bushes{cambc::uninitialized};
    bitboard standable{cambc::uninitialized}; // ~(camp_tiles | blocked_for_us)

    std::vector<Altar> altars;
    std::vector<CampGroup> groups;

    // Group whose camp tile this is, or -1.
    int group_at(vec2 p) const { return static_cast<int>(group_lookup_[tile_index(p)]) - 1; }
    // Altar on this tile, or -1.
    int altar_at(vec2 p) const { return in_bounds(p) ? static_cast<int>(altar_lookup_[tile_index(p)]) - 1 : -1; }
    // Groups with a camp tile within `radius`, seen or not; a scratch vector, valid until the next call.
    const std::vector<int>& groups_near(vec2 p, int radius) const;

    // Walking steps over static terrain (camps and units ignored).
    const Field& from_ally_spawn() const { return ally_field_ ? *ally_field_ : make_ally_field(); }
    bool from_ally_spawn_ready() const { return ally_field_.has_value(); }
    const Field& from_enemy_spawn() const { return enemy_field_ ? *enemy_field_ : make_enemy_field(); }
    const BushCluster& bush_cluster(vec2 p) const;
    const BushCluster* found_bush_cluster(vec2 p) const { // null until p's cluster is found
        const int i = cluster_of_[tile_index(p)];
        return i > 0 ? &bush_clusters_[i - 1] : nullptr;
    }
    // Tiles with a bush within ward placement range (2).
    const bitboard& near_bushes() const { return near_bushes_ ? *near_bushes_ : make_near_bushes(); }
    // Find every cluster viewers(p, radius) needs while more than `fuel_floor` fuel remains; true
    // once all are. The work carries over between calls.
    bool find_bush_clusters(vec2 p, int radius, std::uint64_t fuel_floor) const;
    bool find_all_bush_clusters(std::uint64_t fuel_floor) const; // the same for the whole map
    bool find_bush_clusters(const bitboard& tiles, std::uint64_t fuel_floor) const; // the same for those with a tile in `tiles`
    bool bush_clusters_found(vec2 p, int radius) const; // find_bush_clusters' answer, finding none
    // Tiles from which p is in sight within Chebyshev `radius`: the engine's shadowcast, with
    // walls and every bush cluster but the viewer's own opaque.
    bitboard viewers(vec2 p, int radius) const;
    // viewers(p, radius) & open_for_us off bushes: one shadowcast, no bush cluster needed.
    bitboard sight_off_bushes(vec2 p, int radius) const;
    const bitboard& open_bushes() const; // bushes & open_for_us

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
    bool spawn_steps_drafted() const { return plan_ && header_.spawn_offsets; }
    bool tributes_walked() const { return plan_ && header_.tributes_walked; } // PlanHeader::tributes_walked
    // The drafted spawn and altar steps are a dash's too (PlanHeader::dash_spawn_steps, dash_altar_steps).
    bool dash_spawn_steps_drafted() const { return spawn_steps_drafted() && header_.dash_spawn_steps; }
    bool dash_altar_steps_drafted() const { return plan_ && header_.dash_altar_steps; }
    bool attack_tiles_drafted(int group, int range) const;
    bitboard drafted_attack_tiles(int group, int member, int range) const;
    // Every group: `group`, then the rest by Chebyshev distance between centres, ties by group.
    // Made on first ask; null over 256 groups.
    const std::vector<std::uint8_t>* nearest_groups(int group) const;
    bool nearest_groups_ready(int group) const { return !nearest_.empty() && !nearest_[group].empty(); }
    // The draft's ward tile for working a group, or altar a at groups.size() + a; {-1, -1} if none.
    vec2 drafted_ward(int site) const;

private:
    const DraftPlan* plan_ = nullptr; // matching this map
    PlanHeader header_;
    mutable DraftSteps drafted_; // its enemy steps decoded on first ask
    mutable std::vector<int> attack_first_; // per group, and one past the last: its first member's index over all groups
    mutable std::vector<int> attack_bit_;   // per drafted member: its bush bits' first bit in the plan, or -1 if none sees it
    mutable int attack_indexed_ = 0, attack_next_bit_ = 0; // groups indexed so far; the next one's bush bits
    mutable std::optional<bitboard> open_bushes_, open_off_bushes_;
    mutable std::vector<std::vector<std::uint8_t>> nearest_; // per group, empty until made
    mutable int ward_site_ = -1; // drafted_ward's last answer
    mutable vec2 ward_tile_{-1, -1};
    void index_attack_tiles(int group) const; // through drafted `group`
    // Per tile, row-major, in static storage, which starts zeroed for free: filling a vector costs
    // ~1 fuel a byte. One map per process.
    static constexpr int max_tiles = 100 * 100;
    inline static std::array<std::uint16_t, max_tiles> group_lookup_{}; // group index + 1, or 0
    inline static std::array<std::uint16_t, max_tiles> altar_lookup_{}; // altar index + 1, or 0
    mutable std::optional<Field> ally_field_, enemy_field_;
    mutable std::optional<bitboard> foot_, dash_foot_, landing_dash_foot_;
    mutable std::optional<std::vector<Hop>> hops_;
    mutable std::vector<int> group_hops_;
    mutable int group_hops_next_ = 0;
    mutable bool group_hops_done_ = false, any_group_hop_ = false;
    void add_hop(vec2 from, int altar) const;
    void add_group_hop(int group) const;
    const bitboard& make_foot() const;
    const bitboard& make_dash_foot() const;
    const bitboard& make_landing_dash_foot() const;
    const std::vector<Hop>& make_hops() const;
    mutable std::deque<BushCluster> bush_clusters_; // found so far; references stay valid
    mutable bitboard clustered_;                     // their tiles
    inline static std::array<std::uint16_t, max_tiles> cluster_of_{}; // cluster index + 1, or 0
    // Every cluster is labelled once, then each is built when first asked for (in static storage),
    // in batches priced before they run, so it pauses when the fuel would fall below `fuel_floor`
    // (0: no limit). Returns the cluster it completes, p's unless it finished one begun from another
    // tile, or null if the fuel ran short first.
    const BushCluster* grow_cluster(vec2 p, std::uint64_t fuel_floor) const;
    mutable std::optional<bitboard> near_bushes_;
    const bitboard& make_near_bushes() const;
    const Field& make_ally_field() const;
    const Field& make_enemy_field() const;
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
    static constexpr int end = 64; // a slot after every turn of the round
    int round = 0;
    int slot = -1;
    auto operator<=>(const Moment&) const = default;
};

inline constexpr int home_recall_time = 3;       // turn ends, with a Home emblem
inline constexpr float durability_taken = 0.9f; // damage a Durability emblem's owner takes
inline constexpr float jungle_camp_taken = 0.7f; // camp damage a Jungle emblem's owner takes
inline constexpr float monster_camp_dealt = 1.15f; // damage to camps from a Monster emblem's owner
inline constexpr float treasure_gold = 0.1f;      // gold bonus of a Treasure emblem
inline constexpr float skirmish_dealt = 1.05f;    // damage to champions from a Skirmish emblem's owner
inline constexpr float collectors_dealt = 0.01f;  // extra damage per emblem family (its own included) a Collectors emblem's owner has
inline constexpr int capture_emblem_time = 3;     // capture_time's cap when a Capture emblem's owner holds
inline constexpr int tribute_emblem_cut = 33;     // percent of a tribute's turn ends a Tribute emblem cuts, rounded down
inline constexpr int prospector_part = 4;         // a Prospector emblem's owner gets 1 / this of its share of cluster rewards
inline constexpr int gem_cluster_gems = 7;        // the rules' camp table: what each cluster member pays
inline constexpr int gold_cluster_gold = 20;
inline constexpr int teleport_crystal_range = 3; // Chebyshev, terrain ignored
inline constexpr int altar_lock_range = 2;        // a lock is placed on an altar within this
inline int ward_range() { return static_cast<int>(cambc::constants::ward_placement_radius); }
inline constexpr int ability_cooldown = 8;        // rounds from a cast to the slot's next
inline constexpr int vision_radius = 8;           // a champion's
inline constexpr unsigned shard_price = 30;
inline constexpr unsigned shards_per_emblem = 5; // identical shards that combine
inline constexpr unsigned emblem_price = shards_per_emblem * shard_price;
inline constexpr unsigned greed_shards = 25;      // a Greed emblem's, which then counts as greed_stats shards
inline constexpr unsigned greed_stats = 35;

// A bitboard with no storage, for one that is never read: moved out of a board allocated once.
inline cambc::bitboard no_board() {
    static cambc::bitboard donor{cambc::uninitialized};
    static const cambc::bitboard kept{std::move(donor)};
    return cambc::bitboard{std::move(donor)};
}

struct ChampionBelief {
    ChampionBelief() = default;
    // An ally's: `possible` and `undashed` are only ever read for enemies, so they get no storage
    // (two allocations, ~260 fuel). Copying such a belief would fault, so copies don't compile.
    struct Ally {};
    explicit ChampionBelief(Ally) : possible{no_board()}, undashed{no_board()} {}
    ChampionBelief(const ChampionBelief&) = delete;
    ChampionBelief& operator=(const ChampionBelief&) = delete;
    ChampionBelief(ChampionBelief&&) noexcept = default;
    ChampionBelief& operator=(ChampionBelief&&) noexcept = default;

    cambc::handle_champion_t handle{};
    cambc::champion_type type{};
    team side = team::enemy;
    int index = 0; // position among its team's champions (handle order = pick order)
    bool is_self = false;

    bool alive = true;
    int respawn_earliest = -1; // window for its respawn round while dead
    int respawn_latest = -1;
    int respawned_round = -1; // its respawn turn's round, when known to be this round's

    // Last observation. `visible` means in our vision now; the rest may be stale.
    bool visible = false;
    vec2 pos{-1, -1};
    int pos_round = -1;
    Source pos_source = Source::none;
    float health = 0, max_health = 0, strength = 0, focus = 0;
    float shield = 0;     // a shielder's (Varg, Heart of Ruin) active shield, absorbed before health
    int shield_turns = 0; // its turn ends left
    std::int8_t shield_slot = -1; // enemies' and ours: the shield's slot, read with the cooldowns
    // damage_scale() at `health` times `dealt`, kept with the stats: fights read it often. Camp
    // estimates read it too, a little high for a Skirmish owner.
    float scale = 1;
    int stats_round = -1;
    int gems = 0;
    bool fast_recall = false; // a Home emblem, when last seen: recall takes home_recall_time turn ends
    float taken = 1;          // damage taken per point dealt: durability_taken with a Durability emblem, when last seen
    float dealt = 1;          // damage dealt to champions per point: Skirmish and Collectors emblems, when last seen
    bool fast_tribute = false; // a Tribute emblem, when last seen: tribute_emblem_cut off its tributes
    bool fast_capture = false; // a Capture emblem, when last seen: its holds pay after capture_emblem_time
    bool prospector = false;   // a Prospector emblem, when last seen
    bool acted = false; // had completed its turn when last read this round
    // A stun that will take its next turn, read when first seen this round: nothing but our own
    // casts changes it during our turn (World::read_stuns), though our move may take it out of sight.
    bool stun_pending = false;
    // Turn-order priority for priority_round, and from the round after it.
    int priority = 0, next_priority = 0, priority_round = -1;
    int rank = 0; // place in its team's turn order, from the priorities last read
    int prev_rank = 0; // its rank in the round of our previous update
    int next_rank = 0; // its rank from next round on, by next_priority

    // Abilities: the earliest round each slot could be cast. Exact while visible (read from the
    // engine); through fog, projected with the cooldown rule assuming no unseen cast, so the real
    // round can be later, never earlier, except that a Vendetta kill readies both.
    std::array<int, 2> ready_round{0, 0};

    Channel channel = Channel::none;
    Channel seen_channel = Channel::none; // hidden completion may clear channel while retaining the seen position
    int channel_end_round = -1;
    vec2 tp_dest{-1, -1}; // a visible enemy teleport's destination, when we see it
    // A visible enemy's teleport: it cannot act before channel_end_round, then lands at tp_dest
    // (within 3) unless we stun or kill it first.
    bool teleport_pending() const { return alive && visible && channel == Channel::teleport; }

    // Enemies only: every tile it could be on, from what we have seen and how champions move.
    // Unseen teleports are not modelled. Unread while dead or !tracked. Left uninitialised until
    // the first fix, so never set for allies.
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
    // Farthest tile from which a slot ready in `round` can stun, or -1.
    int ready_stun_reach(int round) const {
        const auto& f = facts();
        int r = -1;
        for (int s = 0; s < 2; ++s)
            if (const int reach = f.stun_reach(s); reach > r && ability_ready(s, round)) r = reach;
        return r;
    }
    // No walking, attacking or casting on the respawn turn.
    bool can_act(int round) const { return alive && round != respawned_round; }
    // Heart of Ruin's multiplier on all its damage at its health; 1 for the rest.
    float damage_scale() const { return scale; }
    // Damage back to whoever hits it (Ren), even as it dies.
    float retaliation() const { return facts().passive == Passive::retaliation ? retaliation_share * focus : 0.0f; }
    // True if an unseen reset could make the abilities ready earlier than ready_round says.
    bool cooldowns_uncertain() const { return !visible && facts().passive == Passive::reset_on_kill; }
    int age(int round) const { return pos_round < 0 ? 1 << 20 : round - pos_round; }
    int recall_turns() const { return fast_recall ? home_recall_time : static_cast<int>(cambc::constants::recall_time); }
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
    StaticArray<float> health;     // per member, last seen; 0 = dead
    StaticArray<int> health_round; // per member: the last round its health was known
    // Groups sleep until damaged; awake while any striking member is, each monster falling asleep
    // after 2 camp phases with no champion within its own range.
    Awake awake = Awake::asleep;
    // Bit i: striking member i read asleep while the group is not. Only damage wakes it, and it
    // wakes every asleep member, so one seen to wake clears them all. Members past 64 count awake.
    std::uint64_t asleep = 0;
    int last_damaged_round = -1; // a health drop we saw
    bool member_asleep(std::size_t i) const { return awake == Awake::asleep || (i < 64 && (asleep >> i & 1)); }
    bool maybe_asleep(std::size_t i) const { return awake != Awake::awake || (i < 64 && (asleep >> i & 1)); }
    // Awake with no striker left asleep: a hit wakes nobody.
    bool fully_awake() const { return awake == Awake::awake && asleep == 0; }
    // Capture in progress: who holds the cleared group's tiles, and the round the hold began
    // (payout at held_since + capture_time + 1).
    std::optional<team> holder;
    int held_since = -1;
    int payout_round() const { return held_since + cambc::constants::capture_time + 1; }
    // Who stood on its tiles when last fully seen: bit i for allies[i], 16 + i for enemies[i].
    std::uint32_t occupants = 0;
    int told_respawn = -1; // the respawn round the team was told through comms
    int cleared_by_us = -1; // the round our own turn killed its last member while we stood on it
    // Changes whenever `state` or `health` does: results computed from them keep while it holds.
    std::uint32_t version = 0;
};

struct AltarBelief {
    bool ally_lock = false, enemy_lock = false;
    int enemy_lock_hits = 0;
    int seen_round = -1;
};

struct Scores {
    int ally = 0, enemy = 0; // tributed gems
};

class World {
public:
    teacher_priority::Enemies priority_start_enemies;
    std::array<cambc::handle_champion_t, 6> priority_start_handles{}; // parallel to priority_start_enemies.units
    // Start of each play turn. The first call also builds the static map.
    void update();
    void observe();
    // After our stunning cast or Marcella's stunning attack: reads stun_pending again for enemies
    // in sight it could have reached, once a turn. True if one changed.
    bool read_stuns();
    std::uint32_t observations = 0; // update() and observe() calls: beliefs change only with one
    // An enemy in sight from p, within r of it, that this turn's reads did not see: our own move
    // revealed it. False at the tile vision was last read from, unless a move refused by a hidden
    // unit (`bumped`) revealed its tile.
    bool revealed(vec2 p, int r, bool bumped = false) const;
    // After our actions: note a group we cleared standing on it, so held from this round.
    void note_turn_end();
    std::uint64_t observe_cost_estimate() const { return 1000 * (allies.size() + enemies.size()); }

    // Merge a teammate's sighting (from comms), with health as a share of max; ignored if not
    // fresher than ours.
    void note_sighting(int enemy_index, vec2 pos, int round, float health);
    // The sighting comms::receive merges after the next update, if any: that enemy is fixed then,
    // so the update does not track it first.
    struct Sighting {
        int enemy = -1;
        vec2 pos{-1, -1};
        int round = -1;
    } expected_sighting, expected_second;
    // A teammate saw the group captured, returning at `respawn_round`.
    void note_capture(int group, int respawn_round);

    void debug_output() const;

    bool ready() const { return static_ != nullptr && self_index < static_cast<int>(allies.size()) && allies[self_index].is_self; }
    const StaticMap& map() const { return *static_; }
    // True if the bot ran out of fuel and resumed in a later round: beliefs are a round old.
    bool is_stale() const { return round_now() != static_cast<std::uint32_t>(round); }
    // Abandons a turn that ran out of fuel at the next costly step (aph::throw_if_stale).
    void throw_if_stale() const {
        if (is_stale()) throw StaleTurn{};
    }

    const ChampionBelief& me() const { return *me_; }
    // An enemy alive and in view, as of the last update or observe.
    bool enemy_seen() const {
        if (!enemy_seen_known_) {
            enemy_seen_ = false;
            for (const auto& e : enemies)
                if (e.alive && e.visible) {
                    enemy_seen_ = true;
                    break;
                }
            enemy_seen_known_ = true;
        }
        return enemy_seen_;
    }
    // Index of the champion's turn in `round`, by its rank then: the current one for this round,
    // that of our previous update for earlier rounds, next_rank for later ones.
    int slot(const ChampionBelief& c, int r) const {
        // Teams alternate one turn at a time, A first in odd rounds; the larger team's extra
        // champions go last.
        const bool ally = c.side == team::ally;
        const int others = ally ? enemy_count_ : ally_count_;
        const bool first = ally == (team_a_ == (r % 2 == 1));
        const int rank = r < round ? c.prev_rank : r == round ? c.rank : c.next_rank;
        return rank < others ? 2 * rank + (first ? 0 : 1) : others + rank;
    }
    int round = 0;
    int first_round = 0; // this instance's first play round

    std::vector<ChampionBelief> allies; // in handle order, self included
    std::vector<ChampionBelief> enemies;
    int self_index = 0;

    std::vector<CampBelief> camps; // parallel to map().groups
    std::uint32_t camps_version = 0; // changes whenever any group's version does
    // f(g) for each group believed alive and awake or maybe awake, in group order.
    template <class F> void each_stirring(F&& f) const {
        for (std::size_t w = 0; w < stirring_.size(); ++w)
            for (std::uint64_t bits = stirring_[w]; bits; bits &= bits - 1)
                f(static_cast<int>(64 * w) + __builtin_ctzll(bits));
    }
    // f(g) for each group believed cleared, in group order.
    template <class F> void each_cleared(F&& f) const {
        for (std::size_t w = 0; w < cleared_.size(); ++w)
            for (std::uint64_t bits = cleared_[w]; bits; bits &= bits - 1)
                f(static_cast<int>(64 * w) + __builtin_ctzll(bits));
    }
    // f(g) for each group believed respawning, in group order, until f returns true.
    template <class F> void each_respawning(F&& f) const {
        for (std::size_t w = 0; w < respawning_.size(); ++w)
            for (std::uint64_t bits = respawning_[w]; bits; bits &= bits - 1)
                if (f(static_cast<int>(64 * w) + __builtin_ctzll(bits))) return;
    }
    std::vector<AltarBelief> altars; // parallel to map().altars
    Scores score;
    // Our tributed gems a round over the later half of the game so far: it follows the economy's
    // growth, unlike the whole game's average.
    float ally_rate() const;
    bitboard visible; // this turn's vision (ours and our ward's)
    // An enemy was seen changing priority: its team's order for next round can change until each
    // has acted, and unseen ones' ranks are guesses.
    bool enemy_priorities_change = false;

private:
    void dump_beliefs() const;
    Moment now() const { return {round, slot(me(), round)}; }
    // Turns the champion takes after `from`, up to and including any in `to`'s slot.
    int turns_between(const ChampionBelief& c, Moment from, Moment to) const;
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
    static void mark_fixed(ChampionBelief& b, Moment when);
    // Adds `turns` of movement to `possible`, ending on landing(); returns whether a dash widened it.
    bool grow(ChampionBelief& b, int turns);
    // Where a growth pruned straight after can end: open to them and out of sight.
    const bitboard& landing();
    // Advance `possible` to now and prune it to unseen tiles; for an enemy of a lineage, copy the
    // result of one of the same lineage and inputs tracked earlier in this pass.
    void track(ChampionBelief& b);
    // `listed`: list_growth() of the board to grow, if it was the last call that listed tiles.
    static void walk(bitboard& tiles, const StaticMap& s, int steps, const bitboard& land, std::uint32_t listed = ~0u);
    static void widen_by_dash(const bitboard& from, bitboard& out, const StaticMap& s, int steps, const bitboard& land,
                              std::uint32_t listed = ~0u);
    // Every change to `possible` but growth goes to `undashed` too.
    static void also_undashed(ChampionBelief& b, const bitboard& tiles);
    void update_camps();
    struct CampViews;
    void update_camp(std::size_t g, bool in_view, CampViews& views);
    int hold_start(const CampGroup& G, team holder, int earliest, bool cleared_by_us) const;
    void update_altars();
    std::uint32_t tributing_enemies() const; // bit i: enemies[i] is believed to be tributing
    void update_scores(std::uint32_t tributing);
    std::vector<int> ally_scores_; // by round

    std::unique_ptr<StaticMap> static_;
    const ChampionBelief* me_ = nullptr; // &allies[self_index], set with the beliefs
    int ally_count_ = 0, enemy_count_ = 0; // allies.size(), enemies.size()
    bool team_a_ = true;                  // map().team_a
    mutable bool enemy_seen_known_ = false, enemy_seen_ = false;
    bitboard unseen_; // ~visible
    bitboard landing_{cambc::uninitialized}; // open_for_them & unseen_, once landing_ready_
    bool landing_ready_ = false;
    vec2 sight_pos_{-1, -1};         // where update() or observe() last looked from
    mutable vec2 clear_pos_{-1, -1}; // where revealed() last found nothing new
    std::vector<std::uint64_t> group_visible_; // update_camps() scratch, bit g
    // Bit g: unseen, update_camps() could still change it (a hold paying out, a return, an
    // awake group's wakefulness going unknown).
    std::vector<std::uint64_t> camps_pending_;
    struct Tracked {
        std::uint32_t before, after;
        int leader, turns, tsf;
        Moment fixed, at;
        bool dasher, dash, fast_recall;
    };
    std::vector<std::uint64_t> stirring_; // bit g: each_stirring() visits group g
    std::vector<std::uint64_t> cleared_;  // bit g: each_cleared() visits group g
    std::vector<std::uint64_t> respawning_; // bit g: each_respawning() visits group g
    void note_stirring(int g);
    std::array<Tracked, 8> tracked_{}; // this pass's track() results
    int tracked_count_ = 0;
    std::uint32_t lineages_ = 0;
    bool ranks_stale_ = true;
    std::array<std::array<std::uint8_t, 16>, 4> turn_order_; // allies', enemies' indices by rank, then by next_rank
    int ranked_round_ = -1;
    int updated_round_ = -1;
    int stuns_read_ = -1;
};

// Cassi or Issac: the other body on its side, whose death is its own; null for anyone else.
inline const ChampionBelief* linked_partner(const World& world, const ChampionBelief& c) {
    if (c.facts().passive != Passive::linked_pair) return nullptr;
    for (const auto& o : c.side == team::ally ? world.allies : world.enemies)
        if (&o != &c && o.facts().passive == Passive::linked_pair) return &o;
    return nullptr;
}

// What its death hands over: both bags for Cassi and Issac.
inline int pair_gems(const World& world, const ChampionBelief& c) {
    const auto* p = linked_partner(world, c);
    return c.gems + (p && p->alive ? p->gems : 0);
}

// Cassi and Issac die together: the visible partner's health, or a huge value.
inline float linked_partner_health(const World& world, const ChampionBelief& e) {
    const auto* p = linked_partner(world, e);
    return p && p->alive && p->visible ? p->health : 1e9f;
}

// Many bots start a recall at every turn end and cancel it next turn unless wanted: only one kept
// through a turn is likely to complete.
inline bool kept_recall(cambc::handle_champion_t c, int full = static_cast<int>(cambc::constants::recall_time)) {
    if (!cambc::champion_state::from_bits_retain(record_of(c).state).contains(cambc::champion_state::recalling)) return false;
    static std::int32_t turns;
    ok(cambc::detail::sdk_champion_channel_time(static_cast<std::uint32_t>(c), &turns));
    return turns < full - 1;
}

inline bool enemy_seen(const World& world) { return world.enemy_seen(); }

// Damage a turn, spells (and dash landings) spread over their cooldown.
inline float raw_output(const ChampionFacts& f, float strength, float focus) {
    float damage = strength;
    for (const auto& a : f.abilities) {
        if (a.kind == AbilityKind::damage || a.lands()) damage += a.multiplier * focus / static_cast<float>(ability_cooldown);
        if (a.kind == AbilityKind::attack_reset) damage += strength / static_cast<float>(ability_cooldown);
    }
    return damage;
}

inline float output(const ChampionBelief& c) { return raw_output(c.facts(), c.strength, c.focus) * c.damage_scale(); }

inline bool enemy_within(const World& world, vec2 p, int r) {
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(p, e.pos) <= r) return true;
    return false;
}

// Of `damage` on a body at `health`, what brings its pair's death closer: only what takes it below
// its partner, for Cassi and Issac.
inline float useful_damage(float damage, float health, float partner) {
    return partner >= health ? damage : std::max(0.0f, damage - (health - partner));
}

} // namespace aph
