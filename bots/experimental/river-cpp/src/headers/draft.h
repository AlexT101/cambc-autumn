#pragma once

#include "../params.h"
#include <cambc.h>
#include <array>
#include <cstdint>
#include <type_traits>
#include <algorithm>
#include <cstring>
#include <span>
#include <vector>
#include "comms.h"

namespace aph {
struct DraftPlan;
struct DraftState;
}
namespace aph {
namespace {
struct Analysis;
}
}
namespace aph {
struct StaticMap;
struct Field;
}

namespace aph {
struct DraftPlan {
    // Bump when the layout changes; a champion ignores a plan with another version.
    static constexpr std::uint16_t current_version = 2;

    std::uint16_t version = current_version; // 0 means the draft bot never wrote a plan
    std::array<std::uint8_t, 2> reserved{};

    // Static map analysis, so that champions skip it. A champion whose map differs (size, group
    // count, first ally spawn tile) ignores it.
    std::uint8_t width = 0, height = 0, groups = 0, spawn_x = 0, spawn_y = 0;
    std::uint8_t spawn_tiles = 0;   // ally spawn tiles with steps in the group entries; 0: none
    std::uint8_t steps = 0;         // 1 once the group entries are in
    std::uint8_t attack_groups = 0; // leading groups whose members' attack tiles are in
    std::uint16_t field_layers = 0; // the deepest field computed
    // Per group, group_bytes: walking steps to its centre from our spawn, from theirs and from the
    // tribute tiles of every altar (u16 each), then 2 bits per ally spawn tile: its steps beyond
    // the whole spawn's. Then per group up to attack_groups, per member, its attack tiles at each of
    // attack_ranges: bits over the square around it, by rows from the bottom left.
    std::array<std::uint8_t, 1010> data{};

