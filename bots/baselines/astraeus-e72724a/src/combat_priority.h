#pragma once
#include <algorithm>
#include <array>
#include <cmath>
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

namespace detail {
enum Kind { none, reset, damage, dash };
struct Ability {
    Kind kind = none;
    float multiplier = 0;
    bool ground = false;
    int radius = 0;
};
struct Kit {
    bool melee;
    std::array<Ability, 2> slots;
};
inline constexpr Ability attack_reset{reset}, plain_dash{dash};
inline constexpr std::array<Kit, 13> kits{{
    {true, {Ability{damage, 1, true}, attack_reset}},
    {false, {attack_reset, plain_dash}},
    {true, {attack_reset, plain_dash}},
    {false, {Ability{damage, 2}, Ability{}}},
    {true, {attack_reset, plain_dash}},
    {false, {Ability{damage, 2}, Ability{damage, 1.4f, true}}},
    {false, {Ability{damage, 1.5f}, Ability{damage, 1, true}}},
    {true, {attack_reset, Ability{damage, 2}}},
    {false, {Ability{}, attack_reset}},
    {true, {Ability{damage, 0.75f}, plain_dash}},
    {true, {attack_reset, Ability{}}},
    {false, {attack_reset, Ability{damage, 1.4f}}},
    {true, {Ability{}, Ability{dash, 1.5f, false, 1}}},
}};
} // namespace detail

// compute_strike's geometric maximum, using raw cooldown zero rather than next-turn readiness.
inline float strike(const Unit& unit, int distance) {
    if (unit.type < 0 || unit.type >= static_cast<int>(detail::kits.size())) return 0;
    const auto& kit = detail::kits[static_cast<std::size_t>(unit.type)];
    float scale = 1;
    if (unit.type == heart_of_ruin && unit.max_health > 0) {
        const float missing = 1.0f - unit.health / unit.max_health;
        scale = 1.0f + 0.5f * std::clamp(missing, 0.0f, 1.0f);
    }
    const float strength = unit.strength * scale, focus = unit.focus * scale;
    const int range = kit.melee ? 1 : 3;
    const int basic = range + (unit.type == varg ? 1 : 0), walk = kit.melee ? 1 : 0;
    float best = 0;
    const auto add = [&](int reach, float amount) {
        if (distance <= std::min(8, reach)) best = std::max(best, amount);
    };
    add(basic + walk, strength);
    for (int slot = 0; slot < 2; ++slot) {
        if (unit.cooldowns[slot] != 0) continue;
        const auto& ability = kit.slots[slot];
        switch (ability.kind) {
        case detail::reset:
            add(basic + walk, 2.0f * strength);
            if (!kit.melee) add(basic + 1, strength);
            break;
        case detail::dash:
            add(basic + walk + 2, strength);
            if (ability.multiplier > 0) {
                add(walk + 2 + ability.radius, ability.multiplier * focus);
                add(walk + 2 + std::min(range, ability.radius), ability.multiplier * focus + strength);
            }
            break;
        case detail::damage:
            add(4 + (ability.ground ? 1 : 0), ability.multiplier * focus);
            add(range, ability.multiplier * focus + strength);
            break;
        default: break;
        }
    }
    return best;
}

inline int priority(const Unit& self, const Enemies& start, int gems) {
    if (!self.alive) return 13;
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
    const int bucket = static_cast<int>(std::floor(10.0f * std::clamp(ratio, 0.0f, 1.0f)));
    return bucket > 0 ? 13 + bucket : idle_priority(role(self.type), self.health, self.shield, self.max_health, gems);
}

} // namespace aph::teacher_priority
