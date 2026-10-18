#pragma once
// Champion kits, read once from the engine's designs (the single source of truth: no transcribed tables).
#include <cambc.h>

#include <array>
#include <cstdint>

namespace hyp {

struct Ability {
    bool present = false;
    cambc::ability_kind kind{};
    float range = 0, modifier = 0, radius = 0;
    int duration = 0;               // stun turns (cc, aoe) or a shield's turn ends
    bool excludes_walking = false;  // can't share a turn with a step
    bool enhanced = false;          // attack reset whose next basic attack stuns (Marcella)
    int cooldown = 8;
    std::uint32_t targets = 0;      // cambc::detail::ability_target_* bits

    bool is(cambc::ability_kind k) const { return present && kind == k; }
    bool stuns() const {
        return present && ((kind == cambc::ability_kind::cc && duration > 0) ||
                           (kind == cambc::ability_kind::aoe_damage && duration > 0) ||
                           (kind == cambc::ability_kind::attack_reset && enhanced));
    }
    // Deals damage when cast (a reset's extra hit is not counted here).
    bool damages() const {
        return present && modifier > 0 &&
               (kind == cambc::ability_kind::damage || kind == cambc::ability_kind::aoe_damage ||
                kind == cambc::ability_kind::cc);
    }
    bool hits_champions() const { return (targets & cambc::detail::ability_target_enemies) != 0 || is_ground(); }
    bool hits_camps() const { return (targets & cambc::detail::ability_target_camps) != 0 || is_ground(); }
    bool is_ground() const { return present && kind == cambc::ability_kind::aoe_damage; }
    // Farthest tile it can affect: a ground cast hits the square of `radius` around its target tile.
    int reach() const { return static_cast<int>(range) + (is_ground() ? static_cast<int>(radius) : 0); }
};

struct Kit {
    cambc::champion_type type{};
    cambc::passive_type passive{};
    int attack_range = 1, vision = 8;
    float hp0 = 0, hpg = 0, str0 = 0, strg = 0, foc0 = 0, focg = 0, camp_mult = 1;
    std::array<Ability, 2> ab{};

    bool ranged() const { return attack_range > 1; }
    // Slot holding an ability of this kind, or -1.
    int slot(cambc::ability_kind k) const {
        for (int s = 0; s < 2; ++s)
            if (ab[static_cast<std::size_t>(s)].is(k)) return s;
        return -1;
    }
    bool has(cambc::ability_kind k) const { return slot(k) >= 0; }
    bool has_stun() const { return ab[0].stuns() || ab[1].stuns(); }
    bool linked() const { return type == cambc::champion_type::cassi || type == cambc::champion_type::issac; }
};

namespace facts {
void init();   // reads the 12 designs (a few thousand fuel); idempotent
const Kit& kit(cambc::champion_type t);
}  // namespace facts

}  // namespace hyp
