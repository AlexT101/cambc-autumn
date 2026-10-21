// Live routes treat the units we see as standing still: walk one step, then replan. A host
// search costs a fixed setup plus a little per layer, not per tile, so routes run in full.
#pragma once
#include <cambc.h>
#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <vector>
#include "util.h"

namespace aph {

// Extra steps a live route may take over the static walking distance.
inline constexpr int max_detour = 16;

class World;
struct StaticMap;

// Tiles a dash from `from` can land on: <= 2 king steps not through walls or camps, onto a free
// tile; off `also` too when given.
bitboard dash_landings_from(const StaticMap& map, vec2 from, const bitboard* also = nullptr);

class Pathing {
public:
    explicit Pathing(const World& world);

    void begin_turn();

    const Field& to_ally_spawn();
    const Field& to_altar(int altar); // goals: the altar's tribute tiles
    const Field& to_any_altar();
    int centre_to_altar(int group); // to_any_altar() at the group's centre, kept once read
    const Field& to_hop(int hop);   // goals: StaticMap::hops[hop]'s source tiles
    int hop_landing_steps(int hop); // the walk from its nearest landing tile to its altar, kept once read
    // Static steps to tiles within `range` of the group's camp tiles, around the camps believed alive:
    // the walk to its attack tiles but for sight lines near the end. Range 0: onto its camp tiles, to
    // capture. Null if no walk reaches it within the search's cap.
    const Field* approach(int group, int range);
    // approach(), or null without searching if the search could take the fuel below `fuel_floor`.
    const Field* prepare_approach(int group, int range, std::uint64_t fuel_floor);
    bool approach_ready(int group, int range); // usable from here without a search
    std::uint64_t approach_cost(int group, int range); // 0 when ready
    static std::uint64_t max_approach_cost() { return search_cost_estimate(cambc::map::width() + cambc::map::height()); }
    // Walking steps from the centre of a group worth farming (a reward, no Monolith): by symmetry,
    // from anywhere to it. Null until warmed up; centres_ready() once all are.
    const Field* from_centre(int group);
    bool centres_ready() const { return centres_ready_; }
    // Walkable tiles from which a basic attack reaches and sees the member, camp tiles included.
    const bitboard& member_attack_tiles(int group, int member, int range);
    // Over the members believed alive; off camp tiles, but for those of its dead members.
    void attack_tiles(int group, int range, bitboard& out);
    // Compute attack_tiles' missing parts while more than `fuel_floor` remains; true once cached.
    bool prepare_attack_tiles(int group, int range, std::uint64_t fuel_floor);
    // The same for the members in `members` (bit i: member i), alive or not.
    bool prepare_member_tiles(int group, int range, std::uint32_t members, std::uint64_t fuel_floor);
    // Precompute while more than `fuel_floor` remains; true once everything is cached.
    bool warm_up(int attack_range, std::uint64_t fuel_floor);
    // The centre fields first: until they are ready, farm builds a field from wherever we stand.
    // A field capped at centre_cap() has a bounded cost, so it may go down to last_reserve.
    bool warm_centres(std::uint64_t fuel_floor);

    // Our static fields' walls: a dasher's leave out the hole and altar lines a dash crosses.
    const bitboard& static_walls() const;
    const bitboard& foot() const;
    const bitboard& live_camps(); // members believed alive
    // Static walls, visible units and teleport reservations, and tiles bumped this round.
    const bitboard& blocked();
    void occupied_into(bitboard& out); // blocked() with our own tile set
    void invalidate(); // after we move or dash

    // A hidden blocker fails a move without spending the walk; the other first steps are tried,
    // then the route is replanned.
    bool step_towards(const bitboard& goals, const bitboard* avoid = nullptr, int max_steps = unreachable);
    bool step_towards_funded(const bitboard& goals, std::uint64_t fuel_floor);
    // A live route within `max_detour` of the static distance, else greedy descent of the field.
    bool step_towards(const Field& field, const bitboard* avoid = nullptr);
    // Cheap fallbacks without a search, when fuel is short: a step down the field, or one that
    // gets closer to the target as the crow flies.
    bool descend(const Field& field, const bitboard* avoid = nullptr);
    bool step_closer(vec2 target, const bitboard* avoid = nullptr);
    // False, spending nothing, if illegal, guarded or blocked by a hidden unit.
    bool try_move(vec2 tile);
    // Tiles no step or dash may end on until cleared: routes go around them.
    void set_guard(const bitboard* guard) { guard_ = guard; }
    const bitboard* guard() const { return guard_; }

