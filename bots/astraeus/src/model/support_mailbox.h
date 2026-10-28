#pragma once

#include <array>
#include <cstdint>

namespace aph::comms::support_mailbox {

// The protected mate's request for heals and the healer's offer, each sent in its own priority
// payload above the claim (comms.cc), so the other reads it only while it sees the sender. A message
// is the intent and its round mod 4: a priority read at our turn start was set this round or last.
inline constexpr int protected_mate = 0; // support_protected: Prism, or Tavi on some 3-pick maps
inline constexpr int healer = 1;         // support_healer: Willow
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
    bool both_alive = false; // as of read_round
    std::array<int, 2> sent{-1, -1}, respawn{-1, -1};
    std::array<bool, 2> positive{};

    // `payload`: the other endpoint's priority payload as read this round, or -1 if unread.
    // Messages are dropped unless both endpoints have stayed alive since our previous turn's read.
    void receive(int round, const std::array<Endpoint, 2>& pair, int other, std::int64_t payload) {
        if (read_round == round) return;
        bool alive = true, respawned = false;
        for (int i = 0; i < 2; ++i) {
            alive &= pair[i].present && pair[i].alive;
            const int r = pair[i].present ? pair[i].respawned_round : -1;
            respawned |= r != respawn[i];
            respawn[i] = r;
        }
        const bool continuous = read_round == round - 1 && both_alive && alive && !respawned;
        read_round = round;
        both_alive = alive;
        if (!continuous) {
            sent = {-1, -1}, positive = {};
        } else if (payload >= 0 && !pair[other].is_self) {
            // Older than last round, it is from a turn the sender skipped (out of fuel).
            const int age = (round - static_cast<int>(payload >> (payload_shift + 1) & 3)) & 3;
            if (age <= 1) {
                sent[other] = round - age;
                positive[other] = (payload >> payload_shift & 1) != 0;
            }
        }
    }

    // Whether `writer`'s latest message, sent within the last two rounds, is positive.
    bool valid(int writer, int round) const {
        return read_round == round && positive[writer] && round <= sent[writer] + 2;
    }
};

} // namespace aph::comms::support_mailbox
