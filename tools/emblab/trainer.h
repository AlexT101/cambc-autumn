#pragma once
// Emblem lab vehicle (tools/emblab/README.md): the draft and every champion's randomised emblems come
// from trainer_table.h, generated per batch, keyed by map and side. The key must match
// tools/draftlab/features.mjs mapKey bit for bit.
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <iterator>

namespace aph::trainer {

inline constexpr int ordinals = 8;
inline constexpr std::uint8_t model_arm = 255; // the bot's own choice

struct Entry {
    std::uint64_t key;
    std::uint8_t team, n;
    std::array<std::uint8_t, 5> picks;
    // arms[row][k]: family * 3 + stat for the row's k-th new emblem. Row i is pick i (Cassi for
    // Cassi and Issac), row 5 Issac.
    std::array<std::array<std::uint8_t, ordinals>, 6> arms;
};

} // namespace aph::trainer

#include "trainer_table.h"

namespace aph::trainer {

// Gold's price in farm choices (prices().per_gold), scaled: we earn less gold than top teams.
inline constexpr float gold_price_scale = 1.5f;

// A (family, stat) best_emblem treats as begun while set, to price it; -1 when not.
inline int pin_family = -1, pin_stat = 0;
// Set by buy_shards: only its best_emblem calls follow the table.
inline bool buying = false;

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

// The table's arm (family * 3 + stat) for a champion of `type`'s `ordinal`-th new emblem, or -1.
inline int emblem_arm(cambc::champion_type type, int ordinal) {
    const Entry* e = find();
    if (!e || ordinal < 0 || ordinal >= ordinals) return -1;
    const int t = static_cast<int>(type), cassi = static_cast<int>(cambc::champion_type::cassi);
    const int issac = static_cast<int>(cambc::champion_type::issac);
    const int draft = t < cassi ? t : t <= issac ? cassi : t - 1;
    int row = -1;
    for (int i = 0; i < e->n; ++i)
        if (e->picks[i] == draft) row = t == issac ? 5 : i;
    if (row < 0) return -1;
    const auto arm = e->arms[row][ordinal];
    return arm == model_arm ? -1 : arm;
}

} // namespace aph::trainer
