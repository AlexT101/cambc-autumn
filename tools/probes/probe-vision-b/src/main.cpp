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
            std::cout << "PROBE " << cambc::round_number() << " B uncaught=" << error.what() << '\n';
        }
        cambc::end_turn();
    }
}
