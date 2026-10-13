// A shared-memory write is visible at once to teammates who act later; earlier ones see it next
// round.
#pragma once
#include <optional>
#include "util.h"

namespace aph {

class World;

namespace comms {

struct Sighting {
    int round;
    int enemy_index;
    vec2 pos;
};

struct Message {
    std::optional<Sighting> sighting;
};

// Placeholder schema.
Message decode(std::uint64_t bits);
std::uint64_t encode(const Message& message);

Message read();
void write(const Message& message);

void receive(World& world);
// With `refresh`, re-read vision first, but only if there is a slot to fill.
void send(World& world, bool refresh);

} // namespace comms
} // namespace aph
