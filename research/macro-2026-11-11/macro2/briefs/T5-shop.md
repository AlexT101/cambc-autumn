# T5: purchase timing as an inventory problem (candidate `bots/variants/macro2-shop`)

Read /home/ubuntu/wt/macro2/research/macro-2026-11-11/briefs/common.md first and follow it. Base: copy
`variants/ocean-ref-b7c87cf` to `variants/macro2-shop`.

## Why (measured in our mirror and solo games)
- Recalls are 43 (solo) to 56 (mirror) per team-game. In the mirror 50% of completed recalls are pure shop trips at
  >=60% HP (23 per team-game); median purchase 120 gold. Each costs the 5-turn channel plus a walk back out
  (median 19, mean 28 rounds), ~33 champion-rounds, ~17% of a team's champion-rounds.
  In solo (no enemy) recall+walk-out from spawn is ~30% of alive time. The economy is labour-bound (half the gem
  supply sits idle), so champion-rounds are the scarce input.
- `wants_shop` (economy/shop.cc) goes when `shop_gain_scale x affordable_prefix(world).gain` (+ heal) beats the
  trip, where `.gain` is the purchase's saving over the WHOLE remaining farming horizon (`gems_share x
  rounds_per_gem` rounds). That compares "buy now" with "never buy". The real alternative is "buy later, together
  with more gold" (or at the next free visit to spawn: death, heal recall, a recall that banks). Early in the game
  the horizon is long, so the rule trips for small purchases.

## The principle (economic order quantity)
With a fixed cost K per trip and a holding cost (the farm time lost because gold sits unspent), the optimal policy
orders when the holding cost accumulated since the last purchase equals K (for linear holding cost, at the
optimum the cycle's holding cost equals its ordering cost). No tuned constant is needed:
- per-round holding loss = the fraction of a round per round that the affordable purchase would save, i.e.
  `affordable_prefix(world)` before it is multiplied by `rounds` (the `quote.gain` it keeps; expose it, or divide
  the returned gain by the same `rounds`). Units: rounds saved per round of play.
- accumulate it each of our turns (per champion, a static in shop.cc is fine since each champion is its own bot
  process) while we hold gold that would buy something (the existing affordability gates: shard price; non-Prism
  needs the emblem price or a begun emblem). Reset the accumulator whenever we buy (any purchase on spawn or while
  dead, i.e. whenever our gold falls by a purchase) and when we can afford nothing.
- K = the trip's cost as `wants_shop` already computes it: `min(back, channel + hurt) + back` (Prism branch
  likewise).
- New rule: a dedicated shop trip goes when `accumulated + heal_rounds_now >= K` AND the existing full-horizon test
  still passes (it guards the end of the game: no trip whose whole remaining value is below its cost). Keep every
  other existing gate of `wants_shop` (bank first, threatened, awake camps near, closing, winning bag...). This can
  only make shop trips rarer or equal; it never adds a trip.
- Leave `shop_gain_scale` in the full-horizon test as it is.
- Leave `farm_recall`, `home_trip`, `continue_recall` and the farm's "recall as travel" pricing unchanged: those
  trips happen for other reasons and buy on arrival anyway, and they reset the accumulator, which is the point.
- Do not change WHAT is bought (that is emblem selection, off limits), only WHEN a dedicated trip goes.

## Check
Add a `debug_block` trace `SHOPQ round handle gold acc K went` on turns where the old rule would go, so the lead
can count suppressed trips. Build, play 2-3 local games (one vs `bots/idle` on a generated map is useful: no enemy,
pure farming) and confirm trips still happen (fewer, larger purchases). Then audit and report as common.md says.
