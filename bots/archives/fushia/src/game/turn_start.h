#pragma once
#include "../common/common.h"
#include "../comms/comms.h"

inline void start_turn() {
    g::start_turn();
    champs::start_turn();
    channel::start_turn();
    comms::start_turn();
    map_info::start_turn();
    camp_info::start_turn();
}
