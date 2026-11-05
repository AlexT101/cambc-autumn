#pragma once
#include <cambc.h>
#include <array>
#include <cstdint>
#include <deque>
#include <memory>
#include <optional>
#include <type_traits>
#include <utility>
#include <vector>
#include "../champions.h"
#include "../draft/draft.h"
#include "../params.h"
#include "../util.h"

namespace aph {

// Derived static parts are built on first use: all at once costs too much fuel on large maps.
// WASM loops, sorting and hashing are costly; host bitboard and field calls are cheap.

struct StaticMap;

// A vector allocator whose value-initialisation writes nothing: resize(n) leaves the elements for
// the caller to write whole, where constructing each cost ~50-110 fuel a camp group.
template <class T> struct UnwrittenAllocator : std::allocator<T> {
    template <class U> struct rebind {
        using other = UnwrittenAllocator<U>;
    };
    UnwrittenAllocator() = default;
    template <class U> UnwrittenAllocator(const UnwrittenAllocator<U>&) {}
    template <class U, class... Args> void construct(U* p, Args&&... args) {
        if constexpr (sizeof...(Args) > 0) ::new (static_cast<void*>(p)) U(std::forward<Args>(args)...);
    }
};

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
    // In the camp layout's word order (StaticMap::build copies them whole).
    std::uint32_t handle; // engine camp id
    cambc::camp_type type;
    vec2 pos;
    float max_health;
    float strength;
    int reach; // attack range
};

struct CampGroup {
    // User-provided, so a value-initialised group (emplace_back()) skips the zero fill of the whole
    // object before its initialisers (~80 fuel a group).
    CampGroup() {}
    std::uint32_t handle; // engine camp-group id
    StaticArray<CampMember> members;
    vec2 centre;        // the member tile nearest the members' mean position
    // StaticMap::build writes every field below, so none has an initialiser (~45 fuel a group).
    int gold, gems;
    int cluster_gold, cluster_gems; // the gold and gem clusters' part, which a Prospector emblem adds to
    int respawn;    // rounds from capture payout to return
    float strength; // damage per camp phase from all members while awake
    float health;   // the members' max_health summed
    int reach;      // longest member reach
    bool has_monolith;

    cambc::camp camp(int member) const;
    const bitboard& tiles() const;    // camp tiles: stand on one, with no enemy on any, to capture
    const bitboard& adjacent() const; // walkable tiles within 1 of a camp tile, camp tiles excluded
    const bitboard& threat() const;   // tiles within a member's reach of it, where its monsters attack
    // No tile of threat() is farther than this from the centre.
    int threat_radius() const;

private:
    friend struct StaticMap;
    const StaticMap* map_;
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
    std::uint32_t built_round = 0;
    cambc::symmetry symmetry{};
    vec2 mirror(vec2 p) const {
        switch (symmetry) {
        case cambc::symmetry::horizontal: return {width - 1 - p.x, p.y};
        case cambc::symmetry::vertical: return {p.x, height - 1 - p.y};
        default: return {width - 1 - p.x, height - 1 - p.y};
        }
    }
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
    bool foot_made(int dash_kind) const { return (dash_kind == 0 ? foot_ : dash_kind == 1 ? dash_foot_ : landing_dash_foot_).has_value(); }
    // A walk region off foot() that a teleport crystal reaches: from a source tile on foot to a
    // landing tile within its range, terrain ignored, then the walk. One per altar no walk reaches
    // (its `altar`), then one per other region holding a farmed group (`altar` -1).
    struct Hop {
        int altar = -1;
        bitboard sources, landings, pocket; // pocket: the region, camp tiles included
        // The pocket's camp tiles within a crystal's range of our walk: landings too while their group
        // or member is believed dead (teleport_crystal.target; Pathing::teleport_targets).
        bitboard camp_landings;
        // An altar's pocket walled in by camps, not terrain (02the-pack's wolf ring): on foot(), so
        // a walk reads short, but none reaches it while the ring stands. Its sources and landings
        // are judged by the walk with every camp standing; `ring`, the groups walling it in.
        bool camps = false;
        std::vector<int> ring;
    };
    // Whether a hop is a camp hop's; the draft clears it on most maps (PlanHeader::camp_sealed),
    // which then makes neither foot() nor the hops for it.
    bool any_camp_hop() const { return may_camp_seal() && (hops(), camp_hops_); }
    const std::vector<Hop>& hops() const { return hops_ ? *hops_ : make_hops(); }
    // The hop into the region of a farmed group no walk reaches, or -1, and whether any group has
    // one; their hops follow the altars'. On a timetable, so that no turn makes more than one: none
    // on the first turn, our walk on the second, then one more tried group a turn, in group order.
    // The warm-up may make them sooner, but they are read only then.
    int group_hop(int group) const;
    bool any_group_hop() const;
    // Whether group_hop may ever give the group one: static, with no round check.
    bool may_hop(int group) const { return list_hop_tried(), hop_rank_[group] >= 0; }

