#pragma once

#include <array>
#include <cstdint>

namespace aph::comms::support_mailbox {

inline constexpr int prism = 0;
inline constexpr int willow = 1;
inline constexpr std::uint64_t payload_mask = std::uint64_t{1} << 31;
inline constexpr std::uint64_t epoch_mask = std::uint64_t{3} << 62;
inline constexpr std::uint64_t bits_mask = payload_mask | epoch_mask;

inline int payload(std::uint64_t bits) { return static_cast<int>((bits >> 31) & 1); }
inline int epoch(std::uint64_t bits) { return static_cast<int>((bits >> 62) & 3); }
inline std::uint64_t raw_bits(std::uint64_t bits) { return bits & bits_mask; }
inline bool publish_value(int round, int intent_round, bool intent, bool both_alive) {
    return intent_round == round && intent && both_alive;
}

inline void write(std::uint64_t& bits, int round, bool positive) {
    bits = (bits & ~bits_mask) | (positive ? payload_mask : 0) | (static_cast<std::uint64_t>(round & 3) << 62);
}

struct Endpoint {
    bool present = false;
    bool alive = false;
    bool is_self = false;
    int respawned_round = -1;
};

struct State {
    std::uint64_t raw = 0;
    int read_round = -1;
    std::array<int, 2> sent{-1, -1}, respawn{-1, -1};
    std::array<bool, 2> positive{}, alive{};

    bool receive(int round, std::uint64_t bits, const std::array<Endpoint, 2>& pair) {
        if (read_round == round) return false;
        bool reset = read_round != round - 1 || !pair[prism].present || !pair[willow].present;
        for (int i = 0; i < 2; ++i) {
            const bool endpoint_alive = pair[i].present && pair[i].alive;
            const int endpoint_respawn = pair[i].present ? pair[i].respawned_round : -1;
            reset |= !endpoint_alive || endpoint_alive != alive[i] || endpoint_respawn != respawn[i];
            alive[i] = endpoint_alive;
            respawn[i] = endpoint_respawn;
        }
        const auto observed = raw_bits(bits);
        if (reset) sent = {-1, -1}, positive = {};
        else if (observed != raw) {
            const int age = (round - epoch(bits)) & 3;
            const int sent_round = round - age, writer = sent_round & 1;
            if (age <= 1 && pair[writer].alive && !pair[writer].is_self) {
                sent[writer] = sent_round;
                positive[writer] = payload(bits) != 0;
            }
        }
        raw = observed;
        read_round = round;
        return true;
    }

    bool valid(int writer, int round) const {
        return read_round == round && sent[writer] >= 0 && round <= sent[writer] + 2
               && alive[prism] && alive[willow] && positive[writer];
    }
};

} // namespace aph::comms::support_mailbox
