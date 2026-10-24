// probe-marcella-gold: does a gold bonus (Treasure emblem, +20%) apply to Marcella's tribute gold (2 per gem)?
// Map 00collision, self-play: side 0 (team A, south spawn) acts; side 1 idles on its spawn all match.
// Side 0's Vendetta and Varg help kill but never stand on camp tiles, so Marcella captures alone.
// Marcella captures group 4 (wolf+gold+gem: 60 gold, 11 gems) and group 6 (wolf+2 gems: 40 gold, 18 gems)
// and tributes the 29 gems at altar (27,20) with no bonus (control). She buys 5 Treasure shards of strength
// (the emblem), recaptures both (72 + 48 gold confirms the emblem) and tributes 29 gems again. Then she
// recaptures group 4 (+72, 11 gems) and tributes 11: the floor shows whether a fractional remainder carried over.
// Gold is read with gold_count(), the only reader (it floors). Every gain before the first two tributes is
// whole, so those floors are exact. State is logged at each turn start ("turn") and end ("end").
// Result (2026-10-24): control 100 -> 158 (+58 = 2x29); Treasure 128 -> 197 (2.4x29 = 69.6);
// third 269 -> 296 (197.6 + 72 + 26.4 = 296.0). Credited when the channel completes, not at the start.
// Run: cambc run tools/probes/probe-marcella-gold tools/probes/probe-marcella-gold --map 00collision --rounds 250 --fuel 50000000 -o <dir>
//      then unzip the .repl26a: tr -d '\000' < team-a.stdout | grep PROBE | grep marcella
#include <cambc.h>
#include <cstdio>
#include "bot.h"
#include "draft.h"

int main() {
    Bot bot;
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else bot.play_turn();
        } catch (const std::exception& error) {
            std::printf("PROBE err %s\n", error.what());
        } catch (...) {
            std::printf("PROBE err unknown\n");
        }
        cambc::end_turn();
    }
}
