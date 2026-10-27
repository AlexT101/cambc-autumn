#pragma once

#include <array>
#include <cstdint>

namespace aph::comms::support_mailbox {

inline constexpr int protected_mate = 0; // Prism
inline constexpr int healer = 1;         // Willow
// The protected mate's request and the healer's offer, each in its own priority payload above the claim
// (comms.cpp): the intent and its round modulo four, read by the other while it sees the sender.
inline constexpr int payload_shift = 8;

inline std::uint32_t encode(int round, bool positive) {
    return (positive ? 1u : 0u) << payload_shift | static_cast<std::uint32_t>(round & 3) << (payload_shift + 1);
}
inline bool publish_value(int round, int intent_round, bool intent, bool both_alive) {
    return intent_round == round && intent && both_alive;
}

struct Endpoint {
    bool present = false;
    bool alive = false;
    bool is_self = false;
    int respawned_round = -1;
};

struct State {
    int read_round = -1;
    std::array<int, 2> sent{-1, -1}, respawn{-1, -1};
    std::array<bool, 2> positive{}, alive{};

    // `payload`: the other endpoint's priority payload as read this round, or -1 if unread.
    bool receive(int round, const std::array<Endpoint, 2>& pair, int other, std::int64_t payload) {
        if (read_round == round) return false;
        bool reset = read_round != round - 1 || !pair[protected_mate].present || !pair[healer].present;
        for (int i = 0; i < 2; ++i) {
            const bool endpoint_alive = pair[i].present && pair[i].alive;
            const int endpoint_respawn = pair[i].present ? pair[i].respawned_round : -1;
            reset |= !endpoint_alive || endpoint_alive != alive[i] || endpoint_respawn != respawn[i];
            alive[i] = endpoint_alive;
            respawn[i] = endpoint_respawn;
        }
        if (reset) sent = {-1, -1}, positive = {};
        else if (payload >= 0) {
            const int age = (round - static_cast<int>(payload >> (payload_shift + 1) & 3)) & 3;
            if (age <= 1 && pair[other].alive && !pair[other].is_self) {
                sent[other] = round - age;
                positive[other] = (payload >> payload_shift & 1) != 0;
            }
        }
        read_round = round;
        return true;
    }

    bool valid(int writer, int round) const {
        return read_round == round && sent[writer] >= 0 && round <= sent[writer] + 2
               && alive[protected_mate] && alive[healer] && positive[writer];
    }
};

} // namespace aph::comms::support_mailbox
