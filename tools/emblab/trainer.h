#pragma once
// Emblem lab vehicle (tools/emblab/README.md): the draft, and which of every champion's new emblems are drawn at
// random, come from trainer_table.h, generated per batch, keyed by map and side. The key must match
// tools/draftlab/features.mjs mapKey bit for bit.
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <iterator>

namespace aph::trainer {

inline constexpr int ordinals = 12;
inline constexpr int arms = 42; // family * 3 + stat; Greed's three are never drawn

struct Entry {
    std::uint64_t key;
    std::uint8_t team, n;
    // 0: the proposal (eps uniform + softmax over the current logic's values); 1: uniform (the unbiased check).
    std::uint8_t mode;
    std::array<std::uint8_t, 5> picks;
    std::uint32_t seed;
    // force[row] bit k: the row's k-th new emblem is drawn rather than the base's. Row i is pick i (Cassi for
    // Cassi and Issac), row 5 Issac.
    std::array<std::uint16_t, 6> force;
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

// This map and side's entry, or null.
inline const Entry* find() {
    static const Entry* hit = []() -> const Entry* {
        try {
            const auto key = map_key();
            const auto team = static_cast<std::uint8_t>(cambc::detail::sdk_my_team());
            const auto* end = std::end(entries);
            const auto* it = std::lower_bound(std::begin(entries), end, std::pair{key, team}, [](const Entry& e, const auto& k) {
                return e.key != k.first ? e.key < k.first : e.team < k.second;
            });
            return it == end || it->key != key || it->team != team ? nullptr : it;
        } catch (const std::exception&) {
            return nullptr;
        }
    }();
    return hit;
}

// The draft's picks in pick order, or null (no entry, or the wrong pick count).
inline const std::uint8_t* lookup() {
    const Entry* e = find();
    return e && e->n == cambc::draft::team_size() ? e->picks.data() : nullptr;
}

// The row of a champion of `type` in this map and side's entry, or -1.
inline int row_of(cambc::champion_type type) {
    const Entry* e = find();
    if (!e) return -1;
    const int t = static_cast<int>(type), cassi = static_cast<int>(cambc::champion_type::cassi);
    const int issac = static_cast<int>(cambc::champion_type::issac);
    const int draft = t < cassi ? t : t <= issac ? cassi : t - 1;
    for (int i = 0; i < e->n; ++i)
        if (e->picks[i] == draft) return t == issac ? 5 : i;
    return -1;
}

// Whether a champion of `type`'s `ordinal`-th new emblem is drawn; if so, *u is a uniform in [0, 1) fixed by the
// entry's seed, the row and the ordinal.
inline bool forced(cambc::champion_type type, int ordinal, double* u, int* mode) {
    const Entry* e = find();
    const int row = row_of(type);
    if (row < 0 || ordinal < 0 || ordinal >= ordinals || !((e->force[row] >> ordinal) & 1)) return false;
    *u = static_cast<double>(mix(e->seed ^ (std::uint64_t{static_cast<unsigned>(row)} << 40) ^ (std::uint64_t{static_cast<unsigned>(ordinal)} << 48)) >> 11) * 0x1p-53;
    *mode = e->mode;
    return true;
}

} // namespace aph::trainer
