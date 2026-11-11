# E2 "hub": allies price where their capture gems end up (bots/variants/hub)

Read /home/ubuntu/wt/macro-o4/research/macro-delphi/briefs/common.md first and follow it. Candidate dir:
`bots/variants/hub` (already created as a copy of bots/charybdis). Reference: `bots/variants/charybdis-ref` (identical
to the copy at the start).

## Why (measured on 512 charybdis-vs-charybdis mirror games, 2x fuel)
- A Prism is in 89% of games (both teams). The game is the Prism duel: 78% of Prism deaths are kills by the enemy
  Prism, and in 63% of Prism deaths the victim had under half the killer side's Prism Focus (under 0.8 in 87%). The
  team whose Prism dies first loses 90.5%. Winner's Prism: 782 gems collected, 4.8 kills, 0.2 deaths a game; loser's:
  513 collected, 1.6 deaths. So the decisive quantity is our Prism's Focus relative to theirs, i.e. its carried bag.
- A Prism gains 1.5 Focus per carried gem (rules: prism passive), and its stun (1.5x Focus) and ground spell (1x Focus)
  scale with Focus. charybdis already prices this on the **Prism's own** side: `carried_bonus()` (economy/capture.cc)
  = gems x per_gold price x (1.5 / Focus growth) x shard price; the Prism's farm values add it (farm.cc `keep_bonus`,
  `keep_most`), and it takes over allies' holds ('G'), groups they leave it ('L', within `carry_reach()`), and clears in
  progress ('Q'). Allies leave a fresh cleared gem group to a nearby Prism (`leave_for_prism`, `prism_eta`) when its
  ETA is within the capture time.
- But **allies choose their farm targets blind to this**: a non-Prism ally values a gem group's gems at 1 each wherever
  it is, so it clears groups far from our Prism, and those gems land in its own bag (worth 1) and walk to an altar
  (bag->altar walking is ~16% of ally turns). Each ally collects only ~110-140 gems a game. Pricing a mechanic the bot
  left unpriced is what has won before (CHANGES 507-512); this is the ally half of the same price.

## Design
1. **Ally-side carry price.** For a champion that is not a keeping Prism, with a living Prism ally that keeps its bag
   (`keeps_bag(world, prism, gems)`), each gem group g (gems > 0, not a Monolith, short of the win as `keep_bonus`
   requires) gains, in every farm value of g (solo, crew, kited, risky, join paths: wherever farm.cc counts a group's
   gems), `carried_bonus(world, prism, G.gems, price) x q(g)`, using the same price the Prism uses (`prices(world).per_gold`).
   - q(g) is whether the Prism will be able to take the capture: 1 when the Prism's ETA to g (from its visible or posted
     tile, `recent_tile`; counting its current task as `prism_eta` does) is at most our own rounds to finish g (walk +
     clear, the same rounds the value already divides by) + `cambc::constants::capture_time` (the leave window
     `leave_for_prism` uses), falling linearly to 0 at that + `carry_reach()`, 0 beyond or if unknown. Use a cheap
     bound first (Chebyshev steps from the Prism's tile to the group's tiles; walking steps are never fewer), and
     compute the real walk (a field from the group, e.g. `team_walk_to`, which farm already builds) only for groups
     that pass the bound and only once per group per round (cache by round, as `prism_eta` does).
   - The Prism itself already gets `keep_bonus`; do not double count. Willow, Cassi & Issac, every non-Prism: all get it.
   - **Prune bounds:** farm_turn prunes groups with upper bounds (`keep_most`, `bound_tribute`, `PreColumns`, the
     kept per-group facts and memo contexts). The ally bonus must be included in those bounds the same way
     `keep_most` is for the Prism (per gem: `carried_bonus(world, prism, 1, price)` is the most per gem, since
     `keeps_bag` only tightens with gems), or groups that now win would be pruned before being weighed. Any memo/
     context that caches values must be invalidated when the bonus changes (the Prism's bag/position changes every
     round, so key it on the round or include it past the kept facts as keep_bonus is).
2. **Consistency with the hand-over.** The bonus only pays if, when our clear ends, we actually leave the capture to
   the Prism and it comes. Check `leave_for_prism` / `left_for_prism` (capture.cc) and the Prism's 'L'/'Q' picks
   (farm.cc ~2270-2390): an ally that chose g for the bonus should leave g's capture to the Prism when the Prism is
   due within the window, and should not stand on its tiles to dilute a sole Prism hold (existing `prism_hold_tiles`
   logic). If `leave_for_prism` refuses cases that q(g) counted (e.g. its `world.round - left.first >= capture_time`
   lapse, or `prism_dominant`), make q(g) agree with it: q must be 0 where the hand-over would not happen. In
   particular respect `prism_dominant` (a Prism already at 2x the enemy's Focus): give q = 0 then, as the leave does.
3. Do not change what the Prism does, the draft, emblems, or banking thresholds.
4. Debug traces (debug_block): when an ally's chosen group differs from what it would have chosen without the bonus
   (if cheap to know; else just log the chosen group's bonus and q), and per hand-over whether the Prism collected.

## Done when
Builds; three local games against charybdis-ref finish without bot errors (one where both teams draft Prism, which is
most maps); traces show allies picking bonus groups and the Prism collecting them. Report as common.md asks, including
how often the bonus changed an ally's choice and how often the Prism then collected the capture.
