// Enemy turn windows: when each enemy may act, given only what the rules force.
//
// Enemies may pick any priority every turn, so their next-round order is known only for those whose
// next priority was read after they acted this round ("settled"; all of them if their team never
// changes priority). Everyone else may slot in anywhere. The worst case depends on the question: an
// enemy that threatens us is taken at its earliest slot, one whose turn would spare us (camp tie hits,
// dash blockers, a channel ending) at its latest.
#pragma once

namespace aph {

class World;
struct ChampionBelief;

// Slot index of a team member holding `rank` in round `r` (World::slot's layout).
int slot_of_rank(const World& world, bool ally, int rank, int r);

// Next-round rank window of an enemy: [earliest, latest].
int enemy_earliest_rank(const World& world, const ChampionBelief& e);
int enemy_latest_rank(const World& world, const ChampionBelief& e);

// Slot windows for round `r`: this round is the read order, next round the rank window, later rounds anything.
int enemy_earliest_slot(const World& world, const ChampionBelief& e, int r);
int enemy_latest_slot(const World& world, const ChampionBelief& e, int r);

// This round: may this enemy still act after our current turn? Visible ones by their acted flag; unseen
// ones while some enemy turn after ours isn't accounted for by a visible enemy yet to act, given to the
// unseen enemies nearest our turn's start.
bool enemy_may_act_after_us(const World& world, const ChampionBelief& e);

// Next round: is this enemy one of the (at most enemy_turns_before) enemies given a turn before our
// next slot? The surely-earlier ones first, then the nearest and strongest of those that could be.
bool enemy_turn_before_ours_next(const World& world, const ChampionBelief& e);

} // namespace aph
