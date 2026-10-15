#pragma once
#include <cambc.h>
#include <cstdint>
#include <optional>
#include <type_traits>

namespace aph {

struct DraftPlan {
    // Bump when the layout changes; a champion ignores a plan with another version.
    static constexpr std::uint16_t current_version = 1;

    std::uint16_t version = current_version; // 0 means the draft bot never wrote a plan
    std::uint8_t draft_round = 0;
    std::uint8_t reserved = 0;

    // Strategy fields go here. Enemy picks need none: champions read them with current_draft.
};
static_assert(std::is_trivially_copyable_v<DraftPlan>);
static_assert(sizeof(DraftPlan) <= 1024, "draft memory is 1024 bytes");

std::optional<DraftPlan> read_draft_plan();

struct DraftState {
    DraftPlan plan;
    int picked_round = -1;
};

void play_draft(DraftState& state);

// A draft turn that ends without a pick makes every remaining pick random, and the draft bot
// never runs again.
void ensure_picked(DraftState& state);

} // namespace aph
