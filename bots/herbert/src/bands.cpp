#include "bands.h"
#include <cambc.h>

namespace aph::bands {

namespace {
Band cur = Band::last, nxt = Band::last;
int set_round = -1;   // the round whose turn chose `nxt` (it takes effect the round after)
int asked = 0;
} // namespace

Band now() {
    if (set_round >= 0 && static_cast<int>(cambc::round_number()) > set_round) cur = nxt;
    return cur;
}

// LAST now and not already spending it this turn.
bool saved() { return now() == Band::last && asked <= 0; }
void use_double() { asked = 1; }
void forfeit() { asked = -1; }
int request() { return asked; }
void clear_request() { asked = 0; }

void set_next(Band b, int round) {
    now();   // settle `cur` before replacing `nxt`
    nxt = b;
    set_round = round;
}

Band next() { return nxt; }

} // namespace aph::bands
