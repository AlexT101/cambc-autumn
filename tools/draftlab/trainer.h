#pragma once
// Draft lab vehicle (tools/draftlab/README.md): the draft comes from trainer_table.h, generated per
// batch, keyed by map and side. The key must match features.mjs mapKey bit for bit.
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <iterator>

namespace aph::trainer {

struct Entry {
    std::uint64_t key;
    std::uint8_t team, n;
    std::array<std::uint8_t, 5> picks;
};

} // namespace aph::trainer

#include "trainer_table.h"

namespace aph::trainer {

inline std::uint64_t mix(std::uint64_t z) {
    z += 0x9E3779B97F4A7C15ull;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
    return z ^ (z >> 31);
}

// Camps are summed, so the engine's handle order does not matter.
inline std::uint64_t map_key() {
    std::uint64_t h = mix(static_cast<std::uint64_t>(cambc::map::width()));
    for (const std::uint64_t v : {static_cast<std::uint64_t>(cambc::map::height()), std::uint64_t{cambc::map::walls().count()},
                                  std::uint64_t{cambc::map::bushes().count()}, std::uint64_t{cambc::map::holes().count()},
                                  std::uint64_t{cambc::map::altars().count()}})
        h = mix(h ^ v);
    static std::array<std::uint32_t, 8192> words;
    std::uint32_t count{};
    cambc::detail::check(cambc::detail::sdk_map_camp_layout(words.data(), static_cast<std::uint32_t>(words.size()), &count));
    const std::uint32_t n = std::min<std::uint32_t>(count, static_cast<std::uint32_t>(words.size()));
    std::uint64_t sum = 0, camps = 0;
    for (std::uint32_t i = 0; i + 5 <= n;) {
        const auto size = words[i + 4];
        i += 5;
        for (std::uint32_t m = 0; m < size && i + 4 <= n; ++m, i += 4, ++camps)
            sum += mix(std::uint64_t{words[i + 1]} | (std::uint64_t{words[i + 2]} << 8) | (std::uint64_t{words[i + 3]} << 16));
    }
    h = mix(h ^ sum);
    return mix(h ^ camps);
}

// This map and side's picks in pick order, or null (no entry, or the wrong pick count).
inline const std::uint8_t* lookup() {
    static const std::uint8_t* hit = []() -> const std::uint8_t* {
        try {
            const auto key = map_key();
            const auto team = static_cast<std::uint8_t>(cambc::detail::sdk_my_team());
            const auto* end = std::end(entries);
            const auto* it = std::lower_bound(std::begin(entries), end, std::pair{key, team}, [](const Entry& e, const auto& k) {
                return e.key != k.first ? e.key < k.first : e.team < k.second;
            });
            if (it == end || it->key != key || it->team != team || it->n != cambc::draft::team_size()) return nullptr;
            return it->picks.data();
        } catch (const std::exception&) {
            return nullptr;
        }
    }();
    return hit;
}

} // namespace aph::trainer
