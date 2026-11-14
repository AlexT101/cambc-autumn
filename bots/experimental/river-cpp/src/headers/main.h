#pragma once

#include <cambc.h>
#include <cstdio>
#include <memory>
#include "comms.h"
#include "draft.h"
#include "state.h"
#include "champions/cassi/states/assess.h"

namespace aph {
struct DraftState;
}
namespace {
struct TableQueue;
}
namespace aph {
class World;
class Pathing;
struct Turn;
}

namespace {
using aph::end_reserve;

// What the turn's last phases need on their cheap paths.
constexpr std::uint64_t late_floor = 1500;

constexpr std::uint64_t end_turn_fuel = 1000;

template <class F> bool run(const char* phase, F&& f);

// Spare fuel fills the terrain-only tables a fight reads, nearest tiles first: around visible
// enemies, then around us (wider while dead). Never changes play: each fills as a miss would. Bound
// by the fuel spent this turn against the real budget, so it fills the same at any budget.
struct TableQueue {
    static constexpr std::uint64_t tile_reserve = 6000; // a tile's tables on 100x100, with margin
    // Filled tiles (or walls) as bits by row and by column, 2 words each: a ring's sides are 4 spans.
    std::vector<std::uint64_t> rows, cols;
    std::vector<std::uint8_t> rings; // by tile: rings around it all done, + 1

    // The first clear bit in [lo, hi] of a 2-word line, or -1.
    static int first_clear(const std::uint64_t* line, int lo, int hi);








    void run(const aph::World& world, std::uint64_t start, std::uint64_t budget);
















































};

struct Instance {
    TableQueue tables;
    aph::DraftState draft;
    std::unique_ptr<aph::World> world;
    std::unique_ptr<aph::Pathing> pathing;
    bool map_warmed_up = false, warmed_up = false;
    bool logged_centres = false; // debug_block only

    void draft_turn();




    [[gnu::flatten]] void play_turn();









































































};

}
// The champion we are: its states (champions/<name>/) run the turn.
void run_champion(aph::Turn& t);
