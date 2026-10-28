#pragma once
#include <algorithm>
#include <cmath>

namespace aph {

// Healthier champions act first, so they take camps' tie hits; role breaks ties within a tenth.
// Shield counts up to max health. Carrying any gems halves the health fraction: a full-health
// carrier ranks with a gemless champion at half health. Range: role + idle_step at full health
// down to role + idle_step * (1 - health_buckets) at none.
inline constexpr int idle_step = 8, health_buckets = 10;

inline int idle_priority(int role, float health, float shield, float max_health, int gems) {
    const float effective_hp = std::min(health + shield, max_health);
    const float denominator = max_health * (gems > 0 ? 2.0f : 1.0f);
    const int missing = static_cast<int>(std::floor(static_cast<float>(health_buckets) * (1.0f - effective_hp / denominator)));
    return role + idle_step * (1 - missing);
}

} // namespace aph
