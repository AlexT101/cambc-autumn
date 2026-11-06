// Turns of travel for a champion with a dash (cambc-rules.yaml turn.walk, abilities.dash, .cooldown):
// each turn one walk step and, while the dash is ready, one dash of up to 2 king steps, in either
// order. `c` is the cooldown at the next turn's start: turns are counted from 1, the next turn, and
// the dash is ready on turn c + 1. A dash cast on a turn is ready again 8 turns later, so a turn that
// dashes leaves c = 7.
#pragma once
#include <algorithm>
#include "../champions.h"

namespace aph::dash_turns {

inline constexpr int after_dash = ability_cooldown - 1;

// Turns to cover s steps of open ground, dashing whenever ready. Any two steps of a walk are a dash
// path (a walkable tile never blocks one), so a dash is worth exactly two steps wherever it is cast:
// past c, m turns cover m + 2 per dash in them, 10j + i + 2 for m = 8j + i (i in 1..8).
constexpr int open(int s, int c) {
    if (s <= 0) return 0;
    if (s <= c) return s;
    const int r = s - c, j = (r - 1) / (ability_cooldown + dash_range);
    return c + ability_cooldown * j + std::max(1, r - (ability_cooldown + dash_range) * j - dash_range);
}

// Steps t turns cover from cooldown c, dashing whenever ready: open(reach(t, c), c) <= t < open(reach(t, c) + 1, c).
constexpr int reach(int t, int c) { return t <= 0 ? 0 : t + (t > c ? dash_range * ((t - c - 1) / ability_cooldown + 1) : 0); }

// Turns by way of a line (holes or altars) only a dash crosses: `a` steps to its launch tile, then
// the 2-step crossing, then `rest` steps beyond the landing. A dash before the launch counts only if
// it is ready again on arrival; arriving before the dash is, we wait on the launch tile and cross with
// a dash then a walk. Arriving with it ready, the walk onto the launch and the crossing share a turn.
constexpr int across(int a, int rest, int c) {
    int best = 1 << 20;
    for (int e = 0; 2 * e <= a; ++e) { // e dashes before the launch, the first on turn c + 1
        const int arrive = a - 2 * e, ready = c + 1 + ability_cooldown * e;
        if (e > 0 && (arrive < 1 || ready - ability_cooldown > arrive)) break;
        best = std::min(best, arrive >= ready ? arrive + open(rest, after_dash) : ready + open(rest - 1, after_dash));
    }
    return best;
}

static_assert(open(3, 0) == 1 && open(4, 0) == 2 && open(10, 0) == 8 && open(11, 0) == 9 && open(13, 0) == 9);
static_assert(open(7, 7) == 7 && open(9, 7) == 8 && open(1, 3) == 1);
static_assert(across(0, 4, 3) == 4 + open(3, after_dash) && across(5, 10, 0) == 5 + open(10, after_dash));
static_assert(across(12, 5, 0) == 10 + 5);
static_assert(reach(1, 0) == 3 && reach(8, 0) == 10 && reach(9, 0) == 13 && reach(7, 7) == 7 && reach(8, 7) == 10);

} // namespace aph::dash_turns
