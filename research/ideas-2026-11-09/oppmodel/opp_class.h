#pragma once
// Which team we face: a posterior over {Intercontinental Fish, Mite, other}, from the enemy's pick
// order and the priorities of enemies in sight. Each champion instance keeps its own, from its own
// sightings. Read-only for the rest of the bot.
#include <cstdint>

namespace aph {
class World;

namespace opp {

struct Posterior {
    float fish = 0.25f, mite = 0.25f, other = 0.5f;
};

// Distinct (enemy, value) priority reads by the encoding they match.
struct Evidence {
    std::uint16_t fish_hits = 0, mite_hits = 0, other_hits = 0, zero_hits = 0;
    std::int16_t first_round_fish = -1, first_round_mite = -1; // first matching read
};

// Called once a turn at the end of World::update.
void observe(const World& world);
const Posterior& posterior(const World& world);
const Evidence& evidence(const World& world);

} // namespace opp
} // namespace aph
