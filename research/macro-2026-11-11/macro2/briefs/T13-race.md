# T13: don't farm groups the enemy wins the race to (candidate `bots/variants/macro2-race`)

Read /home/ubuntu/wt/macro2/research/macro-2026-11-11/briefs/common.md first and follow it. Base: copy
`variants/ocean-ref-b7c87cf` to `variants/macro2-race`.

## Evidence (256 debug ref-vs-ref games, 512 team-games; farm-waste analyst)
- Share of F turns that end without our team capturing the group farmed, by the group's side (walking distance from
  each spawn):

  | Group side | Waste | Notes |
  |---|---|---|
  | Our side | 27% | |
  | Mid | 59% | |
  | Enemy side | 82% | 59 productive vs 273 wasted turns per team-game |

- Bot-observable race (our walk to the group vs the enemy spawn's walk to it):

  | Our walk vs the enemy spawn's | Waste | Notes |
  |---|---|---|
  | 5+ shorter | 34% | |
  | Within ±5 | 65% | |
  | 5+ longer | 82% | 33 productive vs 148 wasted turns per team-game |

- With true positions: when the nearest enemy was closer to the group than us, waste was 63%; otherwise 23.5%.
- The waste classes this targets:
  - walking while the enemy captured the group first: 116 turns per team-game;
  - engaged, and the enemy captured it: 114, with an enemy champion near in 99;
  - part of the 194 turns that woke a group and left it uncleared.
- Example: game dir `0e4e7bfb24967928` in /home/ubuntu/wt/macro2-an/dbg, Cassi id 2, r298-352. She spends 55 F
  turns walking to the enemy-side wolf group g15, 28 away. The enemy Issac wakes it at r316 and captures it at r353
  while she is still 18 away.
- Ocean's farm (economy/farm.cc) already discounts mid groups (`mid_exposure`, up to x1.36 worth for mid groups)
  and uses claims. Find what it does about enemy contest: its contest, exposure or enemy-presence terms. An earlier
  candidate (macro2-plan, chain lookahead) lost by changing the farm order broadly. This change must be narrow.

## Principle
A capture needs sole occupancy for the hold, and camps never regenerate. So a group's value to us is its worth times
the chance that we finish clear-plus-hold before an enemy arrives and contests it. The enemy's earliest arrival is
bounded from what we know:
- for each enemy, its last-seen position plus one tile per round since it was seen;
- for unseen, dead or recalled enemies, the walk from the enemy spawn (after their respawn time, if dead).
Our finish is max(our walk, respawn left) + remaining hp / crew camp damage per round + the capture hold. If the
enemy's earliest arrival comes well before our finish, the group's expected worth falls. That isn't a magic
threshold: an arrival before our finish is a contest, and contests split (the mirror evidence shows about even
splits).

## What to build (bounded)
1. Find the farm's existing enemy and contest terms. If the valuation already prices the enemy's arrival, report how
   and stop unless it is clearly missing for unseen enemies (spawn bound) or for enemy-side groups.
2. Add the race to the group valuation in the farm (one place, the rate or worth computation):
   - expected worth = worth x p_win, where p_win = 1 if our finish comes before the enemy's earliest arrival,
     otherwise 1/2 (a contest).
   - Our finish uses the farm's existing clear-time estimate for the claiming crew. The enemy's earliest arrival
     uses existing world beliefs (enemy last seen, possible sets, respawn timers) and the enemy-spawn walk field
     the map already provides (e.g. `map.enemy_spawn_steps`).
   - The 1/2 comes from the rule that contested captures go to whoever holds the tile alone, and the mirror's even
     split. Say so in a comment.
3. Keep: claims, crews, heavy and Monolith programmes, safety, the draft and emblems. Don't change own-side group
   values when no enemy can arrive in time: p_win = 1, so behaviour is identical.
4. No new tuned constants beyond the derived 1/2.

## Check
Trace `RACE round handle group our_finish enemy_arrive p_win` (debug_block) for groups whose p_win < 1. Report how
often the chosen target changes vs ref, and the share of farm turns on enemy-side groups in your test games. Build,
play 3 local games, audit, and report as common.md says.
