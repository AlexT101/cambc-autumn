// Pathing: thin wrappers over the SDK's host-side distance fields and reachability. Danger and
// preferences belong to decision code, which passes extra tiles to avoid or orders first steps.
//
// Static fields are exact over terrain and cached. Live routes are exact over terrain plus the
// units we see, as if they stood still: walk one step, then replan. A host search costs a fixed
// setup plus a little per layer (search_cost_estimate), not per tile, so routes run in full.
#pragma once
#include <cambc.h>
#include <cstdint>
#include <memory>
#include <optional>
#include <vector>
#include "util.h"

namespace aph {

class World;
struct StaticMap;

class Pathing {
public:
    explicit Pathing(const World& world);

    // Drop per-turn caches. Call at the start of every turn.
    void begin_turn();

    // ----- Static fields (our walking rules: no walls, holes, altars or enemy spawn) -----
    const Field& to_ally_spawn();
    const Field& to_altar(int altar); // goals: the altar's tribute tiles
    const Field& to_any_altar();
    const Field& to_group(int group); // goals: the group's camp tiles, to stand on and capture
    // Walkable tiles, off camp tiles, from which a basic attack of `range` reaches the member and
    // sees it. Static, so cached.
    const bitboard& member_attack_tiles(int group, int member, int range);
    // The same for every member believed alive: where to stand to attack the group now.
    bitboard attack_tiles(int group, int range);
    // Compute the fields and tiles a champion with this attack range is likely to need, while
    // more than `fuel_floor` fuel remains; true once all are cached.
    bool warm_up(int attack_range, std::uint64_t fuel_floor);

    struct Nearest {
        int steps = unreachable; // unreachable: no goal within the cap
        std::vector<vec2> tiles; // the goal tiles at that distance
    };
    // Walking steps over static terrain (units ignored) to the nearest goal tile. One search that
    // stops at the first goal, so it costs by distance rather than by goal count.
    Nearest nearest(const bitboard& goals, int max_steps = unreachable);

    // ----- Per-turn routing -----
    // Static walls | visible champions, camps and teleport reservations | tiles bumped this round,
    // minus our own tile. Cached until invalidate().
    const bitboard& blocked();
    // Forget cached live state; the movement helpers call this themselves after a move.
    void invalidate();
    // Free neighbours that get strictly closer on a static field, nearest first.
    std::vector<vec2> closer_neighbours(const Field& field, const bitboard* avoid = nullptr);

    struct Route {
        int steps = unreachable;      // 0: already on a goal; unreachable: none within the cap
        std::vector<vec2> first_steps; // every first step of a shortest route, in compass order
    };
    // Shortest live routes to any open goal tile, at most `max_steps` long.
    Route route(const bitboard& goals, const bitboard* avoid = nullptr, int max_steps = unreachable);

    // One walking step along a shortest live route; false if no step was taken. A hidden blocker
    // fails the move without spending the walk: the tile is remembered, the route's other first
    // steps (equally short) are tried, then the route is replanned.
    bool step_towards(const bitboard& goals, const bitboard* avoid = nullptr, int max_steps = unreachable);
    bool step_towards(vec2 target, const bitboard* avoid = nullptr);
    // As above towards the field's goals, allowing a detour of `max_detour` steps over the static
    // distance. Without such a route, or the fuel for it, descend the static field greedily.
    bool step_towards(const Field& field, const bitboard* avoid = nullptr, int max_detour = 16);
    // Walk to an adjacent tile; false (spending nothing) if illegal or blocked by a hidden unit.
    bool try_move(vec2 tile);

    // ----- Legal destinations from our tile; unseen units can still block them -----
    bitboard dash_landings();    // <= 2 king steps not through walls or camps, onto a free tile
    bitboard teleport_targets(); // free open or bush tiles within 3, not camp tiles or enemy spawn
    bitboard ward_targets();     // within 2, not wall, hole, altar, enemy spawn or one of our wards

private:
    using Slot = std::unique_ptr<Field>; // empty until computed
    const Field& cached(Slot& slot, const bitboard& goals);
    Slot& altar_slot(int altar);
    Slot& group_slot(int group);
    const StaticMap& map() const;

    const World& world_;
    Slot any_altar_;
    std::vector<Slot> altar_fields_, group_fields_;
    // By attack range, then group, then member; empty until computed.
    std::vector<std::vector<std::vector<std::optional<bitboard>>>> attack_tiles_;
    std::optional<bitboard> blocked_;
    bitboard bumped_;
    int bumped_round_ = -1;
};

} // namespace aph
