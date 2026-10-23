// The turn's strikes on enemy champions, planned over the legal action sequences (cambc-rules.yaml
// turn and abilities): a basic attack, a reset and second attack, an enemy cast, a dash, a walk,
// a heal or a shield, with one successful cast a turn. Each plan is scored in enemy health points: what its hits are
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
};

// A visible enemy near enough to strike this turn, by walk, dash and attack range.
bool strike_possible(const World& world);

struct Planned {
    bool attacked = false;
    bool moved = false;    // the goal's walk is spent
    bool searched = false; // the search chose the turn's cast, heals and shields included
};

// Before the goal acts.
Planned plan_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent);

// Turns the search does not plan (a retreat, a heal on spawn): a reset's second attack could kill
// an enemy, or a dash that lands on enemies is ready, so the cast is not spent on a shield first.
bool reset_may_kill(const World& world);
bool landing_ready(const World& world);

// The basic attack from here on the enemy it is worth most against, if any.
bool strike_enemy(const World& world);

// After the goal: the search again from where it left us, for the attack and cast still unspent,
// without moving.
Planned strike_after(const World& world, Pathing& pathing, Safety& safety);

} // namespace aph
