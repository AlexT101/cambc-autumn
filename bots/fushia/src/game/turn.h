#pragma once
#include "../capture/capture.h"
#include "../common/common.h"
#include "../farm/farm.h"
#include "../fight/fight.h"
#include "actions.h"
#include "../path/dash.h"
#include "../recall/recall.h"
#include "../shop/shop.h"
#include "../tribute/tribute.h"

namespace turn_h {
    inline vec2 explore;

    inline void init() {
        explore = util::rand_pos();
    }
} // namespace turn_h
using namespace turn_h;

// recall, tribute, capture, farm or explore, acting through `out` (actions.h)
template <class Out>
void economy_turn(Out& out) {
    if (recall::step(out))
        return;
    if (tribute::step(out))
        return;
    if (capture::step(out))
        return;
    if (farm::step(out))
        return;

    path::walk_to(out, explore);
    dbg::line(explore);
}

inline void run_turn() {
    if (!g::alive)
        return;
    if (!champs::my_info().restrictions.is_empty())
        return; // stunned: every action is refused this turn

    shop::try_buy();

    // near an enemy, the economy writes its turn down and the fight weighs it among its own plans
    if (fight::is_enemy_in_reach()) {
        actions::plan economy;
        economy_turn(economy);
        economy.close();
        fight::step(economy);
    } else {
        actions::act now;
        economy_turn(now);
    }
}
