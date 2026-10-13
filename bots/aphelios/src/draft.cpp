#include "draft.h"
#include <algorithm>
#include <array>
#include <cstring>
#include <span>
#include <vector>
#include "params.h"
#include "util.h"

namespace aph {

namespace {

int draft_round() { return static_cast<int>(cambc::round_number()); }

// A rejected pick does not spend the turn, so trying the next candidate is always safe.
bool pick_first_available(DraftState& state, std::span<const cambc::champion_draft> order) {
    const auto ours = cambc::draft::current_draft(team::ally);
    for (const auto pick : order) {
        if (std::find(ours.begin(), ours.end(), pick) != ours.end()) continue;
        try {
            cambc::draft::pick(pick);
            state.picked_round = draft_round();
            return true;
        } catch (const cambc::error&) {
        }
    }
    return false;
}

void write_plan(DraftState& state) {
    state.plan.version = DraftPlan::current_version;
    state.plan.draft_round = static_cast<std::uint8_t>(draft_round());
    cambc::draft_memory = std::span<const std::byte>{reinterpret_cast<const std::byte*>(&state.plan), sizeof(DraftPlan)};
}

} // namespace

std::optional<DraftPlan> read_draft_plan() {
    if (cambc::draft_memory.size() < sizeof(DraftPlan)) return std::nullopt;
    DraftPlan plan;
    std::memcpy(&plan, cambc::draft_memory.data(), sizeof(DraftPlan));
    if (plan.version != DraftPlan::current_version) return std::nullopt;
    return plan;
}

void play_draft(DraftState& state) {
    // Write before picking: a pick ends the draft turn's actions (later writes fail with error 18),
    // and the draft bot may not run again after its last pick.
    write_plan(state);
    pick_first_available(state, params::draft_preference);
}

void ensure_picked(DraftState& state) {
    if (state.picked_round == draft_round()) return;
    static constexpr auto everything = [] {
        std::array<cambc::champion_draft, static_cast<std::size_t>(cambc::champion_draft::tavi) + 1> all{};
        for (std::size_t i = 0; i < all.size(); ++i) all[i] = static_cast<cambc::champion_draft>(i);
        return all;
    }();
    pick_first_available(state, everything);
}

} // namespace aph