    static constexpr int group_bytes = 10;
    static constexpr int max_spawn_tiles = 16;
    static constexpr std::array<int, 2> attack_ranges{3, 1};
    static constexpr int member_bits = 7 * 7 + 3 * 3;
};

static_assert(std::is_trivially_copyable_v<DraftPlan>);

static_assert(sizeof(DraftPlan) == 1024, "draft memory is 1024 bytes");

// In the draft memory snapshot, which lasts the match; null if none or another version. Copying
// it costs ~1 fuel a byte.
const DraftPlan* read_draft_plan();

struct DraftState {
    DraftPlan plan;
    int picked_round = -1;
};

void play_draft(DraftState& state);

// A draft turn that ends without a pick makes every remaining pick random, and the draft bot
// never runs again.
void ensure_picked(DraftState& state);

}
namespace aph {
namespace {
int draft_round();

constexpr auto all_champions() {
    std::array<cambc::champion_draft, static_cast<std::size_t>(cambc::champion_draft::heart_of_ruin) + 1> all{};
    for (std::size_t i = 0; i < all.size(); ++i) all[i] = static_cast<cambc::champion_draft>(i);
    return all;
}

// A rejected pick does not spend the turn, so trying the next candidate is always safe.
bool pick_first_available(DraftState& state, std::span<const cambc::champion_draft> order);

// The static map analysis every champion would repeat, carried over draft turns while fuel lasts.
// A draft turn keeps `draft_reserve` for the plan's write and the pick.
constexpr std::uint64_t draft_reserve = 40000;

struct Analysis {
    std::unique_ptr<StaticMap> map;
    std::vector<std::array<std::uint16_t, 3>> steps; // per group: from our spawn, theirs, the altars
    std::vector<std::array<std::uint16_t, DraftPlan::max_spawn_tiles>> spawn_steps; // per group, per ally spawn tile
    int fields = 0; // of those 3 and the spawn tiles', done
    int attack_group = 0, attack_member = 0, attack_bit = 0;
    bool done = false;
};

Analysis& analysis();

void set_steps(const StaticMap& map, const Field& field, int which, Analysis& a);

// Each part checks its fuel first; a part not done is retried next draft turn.
void analyse(DraftPlan& plan);

}
}
namespace aph {
namespace {
namespace test_compositions {
using C = cambc::champion_draft;

constexpr C three[][3] = {
    {C::stellar, C::heart_of_ruin, C::ren},
    {C::heart_of_ruin, C::ren, C::ryth},
    {C::marcella, C::heart_of_ruin, C::stellar},
    {C::heart_of_ruin, C::vendetta, C::ren},
    {C::heart_of_ruin, C::marcella, C::vesper_vale},
    {C::heart_of_ruin, C::varg, C::stellar},
    {C::heart_of_ruin, C::marcella, C::ren},
    {C::heart_of_ruin, C::ryth, C::vesper_vale},
    {C::stellar, C::heart_of_ruin, C::cassi_and_issac},
    {C::heart_of_ruin, C::varg, C::cassi_and_issac},
};

constexpr C four[][4] = {
    {C::heart_of_ruin, C::ren, C::stellar, C::ryth},
    {C::heart_of_ruin, C::vendetta, C::ren, C::vesper_vale},
    {C::marcella, C::heart_of_ruin, C::stellar, C::ren},
    {C::stellar, C::heart_of_ruin, C::ren, C::cassi_and_issac},
    {C::heart_of_ruin, C::marcella, C::vesper_vale, C::ryth},
    {C::heart_of_ruin, C::varg, C::cassi_and_issac, C::ryth},
    {C::vesper_vale, C::cassi_and_issac, C::varg, C::stellar},
    {C::marcella, C::ryth, C::stellar, C::heart_of_ruin},
    {C::heart_of_ruin, C::ren, C::ryth, C::tavi},
    {C::marcella, C::ren, C::stellar, C::ryth},
};

constexpr C five[][5] = {
    {C::heart_of_ruin, C::ren, C::stellar, C::ryth, C::varg},
    {C::marcella, C::heart_of_ruin, C::stellar, C::ren, C::ryth},
    {C::heart_of_ruin, C::ren, C::ryth, C::stellar, C::tavi},
    {C::stellar, C::heart_of_ruin, C::ren, C::cassi_and_issac, C::ryth},
    {C::heart_of_ruin, C::marcella, C::vesper_vale, C::ryth, C::stellar},
    {C::heart_of_ruin, C::vendetta, C::ren, C::vesper_vale, C::varg},
    {C::heart_of_ruin, C::varg, C::cassi_and_issac, C::ryth, C::stellar},
    {C::stellar, C::heart_of_ruin, C::prism, C::marcella, C::ren},
    {C::stellar, C::heart_of_ruin, C::cassi_and_issac, C::marcella, C::willow},
    {C::vesper_vale, C::cassi_and_issac, C::varg, C::vendetta, C::stellar},
};

std::uint64_t mix(std::uint64_t h, std::uint64_t w);

std::uint64_t mix_board(std::uint64_t h, const bitboard& board);

// Both sides see the same map, so the side-swapped game repeats each side's draft.
std::uint64_t map_hash();

std::span<const C> choose();

}
}
}
namespace aph {
namespace {
std::span<const cambc::champion_draft> table_draft();

// Re-read each draft round: a counter rule depends on the enemy picks seen so far.
std::vector<cambc::champion_draft> draft_order();

void write_plan(DraftState& state);

}
}
namespace aph {
const DraftPlan* read_draft_plan();

// Pathing::keep_price, the dash price (half turns; a step costs 2) while a dash may be wanted before it
// is ready again, that travels fastest on this map. Trips from our spawn to every group and from every
// group to the altars are walked down a host field to the goal, turn by turn, as travel_dash dashes away
// from danger: when the dash is ready (8 turns apart) it is taken if a landing gains at least
// price / 2 + 1 steps, then the turn's walk follows. The price is Pathing::eager_price, or the candidate
// keep price while a crossing lies ahead (a takeoff tile within 8 nearer the goal). The candidate with
// the fewest turns over all trips wins; ties keep the dash. Bounded: at most `max_trips`, and it stops
// above a floor that keeps the pick's fuel (the first draft turn's 10M covers it many times).
void tune_dash(DraftPlan& plan);

void play_draft(DraftState& state);

void ensure_picked(DraftState& state);

}
