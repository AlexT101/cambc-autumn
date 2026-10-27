#pragma once
#include "world.h"

namespace aph {

inline int economy_pick_count(const World& world) {
    static const int count = [&] {
        int picks = 0;
        for (const auto& ally : world.allies)
            picks += ally.type != cambc::champion_type::issac;
        return picks;
    }();
    return count;
}

inline bool economy_three(const World& world) {
    static const bool enabled = economy_pick_count(world) == 3;
    return enabled;
}

} // namespace aph
