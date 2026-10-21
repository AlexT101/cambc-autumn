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
    // A flee (retreat): every move is the search's, each step along `field` worth `step_value`; no
    // guarded() ban. Visible blows count in full, unseen ones at their chance, the camps' hit plus
    // their rounds to walk out, and our death (life_value and the bag) where the worst could kill
    // us. Inside a camp's reach only a tile out of every reach earns steps; with no visible enemy
    // near, the least Safety::escape_cost wins.
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
    bool goal_free = false; // no plan ended off our tile: another walk goal would choose the same
    bool acted = false;     // an action was taken: the turn-start beliefs no longer hold
    bool carried = false;   // a plan was chosen and carried out
};

// One read and grow of the turn's search, priced by mode: normal, flee (Intent::flee) or chase
// (Intent::field). Leaves keep no step terms, so a price may use another step value or walk, but
// a flee's pure moves exist only when prepared for a flee. Valid until the Safety generation or
// our state changes (price_strikes then returns an empty Planned; on a turn resumed after running
// out of fuel it throws, as World::throw_if_stale); the next prepare_strikes reuses its storage.
// Never null.
struct Prepared;
Prepared* prepare_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent);
Planned price_strikes(Prepared& prepared, const Intent& intent);
// Whether `prepared` still holds: safety's generation() and our state, tile and health are as
// prepare_strikes found them.
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
