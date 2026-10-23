#pragma once
#include <algorithm>

namespace aph {

// Optimistic movement envelope: allow damage after walking, with no terrain or cast conflicts.
constexpr int earliest_work_delay(int gap, int first_turn, int dash_ready, int dash_steps, int dash_period, bool kill_resets) {
    if (gap <= 0) return 0;
    if (dash_steps <= 0) return first_turn + gap - 1;
    if (kill_resets) return first_turn + (gap - 1) / (1 + dash_steps);
    const int first_dash = std::max(first_turn, dash_ready);
    if (gap <= first_dash - first_turn) return first_turn + gap - 1;
    const int left = gap - (first_dash - first_turn + 1 + dash_steps);
    if (left <= 0) return first_dash;
    const int cycle = dash_period + dash_steps;
    return first_dash + (left - 1) / cycle * dash_period + std::min(1 + (left - 1) % cycle, dash_period);
}

} // namespace aph
