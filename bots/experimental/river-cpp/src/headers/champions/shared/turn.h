#pragma once

#include "../../../params.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <limits>
#include <memory>
#include <optional>
#include <span>
#include <vector>
#include "../../comms.h"

namespace aph {
class World;
class Pathing;
struct Trade;
class Safety;
struct Aims;
}
namespace aph {
namespace {
struct Use;
}
}

namespace aph {
class World;

class Pathing;

// The turn's aims. River keeps nothing between turns: play_turn works them out from what it sees at
// the turn's start, the steps refine them as they decide, and they end with the turn.
struct Aims {
    float damage = 0;     // lost since our turn before (World observes it)
    bool banking = false; // our bag heads for an altar rather than another capture
    int farm_group = -1;  // the group farm works towards: the one we are clearing until farm chooses
    int claim = -1;       // the group we work towards, or -1
    bool crew = false;    // joining an ally's claim rather than our own
    bool siege = false;   // our claim is a Monolith or a group sealing the altars (seals()), attacked by the team together
};

// `world` is as of the turn's start, observed again after a ward; ask cambc for anything that
// changes after acting. Fills `aims` afresh.
void play_turn(World& world, Pathing& pathing, Aims& aims);

// With the turn's spare fuel: the walk to our farm choice from where we ended, so that a costly
// turn next round still walks it well.
void prepare_next_turn(const World& world, Pathing& pathing, const Aims& aims);

}
namespace aph {
namespace {
constexpr int endgame_margin = 20;

constexpr int endgame_slack = 2;

constexpr float escape_step_value = 210;

// The turn's branch, for debug_fights: Chase, Attack, Retreat, Farm, Bank, Wait at an altar,
// Tribute kept / t cancelled, recall Kept / k cancelled, Healing on spawn, Shopping trip,
// holding (P), capture recall (Q), siege or kite of a big group (G), contest (X),
// stopping a game-ending bag (E).
char decision = '-';

bool sieged = false;

bool stunned_turn = false;

bool searched = false;

bool struck = false;

// The Prism-Willow support code chose this turn: the wrap-up's strike, heal, shield and recall stay out.
bool support_owned = false;

bool support_requested = false, support_offered = false, support_retreat = false;

bool end_ward = false;

vec2 searched_at{};

bool searched_hit = false;

// Read by tools/replay/fight_calibration.py.
void log_fight(const char* tag, const World& world, Safety& safety, vec2 p, const Trade& t, int target = -1);

// Our basic attacks and casts per slot over the game, counted at each turn's end (count_use).
struct Use {
    int attacks = 0;
    std::array<int, 2> casts{};
};

Use use;

// One state read: each is a host call.
bool channelling();

bool attack_enemy(const World& world);

bool see_revealed(World& world, Pathing& pathing, Safety& safety);

// What we see changed mid-turn. Safety's beliefs are fixed for its life, so it starts again.
[[gnu::noinline]] void see_again(World& world, Pathing& pathing, Safety& safety);

// A stun we cast takes its target's next turn, which Safety's threats and fights count: it starts again.
void see_stuns(World& world, Safety& safety);

// Our walk or dash brought an enemy into sight that could strike us, or that we could strike,
// before our next turn.
bool see_revealed(World& world, Pathing& pathing, Safety& safety);

}
}
namespace aph {
// The walk to our farm choice, from where we stand. Before the turn's optional work: what is left
// after it then pays for that work rather than the walk.
void prepare_walk(const World& world, Pathing& pathing, const Aims& aims, std::uint64_t fuel_floor);

void prepare_next_turn(const World& world, Pathing& pathing, const Aims& aims);

// From our state at the turn's end: a cast restarted its slot's cooldown, and the basic attack was
// spent unless a ranged walk spent it, a reset adding one (it restores only a spent attack).
void count_use(const World& world, vec2 start, bool could_attack);

// The turn's walk, hits and casts, and the free actions that end it.
void act(World& world, Pathing& pathing, Safety& safety, Aims& aims);

// The group we are clearing, as seen: one whose capture we hold, else the nearest live group with an
// awake member in our attack range; -1 if none.
int engaged_group(const World& world, Pathing& pathing);

void play_turn(World& world, Pathing& pathing, Aims& aims);

}
