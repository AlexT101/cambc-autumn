// Live routes treat the units we see as standing still: walk one step, then replan. A host
// search costs a fixed setup plus a little per layer, not per tile, so routes run in full.
#pragma once
#include <cambc.h>
#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <vector>
#include "../util.h"

namespace aph {

// Extra steps a live route may take over the static walking distance.
inline constexpr int max_detour = 16;

class World;
class Safety;
struct StaticMap;

// Tiles a dash from `from` can land on: <= 2 king steps not through walls or camps, onto a free
// tile; off `also` too when given.
// A scratch board, valid until the next call.
const bitboard& dash_landings_from(const StaticMap& map, vec2 from, const bitboard* also = nullptr);

class Pathing {
public:
    explicit Pathing(const World& world);

    void begin_turn();

    const Field& to_ally_spawn();
    const Field& to_altar(int altar); // goals: the altar's tribute tiles
    const Field& to_any_altar();
    int centre_to_altar(int group); // to_any_altar() at the group's centre, kept once read
    int centre_to_spawn(int group); // steps from the group's centre to our spawn's centre tile, kept once read
    const Field& to_hop(int hop);   // goals: StaticMap::hops[hop]'s source tiles
    int hop_landing_steps(int hop); // the walk from its nearest landing tile to its altar, kept once read
    const Field& from_landings(int hop); // goals: StaticMap::hops[hop]'s landing tiles
    bool hop_ready(int hop) const;       // to_hop and from_landings made
    const Field& to_group(int group);    // goals: the group's camp tiles
    // Static steps to tiles within `range` of the group's camp tiles, around the camps believed alive:
    // the walk to its attack tiles but for sight lines near the end. Range 0: onto its camp tiles, to
    // capture. Null if no walk reaches it within the search's cap.
    const Field* approach(int group, int range);
    // approach(), or null without searching if the search could take the fuel below `fuel_floor`
    // (then approach_skipped() until the next call).
    const Field* prepare_approach(int group, int range, std::uint64_t fuel_floor);
    bool approach_skipped() const { return approach_skipped_; }
    bool approach_ready(int group, int range); // usable from here without a search
    std::uint64_t approach_cost(int group, int range); // 0 when ready
    // Width + height layers: below approach_cost() once walk_cap() has grown.
    static std::uint64_t max_approach_cost() { return search_cost_estimate(cambc::map::width() + cambc::map::height()); }
    // Walking steps from the centre of a group worth farming (a reward, no Monolith): by symmetry,
    // from anywhere to it. from_centre() is null until one is made; centre_field() makes it (at most
    // a full field), null only for a group not farmed.
    const Field* from_centre(int group);
    const Field* centre_field(int group);
    // Walkable tiles from which a basic attack reaches and sees the member, camp tiles included.
    const bitboard& member_attack_tiles(int group, int member, int range);
    // Over the members believed alive; off camp tiles, but for those of its dead members.
    void attack_tiles(int group, int range, bitboard& out);
    // Compute attack_tiles' missing parts while more than `fuel_floor` remains; true once cached.
    bool prepare_attack_tiles(int group, int range, std::uint64_t fuel_floor);
    // The same for the members in `members` (bit i: member i), alive or not.
    bool prepare_member_tiles(int group, int range, std::uint32_t members, std::uint64_t fuel_floor);
    bool prepare_member(int group, int member, int range, std::uint64_t fuel_floor);
    // Precompute while more than `fuel_floor` remains; true once everything is cached.
    bool warm_up(int attack_range, std::uint64_t fuel_floor);
    // A field capped at centre_cap() has a bounded cost, so it may go down to last_reserve above
    // what `fuel_floor` keeps beyond end_reserve.
    // `near`: a group whose nearest groups go first.
    bool warm_centres(std::uint64_t fuel_floor, int near = -1);

    // Our static fields' walls, and what they leave walkable from our spawn: a dasher's leave out
    // the hole and altar lines a dash crosses.
    const bitboard& static_walls() const;
    const bitboard& foot() const;
    const bitboard& live_camps(); // members believed alive
    // Changes whenever a tile of live_camps() does, as of its last call.
    std::uint32_t live_flips() const { return live_flips_; }
    // Static walls, visible units and teleport reservations, and tiles bumped this round.
    const bitboard& blocked();
    void occupied_into(bitboard& out); // blocked() with our own tile set
    void invalidate(); // after we move or dash

