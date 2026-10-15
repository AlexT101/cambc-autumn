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

constexpr auto all_champions() {
    std::array<cambc::champion_draft, static_cast<std::size_t>(cambc::champion_draft::tavi) + 1> all{};
    for (std::size_t i = 0; i < all.size(); ++i) all[i] = static_cast<cambc::champion_draft>(i);
    return all;
}

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

// Camp health per pick in camps with another camp within 1, where Varg's attacks splash.
float splash_health_per_pick() {
    namespace raw = cambc::detail;
    std::vector<std::uint32_t> words(256);
    std::uint32_t count{};
    raw::check(raw::sdk_map_camp_layout(words.data(), static_cast<std::uint32_t>(words.size()), &count));
    if (count > words.size()) {
        words.resize(count);
        raw::check(raw::sdk_map_camp_layout(words.data(), count, &count));
    }
    words.resize(count);
    struct Camp {
        vec2 pos;
        float health;
    };
    std::vector<Camp> camps;
    std::array<float, 5> health{};
    cambc::bitboard tiles;
    for (std::size_t i = 0; i + 5 <= words.size();) {
        const auto size = words[i + 4];
        i += 5;
        for (std::uint32_t m = 0; m < size && i + 4 <= words.size(); ++m, i += 4) {
            const auto type = words[i + 1];
            if (health[type] == 0) {
                raw::camp_design d{};
                raw::check(raw::sdk_camp_design(static_cast<std::int32_t>(type), &d));
                health[type] = d.base_stats.base_health;
            }
            const vec2 pos{static_cast<std::int32_t>(words[i + 2]), static_cast<std::int32_t>(words[i + 3])};
            camps.push_back({pos, health[type]});
            tiles.set(pos);
        }
    }
    float splash = 0;
    for (const auto& c : camps) {
        bool neighbour = false;
        for (int dy = -1; dy <= 1 && !neighbour; ++dy)
            for (int dx = -1; dx <= 1 && !neighbour; ++dx) {
                const vec2 p{c.pos.x + dx, c.pos.y + dy};
                neighbour = (dx || dy) && cambc::map::is_in_bounds(p) && tiles.is_set(p);
            }
        if (neighbour) splash += c.health;
    }
    return splash / 2.0f / static_cast<float>(std::max<std::uint32_t>(cambc::draft::team_size(), 1));
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
    if constexpr (params::random_draft) {
        auto order = all_champions();
        for (std::size_t i = order.size() - 1; i > 0; --i) std::swap(order[i], order[random_below(i + 1)]);
        pick_first_available(state, order);
    } else {
        const bool farm_race = splash_health_per_pick() >= params::farm_race_splash_health;
        pick_first_available(state, farm_race ? std::span<const cambc::champion_draft>{params::farm_race_draft_preference}
                                              : std::span<const cambc::champion_draft>{params::draft_preference});
    }
}

void ensure_picked(DraftState& state) {
    if (state.picked_round == draft_round()) return;
    pick_first_available(state, all_champions());
}

} // namespace aph
