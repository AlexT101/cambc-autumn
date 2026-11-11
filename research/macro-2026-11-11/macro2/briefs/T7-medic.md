# T7: Willow as the team's medic (candidate `bots/variants/macro2-medic`)

Read /home/ubuntu/wt/macro2/research/macro-2026-11-11/briefs/common.md first and follow it. Base: copy
`variants/ocean-ref-b7c87cf` to `variants/macro2-medic`.

## Evidence (512 mirror games)
- Willow is drafted by 62% of teams. Her heal (rules: `willow` ability 0, heal 3 x Focus, ally target; any slot
  recasts 8 rounds later) gives ~420+ HP every 8 rounds, about 52 HP a round and rising with Focus. She actually heals
  15.5 HP a round on average (13.2k a game), so about 30% of capacity is used. Her camp damage is low (6.6k a game,
  against ~18k for Vesper), and 6.2% of all champion turns are her support branch ('h').
- Health only comes back on our own spawn (rules turn_end) or from Willow. Heal recalls are ~28% of recalls, each
  ~33 champion-rounds of channel and walk back. The economy is labour-bound, so a heal that replaces a trip is worth
  about (trip rounds) x (HP healed / HP a trip restores).
- Ocean's Willow code (combat/support.cc) serves one protected mate (Prism, or Tavi), plus an independent heal step
  and formation. Heavy clears cost tanks heal trips (crews: extra_trips, crew_budget in economy/crew.cc and farm.cc).

## Principle
Willow's heal is a team resource with a known rate. Spend each cast where it saves the most farm time, and stand
where it will be needed: next to the champion taking the most camp damage. Camps hit only the nearest champion in
range, so a healer behind its tank, outside every live member's reach or farther than the tank, takes nothing.

## What to build (bounded)
1. Heal target value (when the heal is ready): for each ally in heal range, value = min(heal amount, its missing
   HP) / its max HP x its trip cost home (recall channel + walk back out, as the code already prices it, e.g.
   HomeTrip/heal_rounds_now or the recall line logic). The protected mate keeps priority whenever ocean's existing
   rules say it needs a heal for safety (keep those rules). Otherwise heal the highest-value ally. Don't let a ready
   heal go unused when an ally in range misses HP.
2. Positioning: when the protected-mate support code does not need Willow (its mate is not in a fight, not hurt,
   or not alive), Willow attends the ally with the highest camp-damage intake in the last few rounds, or the planned
   tank of a crew clear (crew.cc knows who tanks; or read allies' claims and positions). She stands within heal
   range of it, on a tile no live camp member can hit (existing `camp_may_hit`, `exposure_at`), and keeps her own
   farming only when no ally needs her. Reuse existing station and step code; don't write a new pathfinder.
3. Integration with the farm, only if it is contained: an ally that Willow attends counts her expected heals
   (heal amount every 8 rounds over the clear's duration, capped at the damage) as extra health budget in its
   heal-trip pricing for that clear (where crew_budget/extra_trips or the farm's `usable_health` are computed). If this
   is not a small, clear change, skip it and say so.
4. Keep: Willow's safety rules (she holds no fight), Prism support behaviour when it is needed, every other champion's
   behaviour except the farm pricing in step 3.
5. No new tuned constants. Derive from rules (heal multiplier, cooldown 8, ranges) and existing measured prices.

## Check
Trace `MEDIC round handle target value attended` (debug_block). Build, play 2-3 local games on maps where Willow
is drafted (check the draft trace; 00interlock or generated maps from /home/ubuntu/wt/macro2-maps/s-200001; any map
where the stdout shows Willow), and report healing done (the replay's meta/stats or your traces) against the
reference on the same map if you can. Audit and report as common.md says.
