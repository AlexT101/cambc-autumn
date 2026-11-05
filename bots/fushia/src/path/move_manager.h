#pragma once
#include "../common/common.h"
#include <optional>

namespace move_manager {
    inline std::optional<cambc::ability> dash_ability;

    inline void init() {
        for (const cambc::ability& slot : g::me().abilities())
            if (slot.is_dash())
                dash_ability = slot;
    }

    inline bool move_absolute(vec2 pos) {
        channel::drop();
        if (g::me().move_absolute(pos)) {
            g::my_pos = pos;
            return true;
        }
        return false;
    }

    // cooldown() is 44 fuel and can_cast() 54
    // ability::is_ready() would be 475
    inline bool can_dash() {
        return dash_ability && dash_ability->cooldown() == 0 && g::me().can_cast();
    }

    inline bool dash(vec2 landing) {
        channel::drop();
        if (dash_ability->use(landing)) {
            g::my_pos = landing;
            return true;
        }
        return false;
    }
} // namespace move_manager