    // The SDK's own boards, read once at start-up.
    const bitboard& walls = cambc::map::walls();
    const bitboard& holes = cambc::map::holes();
    const bitboard& bushes = cambc::map::bushes();
    const bitboard& altar_tiles = cambc::map::altars();
    const bitboard& ally_spawn = cambc::map::spawn_region(team::ally);
    const bitboard& enemy_spawn = cambc::map::spawn_region(team::enemy);
    bitboard camp_tiles;
    std::vector<vec2> ally_spawn_tiles;
    // Our spawn tiles in the order a recall takes the first free one (recall.landing).
    std::vector<vec2> landing_tiles;
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
    // the landing could wake (travel_landing_veto refuses it).
    bitboard landing_dash_walls{cambc::uninitialized};
    bitboard near_enemy_spawn; // within 1 of an enemy spawn tile
    // blocked_for_them without the hole and altar tiles an enemy dash crosses (crossable's rule, from
    // their standable tiles, unthinned): an enemy dasher's static walls. Made on first ask.
    const bitboard& their_dash_walls() const { return their_dash_walls_ ? *their_dash_walls_ : make_their_dash_walls(); }
    bool their_dash_walls_ready() const { return their_dash_walls_.has_value(); }
    bitboard walls_and_bushes{cambc::uninitialized};
    bitboard standable{cambc::uninitialized}; // ~(camp_tiles | blocked_for_us)

    std::vector<Altar> altars;
    std::vector<CampGroup, UnwrittenAllocator<CampGroup>> groups; // written whole by build()
    StaticArray<CampMember> camp_members; // every group's members in group order: each group's are a slice

    // Group whose camp tile this is, or -1.
    int group_at(vec2 p) const { return static_cast<int>(group_lookup_[tile_index(p)]) - 1; }
    // Altar on this tile, or -1.
    int altar_at(vec2 p) const { return in_bounds(p) ? static_cast<int>(altar_lookup_[tile_index(p)]) - 1 : -1; }
    // Groups with a camp tile within `radius`, seen or not; a scratch vector, valid until the next call.
    const std::vector<int>& groups_near(vec2 p, int radius) const;

