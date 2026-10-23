#pragma once

#include <array>
#include <cstdint>

namespace aph::gold_value {

inline bool treasure_owned(const std::array<unsigned, 3>& emblems) {
    return emblems[0] + emblems[1] + emblems[2] > 0;
}

inline int percent(int passive_bonus, bool treasure_emblem) {
    return 100 + passive_bonus + (treasure_emblem ? 20 : 0);
}

// The SDK exposes integer gold, so this deliberately drops any hidden fractional balance.
inline std::uint32_t incoming(int base, int percent) {
    return static_cast<std::uint32_t>(static_cast<std::uint64_t>(base) * static_cast<unsigned>(percent) / 100);
}

inline int share(int base, int sharers, bool lowest_id) {
    return base / sharers + (lowest_id ? base % sharers : 0);
}

inline bool gold_only_holder(bool alive, bool visible, bool standing_on_group, bool healthy,
                             bool forbidden_channel, bool winning_bag, bool kept_recall, bool pressure) {
    return alive && visible && standing_on_group && healthy && !forbidden_channel && !winning_bag
           && !kept_recall && !pressure;
}

// The SDK holds at most four uncompleted shards per stat; 21 counts fit in 63 bits.
inline std::uint64_t inventory_stamp(const std::array<std::uint8_t, 21>& counts) {
    std::uint64_t stamp = 0;
    for (unsigned i = 0; i < counts.size(); ++i)
        stamp |= static_cast<std::uint64_t>(counts[i] & 7u) << (3 * i);
    return stamp;
}

} // namespace aph::gold_value
