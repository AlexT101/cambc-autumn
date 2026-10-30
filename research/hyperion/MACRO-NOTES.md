# Macro overhaul notes (macro-4, from astraeus ef8f0b8, 2026-10-30)

Running log: models, designs, observations, results. Baseline: `bots/variants/astraeus-ef8f0b8` (own drafts),
A/Bs at `--fuel 100000000`. Dev suites: ladder, gen, fresh(gen-s1), fresh-6051..6066 (~9.4k games, ~4 min wall
when the box is free). Held out: fresh-6091..6098.

## Tools

- `tools/replay/macro_stats.py DIR` (extract.mjs `--out DIR` first): per team, winners vs losers: time shares by
  activity, walk segments by what starts/ends them, clears by helpers, captures, deaths, kills, idle groups.

## Self-play picture (m4-self: 512 unique games of gen + fresh-6051; ladder alike)

Time share of champion-rounds (winner team):
- walking empty 31.7%, walking with a bag 19.2%, damaging camps 17.8%, recall channel 6.9%, standing still 6.8%,
  holding a capture 4.8%, dead 3.6% (losers 7.4%), fights 3.1%, tributing 2.7%.
- Walks by what starts them (share of alive time, count a team-game, mean rounds): from a camp 14% (81, 7.6), from a
  tribute 11.5% (35, 14.6), from a hold 10.6% (40, 11.7), from spawn 9.9% (30, 14.7), from a recall landing 8.8%
  (29.5, 13.4), from a fight 6.9%. Spawn + recall walks out: 18.7% of alive time (~60 trips a team-game).
- Group to group: median 21 rounds from the last hit on one group to the first on the next; the chosen group is a
  median 11 tiles off, the nearest live group 9: target choice is mostly near; travel is the map's geometry.
- Camps are abundant: groups up and asleep hold ~4.0 of the map's 6.7 gems/round (sum gems/respawn) at any time.
  The bottleneck is champion time and health, not camps.
- Captures: 99% have one holder. Clears with >=2 champions dealing 10%+: ~55% of striker clears.
- Winners vs losers: deaths 2.5 vs 5.4, kills 4.7 vs 2.0, gems lost 31 vs 71, captured gems 994 vs 789,
  gold earned 5824 vs 4387.
- Champion kills: victim had 0 allies within 6 in 43% of them; (victim side - killer side) within 6: even 38%,
  -1 23%, +1 20%: numbers alone don't decide.
- Monolith maps (123 of 512): no capture in 75; the first capturer wins 37 of 48; median first capture r928.
- Mean Strength 50 / 63 / 88 and max health 960 / 1111 / 1475 at rounds 100 / 300 / 600.

## Model: solo vs pair clears

Solo cycle: travel T + clear C + capture 6 + heal share R*S*C/M (S camp strength, M max health, R ~19 rounds a heal
trip). A pair that both hold: per champion better than solo only if T + 6 < R*S*C/(2M), i.e. only for groups too
costly to clear alone. Pairs pay through fights (local superiority) and safety, not farm throughput.