    // Walking steps over static terrain (camps and units ignored).
    const Field& from_ally_spawn() const { return ally_field_ ? *ally_field_ : make_ally_field(); }
    bool from_ally_spawn_ready() const { return ally_field_.has_value(); }
    // Steps from the enemy spawn: our field at the mirror tile, as terrain is symmetric and each side's board blocks
    // the other's spawn.
    int enemy_spawn_steps(vec2 p) const { return from_ally_spawn().at(mirror(p)); }
    const BushCluster& bush_cluster(vec2 p) const;
    // Tiles with a bush within ward placement range (2).
    const bitboard& near_bushes() const { return near_bushes_ ? *near_bushes_ : make_near_bushes(); }
    bool near_bushes_ready() const { return near_bushes_.has_value(); }
    // Find every cluster viewers(p, radius) needs while more than `fuel_floor` fuel remains (0: no
    // limit); true once all are. The work carries over between calls.
    bool find_bush_clusters(vec2 p, int radius, std::uint64_t fuel_floor) const;
    bool find_all_bush_clusters(std::uint64_t fuel_floor) const; // the same for the whole map
    bool find_bush_clusters(const bitboard& tiles, std::uint64_t fuel_floor) const; // the same for those with a tile in `tiles`
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
    // enemy_steps for one group, without decoding every group's when the plan mirrors them.
    int enemy_steps_of(int group) const;
    // Every group's drafted enemy steps, as enemy_steps decodes them, with more than `fuel_floor` left;
    // false while they still wait for that (enemy_steps would decode them all at once).
    bool warm_enemy_steps(std::uint64_t fuel_floor) const;
    // Every group's fixed steps (PlanIndex), read one at a time on first ask, with more than `fuel_floor`
    // left; false while some still wait for that.
    bool warm_drafted_steps(std::uint64_t fuel_floor) const;
    // From the draft, when it has them: the steps to a group's centre from the tribute tiles of
    // every altar, and from one of our spawn tiles; a member's attack tiles (Pathing).
    std::optional<int> drafted_altar_steps(int group) const;
    std::optional<int> drafted_spawn_steps(vec2 tile, int group) const;
    // Our body `body`'s steps by a dash of `kind` (ChampionFacts::dash_kind) from `tile`, when the
    // draft sent them for that body, tile and kind. A body asks only for itself.
    std::optional<int> drafted_dash_steps(int body, vec2 tile, int group, int kind) const {
        if (dash_for_ != body) decode_dash_steps(body, kind);
        if (dash_steps_.empty() || tile != dash_tile_) return std::nullopt;
        return dash_steps_[group];
    }
    bool drafted() const { return plan_ != nullptr; }
    bool spawn_steps_drafted() const { return plan_ && header_.spawn_offsets; }
    bool tributes_walked() const { return plan_ && header_.tributes_walked; } // PlanHeader::tributes_walked
    bool may_camp_seal() const { return plan_ ? header_.camp_sealed : true; }  // PlanHeader::camp_sealed
    // The drafted spawn and altar steps are a dash's too (PlanHeader::dash_spawn_steps, dash_altar_steps).
    bool dash_spawn_steps_drafted() const { return spawn_steps_drafted() && header_.dash_spawn_steps; }
    bool dash_altar_steps_drafted() const { return plan_ && header_.dash_altar_steps; }
    bool attack_tiles_drafted(int group, int range) const;
    // Whether drafted_attack_tiles has indexed the group's bits (its block, with checkpoints).
    bool attack_tiles_indexed(int group) const {
        return index_.checkpoints ? (attack_blocks_ >> (group / PlanIndex::block) & 1) != 0 : group < attack_indexed_;
    }
    bitboard drafted_attack_tiles(int group, int member, int range) const;
    // Every group: `group`, then the rest by Chebyshev distance between centres, ties by group.
    // Made on first ask; null over 256 groups.
    const std::vector<std::uint8_t>* nearest_groups(int group) const;
    bool nearest_groups_ready(int group) const { return !nearest_.empty() && !nearest_[group].empty(); }
    // The draft's ward tile for working a group, or altar a at groups.size() + a; {-1, -1} if none.
    vec2 drafted_ward(int site) const;
    // The draft's guesses at our body `body`'s first farm choice (DraftPlan's leads); how many.
    int drafted_leads(int body, std::array<int, DraftPlan::leads>& out) const {
        return plan_ ? aph::drafted_leads(*plan_, header_, static_cast<int>(groups.size()), body, out) : 0;
    }

private:
    const DraftPlan* plan_ = nullptr; // matching this map
    PlanHeader header_;
    mutable DraftSteps drafted_; // its enemy steps decoded on first ask
    // With fixed steps (index_.steps), drafted_'s ally steps are read at build (round 2's group hops
    // read every group's), its enemy and altar steps each on first ask, pending_step until then.
    PlanIndex index_;
    static constexpr std::uint16_t pending_step = 0xFFFE;
    mutable TileBox enemy_box_;
    mutable bool enemy_box_known_ = false;
    mutable std::uint8_t steps_warm_ = 0; // bit k: kind k (PlanIndex) warmed
    mutable std::uint32_t attack_blocks_ = 0; // with checkpoints, bit b: block b's attack tiles are indexed
    std::uint16_t fixed_step(int which, int group) const;
    void fixed_steps(int which) const; // every pending group's, in one pass
    mutable std::vector<int> attack_first_; // per group, and one past the last: its first member's index over all groups
    mutable std::vector<int> attack_bit_;   // per drafted member: its bush bits' first bit in the plan, or -1 if none sees it
    mutable int attack_indexed_ = 0, attack_next_bit_ = 0; // groups indexed so far; the next one's bush bits
    mutable std::optional<bitboard> open_bushes_, open_off_bushes_;
    mutable std::vector<std::vector<std::uint8_t>> nearest_; // per group, empty until made
    mutable int ward_site_ = -1; // drafted_ward's last answer
    mutable vec2 ward_tile_{-1, -1};
    // A body's dash steps, decoded whole on its first ask: its dash and spawn tile never change,
    // and skipping to a group's code costs ~50 fuel a code before it.
    void decode_dash_steps(int body, int kind) const;
    mutable std::vector<int> dash_steps_; // drafted_dash_steps' from dash_tile_, for body dash_for_
    mutable vec2 dash_tile_{-1, -1};
    mutable int dash_for_ = -1;
    void index_attack_tiles(int group) const; // through drafted `group`
    // Per tile, row-major, in static storage, which starts zeroed for free: filling a vector costs
    // ~1 fuel a byte. One map per process.
    static constexpr int max_tiles = 100 * 100;
    inline static std::array<std::uint16_t, max_tiles> group_lookup_{}; // group index + 1, or 0
    inline static std::array<std::uint16_t, max_tiles> altar_lookup_{}; // altar index + 1, or 0
    mutable std::optional<Field> ally_field_;
    mutable std::optional<bitboard> foot_, dash_foot_, landing_dash_foot_;
    mutable std::optional<bitboard> their_dash_walls_;
    const bitboard& make_their_dash_walls() const;
    mutable std::optional<std::vector<Hop>> hops_;
    mutable std::optional<bitboard> barren_; // add_hop's pockets no crystal from foot lands in
    mutable bool camp_hops_ = false;
    mutable std::vector<int> group_hops_;          // by group
    mutable std::vector<int> hop_tried_, hop_rank_; // groups that may have one, in order; by group, its index there or -1
    mutable bool hop_tried_listed_ = false;
    mutable int hops_made_ = 0, first_hop_rank_ = 1 << 30; // hop_tried_ made so far; the first of them given a hop
    void add_hop(vec2 from, int altar) const;
    void add_group_hop(int group, bool off_theirs) const; // off_theirs: known off the enemy's walk
    int hops_readable() const; // hop_tried_ readable this round, -1 on the first turn
    void list_hop_tried() const;
    void make_group_hops(int upto) const; // our walk, then hop_tried_ below `upto`
    const bitboard& make_foot() const;
    void dash_flood(const bitboard& walls, bitboard& out) const;
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
    // Grows the cluster of each tile of `left` (bushes), emptying it; false if the fuel ran short.
    bool grow_clusters(bitboard& left, std::uint64_t fuel_floor) const;
    mutable std::optional<bitboard> near_bushes_;
    const bitboard& make_near_bushes() const;
    const Field& make_ally_field() const;
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
inline constexpr float treasure_gold = 0.1f;      // gold bonus of a Treasure emblem
inline constexpr int capture_emblem_time = 3;     // capture_time's cap when a Capture emblem's owner holds
inline constexpr int tribute_emblem_cut = 33;     // percent of a tribute's turn ends a Tribute emblem cuts, rounded down
inline constexpr int prospector_part = 4;         // a Prospector emblem's owner gets 1 / this of its share of cluster rewards
inline constexpr int gem_cluster_gems = 7;        // the rules' camp table: what each cluster member pays
inline constexpr int gold_cluster_gold = 20;
inline constexpr int teleport_crystal_range = 3; // Chebyshev, terrain ignored
inline constexpr int altar_lock_range = 2;        // a lock is placed on an altar within this
inline int ward_range() { return static_cast<int>(cambc::constants::ward_placement_radius); }
inline constexpr int vision_radius = 8;           // a champion's
inline constexpr int max_camp_range = 5;          // the rules' camp table: a Monolith's, the longest
inline constexpr unsigned shard_price = 30;
inline constexpr unsigned shards_per_emblem = 5; // identical shards that combine
inline constexpr unsigned emblem_price = shards_per_emblem * shard_price;
inline constexpr unsigned greed_shards = 25;      // a Greed emblem's, which then counts as greed_stats shards
inline constexpr unsigned greed_stats = 40;

// A bitboard with no storage, for one that is never read: `kept` takes the donor's allocation, so
// every call moves out of an empty donor.
inline cambc::bitboard no_board() {
    static cambc::bitboard donor{cambc::uninitialized};
    static const cambc::bitboard kept{std::move(donor)};
    return cambc::bitboard{std::move(donor)};
}

// Holes and altars with `standable` tiles on two opposite sides, thinned so that no two touch: the
// tiles a dash jumps, which a field crosses at the dash's two steps (StaticMap::crossable).
// Unthinned (`thin` false), a field may walk along a line of them, but only beside land a walk could take.
void crossing_tiles(const StaticMap& s, const bitboard& standable, bitboard& crossable, bool thin = true);

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
    int respawn_earliest = -1; // while dead, the rounds its respawn may fall in
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
    int shield_end_round = -1; // the round at whose turn start it expires, for unseen champions
    std::int8_t shield_slot = -1; // enemies' and ours: the shield's slot, read with the cooldowns
    // damage_scale() at `health` times `dealt`, kept with the stats: fights read it often. Camp
    // estimates use camp_output (economy/camps.cc) instead.
    float scale = 1;
    int stats_round = -1;
    int hurt_round = -1; // the latest update to see its health fall from a reading within 2 rounds
    int gems = 0;
    bool fast_recall = false; // a Home emblem, when last seen: recall takes home_recall_time turn ends
    float taken = 1;          // damage taken per point dealt: durability_taken with a Durability emblem, when last seen
    float camp_taken = 1;     // camp damage taken per point: `taken` and a Jungle emblem's cut, when last seen
    float dealt = 1;          // damage dealt to champions per point: Skirmish and Collectors emblems, when last seen
    float camp_dealt = 1;     // damage dealt to camps per point: Monster and Collectors emblems, when last seen
    bool fast_tribute = false; // a Tribute emblem, when last seen: tribute_emblem_cut off its tributes
    bool fast_capture = false; // a Capture emblem, when last seen: its holds pay after capture_emblem_time
    bool prospector = false;   // a Prospector emblem, when last seen
    std::array<float, 4> items_key{-1, -1, -1, -1}; // max health, Strength, Focus and (Prism) gems at the last emblem read
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
    Channel seen_channel = Channel::none; // as last seen: `channel` is cleared once believed complete, this is not
    int channel_end_round = -1;
    // Allies only: a recall kept through a turn start when last seen (kept_recall). start_recall's
    // turn-end feint makes nearly every ally read as recalling.
    bool recall_kept = false;
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
    // While in bounds, `possible` (and a dasher's `undashed`) hold exactly this tile, as fix() left them.
    vec2 fixed_tile{-1, -1};
    // Nonzero lineages: possible and undashed equal those of every enemy with the same one.
    std::uint32_t lineage = 0;
    Moment fixed, at; // when `possible` was last known exactly, and when it describes
    int turns_since_fixed = 0;

