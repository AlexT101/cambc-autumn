// The user's turn-order bands (hyperion): within a team a HIGHER priority acts first, a change applies from the next
// round. LAST this round -> FIRST next round: two of our actions back to back (a double turn); FIRST -> LAST: the enemy
// gets two in a row (a forfeit), banking a double turn. Values are secret per game (set in turn_order.cpp).
// The micro asks for a double turn or a forfeit during its turn; set_turn_order applies the request at the turn end
// (and otherwise Aph's needs, or the resting band).
#pragma once

namespace aph::bands {

enum class Band { last, first };

// This round's band, from the value we set last turn (first turn: the resting band).
Band now();
// A double turn is ready: LAST now (switching to FIRST next round acts twice in a row).
bool saved();
// The micro's requests for next round; the last call in a turn wins. Cleared at every turn end.
void use_double();   // FIRST next round
void forfeit();      // LAST next round
// What the micro asked this turn: 0 none, 1 FIRST, -1 LAST.
int request();
void clear_request();
// Set by set_turn_order once the band for next round is chosen.
void set_next(Band b, int round);
Band next();

} // namespace aph::bands
