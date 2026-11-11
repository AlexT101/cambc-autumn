// The team's 8 shared bytes. A write is visible at once to teammates who act later; earlier ones
// see it next round. Records carry no round: each instance processes a shared record only when its
// bits change, which every teammate sees within a round of the write.
#pragma once
#include <array>
#include "world.h"

namespace aph::comms {

namespace detail {
// The latest bags and claims: teammates' as they posted them, by ally index, and ours.
struct Posts {
    std::array<int, 8> bags{};
    std::array<int, 8> claims{-1, -1, -1, -1, -1, -1, -1, -1};
    int my_bag = 0, mine = -1;
};
inline Posts posts;
} // namespace detail

// What teammates posted since our previous turn, merged into the world.
void receive(World& world);
// At the turn's end. With `refresh`, re-read vision first.
void send(World& world, bool moved, bool refresh);
// Next round's seat ledger: the allies that took an early seat this round, each at a key that,
// with its index, fixes its priority (turn_order.cc seat_rank), so every teammate knows the top of
// next round's order without seeing them. Written by the seat's owner at its turn end; read this
// round by teammates acting later. `loss`: what moving one seat later would cost it, tier 0-3.
inline constexpr int seat_cap = 3;
struct SeatEntry {
    int ally = -1, key = 0, loss = 0;
};
// Entries that fit in the layout (0: no ledger; every ally then bids alone), and keys, 4 or 8.
int seat_capacity(const World& world);
int seat_keys(const World& world);
// This round's entries so far, as read at our turn start.
int seats(const World& world, std::array<SeatEntry, seat_cap>& out);
// Adds or replaces our entry; false when there is no free entry or the turn is stale.
bool post_seat(const World& world, const SeatEntry& entry);
// The gems we carry, posted when it changes.
void bag(int gems);
// The gems an ally (by index) carries as it last posted, rounded up to a multiple of 4 and capped
// at 508 (ours exact); 0 if never or while dead.
inline int bag_of(const World& world, int ally) {
    const auto& a = world.allies[ally];
    if (a.is_self) return detail::posts.my_bag;
    return a.alive ? detail::posts.bags[ally] : 0;
}
// The group we work towards (-1 for none), posted every turn.
void claim(int group);
// The other support endpoint's intent (the protected mate's request, the healer's offer), posted in
// its priority within the last two rounds and read while we saw it. Both endpoints must be alive;
// the caller still checks the other's position.
bool support_request(const World& world);
bool support_available(const World& world);
// Our own intent this round, published by priority_payload().
void support_intent(int round, bool positive);
// Our priority payload: the claim and support intents posted this turn.
std::uint32_t priority_payload(const World& world);
// The group an ally (by index) claims, -1 for none or while it is dead.
inline int claim_of(const World& world, int ally) {
    const auto& a = world.allies[ally];
    if (a.is_self) return detail::posts.mine;
    return a.alive ? detail::posts.claims[ally] : -1;
}

} // namespace aph::comms
