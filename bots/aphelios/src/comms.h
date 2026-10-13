// Comms: the team's 8 bytes of shared memory as a typed message; the bit layout is in comms.cpp.
//
// Shared memory is read/write all match, and a write is visible at once to teammates who act
// later; a teammate who acted earlier sees it next round.
#pragma once
#include <optional>
#include "util.h"

namespace aph {

class World;

namespace comms {

// The freshest enemy sighting any teammate has posted.
struct Sighting {
    int round;       // 1-2000
    int enemy_index; // index into World::enemies
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

// Merge teammates' information into the world (start of turn).
void receive(World& world);
// Publish what this instance learned this turn (end of turn).
void send(const World& world);

} // namespace comms
} // namespace aph
