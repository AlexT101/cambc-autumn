# Fuel caps for v87 (oc-base25), 2026-11-09

The user asked: "every change probably adds fuel. perhaps we need to start looking at some of the algorithms in our bot and *prove* their fuel usage is capped at some amount or fix / optimise it - potentially branching more etc." Two follow-ups: does v93 lose live because it runs out of fuel more in critical turns, and do we skip the SDK's wrappers by calling the wasm imports directly.

Bot: v87 = `bots/variants/oc-base25`. Local games: fast runner, own drafts on both sides, ladder-v2 suites `maps/suites/fuelcap/s1370000`–`s1370033` (seeds 1370000–1370033).

## Live drift is not fuel

- **Live OOF is flat from v86 to v93.** Out-of-fuel turns per 1k rounds, r2, 512 games each: v86 11.0, v87 11.7, v88 11.2, v89 10.9, v91 10.6, v93 11.2. Over the same versions the live win rate fell from 65.8% to 60.5%.
- **Local OOF matches live.** Release builds against v86 locally: 12.3, 13.0, 13.2, 13.0, 12.5, 11.6 per 1k rounds.
- **Where OOF happens.** About half of live OOF turns are fight turns (an enemy within 4); in tribute turns it is about 0.
- **Paired games.** In v86→v93 games that flipped, fight-OOF fell in 14 and rose in 1.
- **Wins and losses.** Won games have as much OOF as lost games, or more.
- **Fuel cost is the same live and local.** The v66 harness showed identical per-turn fuel. For v87, the draft's first turn differs by only tens of fuel (the local-only `cambc_local.h` guard and the anytime draft).
- **Conclusion.** OOF doesn't explain the drift, and local tests can see fuel effects.

## Where the fuel goes (the budget table)

`budget-v87.txt` holds the per-component distribution over every turn, not just heavy turns. It covers 512 games against oc-base25, about 2.27M turns, at the real budget (left) and at 2x (right). The census's new budget histograms produce it (`CHIST`, `tools/fuel/census/budget.py`).

