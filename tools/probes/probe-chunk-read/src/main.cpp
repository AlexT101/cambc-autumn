// probe-chunk-read: a read of the fuel left just after the bot's own code crosses a 100k fuel chunk inside a
// many-chunk turn (the draft bot's 10M first turn). Run in a release build, once per cambc:
//   cambc run tools/probes/probe-chunk-read tools/probes/probe-chunk-read --map 00ambush --rounds 2 --release -o DIR
// The draft bot loops on guest code until a fuel_remaining() reading is within OFF of a chunk boundary at or below
// 9M, reads it again (g), makes a shadow cast and prints g and a last reading (after); then it yields without
// picking, so it never runs again. team-a.fuel's 9th value is that turn's fuel.
// 2026-11-09, OFF 100: cambc 5.0.0 g=9000000 after=8999485 turn 1004112; 5.0.1 g=8999993 after=8999471 turn
// 1004126 (fastrunner native and exact: 5.0.1's). 5.0.0 read the overrun chunk as spent to its boundary and
// charged the turn 14 less; 5.0.1 runs out_of_gas right after the unpriced read. When the loop stops
// mid-chunk instead (OFF 200 in an earlier version of this probe), both versions agree.
#include <cambc.h>
#include <cstdint>
#include <cstdio>
#ifndef OFF
#define OFF 100
#endif
int main() {
    bool first = true;
    cambc::bitboard walls = cambc::map::walls();
    cambc::bitboard sight;
    volatile std::uint64_t x = 0;
    while (true) {
        if (cambc::is_draft() && first) {
            first = false;
            while (cambc::detail::sdk_fuel_remaining() % 100000 >= OFF || cambc::detail::sdk_fuel_remaining() > 9000000)
                x = x * 6364136223846793005ULL + 1;
            const std::int64_t g = cambc::detail::sdk_fuel_remaining();
            cambc::detail::sdk_Bitboard_ShadowCast(walls.ptr(), 10, 10, sight.ptr(), 8);
            std::printf("PROBE g=%lld after=%lld\n", (long long)g, (long long)cambc::detail::sdk_fuel_remaining());
            std::fflush(nullptr);
            cambc::detail::sdk_yield();
        }
        cambc::end_turn();
    }
}
