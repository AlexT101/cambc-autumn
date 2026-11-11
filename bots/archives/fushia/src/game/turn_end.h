#pragma once
#include "../common/common.h"
#include "../comms/comms.h"

inline void end_turn() {
    comms::end_turn();
}