    // A hidden blocker fails a move without spending the walk; the other first steps are tried,
    // then the route is replanned.
    // An optional aim breaks equal-distance ties, retaining compass order for equal aim distance.
    bool step_towards(const bitboard& goals, const bitboard* avoid = nullptr, int max_steps = unreachable, std::optional<vec2> aim = std::nullopt);
    // The same, without avoid, aim or make_way, searching as deep as the fuel above `fuel_floor` pays for.
    bool step_towards_funded(const bitboard& goals, std::uint64_t fuel_floor);
    // A live route within `max_detour` of the static distance, else greedy descent of the field.
    bool step_towards(const Field& field, const bitboard* avoid = nullptr, std::optional<vec2> aim = std::nullopt);
    // Cheap fallbacks without a search, when fuel is short: a step down the field, or one that
    // gets closer to the target as the crow flies.
    bool descend(const Field& field, const bitboard* avoid = nullptr, std::optional<vec2> aim = std::nullopt);
    bool step_closer(vec2 target, const bitboard* avoid = nullptr, std::optional<vec2> aim = std::nullopt);
    // False, spending nothing, if illegal, guarded or blocked by a hidden unit; `refused`: set
    // unless a hidden unit was the reason.
    bool try_move(vec2 tile, bool* refused = nullptr);
    // A hidden unit refused a move since the last call: it is in sight now.
    bool take_bump() { const bool b = bumped_new_; bumped_new_ = false; return b; }
    // Tiles no step or dash may end on until cleared: routes go around them.
    void set_guard(const bitboard* guard) { guard_ = guard, guard_fn_ = nullptr; }
    // A guard worked out on first need, from inputs read now: a turn that never steps skips it.
    using GuardFn = const bitboard* (*)(const World&, Safety&, vec2 here, int radius);
    // `cover`, if given, returns a superset of the tiles `fn` could guard (null: none), for less.
    void defer_guard(GuardFn fn, Safety& safety, vec2 here, int radius, GuardFn cover = nullptr) {
        guard_ = nullptr, guard_fn_ = fn, guard_safety_ = &safety, guard_here_ = here, guard_radius_ = radius, guard_cover_ = cover;
    }
    // While the guard is deferred with a cover, true with `out` the cover; false otherwise.
    bool guard_cover(const bitboard*& out) const {
        if (!guard_fn_ || !guard_cover_) return false;
        out = guard_cover_(world_, *guard_safety_, guard_here_, guard_radius_);
        return true;
    }
    const bitboard* guard() const {
        if (guard_fn_) {
            const auto fn = guard_fn_;
            guard_fn_ = nullptr;
            guard_ = fn(world_, *guard_safety_, guard_here_, guard_radius_);
        }
        return guard_;
    }
    // The guard as set, deferred or not, to put back without working it out.
    struct GuardState {
        const bitboard* guard;
        GuardFn fn;
    };
    GuardState held_guard() const { return {guard_, guard_fn_}; }
    void restore_guard(const GuardState& s) { guard_ = s.guard, guard_fn_ = s.fn; }

