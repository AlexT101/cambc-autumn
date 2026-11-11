#pragma once
#include "fighter.h"

// The fight takes our turn while an enemy seen this round or last is within its reach of us
// or ours of it (constants::reach); otherwise the economy plays it.
//
//   init()   once, after champs::init() and map_info::init()
//   step()   our turn: the economy's, written down (actions::plan), among the fight's plans
namespace fight {
    // fighter<type>::play_turn for every champion type, by champion_type: whatever the draft
    // gives us plays from its kit
    inline constexpr void (*turns[])(const actions::plan& economy) = {
        &fighter<ct::ryth>::play_turn,     &fighter<ct::vesper_vale>::play_turn,
        &fighter<ct::vendetta>::play_turn, &fighter<ct::cassi>::play_turn,
        &fighter<ct::issac>::play_turn,    &fighter<ct::stellar>::play_turn,
        &fighter<ct::prism>::play_turn,    &fighter<ct::marcella>::play_turn,
        &fighter<ct::willow>::play_turn,   &fighter<ct::ren>::play_turn,
        &fighter<ct::varg>::play_turn,     &fighter<ct::tavi>::play_turn,
        &fighter<ct::heart_of_ruin>::play_turn,
    };
    static_assert(std::size(turns) == std::size(kits));

    inline void (*play_turn)(const actions::plan& economy);

    inline void init() {
        init_value();
        play_turn = turns[u32(champs::my_info().type)];
    }

    inline bool is_enemy_in_reach() {
        const i32 ours = constants::reach[u32(champs::my_info().type)];
        for (u32 i = 0; i < champs::n_enemies; ++i) {
            const champ_info& e = champs::info[champs::enemies[i]];
            if (is_fresh(e) && util::chebyshev(e.pos, g::my_pos) <=
                                   std::max(ours, constants::reach[u32(e.type)]))
                return true;
        }
        return false;
    }

    inline void step(const actions::plan& economy) {
        observe();
        play_turn(economy);
    }
} // namespace fight
