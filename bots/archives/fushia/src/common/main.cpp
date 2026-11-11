#include "../common/common.h"
#include "../draft/draft.h"
#include "../game/full_turn.h"
#include "constants.h"
#include <cstdio>

i32 main() {
    // run assertions to validate assumptions, in the draft only: its first turn has 10x
    // fuel, while a champion's first turn holds all of init
    if constexpr (constants::debug)
        if (cambc::is_draft()) {
            try {
                constants::test();
                fight::test_kits();
            } catch (const std::exception& e) {
                DBG("incorrect assumption: " << e.what());
                throw;
            }
        }

    while (true) {
        try {
            if (cambc::is_draft())
                draft_turn();
            else
                full_turn();

        } catch (const std::exception& e) {
            std::printf("error: %s\n", e.what()), std::fflush(stdout); // release too
        }
        cambc::end_turn();
    }
}
