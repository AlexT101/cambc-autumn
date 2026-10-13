// Draft: picking, and the DraftPlan schema for the 1024-byte draft memory.
// DraftPlan is the contract between the draft bot and the champions: the draft bot writes it,
// every champion reads it through this same definition.
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
    std::uint8_t draft_round = 0;            // the draft round of the latest write
    std::uint8_t reserved = 0;

    // Strategy fields go here once there is strategy (e.g. an intent per pick, a target altar).
    // Enemy picks need no field: champions read every pick with cambc::draft::current_draft.
};
static_assert(std::is_trivially_copyable_v<DraftPlan>);
static_assert(sizeof(DraftPlan) <= 1024, "draft memory is 1024 bytes");

// Read the plan in play; nullopt if it was never written or has another version.
std::optional<DraftPlan> read_draft_plan();

// Draft-bot state that persists across draft turns.
struct DraftState {
    DraftPlan plan;
    int picked_round = -1; // draft round of our latest successful pick
};

// One draft turn: pick, then write the plan. Throws on engine errors.
void play_draft(DraftState& state);

// Make sure this draft turn has a pick, whatever went wrong before. A draft turn that ends without
// a pick makes this and every later pick random, and the draft bot is never run again.
void ensure_picked(DraftState& state);

} // namespace aph
