#pragma once
#include "constants.h"
#include "globals.h"
#include "types.h"
#include <cambc.h>

namespace economy {
    inline f32 gem_worth_in_gold() {
        constexpr f32 early = 0.621f;
        constexpr f32 late = 4.177f;

        // from larping to lerping
        const f32 t = f32(g::round) / f32(constants::max_rounds);
        return early + (late - early) * t;
    }
} // namespace economy