    const ChampionFacts& facts() const { return aph::facts(type); }
    bool ability_ready(int slot, int round) const { return alive && round >= ready_round[slot]; }
    // Farthest tile from which a slot ready in `round` can stun, or -1; `walk`: after a walk that turn.
    int ready_stun_reach(int round, bool walk = false) const {
        const auto& f = facts();
        int r = -1;
        for (int s = 0; s < 2; ++s)
            if (const int reach = walk ? f.stun_reach_with_walk(s) : f.stun_reach(s); reach > r && ability_ready(s, round)) r = reach;
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
    // Bit i: striking member i read asleep while the group is not. Only damage or a stun wakes
    // it, and either wakes every asleep member, so one seen to wake clears them all. Members past
    // 64 count awake.
    std::uint64_t asleep = 0;
    int last_damaged_round = -1; // a health drop we saw
    // From the last reading in view: a member read asleep then, and the respawn round read.
    int witness = -1, read_respawn = -1;
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
    // camp_settled's last settling: its round, version and update_camps' camp-view count then, and
    // the members in view; the rest is read only once settled_round is set.
    int settled_round = -1;
    std::uint32_t settled_version, settled_view;
    std::uint64_t settled_seen;
    // Not zeroed first, as a value-initialised aggregate would be: round 1 paid ~400 for these fields.
    CampBelief() {}
    CampBelief(StaticArray<float> health, StaticArray<int> health_round) : health{health}, health_round{health_round} {}
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
    // Start of each play turn. The first call also builds the static map.
    void update();
    void observe();
    // After our stunning cast or Marcella's stunning attack: reads stun_pending again for enemies
    // in sight it could have reached, once a turn. True if one changed.
    bool read_stuns();
    std::uint32_t observations = 0; // update() and observe() calls: beliefs change only with one
    // Our tile at update(), where the turn started: observe() moves me().pos with us.
    vec2 turn_start{-1, -1};
    // An enemy in sight from p, within r of it, that this turn's reads did not see: our own move
    // revealed it. False at the tile vision was last read from, unless a move refused by a hidden
    // unit (`bumped`) revealed its tile.
    bool revealed(vec2 p, int r, bool bumped = false) const;
    // After our actions: note a group we cleared standing on it, so held from this round.
    void note_turn_end();

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
    // True if the bot ran out of fuel and resumed in a later round: beliefs are a round old. Never
    // while a decision may finish late (finish_late).
    bool is_stale() const { return round_now() != static_cast<std::uint32_t>(round) && !finish_late(); }
    // Resumed in a later round, finishing late or not.
    bool resumed() const { return round_now() != static_cast<std::uint32_t>(round); }
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

    std::vector<CampBelief, UnwrittenAllocator<CampBelief>> camps; // parallel to map().groups; written whole by init_beliefs
    std::uint32_t camps_version = 0; // changes whenever any group's version does
    // Bit g: group g's version moved since Pathing::live_camps last cleared it.
    mutable std::vector<std::uint64_t> camps_dirty;
    // By group (and 4 lanes past them), the health a clear must deal now: the members' left, all of it
    // while respawning; 0 cleared or with a member unread.
    std::vector<float> clear_health;
    // Group g's version has moved, its belief written: camps_version, camps_dirty and clear_health follow.
    void camp_moved(std::size_t g);
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
    bool camp_settled(const CampGroup& G, CampBelief& c);
    int hold_start(const CampGroup& G, team holder, int earliest, bool cleared_by_us) const;
    void update_altars();
    struct Tributing {
        std::uint32_t mask = 0;     // bit i: enemies[i] is believed to be tributing
        std::array<int, 16> gems{}; // its bag then
    };
    Tributing tributing_enemies() const;
    void update_scores(const Tributing& tributing);
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
    std::uint32_t camp_view_ = 0;              // changes whenever group_visible_'s camp-tile board does
    // Bit g: unseen, update_camps() could still change it (a hold paying out, a return, an
    // awake group's wakefulness going unknown).
    std::vector<std::uint64_t> camps_pending_;
    struct Tracked {
        std::uint32_t before, after;
        int leader, turns, tsf;
        Moment fixed;
        bool dasher, dash, fast_recall;
    };
    std::vector<std::uint64_t> stirring_; // bit g: each_stirring() visits group g
    std::vector<std::uint64_t> cleared_;  // bit g: each_cleared() visits group g
    std::vector<std::uint64_t> respawning_; // bit g: each_respawning() visits group g
    void note_stirring(int g);
    std::array<Tracked, 8> tracked_{}; // this pass's track() results
    int tracked_count_ = 0;
    std::uint32_t lineages_ = 0;
    std::array<bool, 2> ranks_stale_{true, true}; // allies', enemies'
    std::array<std::array<std::uint8_t, 16>, 4> turn_order_; // allies', enemies' indices by rank, then by next_rank
    std::array<int, 2> ranked_round_{-1, -1};
    int updated_round_ = -1;
    int previous_update_ = -1; // updated_round_ before this round's update()
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

// Many bots start a recall at every turn end and cancel it next turn unless wanted: only one kept
// through a turn is likely to complete.
inline bool kept_recall(cambc::handle_champion_t c, int full = static_cast<int>(cambc::constants::recall_time)) {
    if (!cambc::champion_state::from_bits_retain(record_of(c).state).contains(cambc::champion_state::recalling)) return false;
    static std::int32_t turns;
    ok(cambc::detail::sdk_champion_channel_time(static_cast<std::uint32_t>(c), &turns));
    return turns < full - 1;
}

// An ally going home by recall, not on the feint every champion starts at a turn end and cancels
// next turn unless wanted. Ours is read live: a cancel leaves our belief's channel as it was.
inline bool real_recall(const ChampionBelief& a) {
    return a.channel == Channel::recall && (a.is_self ? kept_recall(a.handle, a.recall_turns()) : a.recall_kept);
}

// An ally held by a channel: a tribute, a teleport or a real recall.
inline bool held_by_channel(const ChampionBelief& a) {
    return a.channel == Channel::tribute || a.channel == Channel::teleport || real_recall(a);
}

inline bool enemy_seen(const World& world) { return world.enemy_seen(); }

// Our picks, Cassi and Issac counting once: fixed after the draft.
inline int economy_pick_count(const World& world) {
    static const int count = [&] {
        int picks = 0;
        for (const auto& ally : world.allies) picks += ally.type != cambc::champion_type::issac;
        return picks;
    }();
    return count;
}

// The 3-pick economy roles (Tavi, Stellar, Monster for all) run only on 3-pick maps.
inline bool economy_three(const World& world) { return economy_pick_count(world) == 3; }

// The support pair: the healer (Willow) and the gem carrier it protects (Prism).
inline bool support_healer(const ChampionBelief& c) { return c.facts().heals(); }
inline bool support_protected(const ChampionBelief& c) { return c.facts().passive == Passive::gem_focus; }

// The healer's protected mate: Prism, or Tavi on 3 picks with no Prism.
inline bool support_protected(const World& world, const ChampionBelief& c) {
    if (support_protected(c)) return true;
    static const bool tavi = [&] {
        if (!economy_three(world)) return false;
        for (const auto& a : world.allies)
            if (support_protected(a)) return false;
        return true;
    }();
    return tavi && c.type == cambc::champion_type::tavi;
}

// The support pair, {protected mate, healer}, null where not drafted; found once, as the picks are
// fixed after the draft. A team has at most one of each.
inline std::array<const ChampionBelief*, 2> support_pair(const World& world) {
    static std::array<int, 2> index{-2, -2};
    if (index[0] == -2) {
        index = {-1, -1};
        for (int i = 0; i < static_cast<int>(world.allies.size()); ++i) {
            if (support_protected(world, world.allies[i])) index[0] = i;
            if (support_healer(world.allies[i])) index[1] = i;
        }
    }
    std::array<const ChampionBelief*, 2> pair{};
    for (int i = 0; i < 2; ++i)
        if (index[i] >= 0) pair[i] = &world.allies[index[i]];
    return pair;
}

inline float output(const ChampionBelief& c) { return c.facts().raw_output(c.strength, c.focus) * c.damage_scale(); }

// Damage dealt (before its Durability) that kills it: the shield drains by the reduced damage
// before health does.
inline float effective_hp(const ChampionBelief& c) { return (c.health + c.shield) / c.taken; }

// Our active shield and our health with it, read now: a shield absorbs camp hits and Ren's
// retaliation too.
inline float my_live_shield(const World& world) {
    const auto& me = world.me();
    return me.shield_slot >= 0 ? shield_value(me.handle) : 0.0f;
}
inline float my_health_and_shield(const World& world) { return my_health() + my_live_shield(world); }

// A self-shield's amount at its last-read Focus (Varg, Heart of Ruin); 0 without one.
inline float self_shield_amount(const ChampionBelief& c) {
    const int slot = c.facts().slot_of(AbilityKind::shield);
    return slot < 0 ? 0.0f : c.facts().abilities[slot].multiplier * c.focus;
}

inline bool enemy_within(const World& world, vec2 p, int r) {
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(p, e.pos) <= r) return true;
    return false;
}

// Of `damage` on a body at `health`, what brings its pair's death closer: only what takes it below
// `partner`, for Cassi and Issac (partner_bound: the partner's health while it is a route to the kill).
inline float useful_damage(float damage, float health, float partner) {
    return partner >= health ? damage : std::max(0.0f, damage - (health - partner));
}

} // namespace aph