| component | runs on | p50 | p90 | p99 | max | mean | fuel check inside |
|---|---|---|---|---|---|---|---|
| whole turn | 100% | 52k | 86k | 93k | 100k | 53.6k | |
| decide | 100% | 33k | 58k | 79k | 96k | 32.9k | |
| goal / farm tail | 64% | 26k | 45k | 65k | 93k | 16.8k | farm loop: every pass |
| farm.loop | 44% | 11k | 24k | 41k | 84k | 6.0k | yes (`loop_reserve`) |
| turn-end queue | 100% | 2k | 40k | 77k | 84k | 11.4k | yes (spend-bound) |
| world update | 100% | 6k | 10k | 14k | 36k | 7.1k | **no** |
| channels (continue_recall's want_home) | 91% | 2k | 14k | 30k | 92k | 4.9k | **no** |
| wh.stand_lost | 83% | 0 | 10k | 23k | 73k | 2.2k | **no** |
| strike_search | 76% | 0 | 0 | 25k | 82k | 0.7k | caps on nodes and queries; **no fuel check** (P1a adds one) |
| turn_order | 100% | 1k | 3k | 6k | 41k | 1.6k | yes (10k) |
| chase | 63% | 0 | 4k | 28k | 66k | 1.2k | prey: yes |
| comms send | 100% | 1k | 2k | 3k | 9k | 1.4k | no (bounded by message size) |

OOF in this run: 1.70 per 1k turns.

**At 2x the mean turn barely rises (53.6k → 54.4k), but the cut-short work almost disappears.**

| fired | 1x | 2x |
|---|---|---|
| farm-partial-evaluation | 62,142 | 430 |
| step-guard-entry | 39,761 | 148 |
| prey-cut-short | 13,195 | 37 |
| turn-order | 10,628 | 47 |
| OOF | 5,570 | 19 |

At 2x, 70% of the turns over 100k are early-game farm turns with no enemy near, on big winding maps: a capped field costs about 37k, and the route about 23k.

**What runs out.** From the census of 4,131 first-OOF turns:
- 75% have an enemy within 6.
- 71% passed no fuel check before running out; those turns spend their fuel in the ungated rows above (world, channels, stand_lost, strike search).
- Heaviest single items: a strike search, about 18k mean and 34k where it runs; one `s.new_fight` with 5–6 enemies, about 16k.
- The function profile is flat: no function takes over 5% of heavy turns.

**Gate slack** (`budget-v87-slack.txt`, `@slack` rows): the fuel left when decide ends, on turns where a gate cut work and the turn still finished.

| gate | p50 | p90 |
|---|---|---|
| all gates | 16k | 35k |
| farm | 15k | 30k |
| guard | 23k | 39k |
| fight | 14k | 31k |
| turn order | 6k | 9k |

On the farm loop's cut turns, the work after the cut used a median of 0.47 of its reserve (p95 0.71, p99 0.84).

## Which cut work costs games

The decomposition below is the evidence for where fuel converts into wins. It ran against oc-base25 at 1x on `dec16` (4,096 maps, both sides).

**Decomposition (8,192 games):**

| arm | win % (CI) | OOF arm / ref |
|---|---|---|
| v87 at 2x | 53.6 (52.6–54.7) | 707 / 74,022 |
| v87 at 2x, every gate seeing the 1x budget ("view") | 51.4 (50.3–52.5) | 247 / 77,877 |

Never running out is worth about +1.4. The gated work is worth about +2.2 more.

**Per-gate arms (4,096 games each, `dec8`).** Each arm is "view" with one consumer seeing raw fuel. "View" itself scored 51.0 on `dec8`.

| consumer seeing raw fuel | win % | CI |
|---|---|---|
| farm | 54.1 | 52.5–55.6 |
| guard | 52.0 | 50.5–53.6 |
| turn order | 52.1 | 50.5–53.6 |
| prey | 51.8 | 50.3–53.3 |
| queue | 50.9 | 49.4–52.4 |

The farm's cut evaluation is the work that converts fuel into wins. The arms don't add up: farm alone reaches the full 2x.

## Patches tried (frozen copies, against oc-base25 at 1x)

| patch | kind | games | win % (CI) | OOF arm / ref | verdict |
|---|---|---|---|---|---|
| **P1a** `p1a-search-floor.patch` (v87-fuel-p1a): the strike search grows and prices no further below `act_reserve` | cap, bench-identical at 100M (68/68), +2 fuel a turn | 4,096 (p1) | 49.5 (48.0–51.0) | 42,719 / 43,369 (−1.5%) | proves the search's bound; level |
| farm reserve ×0.75 `farm-reserve75.patch` | cap | 4,096 (p2) | 50.7 (49.1–52.2) | 44,243 / 39,963 (+11%) | level, more OOF: no |
| farm reserve ×0.5 | cap | 4,096 (p2) | 50.0 (48.4–51.5) | 47,431 / 38,180 (+24%) | no |
| step guard fails closed on lethal tiles when short `glethal.patch` | behaviour | 4,096 (p2) | 49.6 (48.0–51.1) | 52,405 / 40,922 (+28%) | no |
| raw SDK imports `sdkraw.patch` (v87-sdkraw) | exact | bench | | | −0.39% fuel; see below |

**The reserves are not the lever.** The farm keeps about twice the reserve it needs, yet spending that slack gains nothing and raises OOF. The +3 in the raw-farm arm comes from roughly double the fuel for the loop itself. The farm loop's evaluation (`farm.loop`, mean 6k, p99 41k) and the early big-map fields are where an exact speed-up would pay.

## Bounds, for checking future changes

**Gated.** Each of these subsystems checks fuel inside itself, and each check has a fallback. So its cost is at most the fuel above its floor, plus one step past the last check:
- farm loop: `loop_reserve` every pass.
- step guard: entry, per look and per simulation.
- prey: cut short.
- turn order: 10k.
- field growth: the doubling cap is priced by `static_field_cost_estimate`.
- queue: bound by the turn's spend against the real budget.
- strike search: after P1a, `act_reserve` per node and per query. Before P1a it was capped only by count (12 nodes, `max_exact_queries`), and it measured up to 82k with nothing checking fuel.

**Ungated.** These have no fuel check, so the census maxima are the only bounds:
- world update: 36k.
- continue_recall's `want_home`: 92k.
- `wh.stand_lost`: 73k.
- `comms send`: 9k.
- `act_end`: 52k.

A change that adds work to an ungated row should be compared with `budget.py` against `budget-v87.txt`. Its p99 and max are the cost of a turn that passes no check.

**How to check.** Instrument a census copy (`tools/fuel/census/`, `instrument.py --fine --trace --lenient`), play it with `bench.py --fuel 0` against oc-base25, then run `py tools/fuel/census/budget.py DIR [BASEDIR]`.

## SDK wrappers versus raw imports

**Yes, mostly already done.** `util.h` reads the engine through raw `cambc::detail::sdk_*` imports for the hot calls: board tests and sets, champion records, buffs, field reads, casts, cooldowns. The `ok()` helper throws only on a nonzero code.

A per-site wasm fuel profile (`tools/fuel/fuelprof`, 10 self-play games, 4.46G fuel) shows what is left:

| part | share of all fuel |
|---|---|
| instructions in SDK code (all of `cambc.h` + `imports.h`) | 1.84% (about 1k a turn) |
| `map::is_in_bounds` behind our `in_bounds` | 0.47% |
| the field wrapper's `ptr()` branch in `steps_at` | 0.23% |
| `check()`, `require_self`, design-type guards | about 0.5% |
| host-call prices | 3.0% (fixed whichever way they are called) |

`sdkraw.patch` (bots/variants/v87-sdkraw) makes four changes:
- `in_bounds` in two unsigned compares.
- Raw `ward_cooldown`.
- Raw self `is_alive`.
- Raw `recall`.

Bench at 100M: −0.39% total fuel and −0.4% mean turn on both sets. 52/52 wide replays and 15/16 default replays are identical.

**The differing game (01hooks, side b) changes play through the turn-end queue, not through the patch's logic.** The queue is bound by the fuel spent this turn, so a cheaper turn reaches further into it. The bisect, with each diagnostic applied to both base and patch:

| diagnostic | base and patch |
|---|---|
| none | diverge |
| queue on a fixed 20k at 100M | identical (2/2) |
| ring-table fill alone on a fixed 20k | identical (2/2) |
| reach tables only in the rings | still diverge |
| no altar flood in the queue | still diverge |
| no `prepare_approach` in the queue | identical (2/2) |

The rings cut short return before `prepare_next_turn`. So whether the queue prepared next turn's walk (`Pathing::prepare_approach`) decides play: that walk, searched at turn end, is not the one `act()` searches at turn start when it is missing (its layer cap comes from `approach_steps` at a different time). The queue's comment that it "never changes play" does not hold for this cache.

Consequence: **any fuel-only change can break bench identity on some maps** through the queue. A non-identical game then needs this diagnosis (queue on a fixed budget), not a rejection.

## Files

- `budget-v87.txt`, `budget-v87-slack.txt`: the tables (1x | 2x; slack).
- `*.patch`: candidate patches against `bots/variants/oc-base25/src`; their frozen copies are in `bots/variants/v87-*` (gitignored builds).
- Results: `replays/ab/fuelcap-{dec-f2x,dec-view,raw-*,p1a,frsv50,frsv75,glethal}/summary.md`.
- Scripts: `~/tmp-offload/fuelcap/` (cen3.sh census runs, oofctx.py live OOF by context, pairs.py).

## The farm loop (second round, 2026-11-09)

The question here was whether a genuinely cheaper farm evaluation could finish the loops that now get cut. All games are against oc-base25 at 1x.

**How much finishing the loop is worth.** `v87-raw-loop` is the 2x "view" bot with raw fuel in the loop only; after the loop it restores the fuel the view would have had at its cut. On `dec8` (4,096 games):

| arm | win % (CI) |
|---|---|
| view | 51.0 |
| raw fuel in the loop only | 52.5 (50.9–54.0) |
| raw fuel in all of `farm_turn` | 54.1 |

So finishing the loop is worth about +1.5. The other ~+1.6 comes from the work after the loop: route and field searches that read fuel.

**What a cut loop spends** (`v87-floop`: segment marks and function probes; 256 games, 528k farm loops):
- 5.7% of loops are cut. A cut loop has spent a median 19.5k by the cut, over 8 of 24 groups (about 2k a pass, against about 600 a pass in loops that finish).
- Where the cut loop's fuel goes:

| part | share |
|---|---|
| claimed groups' crew pricing (`plan_crew`, 3.6k a call: base price 0.95k, the expected allies 2.2k) | about 30% |
| `live_steps` (300 a call, 6 calls) | 8% |
| `min_camp_damage` misses (1.8 a loop) | |
| the loop header, `stop_from` and pre-bounds | 11% |
| the flattened inline arithmetic | the rest |

- `min_camp_damage`'s 4-slot cache misses on new belief versions, not on eviction: only 0.29 of 1.82 misses find the slots full. So a bigger or cross-turn cache would save little.

**The arithmetic is against a speedup.** Reaching the stop bound needs a median 20k more (p75 52k). An exact speedup of s finishes:

| speedup | cut loops finished |
|---|---|
| 10% | 8% |
| 20% | 16% |
| 30% | 23% |
| 50% | 40% |

About 13 fuel campaigns have already tuned this code, so a realistic 15–20% would buy perhaps 0.2–0.3 of the +1.5.

**What a full evaluation changes** (`v87-flcut`: loop on raw fuel, the best at the view's cut recorded; 24,650 cut loops):
- In 71% of cut loops the full evaluation keeps the same best.
- In 29% of cut loops there was no best at all by the cut: 14% are cut before their first pass.
- Where the full best differs and one existed, it lies a median 2–4 positions past the cut. More passes, not a different order, is what pays.

**Carrying the cut loop across turns fails.** `v87-fresume` goes on next turn from where the loop stopped, after a head of 4. It is bench-identical at 100M (16/16) because it changes only turns after a cut. dgate against oc-base25: H0 at +0.04 points (6,528 units, 26,624 games). Skipping the near groups costs what the far ones gain.
