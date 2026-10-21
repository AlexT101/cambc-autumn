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
    // Flee mode (W3-A): danger and death priced instead of the guarded() ban, steps along `field`.
    bool flee = false;
    // The walk's steps when set (flee: home; chase: the prey's route), else to_altar/group's.
    const cambc::distance_field* field = nullptr;
};

// A visible enemy near enough to strike this turn, by walk, dash and attack range.
bool strike_possible(const World& world);

// What a shield (or heal) of `amount` lasting `duration` turns is worth at p: no more than could
// hit us there meanwhile.
float shield_cap(Safety& safety, vec2 p, float amount, int duration);

struct Planned {
    bool attacked = false;
    bool moved = false;    // the goal's walk is spent
    bool searched = false; // the search chose the turn's cast, heals and shields included
    bool goal_free = false; // W3-A: the chosen plan leaves the goal's walk and hits to the goal
    bool acted = false;     // W3-A: the plan spent an action
    bool carried = false;   // W3-A: the plan was carried out
};

// One read and grow of the turn's search, priced once per mode (W3-A). Valid until the turn's
// Safety generation or our state changes; the next prepare_strikes reuses its storage.
struct Prepared;
Prepared* prepare_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent);
Planned price_strikes(Prepared& prepared, const Intent& intent);
// Whether `prepared` still holds: safety's generation() and our state (my_state()) are as prepare_strikes found them.
bool prepared_current(const Prepared& prepared, const Safety& safety);

// Before the goal acts: prepare_strikes, then price_strikes.
Planned plan_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent);

// Turns the search does not plan (a retreat, a heal on spawn): a reset's second attack could kill
// an enemy, or a dash that lands on enemies is ready, so the cast is not spent on a shield first.
bool reset_may_kill(const World& world);
bool landing_ready(const World& world);

// The basic attack from here on the enemy it is worth most against, if any.
bool strike_enemy(const World& world);

// After the goal: the attack and cast still unspent, from where the walk ended.
void strike_after(const World& world, Pathing& pathing, Safety& safety);

} // namespace aph
