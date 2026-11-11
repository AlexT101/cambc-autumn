# E3 "pairprice": a Cassi & Issac kill removes two bodies (bots/variants/pairprice)

Read /home/ubuntu/wt/macro-o4/research/macro-delphi/briefs/common.md first and follow it. Candidate dir:
`bots/variants/pairprice` (create it: `./copybot charybdis variants/pairprice`). Reference: `bots/variants/charybdis-ref`.

## Why (measured on 512 charybdis mirror games)
- Cassi & Issac are drafted by 1018 of 1024 teams. Rules: "If either dies, both die, giving one kill reward and both
  bags." Each body then stays dead ~60 rounds. The pair dies 1.69 times a game (Prism 0.90, Vesper 0.58): the
  largest death sink, ~200 body-rounds dead a game. The first kill of a game is Cassi 45% of the time, and the team
  making the first kill wins 69%.
- The bot's kill worth (combat/abilities.h `kill_distance`: full + `params::life_value` + bag; plan.cc builds `bag`
  from `pair_gems`, which already counts both bags, and `partner_bound` so the kill runs through the weaker body)
  counts **one life** for a pair kill. A pair kill takes two lives: the partner's full health and its life are lost too.
  Likewise our own stake when a pair body weighs a fight or a risk counts one life where two are at stake (see e.g.
  model/safety.cc `ally_fall_value`, and wherever our own life/stake enters stand/retreat/fight valuations; read
  `stand_lost_at`, `Safety` trades, `turn_order.cc` `turn_life_value` uses, fight.cc kill costs at ~line 862).

## Design
Price the second life, everywhere a champion's life is priced, from the rules:
1. **Enemy pair as a target.** Where an enemy's kill worth is formed (plan.cc's foe/unit tables `x.bag`/`b.foes`,
   unseen-target worth ~line 1101, fight.cc's chase kill cost ~line 862, abilities.cc hit worth, turn_order.cc's
   kill values), a linked-pair target whose partner is alive is worth, on top of what it is now, the partner's
   life: its `max_health + params::life_value` (in the same units `kill_distance` uses; for turn_order.cc use its
   own `turn_life_value` scale). Put it in one helper (e.g. `pair_life_extra(world, e)`) next to `pair_gems` and use it
   in each place rather than scattering arithmetic. Keep `partner_bound` logic as is.
2. **Our pair's own stake.** Where a body of ours weighs its own life against an enemy's or against gains (own stake
   terms like `ally_fall_value`'s `own`, any `my_max_health() + params::life_value` own-value terms, turn_order's
   protect offers for our own pair), add our living partner's `max_health + life_value` the same way. Do not change
   thresholds expressed as health fractions (recall lines etc.); only the value terms.
3. List every site you changed and every life-priced site you deliberately left alone, with the reason, in your report.
4. Debug traces (debug_block): optional, e.g. count of strike choices where the pair term changed the chosen target.

## Not in scope
Draft, emblems, anything not priced in life/kill-worth terms.

## Done when
Builds; three local games against charybdis-ref finish without bot errors (pick maps where both teams draft Cassi &
Issac; nearly all do). Report as common.md asks.
