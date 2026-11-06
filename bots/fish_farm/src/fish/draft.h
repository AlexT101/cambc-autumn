// Fish's draft (FISH_MODEL 3.1): a fixed pick order per map, blind to the enemy's picks, from a rule
// fitted on the ladder maps Fish played (research/fish-bot-2026-11-06/LOG.md, round 1) on the map's
// camp rewards, so that it holds on maps Fish never saw.
#pragma once
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <vector>

namespace aph::fish {

namespace draft_detail {

struct Layout {
    int gold = 0, gems = 0; // every camp's reward summed
};

// The map's total camp gold and gems (cambc-rules.yaml camps.types).
inline Layout read_layout() {
    Layout out;
    static std::array<std::uint32_t, 8192> words;
    std::uint32_t count{};
    cambc::detail::check(cambc::detail::sdk_map_camp_layout(words.data(), static_cast<std::uint32_t>(words.size()), &count));
    const std::uint32_t n = std::min<std::uint32_t>(count, static_cast<std::uint32_t>(words.size()));
    // By cambc::camp_type: wolf, elk, gem cluster, gold cluster, monolith, golem.
    static constexpr int gold[] = {40, 90, 0, 20, 300, 160}, gems[] = {4, 15, 7, 0, 200, 36};
    for (std::uint32_t i = 0; i + 5 <= n;) {
        const auto size = words[i + 4];
        i += 5;
        for (std::uint32_t m = 0; m < size && i + 4 <= n; ++m, i += 4)
            if (words[i + 1] < 6) out.gold += gold[words[i + 1]], out.gems += gems[words[i + 1]];
    }
    return out;
}
} // namespace draft_detail

// Prism second on gold-free maps (Fish's adgato_gemcombat and gem maps, 7/7); otherwise Vesper Vale
// first on 3 picks (19/21), then Marcella on maps with at most 1800 camp gold (15/19), else Heart of
// Ruin; on 4-5 picks Marcella first on maps with at most 2340 camp gold (94/107; FISH_MODEL's
// gem-over-gold-cluster tendency gets 78/107), else Vesper Vale.
inline std::vector<cambc::champion_draft> draft_order(int picks) {
    using C = cambc::champion_draft;
    const auto layout = draft_detail::read_layout();
    std::vector<C> order;
    if (layout.gold == 0 && layout.gems > 0) {
        order = {C::marcella, C::prism, C::heart_of_ruin, C::cassi_and_issac, C::willow};
        if (picks == 3) order = {C::marcella, C::prism, C::cassi_and_issac};
    } else if (picks <= 3) {
        order = {C::vesper_vale, layout.gold <= 1800 ? C::marcella : C::heart_of_ruin, C::cassi_and_issac};
    } else {
        order = {layout.gold <= 2340 ? C::marcella : C::vesper_vale, C::vendetta, C::heart_of_ruin, C::cassi_and_issac, C::willow};
    }
    if (static_cast<int>(order.size()) > picks) order.resize(static_cast<std::size_t>(picks));
    return order;
}

} // namespace aph::fish
