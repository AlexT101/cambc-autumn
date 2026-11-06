// Turn order within the team for next round. Teams alternate one champion at a time, so an ally
// ranked higher acts before more enemies; each ally sets its own priority from what it needs.
#pragma once
#include <cstdint>
#include "../fish/switches.h"

namespace aph {

class World;
class Safety;

// Fish's priorities carry no payload (turn_order.cc): every bit is the order.
inline constexpr int priority_payload_bits = FISH_PRIORITY ? 0 : 16;

// Ranks us for next round by Fish's encoding; publish_turn_order sets it if it changed (the payload is ignored).
void set_turn_order(const World& world, Safety& safety);
void publish_turn_order(const World& world, std::uint32_t payload);

} // namespace aph
