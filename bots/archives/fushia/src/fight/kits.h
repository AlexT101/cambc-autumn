#pragma once
#include "kit.h"
#include <string>
#include <variant>

// Every champion type's kit, by champion_type: what the fight scores each champion with, ours and
// the enemies' alike (fighter<T> reads its own at compile time). The engine's designs
// (docs/ours/champions.md); test_kits() checks them in the draft.
namespace fight {
    using ct = cambc::champion_type;

    inline constexpr kit kits[] = {
        // ryth
        kit{
            .attack_range = 1,
            .slots = {{.kind = effect::area, .exclusive = true, .range = 4, .radius = 1, .stun = 1,
                       .modifier = 1},
                      {.kind = effect::reset}},
        },
        // vesper_vale
        kit{
            .attack_range = 3,
            .slots = {{.kind = effect::reset}, {.kind = effect::dash, .range = 2}},
        },
        // vendetta
        kit{
            .attack_range = 1,
            .slots = {{.kind = effect::reset}, {.kind = effect::dash, .range = 2}},
            .resets_on_kill = true,
        },
        // cassi
        kit{
            .attack_range = 3,
            .slots = {{.kind = effect::damage, .exclusive = true, .range = 4, .modifier = 2},
                      {.kind = effect::stun, .range = 4, .stun = 1}},
            .paired = true,
        },
        // issac
        kit{
            .attack_range = 1,
            .slots = {{.kind = effect::reset}, {.kind = effect::dash, .range = 2}},
            .paired = true,
        },
        // stellar
        kit{
            .attack_range = 3,
            .slots = {{.kind = effect::damage, .exclusive = true, .range = 4, .modifier = 2},
                      {.kind = effect::area, .exclusive = true, .range = 4, .radius = 1,
                       .modifier = 1.4f}},
        },
        // prism
        kit{
            .attack_range = 3,
            .slots = {{.kind = effect::stun, .exclusive = true, .range = 4, .stun = 1,
                       .modifier = 1.5f},
                      {.kind = effect::area, .exclusive = true, .range = 4, .radius = 1,
                       .modifier = 1}},
        },
        // marcella
        kit{
            .attack_range = 1,
            .slots = {{.kind = effect::reset, .stun = 1},
                      {.kind = effect::damage, .exclusive = true, .range = 4, .modifier = 2}},
            .stun_immune = true,
        },
        // willow
        kit{
            .attack_range = 3,
            .slots = {{.kind = effect::heal, .range = 4, .modifier = 3}, {.kind = effect::reset}},
        },
        // ren
        kit{
            .attack_range = 1,
            .slots = {{.kind = effect::stun, .exclusive = true, .range = 4, .stun = 1,
                       .modifier = 0.75f},
                      {.kind = effect::dash, .range = 2}},
            .retaliate = 0.2f,
        },
        // varg
        kit{
            .attack_range = 1,
            .slots = {{.kind = effect::reset}, {.kind = effect::shield, .range = 4, .modifier = 2.5f}},
            .splash = 1,
        },
        // tavi
        kit{
            .attack_range = 3,
            .slots = {{.kind = effect::reset},
                      {.kind = effect::stun, .exclusive = true, .range = 4, .stun = 1,
                       .modifier = 1.4f}},
        },
        // heart_of_ruin
        kit{
            .attack_range = 1,
            .slots = {{.kind = effect::shield, .range = 4, .modifier = 1.5f},
                      {.kind = effect::dash, .range = 2, .radius = 1, .stun = 1, .modifier = 1.5f}},
            .rage = 0.5f,
        },
    };
    static_assert(std::size(kits) == u32(ct::heart_of_ruin) + 1);

    // ---===
    // throws naming the first kit field the engine's designs disagree with
    inline void test_kits() {
        for (u32 t = 0; t < std::size(kits); ++t) {
            const cambc::champion design{ct(t)};
            const auto same = [&](f32 ours, f32 engine, u32 slot, const char* what) {
                if (ours != engine)
                    throw std::logic_error("fight::kits[" + std::to_string(t) + "] slot " +
                                           std::to_string(slot) + " " + what + ": " +
                                           std::to_string(ours) + ", engine " +
                                           std::to_string(engine));
            };
            same(kits[t].attack_range, f32(design.base_stats().base_attack_range), 0, "attack");
            for (u32 s = 0; s < 2; ++s) {
                const ability_kit& a = kits[t].slots[s];
                std::visit(
                    [&](const auto& x) {
                        using T = std::decay_t<decltype(x)>;
                        constexpr effect kind =
                            std::is_same_v<T, cambc::ability_attack_reset> ? effect::reset
                            : std::is_same_v<T, cambc::ability_damage>     ? effect::damage
                            : std::is_same_v<T, cambc::ability_cc>         ? effect::stun
                            : std::is_same_v<T, cambc::ability_aoe_damage> ? effect::area
                            : std::is_same_v<T, cambc::ability_dash>       ? effect::dash
                            : std::is_same_v<T, cambc::ability_shield>     ? effect::shield
                                                                           : effect::heal;
                        same(f32(a.kind), f32(kind), s, "kind");
                        same(a.exclusive, x.exclusive_with_movement, s, "exclusive");
                        if constexpr (requires { x.range; })
                            same(a.range, x.range, s, "range");
                        if constexpr (requires { x.modifier; })
                            same(a.modifier, x.modifier, s, "modifier");
                        if constexpr (requires { x.radius; })
                            same(a.radius, x.radius, s, "radius");
                        if constexpr (requires { x.duration; } && kind != effect::shield)
                            same(a.stun, f32(x.duration), s, "stun");
                        if constexpr (kind == effect::reset)
                            same(a.stun > 0, x.enhanced_attack, s, "enhanced attack");
                    },
                    design.abilities()[s].info().value());
            }
        }
    }
    // ===---
} // namespace fight
