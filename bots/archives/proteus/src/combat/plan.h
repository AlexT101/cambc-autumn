// The turn's strikes on enemy champions, planned over the legal action sequences: a basic attack, a
// reset and second attack, an enemy cast, a dash, a walk, a heal or a shield, with one cast a turn.
// Each plan is scored in enemy health points: what its hits are worth, plus the goal's progress at
// a turn of our output a step, less the damage we expect at the tile it ends on.
#pragma once
#include "../util.h"

namespace aph {

class World;
class Pathing;
class Safety;

// What the turn's goal does after the strikes: stays (holding a capture, at an altar), or walks a
// step along `field` (null: a way the planner cannot read), each step worth `step_value`.
struct Intent {
    bool walks = false;
    bool anchored = false; // must not leave this tile
    // Anchored to a capture: any of its tiles holds it, so the strikes may move between them.
    const bitboard* hold = nullptr;
    // Where the walk goes, read only when a move is priced: to an altar, else to `group`.
    bool to_altar = false;
    int group = -1;
    // A chase under way: the walk goes towards this tile as the crow flies instead.
    vec2 aim{-1, -1};
    float step_value = 0;
};

// While one is held, nothing that step_guard reads changes: the step guard reuses the first pass
// its cover made from the same tile (the strike search, from reading to its plan).
struct GuardInputsHeld {
    GuardInputsHeld();
    ~GuardInputsHeld();
    void release();
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

// A turn leaving the fight: the strike search's plans that keep our kill bid (follow.h), behind the
// step guard, if any; else nothing.
Planned keep_bid(const World& world, Pathing& pathing, Safety& safety);

// After the goal: the search again from where it left us, for the attack and cast still unspent,
// without moving.
Planned strike_after(const World& world, Pathing& pathing, Safety& safety);

// Fills the terrain-only tables a fight around p reads (Reach's and the search's), each exactly as
// a miss would; p is not a wall.
void warm_tile(const World& world, vec2 p);

} // namespace aph
