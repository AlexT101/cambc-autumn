// Turn order within the team for next round. Teams alternate one champion at a time, so an ally
// ranked higher acts before more enemies; each ally sets its own priority from what it needs.
#pragma once
#include <cstdint>

namespace aph {

class World;
class Safety;

// A priority's low bits, below its rank: free for comms, readable by whoever sees the champion.
// None in a priority of 0, which only a champion yet to publish has.
inline constexpr int priority_payload_bits = 16;

// Ranks us for next round; publish_turn_order sets it, with the payload, once the turn's claim and
// intents are final.
void set_turn_order(const World& world, Safety& safety);
void publish_turn_order(const World& world, std::uint32_t payload);

} // namespace aph
