#pragma once
#include "ally_position.h"
#include "captures.h"
#include "word.h"
#include <stdexcept>

// Each channel adds its fields in init(),
// reads them in start_turn() and sets its own in end_turn().
namespace comms {
    inline void init() {
        ally_position::init();
        captures::init();

        if (!radix::fits(layout.count))
            throw std::length_error("comms: the fields need more than 64 bits");
    }

    inline void start_turn() {
        read();
        ally_position::start_turn();
        captures::start_turn();
    }

    inline void end_turn() {
        ally_position::end_turn();
        captures::end_turn();
        write();
    }
} // namespace comms
