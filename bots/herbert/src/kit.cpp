#include "kit.h"

#include <type_traits>
#include <variant>

namespace hyp::facts {

namespace {
std::array<Kit, 12> kits;
bool ready = false;

Ability read_slot(const cambc::ability& slot) {
    Ability a;
    const auto info = slot.info();
    if (!info) return a;
    a.present = true;
    std::visit(
        [&](const auto& v) {
            using V = std::decay_t<decltype(v)>;
            a.kind = V::kind;
            a.cooldown = v.max_cooldown;
            a.excludes_walking = v.exclusive_with_movement;
            a.targets = v.valid_targets.bits();
            if constexpr (std::is_same_v<V, cambc::ability_attack_reset>) {
                a.enhanced = v.enhanced_attack;
            } else if constexpr (std::is_same_v<V, cambc::ability_dash>) {
                a.range = v.range;
            } else if constexpr (std::is_same_v<V, cambc::ability_aoe_damage>) {
                a.range = v.range, a.modifier = v.modifier, a.radius = v.radius, a.duration = v.duration;
            } else if constexpr (std::is_same_v<V, cambc::ability_cc> || std::is_same_v<V, cambc::ability_shield>) {
                a.range = v.range, a.modifier = v.modifier, a.duration = v.duration;
            } else {   // damage, heal
                a.range = v.range, a.modifier = v.modifier;
            }
        },
        *info);
    return a;
}
}  // namespace

void init() {
    if (ready) return;
    for (const auto& design : cambc::champion_designs) {
        const auto t = design.champion_name();
        Kit& k = kits[static_cast<std::size_t>(t)];
        k.type = t;
        k.passive = design.passive();
        const auto s = design.base_stats();
        k.attack_range = s.base_attack_range;
        k.vision = s.vision_radius;
        k.hp0 = s.base_health, k.hpg = s.health_growth;
        k.str0 = s.base_strength, k.strg = s.strength_growth;
        k.foc0 = s.base_focus, k.focg = s.focus_growth;
        k.camp_mult = s.camp_damage_multiplier;
        const auto slots = design.abilities();
        for (std::size_t i = 0; i < 2; ++i) k.ab[i] = read_slot(slots[i]);
    }
    ready = true;
}

const Kit& kit(cambc::champion_type t) {
    if (!ready) init();
    return kits[static_cast<std::size_t>(t)];
}

}  // namespace hyp::facts
