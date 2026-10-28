#pragma once
#include <algorithm>

namespace aph {

// The turn, counted from 0, on which a champion `gap` tiles beyond its reach first deals damage
// (so also the turns of work it misses). It acts from turn `first_turn`, walks a tile a turn, and
// from turn `dash_ready` dashes `dash_steps` more every `dash_period` turns.
// Optimistic: it may damage after walking, and terrain and cast conflicts are ignored.
// `kill_resets`: an unseen kill may have readied the dash, but the walk itself kills nothing.
constexpr int earliest_work_delay(int gap, int first_turn, int dash_ready, int dash_steps, int dash_period, bool kill_resets) {
    if (gap <= 0) return 0;
    if (dash_steps <= 0) return first_turn + gap - 1;
    const int first_dash = std::max(first_turn, kill_resets ? 0 : dash_ready);
    if (gap <= first_dash - first_turn) return first_turn + gap - 1; // arrives walking before the dash is ready
    const int left = gap - (first_dash - first_turn + 1 + dash_steps);
    if (left <= 0) return first_dash;
    // Each later cycle of dash_period turns closes dash_period - 1 walked tiles, then a dash turn's 1 + dash_steps.
    const int cycle = dash_period + dash_steps;
    return first_dash + (left - 1) / cycle * dash_period + std::min(1 + (left - 1) % cycle, dash_period);
}

static_assert(earliest_work_delay(0, 1, 9, 2, 8, false) == 0);
static_assert(earliest_work_delay(3, 1, 0, 0, 8, false) == 3);
static_assert(earliest_work_delay(4, 0, 5, 2, 8, false) == 3);
static_assert(earliest_work_delay(6, 0, 5, 2, 8, false) == 5);
static_assert(earliest_work_delay(11, 0, 0, 2, 8, false) == 8); // tiles 4-10 walked, 11 on the second dash
static_assert(earliest_work_delay(14, 0, 0, 2, 8, false) == 9);
static_assert(earliest_work_delay(6, 1, 5, 2, 8, true) == 4);

} // namespace aph
