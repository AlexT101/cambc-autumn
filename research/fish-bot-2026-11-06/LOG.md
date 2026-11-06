
## Round 1, agent B: fidelity scorecard (2026-11-06)

Built `tools/fish/scorecard/`. It reuses `extract.mjs`, `team_decode.mjs`, `engage_rows`, `combat_data`, `combat_tiles`,
`farm3_describe` and `combat_rules` unchanged. New code:

- `obs.mjs`: farm3 snapshots plus emblems, camp-phase deaths and engine statistics;
- `build.py`: local batch manifests split into side parts A/B, decode and rows;
- `metrics.py` and `metric_defs.py`: about 110 metrics, per-game counters;
- `compare.py`: gap table, bootstrap SE, fidelity;
- `run.py`: one command.

Write-up: [SCORECARD.md](SCORECARD.md).

- **Fish column:** seventh + fifth + sixth, 412 games. It reproduces FISH_MODEL's figures within a few points, after
  fixing nine problems that a read-only audit found.
- **Control:** astraeus-37e1eb6 mirror, 256 sides. Fidelity 70.1.
  - Largest gaps: the priority encoding (0% of Fish's values), Cassi's stun on her cooldown (46% against 99%), camp
    deaths (0.31 against 1.17 a game), timer-1 recall keeps (94% against 45%), the home gate (64% against 98%), the bush
    tie-break (about 50% against 75-89%), solo Golem and Elk clears (22-28% against 2-10%), and min-EHP basics (79%
    against 94%).
  - Gold concentration per champion is also off: Willow and Issac farm and shop too much, Marcella too little.
  - Grouping is modestly looser: nearest ally 4 against 3, within 4 in 55% against 66%.
- **Candidate:** round-1 `bots/fish`, frozen mid-round (`replays/frozen/b96d6792f9d9`). 25.8% against astraeus-37e1eb6,
  fidelity 75.2.
  - The priority encoding and the home gate now match Fish.
  - Recall keeps, Cassi's stun, bushes, solo big clears, grouping and targets are still astraeus-like.
  - Kills, deaths and gold are worse than astraeus's.
- One `run.py` takes about 7 minutes: 73 s of games, about 5.5 min decode, 20 s metrics.

## Round 1, agent A: the deterministic and economic layer (2026-11-06)

`bots/fish` = `./copybot astraeus fish` (37e1eb64), `test_draft` off. New code in `src/fish/` (in `unity.cpp`):
`fish_math.{h,cc}`, `draft.h`, `builds.h`, `switches.h`.

**What is in** (FISH_MODEL sections):
- **§2 maths** (`fish/fish_math.h`), for round 2: `band`, `health_fraction`, `gem_health`, `ehp`, `reach_damage` (D,
  branch for branch `tools/fish/combat_common.py` one_turn_damage), `danger`, `threat`, `kill_available` (as
  `combat_tiles.py`), `acceptable`, `side_ehp_ratio`, `holder_rank`, `priority_rank`. All are O(enemies) or
  O(allies) with no allocation.
- **§3.1 draft** (`fish/draft.h`, hooked first in `draft/draft.cc` draft_order()): all 128 ladder maps are in
  Fish's replays (every cohort, one order per map). They are matched by `tools/draftlab/trainer.h`'s map key: the
  cached replay maps hold one side's camps, so they were mirrored by symmetry, and all 128 keys match
  `features.mjs`. Off the table:
  - Prism second on gold-free maps (all 7 Prism maps, no others);
  - 3 picks: Vesper Vale, then Marcella if total camp gold ≤ 1800 (15/19), else Heart of Ruin, then C&I;
  - 4-5 picks: Marcella first if total camp gold ≤ 2340, else Vesper Vale (94/107; the gem-over-gold-cluster rule
    gets 78/107, and only 15/26 on 4 picks), then Vendetta, HoR, C&I, Willow.
  - Ren and Varg (4 maps, all one-offs) only via the table.
  - Audit fix: astraeus's draft skipped Vesper Vale unless its model draft had loaded (`vesper_allowed`).
- **§3.2 / §8.4 shopping** (`fish/builds.h`, `fish_buy_shards` in `economy/shop.cc`): floor(gold/30) shards down the
  modal build of each champion, finishing each emblem first, then a repeat cycle (Bruisers; Prism Greed-H). Never
  saves, never sells. Vesper's build has Prospector-H fourth (57/96 games). Types Fish never drafts keep
  astraeus's `best_emblem`.
- **§8.5 locks:** bought only on lock maps (`lock_map`: gap ≤ 4, with the enemy's walk read through mirror); the
  rest of the buying rule is astraeus's order (shards, then a lock with ≥ 10 left), which is equivalent. Placement:
  any altar within 2 with no lock of either team (§14), dropping astraeus's own-side restriction. Astraeus's
  checks against cancelling an ally's tribute stay.
- **§8.6 crystals:** astraeus's logic kept. It buys only once a crystal hop to an altar beats walking, the same
  wall-crossing use Fish makes on a few maps.
- **§5 priority** (`model/turn_order.cc` rewritten; the astraeus version is `turn_order_astraeus.inc`, chosen by
  `FISH_PRIORITY`):
  - `priority = -rank - (N+1) L` with the modes dead, late (contested camp, +1 margin, clusters excluded), contact
    (j = min(16, floor(16 T/EHP)), sign by who starts the round the write applies to) and quiet;
  - written only on change. Traces `FP round handle priority`: the 6-body ranks come out 2,3,4,7,5,6, contact ±700.
  - Late contagion is not implemented.
  - Astraeus's kill and protect bids (`follow::`) are gone.
- **Comms:** nothing rides in priorities any more (`priority_payload_bits` 0). Claims come only from their
  shared-byte fields. The Prism-Willow support mailbox is dead: it had no other channel, and Fish has no fixed escort.
- **§8.1-8.2 recall** (`continue_recall`, `fish_recall_allowed` in `economy/bank.cc`):
  - Astraeus already started a recall at every off-spawn turn end, after all other actions.
  - Fish's gate now binds at every timer:
    - on an empty group, h ≤ 0.40 at timer 1 (h ≤ 0.63 before);
    - on a respawning tile in its payout round, h ≤ 0.63;
    - elsewhere, h ≤ 0.63 or gold ≥ 30.
    - A recall out of a pocket with no walk is always kept.
  - At timer 1 the gate is the whole rule. At timers 4-2, astraeus's reasons decide, plus a quiet capture hold,
    which keeps the recall (Fish's capturing and payout-round rows).
  - Walk-or-recall (walk ≤ 5 steps) and the hurt wait on spawn were already astraeus's (`walk_beats_recall`, `mend`).
- **§8.3 tribute** (`fish_tribute_next`, `may_chain`): chain unless `altar_walk ≤ ready + 2 and gems ≥ 8
  (altar_walk - 2)`.
  - The answer is cached per bag and refreshed when the bag changes or a turn is skipped.
  - ready uses at most two new centre fields per decision; the remaining groups use their Chebyshev bound.
  - Astraeus's winning-bag and enemy-reach checks stay.
  - Prism keeps astraeus's retaining_gems: it banks only a winning or closing bag, close to Fish's ≥ 1000 rule.
  - No tribute while holding a capture, as in astraeus.
- **Left as astraeus:** farming choice, camp targets, holders, combat, wards, the Willow/Prism support code,
  crystals, the walk home.

**Shared bytes:** unchanged from astraeus (`model/comms.cc`), least significant bits first:
- per ally, a claim field (`bit_width(groups+1)` bits, capped at (64 − bag)/team);
- the bag (in fours × team + body);
- the camp-capture record (respawn round mod period), only if it fits.

With 6 bodies on maps of 128+ groups this fills the 8 bytes and the camp record is dropped. Round 2's team camp memory
(§7.2) should take the claim fields' room: Fish has no claims, and once farm stops reading `comms::claim_of` (farm,
crew, siege, capture, pathing), 6 × 8 bits come free.

**Ablations** (ladder + fresh-540000, 768 games each, vs astraeus-37e1eb6; `bots/variants/fish-r1-*`, one
`fish/switches.h` switch each):

| variant | win | out-of-fuel turns CAND / REF |
| --- | ---: | ---: |
| all switches off | 49.9% (46.3-53.4) | 6425 / 6321 |
| Fish's draft off | 40.4% | 6456 / 6094 |
| Fish's recall gate off | 30.1% | 9082 / 6764 |
| Fish's priority off | 28.9% | 7332 / 6146 |
| Fish's shop off | 28.4% | 9247 / 7039 |
| Fish's tribute rule off | 25.7% | 8144 / 6779 |
| Fish's lock rules off | 24.7% | 7980 / 6606 |
| everything on (before the audit fixes) | about 25% | |

- With everything off it is astraeus again (49.9%), so the hooks are clean.
- No single bug explains the drop. The costs roughly add up: the draft about −15, recall about −5, priority about −4,
  shop about −3.5. Tribute and locks are level.
- Fish's lineups (Willow, C&I, HoR) inside astraeus's farming and fights cost most, as in EXPERIMENTS "Fish's draft in
  demeter".

**A/B `fish-r1`** (after the audit fixes and the capture-hold recall), `fish` vs `variants/astraeus-37e1eb6`,
`--no-test-draft`: **23.6%** of 10,496 (95% CI 22.8-24.4).
- fish-dev: 23.5% of 10,240.
- ladder: 26.6% of 256.
- No failed matches.
- Out-of-fuel turns: fish 96,279 in 7,942 games, astraeus 76,347 in 7,565 (+26%). Most of it goes with the draft:
  with Fish's draft off the excess is about 6%. Fish's 6-body teams and Willow run more instances.

**Audit** (read-only subagent). Fixed:
- Vesper Vale skipped by the draft filter;
- a stale cached tribute answer for a same-size later bag;
- clusters counted as awake members in the late test;
- a 2 KB zero-fill on each tribute decision.

Checked and correct: band, D, kill, priority ranks, the sign rule, item layout, map key, camp rewards, timer
semantics.

Unverified: priority writes while channelling. The publish runs after the turn-end recall starts. FP traces show the
writes succeed off spawn, where nearly every turn has started one, but no probe covers it.

**Open for round 2:**
- The draft is the biggest single cost. Fish's teams need Fish's farming, crew habits and combat (round 2's chunks)
  rather than astraeus's.
- Kills fall and deaths rise (scorecard): astraeus's kill bids went with its priority. §10's kill override, chase and
  targets are needed.
- Late contagion (§5.3), and whether to share a late flag.
- Fish's timer-1 keep rate is 45% against astraeus's ~93%. The capture-hold keep is a start; what Fish keeps through
  timers 4-2 elsewhere is unknown (§13: no timer-4 classifier).
- Shared bytes for §7.2: drop claims.

## Round 2, agent C (farming) (2026-11-06)

`bots/fish_farm` = round 1's `bots/fish` plus the farming chunk, behind `fish::use_farm` (`fish/switches.h`).
New files: `fish/farm_memory.h` (camp memory, history), `fish/farm_choice.cc` (logit, forecast), `fish/farm_turn.cc`
(events, farm turn, holders, recall idle), `fish/farm.h` (declarations). Draft: round 1's camp-gold rule with the
128-map ladder table and its map key deleted (coordinator's correction; the first A/B below used fixed per-pick-count
orders for a few minutes, every later run the camp-gold rule).

**Implemented:**
- **§7.2 team-union memory.** Our own sightings each turn (groups read in view), the team's from comms; the
  union takes the team's when strictly newer. History as `routes_data.py`: visits, (origin, dest) transitions,
  `source` reset on a home arrival, `last`, the round an ally was last seen on a group's tiles.
- **§7.2 logit**, all 41 features and both weight sets (`farm3-fit.json`; the auditor checked every weight).
  Walk field from our tile with visible live camps as walls; goals approach tiles (alive or unknown) or camp tiles
  (empty or respawning); `us`/`them` from one static spawn field read at mirrored tiles. Events:
  - **payout** (last turn ended on a cleared group, same tile, now respawning): payout weights, origin and
    exclusion the paid group;
  - **spawn exit** (on spawn after an arrival, a respawn or round 1): spawn weights, origin -1, again every 5
    rounds while still on spawn;
  - **re-decisions** with payout weights between them: no target; target taken (turned respawning without our
    payout); a higher-ranked holder on the cleared target, seen at any distance; we stand on a cleared target the
    holder rule leaves; a completed tribute; no walk on (that group excluded).
  - Fuel: static per-group parts (12 features, the spawn walks, approach tiles) once a game; per decision one field
    capped at 80 steps, a linear export, and full pricing of the 20 soonest-ready candidates only; ln by a series
    (libm's cost ~150 a call). About 20k a decision on 50x50 maps, 35-50k on 89-100 wide ones; round 1's statics
    20-40k more.
- **§7.3 target:** prev's camps if one is in basic range, else (once the destination is in range) every camp in range,
  argmin (hp, y, x, handle). Nothing in passing while walking: a deviation (Fish's rule is conditional on attacking).
- **§7.4:** lone holder and highest rank stay; lower-ranked: best timer > 3 → leave iff h > 0.406, else leave iff own
  timer > 3 and free exits > 3 (`holding_capture_now`). Entry: decline a cleared target unless we outrank its best
  visible holder, or within 2 at capture timer ≤ 1 with gold ≤ 12. No tribute while capturing (astraeus already).
  Astraeus's Marcella join, yield and hand-over are off.
- **§7.5:** waking alone, no crew wait (crews, siege and kite are off); no flight from camp fire in the farm turn; at
  the camp-range edge under fire, step out on a deterministic 45% hash.
- **§8.1-8.2:** a prepared recall is kept at timers 4-2 through idle turns (a quiet capture hold, a respawn wait at
  the destination's attack tiles with nothing in reach, a home trip whose walk is > 5) with no enemy seen, then the
  timer-1 keep rule decides; otherwise round 1's gate, and astraeus's retreat, bank and pocket keeps (no shop keep,
  no recall to farm). Home trip = the payout forecast tree (econ-payout.json) says home and the gate holds; walked
  if ≤ 5 steps, else the recall. Cleared on arrival, death, or a failed timer-1 gate.
- **Opening:** the spawn-weight logit (Fish's opening is not recovered; the tools fit the spawn weights without
  openings).

**Stays astraeus:** banking and chaining with a bag (`farm()` hands a bag's turn to astraeus's `farm_banking`: Fish's
own chained farm read 4 points lower), the walk (astraeus's approach search when made or affordable above a 60k floor,
else the static centre field's descent), want_home and retreat (combat's), wake_ring, sealed_in, contest_capture,
Prism's retaining gems, the r1 tribute rule, crystals, late contagion (combat's).

**Shared bytes** (`model/comms.cc`, least significant first): the bag (bag in fours × team + body, 10 bits at 6
bodies), then as many camp records as fit, 3 at 6 bodies and 255 groups (up to 4): group + 1 (`bit_width(groups+1)`
bits), Fish state − 1 (2 bits: alive, empty, respawning), a round mod 256 (8 bits: the sighting round for alive and
empty, the return round for respawning, decoded within [now − 100, now + 155]). A slot is rewritten only once two
rounds have passed since it changed (every teammate has read it), oldest first; posts go respawning, then empty, then
alive only where the team holds the group empty or respawning. Claims are gone: `claim_of` reads -1 for allies.

**Shared-file hunks:**
- `bot.cc`: `#include "fish/farm.h"`; `fish_farm::events` at decide's top; join_marcella / yield / hand-over skipped
  under `use_farm`; `fish_farm::home_walk` in place of the `wants_shop` trip; siege and kite skipped; act()'s
  unbounded `pathing.approach` kept only when banking; `fish_farm::turn_end` before `comms::claim`.
- `unity.cpp`: `fish/farm_choice.cc`, `fish/farm_turn.cc` after `economy/farm.cc`.
- `fish/switches.h`: `use_farm`.
- `fish/draft.h`: ladder table and map key deleted (coordinator's instruction, the same in combat's copy).
- `bot.h`, `bot_parts.h`, `fish_math.*`: untouched.

**A/B** `fish_farm` vs `variants/astraeus-37e1eb6`, fish-dev, `--no-test-draft`, 10,240 games each (fast runner):

| run | win (95% CI) | out-of-fuel CAND / REF |
| --- | ---: | ---: |
| first build (`fish-r2-farm`, fixed-order draft) | 7.5% (7.0-8.0) | 405,873 / 52,752 |
| walk by centre descent only (`-b`) | 3.9% (3.5-4.3) | 194,138 / 50,433 |
| same, `use_farm` off (`-off`): round 1 plus the new comms | 28.0% (27.1-28.9) | 136,498 / 83,567 |
| ablations of `-b`: no home trip or respawn keep 3.8%, no edge step 4.6%, no Fish holder rule 4.1%, no Fish recall keeps 3.5%, choice by `lograte` alone 4.0%, no waits beyond the walk 9.1% (of the `-c` build) | | |
| approach walk within a floor, descent fallback (`-c`) | 9.8% (9.2-10.4) | 204,521 / 52,199 |
| + astraeus's banking farm (`-d`) | 12.3% (11.7-13.0) | 284,740 / 59,052 |
| + act()'s approach on banking turns (**`-e`, final**) | **12.6% (12.0-13.3)** | 298,748 / 58,708 |

Below round 1's 23.6% and well below the 28.0% of the same build with the farm off. The loss is the farm turn's
execution, not the choice: choosing by `lograte` alone reads the same as the logit, and no single rule (home trip,
edge step, holders, recall keeps, respawn waits) moves it. The walk alone was worth 6 points (descent only 3.9%,
approach 9.8%). Out-of-fuel turns are 5x astraeus's and twice the farm-off build's; the first build's were the
approach search on far targets (50-75k a search: its estimate runs short), and `fuel/census` puts most of the rest in
decide and the turn-order queue.

**Scorecard** `farm-r2` (128 ladder maps, 256 games; saved as `scorecard-farm-r2.{md,json}`): fidelity 75.2 (r1
75.2, control 70.1). Farming and economy, Fish / r1 / r2:
- closer: `solo_clear:Wolf` 30.0% / 39.5% / 20.1% (now under), `solo_clear:Elk` 9.7% / 24.0% / 9.4%, `solo_clear:Golem`
  2.3% / 13.3% / 2.5%, `wake_alone` 60.9% / 68.9% / 60.6% (Elk 54.1 / 62.4 / 59.2, Wolf 61.2 / 70.8 / 60.5),
  `pay_single` 93.6% / 97.8% / 94.0%, `keep_rate` 45.0% / 93.4% / 49.0%, `recall_survive` 4.6% / 1.4% / 3.3%,
  `camp_deaths` 1.17 / 0.25 / 1.5, `nearest_ally` 3 / 4 / 2;
- farther: `pay1k` 9.9 / 9.3 / 7.8 (mean 13 / 10.8 / 9.9), `pay_groups` 5.41 / 5.08 / 3.79, `pay_own` 79.9% / 79.9% /
  90.0%, `side_own` 67.4% / 71.5% / 77.4%, `team_within8` 31.8% / 29.8% / 39.5%, `spent` 1,110 / 763 / 633, `shards`
  36.5 / 25.1 / 20.8, `trib_bag` 26 / 21 / 18, `gems600` 576 / 368 / 274, `gold600` 4,354 / 2,766 / 2,563;
- `keep_rule` 90.0% / 99.4% / 99.7% and `home_gate` 98.3% / 99.4% / 99.5% stay too exact.
So the micro rates now match Fish (crews, wakes, keeps), but income does not: fewer payouts per round, from fewer groups,
too much on our own side and too bunched.

**Audit** (read-only subagent; FISH_MODEL, `tools/fish`). Fixed: the no-walk re-decision did not exclude the failed
group (it looped every turn); the camp target looked only at prev or the destination; `awake` was zeroed for every
team sighting; a target that came back from respawning was never seen as taken again; spawn decisions every turn on
spawn. Checked correct: all 41 weights, the feature formulas, walls and candidates, the union rule, the forecast tree,
the holder and entry trees, the timer-1 rule, the comms encoding. Left (low): the forecast's ready/ready_walk come from
the team-union dynamic walk (Python: own memory, static walk); `altar_walk`/`home_walk` are dash-aware for dashers;
entry fires within 2 rather than 1 and unranked types always decline; `ally_recent` counts this turn; visits count
basic hits only; alive sightings are posted only against a team empty/respawning.

**Open problems:**
- The farm turn loses about 15 points to astraeus's farming even with Fish's choice replaced by a plain rate: walking
  (detours, approach skips; 27 turns for 19 tiles in one harvest trace), long respawn waits by design (Fish waits),
  no gems in passing, no health budget before a clear (astraeus's `affordable`), and no enemy-aware zones. A turn-level
  diff against Fish's replays (paths, waits) is the next step.
- Fuel: the decision is 20-50k on wide maps and the approach search 50k+; round 1 runs out on 89-100 wide maps.
- `pay_own` 90% and `team_within8` 40%: everyone converges on the same own-side groups; the entry rule then sends the
  lower ranks off again (30-55 declines a game).

## Round 2, agent D (combat) (2026-11-06)

`bots/fish_combat`: FISH_MODEL sections 9, 10, 12 and the rest of 5, in a new `src/fish/combat_turn.{h,cc}` (namespace
`fishc`). It is switched in pieces from `fish/switches.h`. Every rule reads the turn-start view, and targets are read
live.

**Implemented** (all on unless marked):
- **Contact turn (§10),** `contact_turn`, before the goal, in place of `search_strikes`. Order:
  1. Willow's heal.
  2. A spell kill from the start tile, on the spell's own target.
  3. A dash kill, with windows HoR 2-3, melee 3-4 and ranged dasher 4-5. A landing counts if the blow is at least
     the target's EHP. HoR lands on the tile with the most enemies within 1, and melee walks in and hits.
  4. Stand-and-cast, iff the start tile is acceptable or a capture is held.
  5. The contexts m2 / m1 / r.
     - Engage iff a kill is available, or h > 0.49 and danger ≤ 0.28.
     - Engage tiles are adjacent to the weakest reachable enemy, at least danger, ties to the bush.
     - Decline goes to the lowest-danger farther tile; ties go homeward, then to the bush.
     - Ranged with a melee enemy within 2 kites: tiles 3 or more from melee enemies first, then max min(dmelee, 3).
     - m2 declining from an acceptable tile lets the goal walk, with the step guard keeping it off tiles adjacent to
       enemies (`stay_out_round`).
  6. In basic range: hit there.
  7. The chase (0.37 / 1.24 / 0.44).
  - Basic target: argmin (EHP, id). Ren is skipped when its retaliation would kill us; the round-1 own-spawn
    exclusion is dropped.
  - Unit spell target: argmax (gems + 8) / EHP. Cassi stuns max Strength, Marcella and already-stunned enemies
    excluded, iff her damage spell is on cooldown or she walked. Prism's ground centre covers the most enemies
    within 1.
  - Resets: Marcella re-hits the first target. There is no focus fire, no kill holding and no channel-interrupt
    priority. A running capture limits candidates to its tiles, and HoR does not dash off a capture.
  - Beyond distance 5 it returns at once unless the nearest enemy was hit last turn.
- **After the goal,** `after_goal` (`use_after`), in place of `strike_after`: Willow's heal, an unspent basic, a
  ranged walk's reset, Cassi's stun, and a ready exclusive damage spell if the champion stood still.
- **Range 4-8 (§9).**
  - `near_turn` (`use_near`), with the nearest enemy within 4:
    - camp hits stop;
    - healthy, momentum: close iff last turn's step continued would close, else hold the distance, on acceptable
      tiles;
    - hurt, the decline tile.
  - `step_guard` (`use_guard`, in place of astraeus's step and work guards): at h ≤ 0.5, steps closing on the
    nearest enemy are guarded.
  - Danger-weighted steps, then bush first (`use_steps`): `fish_rank` in `closer_neighbours` and in `route()`'s
    first-step sort.
  - No pursuit, hunting or rally: `chase()` is off.
- **Casting.**
  - HoR shields iff a visible unstunned enemy has D > 0 against it (`use_shield`); camp shield reasons stay.
  - Willow's heal goes to the visible ally within 4 with max min(missing, heal) / max (`use_support`). The
    Willow/Prism support code is off.
- **Turn order (§5).**
  - Late contagion (`use_late`): late (band + 5) when an enemy is in sight and a visible ally is late on its own
    account (at a contested camp, no enemy in reach). The ally's priority is not read, because two allies copying
    each other latched late for good.
  - Contact sign checked in replays: a champion alone in contact on consecutive rounds (last in its team in round r,
    first in r+1) had no enemy turn between its two turns in 28 of 44 cases. The other 16 are explained by the
    enemy having more bodies (C&I) whose turns run in a row. With several allies in contact, only the one with the
    highest j is last.
- **Wards (§12),** `place_ward` (`use_wards`):
  - the rate comes from the context at the start of the turn (contact 8%, enemy 5%, none 2.9%), drawn
    deterministically from a hash;
  - tiles are bush tiles within 2, not on the enemy spawn and not a visible allied ward;
  - score: unseen bush tiles reachable through bushes within 6 (king steps); ties go to distance 2, then away from
    the enemy;
  - allied wards are not tracked.
- **Draft,** at the coordinator's request: the 128-map ladder table and its map key are deleted from `fish/draft.h`.
  The fitted feature rule (gold-free Prism, camp gold 1800 / 2340) is kept.

**Off, measured worse:**
- `use_home`: want_home cut down to Fish's (low health, mono/camp trap, camp fled), dropping pack zone and stand_lost.
  The cut alone cost about 13 points on 256 ladder games.
- `use_free_search`: astraeus's search on turns the rules leave free. It made about +2 points but doubled
  out-of-fuel turns.
- `use_contact_first`: Fish's declines in place of want_home's retreat in contact. 6% on 256 ladder games, with
  12.4 deaths a game.

**Stays astraeus:**
- the escape timing (want_home / retreat), which decides most contact turns before `contact_turn` runs: the debug
  games show almost no declines reaching it;
- mend, captures and the Monolith / camp logic.

**Shared-file hunks:**
- `fish/switches.h`: the combat switch block, listed above.
- `unity.cpp`: `#include "fish/combat_turn.cc"` before `bot.cc`.
- `bot_parts.h`: `#include "fish/combat_turn.h"` and `#include "fish/switches.h"` after `draft/map_economy.h`.
- `bot.cc`:
  1. `place_ward` top: `if constexpr (fish::use_wards) return bushes && fishc::place_ward(world, memory);`
  2. willow/prism become `!fish::use_support && support_healer(...)` / `support_protected(...)`.
  3. `leave` gets `!(fish::use_contact_first && fishc::in_contact(world)) &&` (the switch is off).
  4. The strike search is replaced by `fishc::contact_turn`. If it took the turn: settle the guard, see stuns,
     refresh, `hold_capture` if holding, return. Otherwise, under `use_free_search` (off), `search_strikes`. The
     `else` branch keeps the old search.
  5. Before `decision = Branch::farm`: `if constexpr (fish::use_near) if (fishc::near_turn(...)) return;`
  6. In `act()`: `if constexpr (fish::use_after) fishc::after_goal(world); else ... strike_after ...`
- `fish/draft.h`: table and map key removed, as above.

**A/B** on fish-dev (`--no-test-draft`, 10,240 games each, against `variants/astraeus-37e1eb6`, current draft):

| variant | win (95% CI) | out-of-fuel turns CAND / REF |
| --- | ---: | ---: |
| combat all off (r1's level; table drop changes nothing here) | 23.5% (22.7-24.3) | 93,525 / 74,143 |
| shipped (`fish-r2c-final`, free search off) | **11.2% (10.6-11.8)** | 51,033 / 69,211 |
| shipped + free search (`fish-r2-combat`) | 13.3% (12.7-14.0) | 112,215 / 68,161 |
| shipped, contact rules off (`fish-r2-combat-nocontact`) | 18.5% (17.8-19.3) | 74,763 / 69,734 |
| strike target only (`basic_hit`) | 23.6% | 93,883 / 73,858 |
| only the step guard | 20.1% | 63,460 / 72,444 |
| only near_turn | 22.9% | 99,313 / 72,827 |
| only the step order | 23.6% | 99,240 / 71,547 |
| only the Willow heal rule | 23.0% | 90,048 / 73,772 |
| only the HoR shield rule | 23.2% | 93,144 / 73,106 |
| only late contagion | 23.8% | 104,959 / 73,317 |
| only Fish's wards | 20.6% | 86,676 / 72,229 |

- Losses against r1: the contact rules and after_goal cost about 7 points, the step guard about 3.5 and Fish's wards
  about 3 (far fewer wards, so less sight). Near, steps, heal rule, shield, late and target are level. The
  contact-only run was stopped at wrap-up.
- Kills fall: 2.1 a game against nocontact's 3.9 (ladder, 256 games). Deaths are about the same in every variant
  (8.5 a game, 2.2 for astraeus), so deaths are not from this chunk.
- Out-of-fuel turns fall below astraeus's: the rules and guard replace astraeus's safety work.

**Scorecard** `combat-r2` (shipped config, ladder 256 games; values Fish / r1 / r2):

| metric | Fish | r1 | r2 |
| --- | ---: | ---: | ---: |
| fidelity | | 75.2 | 71.2 (control 70.1) |
| kills | 8.6 | 4.64 | 2.06 |
| deaths | 5.15 | 11.1 | 11.4 |
| contact_hit | 53.8% | 49.0% | 41.0% |
| engage_rule | 73.9% | 66.8% | 68.5% |
| engage_rate m2 | 58.6% | 47.5% | 38.5% |
| engage_rate m1 | 69.7% | 61.7% | 58.8% |
| engage_rate r | 62.1% | 53.2% | 48.8% |
| kill_override | 98.4% | 90.6% | 95.5% |
| chase_rule | 73.9% | 67.3% | 75.3% |
| chase_rate | 61.4% | 52.7% | 46.9% |
| basic_minehp | 94.0% | 79.4% | 84.0% |
| hor_shield_rule | 93.1% | 88.2% | 90.8% |
| cassi_stun_on_cd | 99.3% | 49.9% | 89.3% |
| momentum | 70.9% | 68.7% | 70.7% |
| campcont_rule | 79.8% | 81.7% | 91.0% |
| campcont d4 | 43.2% | 52.4% | 10.0% |
| ward_rate contact / enemy / none | 8.8 / 5.4 / 3.0% | 3.2 / 3.3 / 3.7% | 1.1 / 0.6 / 0.4% |
| ward_bush | 83.3% | 73.4% | 100% |
| bush_tie contact / enemy / none | 83.6 / 88.9 / 74.8% | 50.5 / 46.6 / 49.1% | 73.2 / 87.8 / 93.1% |
| prio late / contact | 2.3 / 4.8% | 2.9 / 7.3% | 3.6 / 5.3% |

- The total fidelity drop includes the coordinator's draft change, which removed the ladder table.
- Gains: Cassi's stun, bush ties, chase rule, kill override and HoR's shield.
- Engage rates are lower than r1's: want_home's retreats take most contact turns before the rules see them.
- The ward rate is far too low: bush-only candidates with a deterministic draw; see the open problems.

**Audit** (read-only subagent). Fixed:
- HoR dashing off a capture;
- turns that did nothing yet blocked the goal (m2 decline, all targets excluded, r decline with a failed walk,
  chase with no step);
- the late latch;
- momentum missing;
- m1 engage never moving;
- the spell kill missing its target;
- Willow's heal losing to after_goal's reset;
- decline ties putting the bush before home.

Not fixed:
- ward tiles off bushes (21% for Fish);
- the ward score's king-step clusters;
- the visible-ward test uses the turn-start view (a caught error, ~3.9k, after walking into a cluster);
- the reset ignores whether the first target survived;
- stand-and-cast also covers Ren and Ryth;
- `context()` is not excluded on our own spawn.

**Deviations:**
- The ward rate is a deterministic draw.
- HoR's non-kill landing is limited to acceptable tiles.
- Camps still shield HoR.
- m2 decline holds an acceptable start tile, with the goal walking off the engage tiles.
- Cassi with both spells ready, standing, casts damage (Fish's stand-and-cast), not astraeus's choice.

**Open problems:**
- Why the contact rules lose fights (kill share at equal numbers 0.20 against nocontact's 0.32): engagement is rare
  and mostly the m1/m2 hit-and-stay, while astraeus's planner times its focus and escapes.
- The step guard alone costs 3.5 points: Fish's guard protects much less than astraeus's danger guard.
- Fish's wards alone cost 3 points: too few wards. Fix the rate first (off-bush tiles, a real draw).
- The ward rate is about 10x too low.
- campcont d4 is 10% against Fish's 43%: near_turn stops camp hits whenever it can make a step.

## Merge of round 2's chunks (2026-11-06)

`bots/fish_farm` and `bots/fish_combat` are merged into `bots/fish` and deleted, so the attempt lives in one bot. The
two chunks were disjoint except for `bot.cc`, `fish/switches.h` and `unity.cpp`, which were merged three-way with
round 1 as the base, with no conflicting hunks (switches.h keeps both blocks). Every other file comes from the chunk
that changed it: the farming chunk's `economy/{bank,camps,capture,farm}.cc`, `fish/draft.h`, `fish/farm*` and
`model/comms.cc`; the combat chunk's `bot_parts.h`, `combat/{fight,guard,plan,self_abilities}.cc`,
`fish/combat_turn.*`, `model/pathing.cc` and `model/turn_order.cc`. Both switches stay as each chunk left them
(`use_farm`, `use_combat` and `use_wards` on, the combat parts as in agent D's section). The merged bot is not A/B'd:
each chunk alone lost to round 1 (12.6% and 11.2% against round 1's 23.6%). Setting `use_farm` or `use_combat` to
false gives that system's round 1 behaviour back, except `model/comms.cc`, which the farming chunk rewrote
unconditionally.
