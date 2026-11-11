// probe-lock-own: misc rules probes (monolith range, capture contest, damage modifiers, altar locks, health purchases, inventory).
// Shared source with probe-lock-own-b (scripted opponent); run.sh copies src/ there and sets SIDE=1.
//   bash tools/probes/probe-lock-own/run.sh <scenario> <map> <rounds>
#include <cambc.h>
#include <iostream>
#include "bot.h"
#include "draft.h"

int main() {
    Bot bot;
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else bot.play_turn();
        } catch (const std::exception& error) {
            std::cout << "PROBE " << cambc::round_number() << " err " << err_str(error) << '\n';
        } catch (...) {
            std::cout << "PROBE err unknown\n";
        }
        cambc::end_turn();
    }
}
