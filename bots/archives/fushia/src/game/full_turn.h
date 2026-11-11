#pragma once
#include "../common/common.h"
#include "init.h"
#include "turn.h"
#include "turn_end.h"
#include "turn_start.h"

inline void full_turn() {

    // why this instead of round number check? ans: continues after crash
    static bool initialised = false;
    if (!initialised)
        init::init(), initialised = true;

    start_turn();
    run_turn();
    end_turn();
}
