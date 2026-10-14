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
// WASM loops cost ~10 fuel per iteration (sorting 120 pairs ~45k, an unordered_map ~70k); host
// bitboard and field calls ~30-350 each. Prefer host operations; avoid sorting and hashing.

struct StaticMap;

struct Altar {
    vec2 pos;
    int mirror = -1; // index of the symmetric altar (itself if on the axis)

    const bitboard& tribute_tiles() const; // walkable for us within tribute range (1)
    const bitboard& lock_tiles() const;    // walkable for us within 2: where a lock can be placed from
    int ally_steps() const;  // our walking steps from our spawn to the nearest tribute tile
    int enemy_steps() const; // the enemy's from their spawn

private:
    friend class World;
    friend struct StaticMap;
    const StaticMap* map_ = nullptr;
    mutable std::optional<bitboard> tribute_, lock_;
    mutable std::optional<int> ally_steps_, enemy_steps_;
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
    std::vector<CampMember> members;
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
    int ally_steps() const;  // our walking steps from our spawn to stand on a camp tile
    int enemy_steps() const; // the enemy's from their spawn

private:
    friend class World;
    friend struct StaticMap;
    const StaticMap* map_ = nullptr;
    mutable std::optional<bitboard> tiles_, adjacent_, threat_;
    mutable std::optional<int> ally_steps_, enemy_steps_;
};

// An edge-connected set of bush tiles (diagonal bushes are separate clusters). From inside a
// cluster it is see-through, within the usual vision square; from outside you see none of it.
struct BushCluster {
    bitboard tiles;
    int size = 0;
};

struct StaticMap {
    int width = 0, height = 0;
    cambc::symmetry symmetry{};
    bool team_a = true; // team A starts odd rounds; B starts even rounds and wins a full tie

    bitboard walls, holes, bushes, altar_tiles, camp_tiles;
    bitboard ally_spawn, enemy_spawn;
    std::vector<vec2> ally_spawn_tiles, enemy_spawn_tiles;
    vec2 ally_spawn_centre, enemy_spawn_centre;

    bitboard impassable;       // walls | holes | altars: nobody walks or lands there
    bitboard blocked_for_us;   // impassable | enemy spawn: static walls for our walking
    bitboard blocked_for_them; // impassable | our spawn

    std::vector<Altar> altars;
    std::vector<CampGroup> groups;

    vec2 mirror(vec2 p) const;
    bitboard mirror(const bitboard& b) const;
    int group_at(vec2 p) const; // group whose camp tile this is, or -1
    int altar_at(vec2 p) const; // altar on this tile, or -1
    bool walkable(vec2 p) const { return in_bounds(p) && !blocked_for_us.is_set(p); }

    // Walking steps over static terrain (camps and units ignored).
    const Field& from_ally_spawn() const;
    const Field& from_enemy_spawn() const;
    const BushCluster& bush_cluster(vec2 p) const;
    // Tiles from which p is in sight within Chebyshev `radius`: the engine's shadowcast, with
    // walls and every bush cluster but the viewer's own opaque.
    bitboard viewers(vec2 p, int radius) const;

    // Compute derived parts while more than `fuel_floor` fuel remains; true once all are done.
    bool warm_up(std::uint64_t fuel_floor) const;

private:
    friend class World;
    std::vector<std::uint8_t> group_lookup_; // per tile, row-major: group index + 1, or 0
    mutable std::optional<Field> ally_field_, enemy_field_;
    mutable std::deque<BushCluster> bush_clusters_; // found so far; references stay valid
    mutable std::optional<bitboard> diagonal_links_;
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

    // Last observation. `visible` means in our vision now; the rest may be stale.
    bool visible = false;
    vec2 pos{-1, -1};
    int pos_round = -1;
    Source pos_source = Source::none;
    float health = 0, max_health = 0, strength = 0, focus = 0;
    int stats_round = -1;
    int gems = 0;
    int gems_round = -1;
    int items = 0;
    bool fast_recall = false; // a Home emblem, when last seen: recall takes home_recall_time turn ends
    bool acted = false; // had completed its turn when last read this round
    // Turn-order priority for priority_round, and from the round after it.
    int priority = 0, next_priority = 0, priority_round = -1;
    int rank = 0; // place in its team's turn order, from the priorities last read

