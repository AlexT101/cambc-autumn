#pragma once
#include <cambc.h>
#include <array>
#include <cstdint>
#include <type_traits>

namespace aph {

struct DraftPlan {
    // Bump when the layout changes; a champion ignores a plan with another version.
    static constexpr std::uint16_t current_version = 3;

    std::uint16_t version = current_version; // 0 means the draft bot never wrote a plan
    std::uint8_t draft_round = 0;
    std::uint8_t reserved = 0;

    // Static map analysis, so that champions skip it. A champion whose map differs (size, group
    // count, first ally spawn tile) ignores it.
    std::uint8_t width = 0, height = 0, groups = 0, spawn_x = 0, spawn_y = 0;
    std::uint8_t spawn_tiles = 0;   // ally spawn tiles with steps in the group entries; 0: none
    std::uint8_t steps = 0;         // 1 once the group entries are in
    std::uint8_t attack_groups = 0; // leading groups whose members' attack tiles are in
    std::uint16_t field_layers = 0; // the deepest field computed
    // Hyperion: the user's turn-order split M (LAST values in [1, M), FIRST in [M, 2M)), secret per game: enemies read
    // priorities. Drawn by the draft bot; 0 if absent.
    std::uint32_t prio_split = 0;
    // Per group, group_bytes: walking steps to its centre from our spawn, from theirs and from the
    // tribute tiles of every altar (u16 each), then 2 bits per ally spawn tile: its steps beyond
    // the whole spawn's. Then per group up to attack_groups, per member, its attack tiles at each of
    // attack_ranges: bits over the square around it, by rows from the bottom left.
    std::array<std::uint8_t, 1004> data{};

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

} // namespace aph
