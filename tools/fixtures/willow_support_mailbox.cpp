#include <array>
#include <cassert>
#include <cstdint>
#include "../../bots/hyperion/src/support_mailbox.h"

namespace mailbox = aph::comms::support_mailbox;

constexpr std::array<mailbox::Endpoint, 2> remote_pair{{
    {true, true, false, 0},
    {true, true, false, 0},
}};

std::uint64_t code_bits(int round, bool positive, std::uint64_t base = 0) {
    mailbox::write(base, round, positive);
    return base;
}

void accepted(std::uint64_t base_round, int age) {
    mailbox::State s;
    auto bits = code_bits(static_cast<int>(base_round), false);
    assert(s.receive(static_cast<int>(base_round - 1), bits, remote_pair));
    for (int r = static_cast<int>(base_round); r < static_cast<int>(base_round + age); ++r)
        assert(s.receive(r, bits, remote_pair));
    bits = code_bits(static_cast<int>(base_round), true);
    const int now = static_cast<int>(base_round + age);
    assert(s.receive(now, bits, remote_pair));
    const int writer = static_cast<int>(base_round & 1);
    assert(s.sent[writer] == static_cast<int>(base_round));
    assert(s.positive[writer]);
}

void rejected_stale(std::uint64_t base_round, int age) {
    mailbox::State s;
    auto bits = code_bits(static_cast<int>(base_round), false);
    assert(s.receive(static_cast<int>(base_round - 1), bits, remote_pair));
    for (int r = static_cast<int>(base_round); r < static_cast<int>(base_round + age); ++r)
        assert(s.receive(r, bits, remote_pair));
    bits = code_bits(static_cast<int>(base_round), true);
    assert(s.receive(static_cast<int>(base_round + age), bits, remote_pair));
    assert(s.sent[0] < 0 && s.sent[1] < 0);
}

int main() {
    // A positive is publishable only for this round's own positive intent and a live pair.
    assert(mailbox::publish_value(12, 12, true, true));
    assert(!mailbox::publish_value(12, 11, true, true));
    assert(!mailbox::publish_value(12, 12, false, true));
    assert(!mailbox::publish_value(12, 12, true, false));

    // All 8 payload/epoch words round-trip, while write preserves each of the other 61 bits.
    const std::uint64_t unrelated = ~mailbox::bits_mask;
    for (int epoch = 0; epoch < 4; ++epoch)
        for (int payload = 0; payload < 2; ++payload) {
            auto bits = unrelated;
            mailbox::write(bits, epoch, payload != 0);
            assert(mailbox::payload(bits) == payload);
            assert(mailbox::epoch(bits) == epoch);
            assert((bits & ~mailbox::bits_mask) == unrelated);
        }

    // First read seeds raw/presence/respawn state only; its apparent positive is not accepted.
    mailbox::State seeded;
    auto bits = code_bits(20, true);
    assert(seeded.receive(20, bits, remote_pair));
    assert(seeded.sent[0] < 0 && seeded.sent[1] < 0);
    assert(seeded.receive(21, bits, remote_pair));
    assert(seeded.sent[0] < 0 && seeded.sent[1] < 0); // unchanged raw does not refresh/accept

    // Changed age zero and one codes are accepted from their parity-owned endpoint.
    for (int epoch = 0; epoch < 4; ++epoch) {
        const auto base = static_cast<std::uint64_t>(100 + epoch);
        accepted(base, 0); // even/odd owner follows the encoded send round
        accepted(base, 1);
    }
    rejected_stale(24, 2);
    rejected_stale(25, 3);

    // A changed word from our own endpoint is ignored.
    mailbox::State own;
    const std::array<mailbox::Endpoint, 2> prism_self{{
        {true, true, true, 0}, {true, true, false, 0},
    }};
    bits = code_bits(29, false);
    assert(own.receive(28, bits, prism_self));
    assert(own.receive(29, bits, prism_self));
    bits = code_bits(30, true);
    assert(own.receive(30, bits, prism_self));
    assert(own.sent[0] < 0);
    mailbox::State own_willow;
    const std::array<mailbox::Endpoint, 2> willow_self{{
        {true, true, false, 0}, {true, true, true, 0},
    }};
    bits = code_bits(30, false);
    assert(own_willow.receive(29, bits, willow_self));
    assert(own_willow.receive(30, bits, willow_self));
    bits = code_bits(31, true);
    assert(own_willow.receive(31, bits, willow_self));
    assert(own_willow.sent[1] < 0);

    // Repeated receive in a round is idempotent, including if the shared word changes afterward.
    mailbox::State once;
    bits = code_bits(39, false);
    assert(once.receive(38, bits, remote_pair));
    assert(once.receive(39, bits, remote_pair));
    bits = code_bits(40, true);
    assert(once.receive(40, bits, remote_pair));
    assert(once.valid(mailbox::prism, 40));
    const auto before = once;
    assert(!once.receive(40, code_bits(40, false), remote_pair));
    assert(once.raw == before.raw && once.sent == before.sent && once.positive == before.positive);
    assert(once.valid(mailbox::prism, 40));

    // No-change reads retain the original absolute timestamp and expire at sent+3.
    mailbox::State expiry;
    bits = code_bits(50, false);
    assert(expiry.receive(49, bits, remote_pair));
    bits = code_bits(50, true);
    assert(expiry.receive(50, bits, remote_pair));
    for (int r = 51; r <= 53; ++r) {
        assert(expiry.receive(r, bits, remote_pair));
        assert(expiry.valid(mailbox::prism, r) == (r <= 52));
    }

    // A skipped round or rollback reseeds; a missing endpoint, death, or respawn also clears it.
    mailbox::State reset;
    bits = code_bits(60, false);
    assert(reset.receive(59, bits, remote_pair));
    bits = code_bits(60, true);
    assert(reset.receive(60, bits, remote_pair));
    assert(reset.sent[mailbox::prism] == 60);
    assert(reset.receive(62, bits, remote_pair));
    assert(reset.sent[mailbox::prism] < 0);
    assert(reset.receive(61, bits, remote_pair));
    assert(reset.sent[mailbox::prism] < 0);

    mailbox::State missing;
    bits = code_bits(70, false);
    assert(missing.receive(69, bits, remote_pair));
    bits = code_bits(70, true);
    assert(missing.receive(70, bits, remote_pair));
    auto no_willow = remote_pair;
    no_willow[mailbox::willow] = {};
    assert(missing.receive(71, bits, no_willow));
    assert(missing.sent[0] < 0 && !missing.alive[mailbox::willow]);

    mailbox::State death;
    bits = code_bits(80, false);
    assert(death.receive(79, bits, remote_pair));
    bits = code_bits(80, true);
    assert(death.receive(80, bits, remote_pair));
    auto dead_prism = remote_pair;
    dead_prism[mailbox::prism].alive = false;
    assert(death.receive(81, bits, dead_prism));
    assert(death.sent[0] < 0 && !death.alive[mailbox::prism]);

    mailbox::State respawn;
    bits = code_bits(90, false);
    auto old_life = remote_pair;
    old_life[mailbox::prism].respawned_round = 12;
    assert(respawn.receive(89, bits, old_life));
    bits = code_bits(90, true);
    assert(respawn.receive(90, bits, old_life));
    auto new_life = old_life;
    new_life[mailbox::prism].respawned_round = 91;
    assert(respawn.receive(91, bits, new_life));
    assert(respawn.sent[0] < 0);
}
