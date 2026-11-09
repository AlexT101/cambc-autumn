// Which maps reward Tavi or Stellar, read by the draft and the champions' 3-pick roles.
// Static, so measured once per bot instance.
#pragma once
#include <algorithm>
#include "../model/world.h"

namespace aph {

struct MapEconomy {
    // Supply per round of reachable groups, weighted by measure_economy.
    float gems = 0, cluster_gems = 0;
    float damaging_gems = 0; // from groups that hit back, monoliths aside
    bool mixed_gems = false; // a group that hits back holds gem clusters
    // Gold-cluster-only groups on our side: their count, gold and summed steps from our spawn.
    int pure_gold_groups = 0, pure_gold = 0;
    float gold_steps = 0;
    int total_gems = 0; // per capture, unweighted, reachable or not

    bool cluster_gem_map() const { return gems > 0 && 2 * cluster_gems >= gems; }
    bool stellar_map() const { return cluster_gem_map() && mixed_gems && 4 * damaging_gems >= gems; }
    // Tavi shops anywhere, so it farms gold best where that gold lies far (12 steps on average) from spawn.
    bool tavi_map() const { return pure_gold_groups >= 2 && pure_gold >= 120 && gold_steps >= 12 * pure_gold_groups; }
};

inline MapEconomy measure_economy(const StaticMap& map) {
    MapEconomy out;
    const auto& own_field = map.from_ally_spawn();
    for (const auto& group : map.groups) {
        out.total_gems += group.gems;
        // Nearest member, not the centre: a large group can lie near both spawns.
        int own = unreachable, enemy = unreachable;
        for (const auto& member : group.members) {
            own = std::min(own, own_field.at(member.pos));
            enemy = std::min(enemy, map.enemy_spawn_steps(member.pos));
        }
        if (own == unreachable) continue;
        // Groups at least as near us count in full; nearer the enemy, by the ratio of distances. Each is
        // per round of its capture cycle (respawn plus the 6-round hold).
        const bool ours = enemy == unreachable || own <= enemy;
        const float home = ours ? 1.0f : static_cast<float>(enemy + 1) / static_cast<float>(own + 1);
        const float weight = home / static_cast<float>(std::max(1, group.respawn + 6));
        out.gems += weight * static_cast<float>(group.gems);
        out.cluster_gems += weight * static_cast<float>(group.cluster_gems);
        if (group.strength > 0 && !group.has_monolith) {
            out.damaging_gems += weight * static_cast<float>(group.gems);
            out.mixed_gems |= group.cluster_gems > 0;
        }
        if (ours && group.gold > 0 && group.gems == 0 && group.strength == 0) { // only gold clusters
            ++out.pure_gold_groups;
            out.pure_gold += group.gold;
            out.gold_steps += static_cast<float>(own);
        }
    }
    return out;
}

inline const MapEconomy& map_economy(const StaticMap& map) {
    static const MapEconomy profile = measure_economy(map);
    return profile;
}

} // namespace aph
