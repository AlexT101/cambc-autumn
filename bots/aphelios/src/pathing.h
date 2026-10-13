// Pathing: thin wrappers over the SDK's host-side distance fields and reachability.
//  - Static fields to fixed goals (spawn, altars, camps), computed on first use and cached.
//  - Per-turn routing around live blockers, under the walking rules.
//  - Movement that tolerates hidden blockers.
//  - Legal destinations for dashes, teleport crystals and wards.
// Danger, preferences and targets belong to decision code: it passes extra tiles to avoid.
#pragma once
#include <cambc.h>
#include <cstdint>
#include <memory>
#include <optional>
#include <unordered_map>
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
    // Goals: walkable tiles within `range` of the group's camp tiles, off the camp tiles.
    const Field& to_group_attack(int group, int range);
    // Compute the fields a champion with this attack range is likely to need, while more than
    // `fuel_floor` fuel remains; true once all are cached.
    bool warm_up(int attack_range, std::uint64_t fuel_floor);

    // ----- Per-turn routing -----
    // Static walls | visible champions, camps and teleport reservations | tiles bumped this round,
    // minus our own tile. Cached until invalidate().
    const bitboard& blocked();
    // Forget cached live state; the movement helpers call this themselves after a move.
    void invalidate();
    // Free neighbours that get strictly closer on a static field, nearest first.
    std::vector<vec2> closer_neighbours(const Field& field, const bitboard* avoid = nullptr);
    // First step of a shortest live route to any open goal tile; nullopt if none or already there.
    std::optional<vec2> route(const bitboard& goals, const bitboard* avoid = nullptr);

    // One walking step towards the goals; false if no step was taken. Static-field moves are tried
    // first (cheap), then a live route. A hidden blocker fails the move without spending the walk;
    // the tile is remembered and the next candidate is tried.
    bool step_towards(const Field& field, const bitboard* avoid = nullptr);
    bool step_towards(const bitboard& goals, const bitboard* avoid = nullptr);
    bool step_towards(vec2 target, const bitboard* avoid = nullptr);
    // Walk to an adjacent tile; false (spending nothing) if illegal or blocked by a hidden unit.
    bool try_move(vec2 tile);

    // ----- Legal destinations from our tile; unseen units can still block them -----
    bitboard dash_landings();    // <= 2 king steps not through walls or camps, onto a free tile
    bitboard teleport_targets(); // free open or bush tiles within 3, not camp tiles or enemy spawn
    bitboard ward_targets();     // within 2, not wall, hole, altar, enemy spawn or one of our wards

private:
    const Field& cached(std::uint32_t key, const bitboard& goals);
    const StaticMap& map() const;

    const World& world_;
    std::unordered_map<std::uint32_t, std::unique_ptr<Field>> fields_;
    std::optional<bitboard> blocked_;
    bitboard bumped_;
    int bumped_round_ = -1;
};

} // namespace aph
