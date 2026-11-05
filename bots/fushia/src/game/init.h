#pragma once
#include "../common/common.h"
#include "../common/globals.h"
#include "../comms/comms.h"
#include "../path/dash.h"
#include "../path/path.h"
#include "turn.h"

// first turn of game

namespace init {
    inline void init() {
        g::init();
        champs::init();
        comms::init();
        map_info::init();
        camp_info::init();
        move_manager::init();
        const vec2 start = g::my_pos;
        rng::seed(u64(start.x) << 32 | u64(start.y));
        path::dashing::init();
        turn_h::init();
        fight::init();
    }
} // namespace init
