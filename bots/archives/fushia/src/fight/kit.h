#pragma once
#include "../common/common.h"

// What a champion type can do in a fight: the numbers the simulator plays every champion with,
// and our own champion's plans are made from. They are the engine's designs (champions.md);
// fight::test_kits() checks them against the engine in debug builds.
namespace fight {
    enum class effect : u8 {
        none,
        damage, // one enemy: modifier x Focus
        stun,   // one enemy: modifier x Focus (0 for Cassi), stunned `stun` turns
        area,   // every enemy within radius of a tile: modifier x Focus, stunned `stun` turns
        dash,   // up to range tiles; Heart of Ruin's lands for modifier x Focus around it
        reset,  // a second basic attack; Marcella's stuns
        shield, // absorbs modifier x Focus for 5 rounds; range 4, but we keep it for ourselves
        heal,   // an ally: modifier x Focus
    };

    struct ability_kit {
        effect kind = effect::none;
        bool exclusive = false; // not in a turn we walk ("stops walking")
        i8 range = 0;           // cast range, or a dash's travel
        i8 radius = 0;          // around the target tile
        i8 stun = 0;            // turns the target loses
        f32 modifier = 0;       // x Focus

        constexpr bool is_offensive() const {
            return kind == effect::damage || kind == effect::stun || kind == effect::area;
        }
    };

    struct kit {
        i8 attack_range; // 1 melee, 3 ranged
        ability_kit slots[2];
        // passives
        i8 splash = 0;               // Varg: an attack also hits enemies this near the target
        f32 retaliate = 0;           // Ren: x Focus back at whoever hits him
        f32 rage = 0;                // Heart of Ruin: + this x the share of health missing
        bool resets_on_kill = false; // Vendetta: cooldowns
        bool stun_immune = false;    // Marcella
        bool paired = false;         // Cassi and Issac die together

        constexpr bool is_ranged() const {
            return attack_range > 1;
        }
        // the slot holding an ability of this kind, -1 none
        constexpr i32 slot_of(effect e) const {
            return slots[0].kind == e ? 0 : slots[1].kind == e ? 1 : -1;
        }
    };
} // namespace fight
