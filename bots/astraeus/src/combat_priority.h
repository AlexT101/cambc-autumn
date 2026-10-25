#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include "champions.h"
#include "idle_priority.h"

namespace aph::teacher_priority {

// Physical champion type indices, matching champions.h and the engine's public enum.
enum Type { ryth, vesper_vale, vendetta, cassi, issac, stellar, prism, marcella, willow, ren, varg, tavi, heart_of_ruin };

struct Unit {
    int type = prism;
    int x = -1, y = -1;
    float health = 0, shield = 0, max_health = 0, strength = 0, focus = 0;
    std::array<int, 2> cooldowns{0, 0};
    bool alive = true, stunned = false;
};

struct Enemies {
    std::array<Unit, 6> units;
    int count = 0;
};

constexpr int role(int type) {
    switch (type) {
    case prism: return 0;
    case vesper_vale: return 1;
    case ryth:
    case vendetta: return 2;
    case marcella: return 3;
    case heart_of_ruin: return 4;
    default: return -1;
    }
}

// compute_strike's geometric maximum, using raw cooldown zero rather than next-turn readiness.
// Stuns, heals and shields add no damage here.
inline float strike(const Unit& unit, int distance) {
    if (unit.type < 0 || unit.type >= static_cast<int>(champion_table.size())) return 0;
    const auto& f = champion_table[static_cast<std::size_t>(unit.type)];
    const float scale = damage_scale(f.passive, unit.health, unit.max_health);
    const float strength = unit.strength * scale, focus = unit.focus * scale;
    const int range = f.attack_range();
    const int basic = f.basic_reach(), walk = f.ranged ? 0 : 1;
    float best = 0;
    const auto add = [&](int reach, float amount) {
        if (distance <= reach) best = std::max(best, amount);
    };
    add(basic + walk, strength);
    for (int slot = 0; slot < 2; ++slot) {
        if (unit.cooldowns[slot] != 0) continue;
        const auto& a = f.abilities[static_cast<std::size_t>(slot)];
        switch (a.kind) {
        case AbilityKind::attack_reset:
            add(basic + walk, 2.0f * strength);
            if (f.ranged) add(basic + 1, strength);
            break;
        case AbilityKind::dash:
            add(basic + walk + a.range(), strength);
            if (a.multiplier > 0) {
                add(walk + a.range() + a.radius, a.multiplier * focus);
                add(walk + a.range() + std::min(range, a.radius), a.multiplier * focus + strength);
            }
            break;
        case AbilityKind::damage:
            add(a.reach(), a.multiplier * focus);
            add(range, a.multiplier * focus + strength);
            break;
        default: break;
        }
    }
    return best;
}

// Dead, then danger in tenths of a kill (either way) above it, all above every idle priority.
inline constexpr int dead_priority = 13, danger_buckets = 10;

inline int priority(const Unit& self, const Enemies& start, int gems) {
    if (!self.alive) return dead_priority;
    float outgoing = 0, incoming = 0;
    for (int i = 0; i < start.count; ++i) {
        const auto& enemy = start.units[static_cast<std::size_t>(i)];
        const int distance = std::max(std::abs(self.x - enemy.x), std::abs(self.y - enemy.y));
        const float enemy_hp = enemy.health + enemy.shield;
        if (enemy_hp > 0) outgoing = std::max(outgoing, strike(self, distance) / enemy_hp);
        if (enemy.alive && !enemy.stunned) incoming += strike(enemy, distance);
    }
    const float self_hp = self.health + self.shield;
    const float ratio = std::max(outgoing, self_hp > 0 ? incoming / self_hp : 0.0f);
    const int bucket = static_cast<int>(std::floor(static_cast<float>(danger_buckets) * std::clamp(ratio, 0.0f, 1.0f)));
    return bucket > 0 ? dead_priority + bucket : idle_priority(role(self.type), self.health, self.shield, self.max_health, gems);
}

} // namespace aph::teacher_priority
