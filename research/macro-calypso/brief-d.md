# cal-d: the win window (endgame macro)

Variant NAME `cal-d`: edit only /home/ubuntu/wt/macro-o3/bots/variants/cal-d/ (create it first with
`cd /home/ubuntu/wt/macro-o3 && ./copybot charybdis variants/cal-d`).

## Why (measured, charybdis vs itself, 400 maps)

- Most games end with one big tribute: 401 completed tributes of 200+ gems in 400 games, 90% of them by the game's
  winner, channel median 41 rounds (a tribute channels ceil(bag/10) turn ends, scores the whole bag at the end, and
  any stun cancels it; an enemy altar lock placed there cancels it too; damage does not). The carrier is usually
  Prism, which keeps every gem for Focus until its bag wins (`keeps_gems`, `winning_bag`, economy/bank.cc).
- Making Prism keep a winning bag instead of channelling it loses 7.6 points: completing the winning channel is
  decisive.
- But 2,652 such channels start and 2,184 are cancelled. A 200+ channel completes ~45% of the time when no enemy
  stands within 10 tiles at its start, and only 5-15% with one or more. The current rule (`tribute_safe`,
  `tribute_ok`, `any_risk`, `continue_tribute`) judges safety over only params::tribute_window = 11 turns, so it
  starts 40-turn channels that enemies arriving later cancel, again and again, while the carrier stands at the altar.
- A champion dead in round D respawns at D+60/61 on its spawn: a kill opens a window longer than a median channel.
- Escort: altar_guard.cc already makes the team hold the altar while one of us carries a winning bag (`escorting`),
  but only on one-altar maps (`guarded_altar` returns -1 when altars form several sites).

## Design

1. **Window-timed winning channels.** When our bag would win (winning_bag, i.e. the channel the game turns on),
   estimate, for each altar we could tribute at, the earliest round any living enemy champion able to cancel the
   channel (any champion can stun? no: check each enemy type's abilities via its facts: a stun in reach, or a
   carried/buyable altar lock within 2 of the altar; a kill also ends it, so treat any enemy reaching attack range
   while our carrier would die... keep it simple: an enemy that reaches within max(its stun reach, lock range 2,
   attack range) of the channelling tile) could arrive:
   - dead enemy: its earliest respawn round (ChampionBelief respawn_earliest) + its walk from the enemy spawn;
   - visible or tracked (seen within params::track_horizon): its walk / Chebyshev distance from its tile, less its
     reach and a dash if it has one ready (or unknown);
   - untracked: last seen tile + 1 tile a round since (Chebyshev), as a lower bound; never seen: its spawn at round 1.
   The window margin of an altar = (earliest interrupt - now) - (our walk there + channel turns). Then:
   - prefer the altar with the largest margin among those we can reach (an extra walk is worth it if it buys margin);
   - start the winning channel when the margin is >= 0 (it should complete) - with any risk otherwise allowed by today's
     rules (`any_risk`) kept for short channels and the round limit;
   - when no altar has margin >= 0, keep today's behaviour (tribute_safe over the window), so nothing gets worse
     where we cannot see a window.
   - continue_tribute: do not cancel a channel whose margin is still >= 0 just because the 11-turn check flickers;
     do cancel as today when an enemy can actually stun/kill us before it completes.
2. **Escort on every map.** Generalise altar_guard.cc's escort: while an ally of ours carries a winning bag
   (`escorting`: score + bag >= 1000, bag as seen or comms::bag_of), the other allies guard the altar that carrier
   will use (if the carrier is visible and channelling: that altar; else the altar nearest the carrier's position as
   seen or posted via comms; each ally must compute the same choice from what it reads), not just on one-altar maps.
   Keep altar_guard's existing stand-tile / leash / strongest-bodies logic and its params; at most leave
   params::altar_farmers_min farming. The carrier itself is not a guard.
3. Debug traces (debug_block): when a winning channel starts (round, handle, bag, altar, margin, earliest interrupt,
   which enemy), when one is held back for lack of margin, when an escort starts on a multi-altar map, and at each
   cancellation of a winning channel (cause).

Everything must degrade to today's behaviour without a winning bag. Be careful with kept/cached values in bank.cc
(Key structs), with tribute_turns' Tribute-emblem cut (use the existing helpers), and with the enemy readings for
dead champions (respawn_earliest/latest semantics in model/world.h).
