# Presence on one-zone maps (PLAN step 5), 2026-11-05

Dev copy `bots/variants/ast-presence-dev` (astraeus 29cd0921 plus this change). Baseline `bots/variants/astraeus-29cd092`.
Both bots on their own drafts, fast runner, real fuel. Not committed.

## What it does

- **Zones** (`economy/presence.cc` `one_zone`): altars are linked when the walk between their tribute tiles is at most
  `zone_link` = 10. Walks go around `impassable`, so both teams get the same answer. Linked altars form one zone,
  transitively, and a single altar is one zone. A crow-flies pre-check (`zone_link + 2`) skips the fields when no
  link is possible. Otherwise each altar gets one field capped at 10 layers. Computed once a game.
- **Stakes** (`presence_level`):
  - P = max(ours, theirs) / 1000.
  - Ours is our tributed gems plus our bags (our own exact, allies' as posted in comms, so the team agrees).
  - Theirs is their tributed gems plus their believed bags. Those beliefs are emptied when a tribute lands, so they
    count what the enemy must still bank.
  - The stake is P², quantised into `presence_levels` = 32 steps. Squared, because a tribute decides the game
    only near the win.
  - The level is 0 below P ≈ 0.18, and always 0 off one-zone maps.
- **Value** (`presence_weights`):
  - A group's nearness is n = clamp(2 − walk(centre → tribute tiles) / 8, 0, 1): full within sight (8) of the zone,
    none past 16. From the group, a body sees a tribute start and walks into stun range before a long channel ends.
  - Its factor is (1 + β s n) / (1 + β s), with s = level / 32 and β = `presence_weight` = 1. At the win's stakes a
    near group outweighs a far one 2:1.
  - The factor is applied as a discount (at most 1). The farm loop's bounds all assume a weight of at most 1
    (`home_weights()`, `max_exposure`), so they stay valid upper bounds with no change.
  - Ranking between groups is the same as a (1 + β s n) bonus. The factor multiplies the kept per-group weight
    (`known.weight` in `farm_turn`), and `FarmContext` gains `presence` so the facts are read again at each level.
    The takeover weighs its gain by the factor; its work_rate is already weighted.
  - Our own shorter bank trips are not counted again: the loop already prices trip length. Enemy carriers to
    intercept, our channels needing allies, and both sides' bags all enter through the stakes.
- **Idle turns** (`presence_wait`, the `best < 0` branch of `farm_turn`):
  - With no group to farm, presence on, no pack zone (not carrying) and not threatened, the body walks
    (`step_safely`) to a screen tile and waits there. Before, it only stepped off respawning tiles.
  - Screen tiles are 2-4 steps out from the tribute tiles. In order of preference: on the enemy-facing side (enemy
    spawn walk below the zone's), bush and out of every striker's reach first, then the same classes off that side.
  - They are built once, when presence first applies. They come from whole boards plus one test a tile (a reach
    board drawn from the strikers), and the call checks for a stale turn after.
  - Idle turns are rare: base had 13 of 2,207 farm turns in a traced game, and the traced candidate games had no
    `PWAIT` at all. So this part changes almost nothing.
- **Knobs**: `zone_link` 10, `presence_weight` 1.0, `presence_levels` 32 (a resolution, not a tuning).
  The near/far radii come from `vision_radius`.

## Audit (read-only subagent)

Fixed:
1. The screen build looped over every group's threat board per band tile (up to ~270k fuel on maps with 100+
   groups). It ran after the farm loop with no reserve. Now it uses one reach board and runs before the loop, at
   presence onset, with a stale check after.
2. `presence_wait` ignored the pack zone and could hold a threatened tile. Now it is skipped while `zoned`
   (carrying) and when `safety.threatened(here)`.
3. The level flickered as an ally walked in and out of sight (exact bag against posted bag). Every ally but us now
   uses `comms::bag_of`.
4. The takeover counted the discount twice, since work_rate is already weighted. Now only its gain is weighted.

Rejected:
- A screen tile blocking a corridor to the altar: tribute tiles are excluded, the wait is rare, and the body
  leaves as soon as any group is worth farming.
- One-off costs before the loop (one_zone fields, first centre_to_altar reads): small, and the loop's `room()`
  absorbs them.

Checked fine by the auditor: prune bounds (PreUpper/PreLanes, claim_most, beyond, altar_below, rated_below),
weighted comparisons (best, shared, floor, risky, from_altar), context invalidation, and multi-zone and no-altar
logic.

## Results

All on the final source, the same code the A/B froze. The diff is `presence.diff` next to this file.

### Maps

- **Suites**: fresh ladder-mix `fresh-561001..561070`, 17,920 maps. Every map's zone count is in
  `zones-561001-561070.txt`, made by `tools/zones.mjs`, which uses the bot's walk rule.
- **One-zone share**: 9,149 of 17,920 maps (51.1%). Of those, 3,926 (21.9% of all maps) have a single altar, and
  none has no altar. In 561001-561040 the share is 5,249 of 10,240 (51.3%).
- **A/B suite**: `maps/suites/merged/presence-1z`, the 5,249 one-zone maps of 561001-561040.
- **Camp-gem share** within 10 of an altar on one-zone maps: p25 7.8%, median 29.9%, p75 65.2%.

### Multi-zone identity

- 10 multi-zone maps (`fresh-5610xx`), both sides, 100M fuel: 20/20 replays identical.
- Fuel on them: mean +0.05%, p99 +0.1%. That is codegen and one capped zone check; `presence_level` returns at
  once off one-zone maps.

### Fuel (`bench.py`, real budget, default set, 16 games)

- Mean 50,938 → 50,935.
- p99 90,459 → 90,897.
- Out-of-fuel play turns 63 → 110. 10 of the 16 games diverge, and 00contest-b alone adds about 40.

On 20 one-zone maps of 561041+ (40 games):

| | mean | p50 | p99 | turns over 100k | OOF (real budget) | farm-partial-evaluation |
|---|---|---|---|---|---|---|
| 100M fuel | +2.4% | +4.9% | +3.3% | 1.15% → 1.41% | | |
| real budget | +0.3% | +2.1% | +1.0% | | 120 → 151 | 5,553 → 6,673 |

The likely cause is the discount itself. With far groups worth less, `best_value` is lower, while the unweighted
bounds (`rated_below`, `beyond`, `altar_below`, the PreLanes `out` test) are not. So they prune less, and more
groups' facts are read.

### A/B (own drafts, real fuel, fast runner)

`ab.py variants/ast-presence-dev variants/astraeus-29cd092 --no-test-draft --suites maps/suites/merged/presence-1z`

- **Win rate: 50.1% of 10,498 one-zone games (5,257-5,241), 95% CI 49.1-51.0.** No failed matches.
- **Out-of-fuel turns**: candidate 99,928 in 7,939 games, base 86,580 in 7,495 (+15%).
- **Overall**: multi-zone maps are unchanged by construction, so the effect is about 0.51 × (+0.1) ≈ +0.05 points.
- Batch: `replays/batch-20261105-162430-ab-pres-1z-presence-1z`.

### Mechanism (1,000 of the A/B's games, `replays/analysis-pres1z`)

The research tools define a zone as altars within Chebyshev 10 of each other, so a few maps count differently.

| | candidate | base |
|---|---|---|
| presence within 8 of an altar, rounds 30-600 (`presence1z.py`) | 0.347 | 0.336 |
| ... rounds 30-300 / 300-600 / 600+ | 0.366 / 0.411 / 0.424 | 0.361 / 0.390 / 0.406 |
| long channels completed (n) | 44.5% (2,460) | 41.6% (2,504) |
| long channels cancelled by the enemy | 24.7% | 27.4% |
| one-zone 21+ turn channels completed | 24.4% (1,457) | 20.9% (1,539) |
| bags lost to champion kills per game, altar ≤3 / ≤8 / away | 83.2 / 58.9 / 43.2 | 77.3 / 60.0 / 45.1 |
| side with a winning bag won (`winready.py`, one zone) | 90.3% of 504 | 89.2% of 493 |
| rounds from a winning bag to the win: median / p75 / share over 30 | 37.5 / 93 / 54% | 45.5 / 120 / 57% |

- `presence1z.py`: the side with more presence won 69.6% of 830 games. This is correlational.
- In these mirror games the base's channels are the ones the candidate cancels, and the other way round. The
  candidate's long channels complete more often and get cancelled less. Its bags are smaller (442 against 484),
  which confounds the comparison.

## Read

- The change does what it is meant to: more presence late, more long channels completed, winning bags cashed
  about 8 rounds sooner.
- The effect is small and the win rate is level. The stakes are low for most of the game (P² is below 0.25 until
  500 gems), and at one-zone maps' median camp share most picks are unchanged.
- It also costs fuel: +15% out-of-fuel turns on one-zone maps.
- It does not hurt, but a single A/B shows no gain.

## Next

1. **Tighten the bounds with the weight.** Multiply the per-group unweighted bounds (`rated_below` and
   `unweighed_beaten`, `altar_below`, `claim_most`, PreLanes' weight table) by `presence_weight[g]`. Bound the
   `beyond` stop by the suffix maximum of the nearness: static per order, so it is cheap. That takes the
   out-of-fuel turns back without changing a pick, and it can be checked by 100M identity.
   - Same pass: make `presence_level` check the stakes first and remember a false `one_zone`. It now runs the zone
     check's capped fields on round 1, and 00lanes (18 altars) showed round-2 out-of-fuel turns.
2. Then step 2/4 of the plan (zone choice and the hold for long bags). Presence alone moves the metrics only a
   little; the hoard-cashing problem (finding 6) is where the rounds go.
