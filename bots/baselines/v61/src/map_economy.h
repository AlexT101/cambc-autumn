#pragma once
#include "world.h"

namespace aph {

struct MapEconomy {
    float gems = 0, cluster_gems = 0, gold = 0, cluster_gold = 0;
    float gold_steps = 0;
    int gem_groups = 0, pure_gold_groups = 0, pure_gold = 0;
    int reachable_gems = 0;
    int total_gems = 0;
    float damaging_gems = 0;
    bool mixed_gems = false;

    bool cluster_gem_map() const { return gems > 0 && 2 * cluster_gems >= gems; }
    bool stellar_map() const { return cluster_gem_map() && mixed_gems && 4 * damaging_gems >= gems; }
    bool tavi_map() const {
        return pure_gold_groups >= 2 && pure_gold >= 120 && gold_steps >= 12 * pure_gold_groups;
    }
    bool prospector_map() const {
        const float supply = gems + gold / 2;
        return supply > 0 && 2 * (cluster_gems + cluster_gold / 2) >= supply;
    }
};

inline int closest_member_steps(const CampGroup& group, const Field& field) {
    int steps = unreachable;
    for (const auto& member : group.members) steps = std::min(steps, field.at(member.pos));
    return steps;
}

inline MapEconomy measure_economy(const StaticMap& map) {
    MapEconomy out;
    const auto& own_field = map.from_ally_spawn();
    const auto& enemy_field = map.from_enemy_spawn();
    for (int g = 0; g < static_cast<int>(map.groups.size()); ++g) {
        const auto& group = map.groups[g];
        out.total_gems += group.gems;
        // Large groups can touch both spawns while their centre favours only one side.
        const int own = closest_member_steps(group, own_field);
        if (own == unreachable) continue;
        out.reachable_gems += group.gems;
        const int enemy = closest_member_steps(group, enemy_field);
        // Central work counts once at full weight; enemy-favoured supply tapers with real travel.
        const float home = enemy == unreachable || own <= enemy ? 1.0f : static_cast<float>(enemy + 1) / static_cast<float>(own + 1);
        const float weight = home / static_cast<float>(std::max(1, group.respawn + 6));
        out.gems += weight * group.gems;
        out.cluster_gems += weight * group.cluster_gems;
        out.gold += weight * group.gold;
        out.cluster_gold += weight * group.cluster_gold;
        if (group.cluster_gems > 0 && (enemy == unreachable || own <= enemy)) ++out.gem_groups;
        if (group.strength > 0 && !group.has_monolith) {
            out.damaging_gems += weight * group.gems;
            out.mixed_gems |= group.cluster_gems > 0;
        }
        if (group.gold > 0 && group.gems == 0 && group.strength == 0
            && group.cluster_gold == group.gold && (enemy == unreachable || own <= enemy)) {
            ++out.pure_gold_groups;
            out.pure_gold += group.gold;
            out.gold_steps += own;
        }
    }
    return out;
}

inline const MapEconomy& map_economy(const StaticMap& map) {
    static const MapEconomy profile = measure_economy(map);
    return profile;
}

} // namespace aph
