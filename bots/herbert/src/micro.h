// Champion-vs-champion micro: the user's matchup rules (Helios attack.cpp; hyperion_rewrite/src/micro.cpp), on Aph's
// world. Engaging and disengaging are the line model's calls (linefight.h); this moves, attacks and casts in the fight.
//   melee vs melee  : move + attack; else dash + move + attack; else hold where their walking distance to us is > 2
//                     (they can't move + attack us: we get the first hit), seeing them, as close as that allows; with
//                     a turn to give, forfeit there (a saved double turn).
//   melee vs ranged : with a turn to give, forfeit; move + attack; else dash + move + attack; else a double move that
//                     reaches them; else a stun that reaches them; else walk toward them.
//   melee in range  : stand on the in-range tile farthest from the nearest other enemy (else their spawn).
//   melee casts     : a shield when they can hit us next turn; damage spells whenever they reach; a reset after
//                     hitting; vs melee a stun at the END of the turn (vs ranged: the stun first).
//   ranged vs melee : out of range: walk toward them (a walk-compatible stun / damage spell still fires). In range:
//                     stand: stun, damage spell, attack (+ reset); the cast unused and they could reach us: dash away.
//   ranged vs ranged: in range: as vs melee without dashing away; else dash into range; else walk toward them but
//                     never into their range.
//   any             : a saved double turn confirms a kill.
//   retreat         : dash away; stun a chaser when the stun still lets us walk or deals damage; flee; about to be
//                     caught with a saved double turn: double-move away.
// Steps and dash landings avoid Pathing::blocked() (occupied tiles and the one-shot camp walls).
#pragma once
#include "util.h"

namespace aph {

class World;
class Pathing;
class Safety;
struct ChampionBelief;

namespace micro {

// Which champion fight to take this turn, on Helios's ladder (the user's combat system; hyperion_rewrite combat.cpp):
//   95  a channelling enemy (recall / tribute / teleport: a hit or stun breaks it) we reach and survive
//   85  an enemy our burst kills now, and we survive
//   72  the line-model fight is ours (we win, I live, by the linked pair's margin); ranged: holding 2 rounds is safe
//   70  retreat: no fight to take, the fight is not ours, and an enemy can hit us next turn
// Reach: melee within max_chase (a dasher 6, Varg 3, else 4); ranged what it reaches from here (range, or 4 with a
// damage spell ready), vs melee up to 3 past its range, vs ranged a dash into range or up to 3 past theirs. An enemy
// on or next to its spawn heals there: only a kill. Ties: more gems, then lower hp. Re-chosen every turn.
enum class Mode { none, fight, retreat };
struct Choice {
    Mode mode = Mode::none;
    const ChampionBelief* target = nullptr;
    double score = 0;
};
// `zone`: Aph's pack zone (null for none) -- a target whose every in-reach tile lies in it is skipped (Aph's awareness).
Choice choose(const World& world, Safety& safety, const bitboard* zone);

void engage(const World& world, Pathing& pathing, Safety& safety, const ChampionBelief& e);
void retreat(const World& world, Pathing& pathing, Safety& safety);
// The nearest visible enemy that can hit us next turn (within its attack range + 1), or null.
const ChampionBelief* chaser(const World& world);
// Our best single action next turn kills `e` (a basic attack plus the best ability ready by then), hitting it without
// it moving.
bool double_kills(const World& world, const ChampionBelief& e);

} // namespace micro
} // namespace aph
