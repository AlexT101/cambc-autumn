#pragma once
#include <algorithm>
#include <cmath>

namespace aph {

// An idle priority falls by idle_step for each tenth of health missing.
inline constexpr int idle_step = 8, health_buckets = 10;

inline int idle_priority(int role, float health, float shield, float max_health, int gems) {
    const float effective_hp = std::min(health + shield, max_health);
    const float denominator = max_health * (gems > 0 ? 2.0f : 1.0f);
    return role + idle_step - idle_step * static_cast<int>(std::floor(static_cast<float>(health_buckets) * (1.0f - effective_hp / denominator)));
}

} // namespace aph
