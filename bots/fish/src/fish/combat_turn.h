// Intercontinental Fish's behaviour around and against enemies (FISH_MODEL sections 9, 10, 12), in
// place of astraeus's strike search, chase, step guard and wards (fish::use_combat, fish::use_wards).
// Every rule reads the turn-start view, as fitted (tools/fish/combat_rules.py, micro_*.py, tactic_*.py).
#pragma once
#include <optional>
#include "../util.h"

namespace aph {

class World;
class Pathing;
class Safety;
struct Memory;

namespace {
namespace fishc {

struct Contact {
    bool done = false;     // the fight took the turn's walk: the goal does not walk
    bool attacked = false; // an enemy champion was hit
    bool stay_out = false; // m2 declined from an acceptable tile: the goal walks, off tiles adjacent to enemies
};

// The fight's part of the turn, before the goal: Willow's heal, a spell kill from here, a dash kill,
// stand-and-cast, the positioning contexts m2 / m1 / r (engage iff kill or h > 0.49 and danger <=
// 0.28; declines to the lowest-danger farther tile), the chase rule, basic and spell targets and
// attack resets. `holding`: a running capture holds, so only its tiles are candidates.
Contact contact_turn(World& world, Pathing& pathing, Safety& safety, Memory& memory, bool holding);

// A visible enemy within 3 at the turn start: Fish's contact rules (10) own the turn.
bool in_contact(const World& world);

// After the goal walked: the attack and casts still unspent (in place of strike_after).
void after_goal(World& world);

// Before farming, with a visible enemy within 4 and the walk unspent: camp hits stop (keep hitting
// iff the nearest enemy is beyond 4). Healthy, a step closing on it to an acceptable tile; hurt, the
// lowest-danger step away, homeward. False to let the farm go on.
bool near_turn(World& world, Pathing& pathing, Safety& safety);

// The route bends by health: at h <= 0.5, steps closing on the nearest visible enemy are guarded.
const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius);

// The basic attack on argmin (EHP, id) in range, if any (10.4).
bool basic_hit(const World& world);

// Willow: heal iff a visible ally within 4 is injured, the one with most of min(missing, heal) / max.
bool heal(const World& world);
// Heart of Ruin's shield rule: a visible enemy not stunned for its next turn has D > 0 against us.
bool hor_threatened(const World& world);

// A ward at the context's rate (contact 8%, enemy in sight 5%, none 2.9% of ready turns) on the
// tile within 2 that adds the most unseen bush tiles; allied wards are not tracked.
bool place_ward(const World& world, Memory& memory);

} // namespace fishc
} // namespace

} // namespace aph
