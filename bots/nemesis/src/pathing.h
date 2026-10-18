// Live routes treat the units we see as standing still: walk one step, then replan. A host
// search costs a fixed setup plus a little per layer, not per tile, so routes run in full.
#pragma once
#include <cambc.h>
#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <vector>
#include "params.h"
#include "util.h"

namespace aph {

class World;
struct StaticMap;

class Pathing {
public:
    explicit Pathing(const World& world);

    void begin_turn();

    const Field& to_ally_spawn();
    const Field& to_altar(int altar); // goals: the altar's tribute tiles
    // Null if not cached and computing it could take the fuel below `fuel_floor`.
    const Field* to_altar(int altar, std::uint64_t fuel_floor);
    const Field& to_any_altar();
    int centre_to_altar(int group); // to_any_altar() at the group's centre, kept once read
    const Field& to_group(int group); // goals: the group's camp tiles, to stand on and capture
    // Static steps to tiles within `range` of the group's camp tiles, around the camps believed alive:
    // the walk to its attack tiles but for sight lines near the end. Range 0: onto its camp tiles, to
    // capture. Null if the search out to us would take the fuel below `fuel_floor`.
    const Field* approach(int group, int range, std::uint64_t fuel_floor);
    bool approach_ready(int group, int range); // usable from here without a search
    std::uint64_t approach_cost(int group, int range); // 0 when ready
    int approach_steps(int group, int range);
    // Walking steps from the centre of a group worth farming (gems, no monolith): by symmetry,
    // from anywhere to it. Null until warmed up; centres_ready() once all are.
    const Field* from_centre(int group);
    bool centres_ready() const { return centres_ready_; }
    // Walkable tiles from which a basic attack reaches and sees the member, camp tiles included.
    const bitboard& member_attack_tiles(int group, int member, int range);
    // Over the members believed alive; off camp tiles, but for those of its dead members.
    bitboard attack_tiles(int group, int range);
    // Compute attack_tiles' missing parts while more than `fuel_floor` remains; true once cached.
    bool prepare_attack_tiles(int group, int range, std::uint64_t fuel_floor);
    // The same for the members in `members` (bit i: member i), alive or not.
    bool prepare_member_tiles(int group, int range, std::uint32_t members, std::uint64_t fuel_floor);
    // Precompute while more than `fuel_floor` remains; true once everything is cached.
    bool warm_up(int attack_range, std::uint64_t fuel_floor);
    // The centre fields first: until they are ready, farm builds a field from wherever we stand.
    // A field capped at centre_cap() has a bounded cost, so it may go down to last_reserve.
    bool warm_centres(std::uint64_t fuel_floor);

    struct Nearest {
        int steps = unreachable;
        std::vector<vec2> tiles;
    };
    // Static terrain only. Stops at the first goal, so it costs by distance, not goal count.
    Nearest nearest(const bitboard& goals, int max_steps = unreachable);

    // Static walls, visible units and teleport reservations, and tiles bumped this round.
    const bitboard& blocked();
    void invalidate(); // after we move or dash
    vec2 my_pos();     // our tile, read again after invalidate() or in a new round
    // Free neighbours that get strictly closer on a static field, nearest first.
    std::vector<vec2> closer_neighbours(const Field& field, const bitboard* avoid = nullptr);

    struct Route {
        int steps = unreachable; // 0: already on a goal; unreachable: none within the cap
        int count = 0;
        std::array<vec2, 8> first_steps; // the first `count`: all equally short, in compass order
    };
    Route route(const bitboard& goals, const bitboard* avoid = nullptr, int max_steps = unreachable);

    // A hidden blocker fails a move without spending the walk; the other first steps are tried,
    // then the route is replanned.
    bool step_towards(const bitboard& goals, const bitboard* avoid = nullptr, int max_steps = unreachable);
    bool step_towards(vec2 target, const bitboard* avoid = nullptr);
    // A live route within `max_detour` of the static distance, else greedy descent of the field.
    bool step_towards(const Field& field, const bitboard* avoid = nullptr, int max_detour = params::max_detour);
    // Cheap fallbacks without a search, when fuel is short: a step down the field, or one that
    // gets closer to the target as the crow flies.
    bool descend(const Field& field, const bitboard* avoid = nullptr);
    bool step_closer(vec2 target);
    // False, spending nothing, if illegal or blocked by a hidden unit.
    bool try_move(vec2 tile);

    // Unseen units can still block these.
    bitboard dash_landings();    // <= 2 king steps not through walls or camps, onto a free tile
    bitboard teleport_targets(); // free open or bush tiles within 3, not camp tiles or enemy spawn
    // Within 2, not wall, hole, altar, enemy spawn or one of our wards.
    bitboard ward_targets();

private:
    using Slot = std::unique_ptr<Field>;
    const Field& cached(Slot& slot, const bitboard& goals);
    Slot& altar_slot(int altar);
    Slot& group_slot(int group);
    struct Approach {
        Field field;
        bitboard camps; // the live camp tiles it walks around
    };
    std::unique_ptr<Approach>& approach_slot(int group, int range);
    // approach_ready's latest answer: farm asks it once a group with nothing changed between.
    struct ReadyCheck {
        const Approach* slot = nullptr;
        int round = -1;
        vec2 at{-1, -1};
        bool ready = false;
    } ready_check_;
    std::unique_ptr<Approach> spare_approach_; // a replaced one, refilled by the next search
    const bitboard& live_camps(); // members believed alive, as of this round
    std::optional<bitboard>& attack_slot(int group, int member, int range);
    bool prepare_member(int group, int member, int range, std::uint64_t fuel_floor);
    const StaticMap& map() const;
    bool farmed(int group) const; // farm reads only groups with a reward and no monolith
    // Layers to cap its centre field at, doubled after a field cut short; 0: uncapped (no draft plan).
    int& centre_cap(int group);

    const World& world_;
    Slot any_altar_;
    std::vector<std::optional<int>> centre_to_altar_;
    std::vector<Slot> altar_fields_, group_fields_, centre_fields_;
    std::vector<int> centre_caps_;
    std::vector<std::vector<std::unique_ptr<Approach>>> approach_fields_; // by range, then group
    bitboard live_camps_;
    int live_camps_round_ = -1;
    bool centres_ready_ = false;
    int warm_group_ = 0, warm_member_ = 0; // warm_up's progress through the attack tiles
    // By attack range, then group, then member.
    std::vector<std::vector<std::vector<std::optional<bitboard>>>> attack_tiles_;
    // Kept between rebuilds: allocating a board costs more than filling it.
    bitboard blocked_{cambc::uninitialized};
    bool blocked_fresh_ = false;
    bitboard bumped_;
    bool bumped_any_ = false;
    int bumped_round_ = -1;
    vec2 pos_;
    std::uint32_t pos_round_ = 0;
    bool pos_fresh_ = false;
};

} // namespace aph
