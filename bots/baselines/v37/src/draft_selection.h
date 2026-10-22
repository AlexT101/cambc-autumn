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

enum class DraftRole { prism, vesper_vale, marcella, ryth, vendetta, heart_of_ruin };

inline std::array<DraftRole, 5> teacher_draft_roles(DraftCampCounts counts) {
    // A provisional separator inside the observed gap, rather than a recovered teacher constant.
    const bool vendetta = 3ull * counts.members > 10ull * counts.groups;
    return {DraftRole::prism, DraftRole::vesper_vale, DraftRole::marcella,
            vendetta ? DraftRole::vendetta : DraftRole::ryth, DraftRole::heart_of_ruin};
}

} // namespace aph