    // Unseen units can still block these.
    bitboard dash_landings();    // <= 2 king steps not through walls or camps, onto a free tile, off the guard
    bitboard teleport_targets(); // free open or bush tiles within 3, not camp tiles or enemy spawn

private:
    vec2 my_pos(); // our tile, read again after invalidate() or in a new round
    struct Neighbours {
        std::array<vec2, 8> tiles;
        int count = 0;
        const vec2* begin() const { return tiles.data(); }
        const vec2* end() const { return tiles.data() + count; }
    };
    // Free neighbours that get strictly closer on a static field, nearest first.
    Neighbours closer_neighbours(const Field& field, const bitboard* avoid = nullptr);
    struct Route {
        int steps = unreachable; // 0: already on a goal; unreachable: none within the cap
        int count = 0;
        std::array<vec2, 8> first_steps; // the first `count`: all equally short, in compass order
    };
    Route route(const bitboard& goals, const bitboard* avoid = nullptr, int max_steps = unreachable, vec2 through = {-1, -1});
    // The latest route's search: its distances from the goals, and whether it found no way
    // although it stopped short of its cap, so that no wider search finds one either.
    cambc::distance_field route_field_;
    bool route_exhausted_ = false;
    // Two allies head-on with no way past: the one with fewer gems (ties: lower champion) backs off.
    // Right after a route that found no way, with the same arguments: read from its field.
    // Leaves route_exhausted_ set only if no ally's tile, freed, opens a way at any cap.
    bool make_way(const bitboard& goals, const bitboard* avoid, int max_steps);
    int approach_steps(int group, int range);
    const Field* search_approach(int group, int range, int steps); // approach() once known not ready
    using Slot = std::unique_ptr<Field>;
    const Field& cached(Slot& slot, const bitboard& goals);
    Slot& altar_slot(int altar);
    struct Approach {
        Field field;
        bitboard camps; // the live camp tiles it walks around
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
    bool prepare_member(int group, int member, int range, std::uint64_t fuel_floor);
    const StaticMap& map() const;
    bool farmed(int group) const; // farm reads only groups with a reward and no monolith
    // Layers to cap its centre field at, doubled after a field cut short; 0: uncapped (no draft plan).
    int& centre_cap(int group);

    const World& world_;
    Slot any_altar_;
    Slot ally_spawn_;
    std::vector<std::optional<int>> centre_to_altar_;
    std::vector<Slot> altar_fields_, centre_fields_, hop_fields_;
    std::vector<std::optional<int>> hop_landing_steps_;
    std::vector<int> centre_caps_;
    std::vector<std::vector<std::unique_ptr<Approach>>> approach_fields_; // by range, then group
    bitboard live_camps_;
    std::uint32_t live_camps_version_ = ~0u; // the World::camps_version it was built for
    std::vector<std::uint32_t> live_versions_; // per group: the CampBelief::version written
    bool centres_ready_ = false;
    int warm_group_ = 0, warm_member_ = 0; // warm_up's progress through the attack tiles
    // By attack range, then group, then member.
    std::vector<std::vector<std::vector<std::optional<bitboard>>>> attack_tiles_;
    // Kept between rebuilds: allocating a board costs more than filling it.
    bitboard blocked_{cambc::uninitialized};
    bool blocked_fresh_ = false;
    bitboard bumped_;
    bool bumped_any_ = false;
    const bitboard* guard_ = nullptr;
    int bumped_round_ = -1;
    vec2 pos_;
    std::uint32_t pos_round_ = 0;
    bool pos_fresh_ = false;
    unsigned dashes_seen_ = 0; // outside_dashes() when our tile was last read
};

} // namespace aph
