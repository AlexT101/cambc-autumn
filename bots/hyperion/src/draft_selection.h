#pragma once
#include <array>
#include <cstdint>
#include <span>
#include <stdexcept>

namespace aph {

struct DraftCampCounts {
    std::uint32_t members = 0, groups = 0;
};

inline DraftCampCounts count_draft_camps(std::span<const std::uint32_t> words) {
    DraftCampCounts counts;
    for (std::size_t at = 0; at < words.size();) {
        if (words.size() - at < 5) throw std::invalid_argument("incomplete camp group header");
        const auto members = words[at + 4];
        if (members > (words.size() - at - 5) / 4) throw std::invalid_argument("incomplete camp members");
        counts.members += members;
        ++counts.groups;
        at += 5 + 4 * static_cast<std::size_t>(members);
    }
    return counts;
}

enum class DraftRole { prism, vesper_vale, marcella, willow, ryth, vendetta, heart_of_ruin };

inline std::array<DraftRole, 5> willow_prism_draft_roles(int picks, DraftCampCounts counts) {
    if (picks == 3)
        return {DraftRole::prism, DraftRole::vesper_vale, DraftRole::heart_of_ruin,
                DraftRole::willow, DraftRole::marcella};
    const bool vendetta = picks == 5 && 3ull * counts.members > 10ull * counts.groups;
    return {DraftRole::prism, DraftRole::vesper_vale, DraftRole::marcella,
            DraftRole::willow, vendetta ? DraftRole::vendetta : DraftRole::heart_of_ruin};
}

} // namespace aph
