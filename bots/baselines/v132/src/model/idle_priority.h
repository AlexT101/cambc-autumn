#pragma once
#include <algorithm>
#include <cmath>

namespace aph {

// A camp's tie hit goes to whoever of the champions as near acts first (rules camps.attack), so
// the idle order decides who absorbs it; higher acts first. First those the hit leaves alive, most
// such hits in hand first and gemless before carriers at a count; then those it would kill, fewest
// gems first, since a camp kill takes the bag (rules combat.camp_kill). `hit`: the camp hits we
// could take next phase, our emblems counted. With none, the nearer an enemy (`enemy_dist`,
// in steps of 2 tiles) the later we act: acting before it only hands it the reply (EXPERIMENTS
// "Turn order and ally coordination"). Range idle_lowest to idle_top.
inline constexpr int idle_top = 12, max_hits = 8, gem_buckets = 6;
inline constexpr int idle_lowest = idle_top - 2 * max_hits - 2 - (gem_buckets - 1);

inline int idle_priority(float health, float shield, float hit, int gems, int enemy_dist) {
    const float effective = health + shield;
    const auto in_hand = [&](float hits) { return idle_top - 2 * (max_hits - std::clamp(static_cast<int>(std::floor(hits)), 0, max_hits)) - (gems > 0); };
    if (hit <= 0) return in_hand(static_cast<float>(enemy_dist / 2));
    if (effective > hit) return in_hand((effective - hit) / hit);
    const int bucket = gems <= 0 ? 0 : gems < 10 ? 1 : gems < 30 ? 2 : gems < 60 ? 3 : gems < 100 ? 4 : 5;
    return idle_top - 2 * max_hits - 2 - bucket;
}

} // namespace aph
