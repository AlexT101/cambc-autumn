#pragma once
#include "types.h"

namespace g {
    inline cambc::champion* me_ptr;
    inline i32 W, H, maxX, maxY;
    inline vec2 my_spawn_pos, enemy_spawn_pos;

    inline bool alive = false;
    inline i32 round;
    inline vec2 my_pos;
    inline bool is_team_a;
    inline i32 my_team; // 0 = team A, 1 = team B
    inline i64 fuel_start; // fuel_remaining() as the turn began

    // g::me() ~2 fuel vs 4 normally
    inline cambc::champion& me() {
        return *me_ptr;
    }

    inline void init_spawn() {
        using cambc::symmetry;
        const auto tiles =
            cambc::map::spawn_region(is_team_a ? cambc::team::ally : cambc::team::enemy)
                .positions();
        const vec2 a =
            *std::min_element(tiles.begin(), tiles.end(), [](vec2 p, vec2 q) {
                return p.y != q.y ? p.y < q.y : p.x < q.x;
            });
        const symmetry s = cambc::map::symmetry();
        const vec2 b{s == symmetry::vertical ? a.x : maxX - a.x,
                     s == symmetry::horizontal ? a.y : maxY - a.y};
        my_spawn_pos = is_team_a ? a : b, enemy_spawn_pos = is_team_a ? b : a;
    }

    inline void init() {
        me_ptr = &cambc::self();
        my_pos = me_ptr->position();
        my_team = cambc::detail::sdk_my_team(), is_team_a = my_team == 0;
        W = cambc::map::width(), H = cambc::map::height(), maxX = W - 1, maxY = H - 1;
        init_spawn();
    }

    inline void start_turn() {
        fuel_start = i64(cambc::fuel_remaining());
        round = i32(cambc::round_number());
        my_pos = me_ptr->position();
        alive = my_pos.x >= 0;
    }
} // namespace g