    // Abilities: the earliest round each slot could be cast. Exact while visible (read from the
    // engine); through fog, projected with the cooldown rule assuming no unseen cast, so the real
    // round can be later, never earlier, except that Vendetta resets hers by killing anything.
    std::array<int, 2> ready_round{0, 0};
    std::array<int, 2> last_cast_round{-1, -1}; // inferred from the cooldown jumping up

    Channel channel = Channel::none;
    int channel_end_round = -1;

    // Enemies only: every tile it could be on, from what we have seen and how champions move.
    // Teleport crystals are not modelled. Empty while dead; anywhere while !tracked.
    bitboard possible;
    bool tracked = false;
    Moment fixed, at; // when `possible` was last known exactly, and when it describes
    int turns_since_fixed = 0;

    const ChampionFacts& facts() const { return aph::facts(type); }
    bool ability_ready(int slot, int round) const { return alive && round >= ready_round[slot]; }
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
    std::vector<float> health; // per member, last seen; 0 = dead
    int health_round = 0;
    // Groups sleep until damaged and fall asleep after 2 camp phases with no champion within 3.
    Awake awake = Awake::asleep;
    int last_damaged_round = -1; // a health drop we saw
    int quiet_rounds = 0;        // consecutive fully observed rounds with no champion within 3
    // Capture in progress: who holds the cleared group's tiles, and the round the hold began
    // (payout at held_since + capture_time + 1).
    std::optional<team> holder;
    int held_since = -1;
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
    // Generous: 0.5-0.75k per champion measured.
    std::uint64_t observe_cost_estimate() const { return 1000 * (allies.size() + enemies.size()); }

    // Merge a teammate's sighting (from comms); ignored if not fresher than ours.
    void note_sighting(int enemy_index, vec2 pos, int round);

    void debug_output() const;
    void dump_beliefs() const;

    bool ready() const { return static_ != nullptr && self_index < static_cast<int>(allies.size()) && allies[self_index].is_self; }
    const StaticMap& map() const { return *static_; }
    // True if the bot ran out of fuel and resumed in a later round: beliefs are a round old.
    bool is_stale() const { return cambc::round_number() != static_cast<std::uint32_t>(round); }

    const ChampionBelief& me() const { return allies[self_index]; }
    // Index of the champion's turn in `round`, by its current rank.
    int slot(const ChampionBelief& c, int round) const;
    Moment now() const { return {round, slot(me(), round)}; }
    // Turns the champion takes strictly between two moments.
    int turns_between(const ChampionBelief& c, Moment from, Moment to) const;
    int round = 0;
    int first_round = 0; // this instance's first play round
    std::optional<DraftPlan> plan;

    std::vector<ChampionBelief> allies; // in handle order, self included
    std::vector<ChampionBelief> enemies;
    int self_index = 0;

    std::vector<CampBelief> camps; // parallel to map().groups
    std::vector<AltarBelief> altars; // parallel to map().altars
    std::vector<WardSighting> enemy_wards;
    Scores score;
    bitboard visible; // this turn's vision (ours and our ward's)

private:
    void build_static();
    void init_beliefs();
    void rank_turns();
    void update_champions(bool full);
    void update_champion(ChampionBelief& b, bool full);
    static void fix(ChampionBelief& b, bitboard tiles, Moment when);
    void advance(ChampionBelief& b);
    void update_camps();
    int hold_start(const CampGroup& G, team holder) const;
    void update_altars();
    void update_wards();
    std::uint32_t tributing_enemies() const; // bit i: enemies[i] is believed to be tributing
    void update_scores(std::uint32_t tributing);

    std::unique_ptr<StaticMap> static_;
    bool ranks_stale_ = true;
};

} // namespace aph
