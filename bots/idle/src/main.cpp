// Dispatch draft and gameplay; a failed pick still yields.
#include <cambc.h>
#include "bot.h"
#include "draft.h"

int main() {
    while (true) {
        try {
            if (cambc::is_draft())
                play_draft();
            else
                play_turn();
        } catch (...) {
        }
        cambc::end_turn();
    }
}