    // Unseen units can still block these.
    const bitboard& dash_landings(); // <= 2 king steps not through walls or camps, onto a free tile, off the guard
    // Free open or bush tiles within 3, off the enemy spawn and live camps: a camp tile only of a group
    // believed cleared or respawning (not yet due, unless seen empty) with no camp in sight on it.
    bitboard teleport_targets();

private:
    vec2 my_pos(); // our tile, read again after invalidate() or in a new round
    struct Neighbours {
        std::array<vec2, 8> tiles;
        int count = 0;
        const vec2* begin() const { return tiles.data(); }
        const vec2* end() const { return tiles.data() + count; }
    };
    // p is on the board, off `walls`, `avoid` and the guard.
    bool steppable(vec2 p, const bitboard& walls, const bitboard* avoid) const;
    // Free neighbours that get strictly closer on a static field, nearest first.
    Neighbours closer_neighbours(const Field& field, const bitboard* avoid = nullptr, std::optional<vec2> aim = std::nullopt);
    struct Route {
        int steps = unreachable; // 0: already on a goal; unreachable: none within the cap
        int count = 0;
        std::array<vec2, 8> first_steps; // the first `count`: all equally short, compass order unless aimed
    };
    Route route(const bitboard& goals, const bitboard* avoid = nullptr, int max_steps = unreachable, std::optional<vec2> aim = std::nullopt);
    // The latest route's search: its distances from the goals, and whether it found no way
    // although it stopped short of its cap, so that no wider search finds one either.
    cambc::distance_field route_field_;
    bool route_exhausted_ = false;
    // Where a failed search last found us enclosed (enclosed()).
    vec2 pocket_at_{-1, -1};
    static constexpr int pocket_radius = 16;
    // No goal within the walkable region around us, which ends within pocket_radius, and no ally beside us.
    bool enclosed(const bitboard& walls, const bitboard& goals, vec2 me);
    // The latest search that found a way, with its goals and walls: complete below `layer`, the
    // layer that reached us.
    struct KeptRoute {
        cambc::distance_field field;
        bitboard goals{cambc::uninitialized}, walls{cambc::uninitialized};
        int layer = -1;
    } kept_route_;
    // Our steps in k if a search over `walls` would label every tile below them as k's did.
    static int kept_steps(const KeptRoute& k, const bitboard& goals, const bitboard& walls, vec2 me, int cap);
    // Two allies head-on with no way past: the one with fewer gems (ties: lower champion) backs off.
    // Right after a route that found no way, with the same arguments: read from its field.
    // Leaves route_exhausted_ set only if no ally's tile, freed, opens a way at any cap.
    bool make_way(const bitboard& goals, const bitboard* avoid, int max_steps);
    // `make`: the centre field or our spawn's field is made if missing, so the steps do not depend
    // on what the warm-up made; estimates read only what is there.
    int approach_steps(int group, int range, bool make);
    bool approach_skipped_ = false;
    // Layers an approach search may run when no field bounds the walk: width + height, doubled each
    // time a search is cut off at it (winding maps walk farther).
    int walk_cap() const;
    int walk_cap_ = 0;
    const Field* search_approach(int group, int range, int steps); // approach() once known not ready
    using Slot = std::optional<Field>;
    const Field& cached(Slot& slot, const bitboard& goals);
    void make_centre(Slot& slot, int group); // capped at centre_cap(), doubled until whole
    void grow_centre(Slot& slot, int group); // one capped try: the field, or the cap doubled
    Slot& altar_slot(int altar);
    struct Approach {
        Field field;
        bitboard camps; // the live camp tiles it walks around
        std::uint32_t flips = 0; // live_flips() when made
    };
    std::unique_ptr<Approach>& approach_slot(int group, int range);
    // approach_ready's latest answer, reused for the same slot, round and tile.
    struct ReadyCheck {
        const Approach* slot = nullptr;
        int round = -1;
        vec2 at{-1, -1};
        bool ready = false;
    } ready_check_;
    std::unique_ptr<Approach> spare_approach_; // a replaced one, refilled by the next search
    std::optional<bitboard>& attack_slot(int group, int member, int range);
    const StaticMap& map() const;
    bool farmed(int group) const; // farm reads only groups with a reward and no monolith
    // Layers to cap its centre field at, doubled after a field cut short; 0: uncapped (no draft plan).
    int& centre_cap(int group);

    const World& world_;
    Slot any_altar_;
    Slot ally_spawn_;
    std::vector<std::optional<int>> centre_to_altar_, centre_to_spawn_;
    Slot spawn_centre_; // from our spawn's centre tile
    std::vector<Slot> altar_fields_, centre_fields_, hop_fields_, landing_fields_, group_fields_;
    std::vector<std::optional<int>> hop_landing_steps_;
    std::vector<int> centre_caps_;
    std::vector<std::vector<std::unique_ptr<Approach>>> approach_fields_; // by range, then group
    bitboard live_camps_;
    std::uint32_t live_camps_version_ = ~0u; // the World::camps_version it was built for
    std::vector<std::uint32_t> live_versions_; // per group: the CampBelief::version written
    std::vector<std::uint64_t> live_members_;  // per group: bit i, member i written alive
    std::uint32_t live_flips_ = 0;
    void draw_all_camps();
    bool centres_ready_ = false;
    int warm_group_ = 0, warm_member_ = 0; // warm_up's progress through the attack tiles
    // By attack range, then group, then member.
    std::vector<std::vector<std::vector<std::optional<bitboard>>>> attack_tiles_;
    // Kept between rebuilds: allocating a board costs more than filling it.
    bitboard blocked_{cambc::uninitialized};
    bool blocked_fresh_ = false;
    bitboard bumped_;
    bool bumped_any_ = false, bumped_new_ = false;
    mutable const bitboard* guard_ = nullptr;
    mutable GuardFn guard_fn_ = nullptr;
    GuardFn guard_cover_ = nullptr;
    Safety* guard_safety_ = nullptr;
    vec2 guard_here_{-1, -1};
    int guard_radius_ = 1;
    int bumped_round_ = -1;
    vec2 pos_;
    std::uint32_t pos_round_ = 0;
    bool pos_fresh_ = false;
    unsigned dashes_seen_ = 0; // outside_dashes() when our tile was last read
};

} // namespace aph
