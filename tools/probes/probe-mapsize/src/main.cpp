// map.size: the engine's width and height of a map, printed once by every bot instance (draft and champions).
//   cambc run tools/probes/probe-mapsize tools/probes/probe-mapsize --map 00breadcrumbs --rounds 1 --fuel 50000000 -o DIR
// The draft makes no picks (they go random).
#include <cambc.h>
#include <cstdio>

int main() {
    std::printf("PROBE map width=%d height=%d draft=%d\n", cambc::map::width(), cambc::map::height(), cambc::is_draft() ? 1 : 0);
    while (true) cambc::end_turn();
}
