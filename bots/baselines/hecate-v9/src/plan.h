// The turn's strikes on enemy champions, planned over the legal action sequences (cambc-rules.yaml
// turn and abilities): a basic attack, a reset and second attack, an enemy cast, a dash, a walk,
// with one successful cast a turn. Each plan is scored in enemy health points: what its hits are
// worth, plus the goal's progress at a turn of our output a step, less the damage we expect at the
// tile it ends on.
#pragma once
#include "util.h"

namespace aph {

class World;
class Pathing;
class Safety;

// What the turn's goal does after the strikes: stays (holding a capture, at an altar), or walks a
// step along `field` (null: a way the planner cannot read), each step worth `step_value`.
struct Intent {
    bool walks = false;
    bool anchored = false; // must not leave this tile
    // Where the walk goes, read only when a move is priced: to an altar, else to `group`.
    bool to_altar = false;
    int group = -1;
    float step_value = 0;
    bool keep_walk = false; // carrying: cast_at_enemies' own walk threshold prices the walk
};

// A carrier's step, as cast_at_enemies prices it: its keep-walk threshold less a cast's cost.
inline constexpr float carried_step_value = 210;

// A visible enemy near enough to strike this turn, by walk, dash and attack range.
bool strike_possible(const World& world);

struct Planned {
    bool attacked = false;
    bool moved = false; // the goal's walk is spent
};

// Before the goal acts.
Planned plan_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent);

// A reset's second attack could kill an enemy this turn: a cast worth keeping for the plan.
bool reset_may_kill(const World& world);
// A dash that lands on enemies is ready: likewise.
bool landing_ready(const World& world);

// The basic attack from here on the enemy it is worth most against, if any.
bool strike_enemy(const World& world);

// After the goal: the attack and cast still unspent, from where the walk ended.
void strike_after(const World& world, Safety& safety);

} // namespace aph
