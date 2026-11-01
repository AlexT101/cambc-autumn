// probe-ally-gold: can a champion read a teammate's gold, in vision and out of it, and an enemy's?
// cambc-rules.yaml said "Gold is readable only for yourself"; the C++ gold_count() requires self, but only
// client-side. This is probe-marcella-gold's scenario (00collision, side 0 acts, side 1 idles; Marcella captures
// alone, so her gold climbs while Vendetta's and Varg's stay 0), plus a "goldread" line per other champion at each
// turn start: the raw sdk_champion_gold's code and value. Compare each read of Marcella with her own gold=
// on her "turn" or "end" line that round, or her "end" line the round before (turn order).
// Result (2026-10-30): all 500 teammates' reads of Marcella's gold (0 to 272) matched, 28 of them out of vision
// (158 while she tributed); unseen enemies 105. Enemies in vision: probe-ally-gold-b, also 105.
// Run: cambc run tools/probes/probe-ally-gold tools/probes/probe-ally-gold --map 00collision --rounds 250 --fuel 50000000 -o <dir>
//      then unzip the .repl26a: tr -d '\000' < team-a.stdout | grep -E 'goldread|turn'
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
