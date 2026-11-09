// Escape planning (research/retreat-2026-11-09): the race over our next turns between our walk (and
// dash) home and the pursuers' reach, on a window of the map around us. Retreat's walk and escape dash
// rank their moves by it beyond the turn Safety prices exactly, so a route that bends round the
// pursuers, crosses a hole line they must walk round, hides in a bush they would have to enter, or
// takes one hit now to be clear after, wins over the step that only looks safe this turn.
//
// Model, per our turn k (the current one is 1): we walk a king step and, once ready, may dash 2 more
// (across holes and altars) once. A pursuer walks a step a turn and dashes once when ready; a melee
// one hits within its basic reach after moving, a ranged one only without walking (its walk spends
// the attack), after a dash if it has one. Bush tiles are seen only from bush tiles (each cluster's
// own, approximated). Terrain and live camps only: units, spells and turn order are Safety's.
// A hit is a turn ending in some pursuer's reach. Our spawn is never hit: its turn end heals.
// Goal: to the tiles on our home field (Pathing::to_ally_spawn) at most `horizon` walking steps nearer than now by the plan's
// last turn (full), or slack_steps short of that (slack, worked out only when asked).
//
// The same race runs with the sides swapped for a chase (build_chase): a visible enemy runs to its own
// spawn from its tile, where its last turn ended, and our pursuers are this champion and the visible
// allies. Their intent is ours to know, so the worst case falls on the runner: a clean way home for it
// means no pursuit of ours, however good, lands a hit before it gets there.
#pragma once
#include <array>
#include <cstdint>
#include "../params.h"
#include "../util.h"

namespace aph {

class World;
class Pathing;
class Safety;
struct ChampionBelief;

namespace escape {

inline constexpr int horizon = 5;              // our turns planned, this one included
inline constexpr int radius = horizon + 2;     // the window: tiles within this of us (horizon walks and a dash)
inline constexpr int side = 2 * radius + 1;
inline constexpr int many = 2;                 // hits are counted 0, 1, or 2 for two or more (or no way to the goal)

// Window row y is bits 0..side-1 of lane y % 8 of vector y / 8 (SIMD128 in the bot: our own code
// costs about a fuel a wasm instruction, so a scalar row loop costs several times as much).
using Lanes = std::uint16_t __attribute__((vector_size(16)));
static_assert(side <= 16 && side > 8);
struct Rows {
    Lanes v[2]{};
};

class Plan {
public:
    bool active() const { return active_; }
    // Hits on turns 2..horizon after a walk this turn that ends on p, the dash (if the plan has one)
    // still to come. Off the window: many.
    int after_walk(vec2 p, bool slack) const;
    // A dash now that lands on p, then this turn's walk: hits on turns 1..horizon.
    int after_dash(vec2 p, bool slack) const;
    // This turn's walk with the dash kept: hits on turns 1..horizon.
    int keep_dash(bool slack) const;
    bool dash_now() const { return dash_now_; } // a dash of ours can be cast this turn
    // The slack pass, worked out on first ask; until then the slack values read as the full ones.
    void want_slack();
    bool slack_ready() const { return pass_[1].ready; }

    // Built from our tile for this turn: inactive with no pursuer in the window, our home unreachable,
    // or the fuel short.
    void build(const World& world, Pathing& pathing, Safety& safety);
    // The chase race: `target` (visible) runs home from its tile; we pursue from this turn's start tile with
    // the turn's moves still ours, as do the visible allies. Turn 1 is the target's last, now ended, so its
    // pursuers' first turns (ours this one) hit it where it stands. Inactive on its spawn or with it cut off.
    void build_chase(const World& world, Pathing& pathing, const ChampionBelief& target);
    // A chase plan's runner: its hits, turns 1..horizon, on its best way to the goal (`many` past one).
    int runner_hits(bool slack) const;
    bool runner_hit_now() const; // its tile in reach of our pursuers' first turns

    // The cache key: rebuilt when any of these change.
    int round = -1;
    std::uint32_t handle = 0, observations = 0; // World::observations: what the beliefs were read from
    vec2 at{-1, -1};

public:
    struct Pass {
        bool ready = false;
        // By hits allowed (0, 1) and dash kept (0 spent or none, 1 kept): S_1, the tiles from which,
        // after turn 1, the goal is reached by `horizon` within those hits.
        Rows after[2][2];
        Rows dashed[2]; // the tiles a dash now may land on: this turn's walk from them, then S_1 (dash spent)
        Rows kept[2];   // this turn's walk without a dash, then S_1 (dash kept)
    };

private:
    struct Race;
    void finish(Pathing& pathing, Race& race);
    void run(const Rows& goal, Pass& out) const;
    int value(const Rows& none, const Rows& one, vec2 p) const;
    const Pass& pass(bool slack) const { return pass_[slack && pass_[1].ready ? 1 : 0]; }

    bool active_ = false, dash_ = false, dash_now_ = false;
    int dash_turn_ = 0; // our first turn (2..horizon) a planned dash may fall in
    vec2 origin_{0, 0}; // the window's tile (0, 0)
    Rows walk_{}, path_{}, slack_goal_{}; // our walk and landing tiles, the tiles a dash path of ours crosses
    std::array<Rows, horizon + 1> hit_{}; // [k]: tiles where a turn k ending there is hit
    Pass pass_[2];
};

// The plan for this turn from our tile, built on first ask and kept while its key holds.
Plan& plan(const World& world, Pathing& pathing, Safety& safety);

// The chase plan against a visible enemy this round, built on first ask (null if the fuel left is under
// `need` then) and kept for the round: nothing it reads moves during our turn.
Plan* chase_plan(const World& world, Pathing& pathing, const ChampionBelief& target, std::uint64_t need);

// A first move's rank, lower first, from its hits on the full and slack goals (this turn's included):
// a hit weighs hit_steps steps of progress home, and the slack goal costs slack_steps.
inline int rank(int full, int slack) {
    const int a = params::escape::hit_steps * full, b = params::escape::hit_steps * slack + params::escape::slack_steps;
    return a < b ? a : b;
}

} // namespace escape

} // namespace aph
