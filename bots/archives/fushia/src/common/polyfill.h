#pragma once
#include "bb.h"
#include "globals.h"
#include "types.h"
#include <cambc.h>
#include <cstdio>

// faster engine funcs

namespace polyfill {
    namespace d = cambc::detail;

    // map::is_in_bounds: 21 against 26
    inline bool is_in_bounds(vec2 t) {
        return u32(t.x) < u32(g::W) && u32(t.y) < u32(g::H);
    }

    // bitboard::is_set through the import: 32 against 41. Off the map the import fails and
    // writes nothing, so it reads false.
    inline bool is_set(const cambc::bitboard& b, vec2 t) {
        i32 on = 0;
        d::sdk_Bitboard_Test(b.ptr(), t.x, t.y, &on);
        return on;
    }

    // vision::has_champion, has_camp, has_teleport through the imports: 28 against 36. Out of
    // sight (error 97) reads false, as in the SDK.
    inline bool has_champion(vec2 t) {
        i32 on;
        return d::sdk_has_champion(t.x, t.y, &on) == 0 && on;
    }
    inline bool has_camp(vec2 t) {
        i32 on;
        return d::sdk_has_camp(t.x, t.y, &on) == 0 && on;
    }
    inline bool has_teleport(vec2 t) {
        i32 on;
        return d::sdk_has_teleport(t.x, t.y, &on) == 0 && on;
    }

    // vision::champion_tiles_into(out), both teams, without the SDK's temporary board for the
    // second team: about 70 against 315
    inline void champion_tiles_into(cambc::bitboard& out) {
        static cambc::bitboard enemies;
        cambc::vision::champion_tiles_into(cambc::team::ally, out);
        cambc::vision::champion_tiles_into(cambc::team::enemy, enemies);
        bb::or_into(out, enemies, out);
    }

} // namespace polyfill
