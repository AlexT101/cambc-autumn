// probe-capture: verifies capture timing/rewards/respawn, gold modifiers, passive gold and tribute timing.
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
            std::cout << "PROBE err " << error.what() << '\n';
        } catch (...) {
            std::cout << "PROBE err unknown\n";
        }
        cambc::end_turn();
    }
}
