#pragma once
// The replay book: recorded winning games (research/ideas-2026-11-13/rbook). Where the map, our side and both teams'
// picks match an entry, the draft forces the recorded picks and each champion replays its recorded actions, checking
// a fingerprint of what it sees each turn; at the first difference it hands over to the bot for good.
#include <cambc.h>
#include <cstdint>
#include <vector>

namespace book {

// Draft: the recorded pick order while the picks so far match an entry, else null.
const std::vector<cambc::champion_draft>* draft_order();

// Champion: whether this instance plays an entry (decided on its first call).
bool active();

// Whether this game started on an entry (the same answer for every champion of the team, on or off it by now).
bool matched();

enum class Turn { done, rollover, handed_over };
// One turn of the entry. rollover: the recorded turn ran out of fuel, so this one spun to the next round, whose
// turn is the caller's to play next without ending one. handed_over: the bot plays this turn and the rest.
Turn play(std::uint32_t round);

} // namespace book
