#pragma once
// Live builds only (written in by the live scheduler's mask_patch.py; never in git): our priorities
// as replays show them, coded per game from a secret key and facts every ally knows at round 1.
// packed_priority shifts the rank above the payload by a secret amount on each side of 0, which keeps
// the order and the sign, so the engine's turn order, every set_priority call and every comparison
// of ranks (ours, the allies' as read, World's) are unchanged. The payload is xored with a mask
// fixed per game; payload_of undoes it. Each costs a few instructions: they run in hot loops.
#include <cstdint>

namespace aph {
class World;
}

namespace aph::prio_mask {

inline constexpr std::uint64_t key[2] = {0x0ull, 0x0ull}; // PRIO_MASK_KEY
inline constexpr bool on = key[0] != 0 || key[1] != 0;

struct Code {
    // Rank r >= 0 shows as r + pos, r < 0 as r - neg (pos >= 1); the payload as payload ^ mask.
    std::int32_t pos = 1, neg = 0;
    std::uint32_t mask = 0;
};
inline Code code;

inline std::uint64_t mix(std::uint64_t z) {
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
    return z ^ (z >> 31);
}

// The code for one game, ranks in [rank_min, rank_max] (rank_max < 32767, rank_min > -32768).
inline void make(std::uint64_t seed, int rank_min, int rank_max) {
    const std::uint64_t h = mix(seed ^ key[0]);
    const auto lo = static_cast<std::uint32_t>(h), hi = static_cast<std::uint32_t>(h >> 32);
    // The top rank's code must stay at most 32767 and the bottom's at least -32768.
    code.pos = 1 + static_cast<std::int32_t>((lo >> 16) % static_cast<std::uint32_t>(32767 - rank_max));
    code.neg = static_cast<std::int32_t>((hi >> 16) % static_cast<std::uint32_t>(32769 + (rank_min < 0 ? rank_min : 0)));
    code.mask = (lo ^ hi) & 0xffff;
}

void setup(const World& world); // turn_order.cc: make() with this game's seed and the rank range; once, at World's init

// packed_priority's value for rank r over `payload`: never 0.
inline std::int32_t packed(std::int32_t r, std::uint32_t payload) {
    const std::int32_t t = r >= 0 ? r + code.pos : r - code.neg;
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(t) << 16 | (payload ^ code.mask));
}

// The plain payload of an ally's next priority `v` as read (not 0).
inline std::uint32_t payload_of(std::int32_t v) {
    return (static_cast<std::uint32_t>(v) ^ code.mask) & 0xffff;
}

// A published priority, plain (tools and tests).
inline std::int32_t decode(std::int32_t v) {
    const std::int32_t t = v >> 16;
    const std::int32_t r = t > 0 ? t - code.pos : t + code.neg;
    return static_cast<std::int32_t>(static_cast<std::uint32_t>(r) << 16 | payload_of(v));
}

} // namespace aph::prio_mask
