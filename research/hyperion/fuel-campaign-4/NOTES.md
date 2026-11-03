# Fuel campaign 4 (2026-11-03): notes

Findings, dropped attempts with numbers and open leads, by area. Workers append a `## <area>` section on their
branch; the merge agent keeps them on fuel4-orch. Baseline and method: BRIEF.md.

## Campaign summary

Against the baseline fc4b (main fc99b847): fresh-11000..11019, 10,240 games each, own drafts, real budget, fast
runner. OOF counts per bot. The mirror row is fc4b against itself. Each later row is a direct A/B against fc4b, with
fc4b's own side after the slash.

| bot | win vs fc4b | OOF / fc4b side | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p90 / p99 | >= 100k | shortcuts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fc4b mirror | 50 | 97,011 | 10,705 | 10,093 | 14,126 | 23,262 | 38,825 | 62,977 / 29,172 / 4,862 | 50,621 / 86,450 / 92,950 | 0.29% | 4.09M |
| m1 | 49.6 | 66,239 / 95,128 (-30.4%) | 7,746 | 6,455 | 9,997 | 14,321 | 27,720 | | 50,589 / 86,350 / 92,950 | 0.23% | 3.86M / 4.11M |
| m2 | 50.3 | 66,082 / 95,949 (-31.1%) | 7,127 | 6,142 | 9,541 | 13,324 | 29,948 | 41,081 / 19,680 / 5,321 | 50,070 / 86,250 / 92,550 | 0.23% | 3.13M / 4.11M (-23.9%) |
| m3 | 50.3 (49.3-51.2) | 59,134 / 93,635 (-36.8%) | 4,028 | 6,561 | 9,461 | 12,925 | 26,159 | 38,476 / 18,284 / 2,374 | 49,911 / 86,150 / 92,450 | 0.22% | 3.16M / 4.18M (-24.3%) |
| **m4** | **50.0 (49.0-50.9)** | **57,482 / 93,462 (-38.5%)** | 4,026 | 6,561 | 9,161 | 12,568 | 25,166 | 38,048 / 17,384 / 2,050 | 49,904 / 86,150 / 92,350 | 0.22% | 3.07M / 4.18M (-26.5%) |

Top shortcut tags, m4 / fc4b in the m4 run: farm-partial-evaluation 2,050,173 / 2,309,636, step-guard-entry
427,524 / 476,212, turn-order 114,787 / 382,705, prey-cut-short 99,610 / 97,389, step-guard-look 74,596 / 62,226,
crow-flies-farm 62,437 / 73,036, comms-stale-vision 53,055 / 498,293, ward-no-bushes-clusters 51,275 / 68,878,
farm-no-route 48,533 / 77,726, static-descend 17,926 / 27,490.

OOF fell 38.5% against fc4b at a level win rate. The campaign target was <= 67.9k (-30%), and m1 already met it.
Fuel a play turn barely moved (mean -1.5%). The cut came from making expensive work cheaper or bounded, not from
doing less.

**Kept** (CHANGES):
- round 1: 298-301 (the farm reserve covers dash travel, the comms vision re-read, the step guard's estimate,
  ward_bushes);
- round 2: 302-303 (the farm loop's crew facts, the fight-sim walk lift);
- round 3a: 304 (make_way / label_through, fuel only), 305 (the opening loop's attack-tile reserve);
- round 3b: 306 (walk_down / camp_cast, fuel only), 307 (the quiet-turn turn-order reserve).

**Dropped:**
- the per-tile step guard (OOF +6-8%), and its follow-up on m3 with a stricter entry and one re-search (OOF
  +4.7-5.1% in all three versions; guard firings -36-49%; census: dearer farm walks and strike searches near
  enemies, not the guard's own fuel; untested: walling guarded dash tiles 2 away as the whole guard did);
- the attack-tile decode's bush bits read per chunk (exact, A/B level, <0.01% fuel: the decode's cost is fixed
  per call, mostly sight; code left on branch fc4-decode dd618ce3);
- 305's reserve on every turn (farm-partial-evaluation +16%), or for the first 10 rounds (+5.7%);
- the turn-order reserve at 5k (comms-stale-vision +33%);
- a 3-slot failed-route cache (level);
- the per-section drops listed in each worker section.

**Best open leads:**
- **farm-partial-evaluation** is 2.05M, two thirds of all shortcuts. It is the loop's reserve cutting candidate
  evaluation ("Farm loop", "Worst-case tail").
- **300+ rounds are 44% of OOF** (25.2k). The non-quiet turn-order firings (seen + near, ~40%: `offer_kills`,
  `threats_at`) and the step guard's whole-guard placements in strike search and dash_landings ("Per-tile step
  guard") are the fight-side tail.
- **The post-loop reserve on later turns** doesn't count `camp_cast` or a not-yet-decoded attack-tile set. Make
  those cheap (cache `camp_cast` per group per round, decode only the walk's tiles) rather than reserve more.
- **A failure memo for standoff searches**, keyed on goals, walls/occupancy, tile and cap (wild-1100006217: ~50k a
  turn of repeated failing searches after the loop).
- **Runs of 50+:** 2,050 against fc4b, and 3,074 on fresh-10000..10019 (vs m3's 3,175). The fortress
  respawn-blocking rule (behaviour) and world init over 187k on fuel-stress maps.
- **Minor:**
  - comms send skipping `observe` when no camp tile entered view;
  - `refresh()` reading far camp members;
  - camp_cast's per-slot `draw_alive_members` / `landing_threats`, shared between slots;
  - `enemy_cast` counting far unseen enemies.

## Baseline mirror A/B (orchestrator)

`astraeus-fc4b` (main fc99b847) against itself, real budget, own drafts, fast runner, `maps/fresh-11000..11019`
(10,240 games, 1m57s; batches `fuel4/replays/batch-*-ab-fc4-mirror-*`). Per bot:
- **OOF 97,011** (target <= 67.9k; campaign 3's final m4 read 37,908 on these suites: the bot got much heavier since,
  CHANGES 269-297), 94,760 without shared-gem maps. By round: 1 10,705, 2-10 10,093, 11-60 14,126, 61-300 23,262,
  300+ 38,825. Champion-game runs <10 / 10-49 / 50+: 62,977 / 29,172 / 4,862.
- Fuel a play turn (`fuelstats.py`): mean 50,621, p50 49,050, p90 86,450, p99 92,950, at/over 100k 0.29%.
- Shortcuts (`shortcuts.py`), 4.09M without out-of-fuel: farm-partial-evaluation 2,318,789, comms-stale-vision
  493,786, step-guard-entry 471,132, turn-order 384,788, prey-cut-short 93,272, farm-no-route 77,494, crow-flies-farm
  73,677, ward-no-bushes-clusters 69,005, step-guard-look 63,556, static-descend 28,604, farm-kept-target 6,379,
  step-guard-sim 3,783, siege-route-fuel 2,081, farm-no-attack-tiles 1,203, spell-clear-no-tiles 960,
  siege-no-tiles 241.

**Where the OOF grew since campaign 3** (mirror A/Bs of past commits, same suites; a guide to hot spots, not a
regression to undo: much of it is beneficial behaviour, more fighting, and an extra body): 1920ec92 (fc3 final)
38,828; 80721f68 (269-273) 41,317; 9abbbdea (274 dash travel) 54,022 (+12.7k); f9074463 (275-288) 55,913;
e9c37971 (289-292 chases, cohesion) 72,101 (+16.2k); 24491f3c (293) 71,976; 38aa25ce (294 pair-yield: Cassi & Issac
in every own draft, Cassi farms with the crew) 97,267 (+25.3k, every round bucket and every gate up ~25-35%);
c0746d3e (295) 98,339; 10b2313f (296) 98,366; fc99b847 97,011.

## Worst-case census

Branch `fc4-census`. Mirror (astraeus-fc4b vs itself, fresh-11000..11019): 97,011 OOF turns per bot. Census:
`tools/fuel/census` with `--fine --trace` on the 48 worst mirror maps (96 games) and 64 random maps (128 games).

**Where OOF comes from**
- By round: 1: 10.7k; 2-10: 10.1k; 11-60: 14.1k; 61-300: 23.3k; 300+: 38.8k. Run lengths <10 / 10-49 / 50+: 63.0k / 29.2k / 4.9k.
- By team size, OOF per 1k turns: 4 bodies 0.73, 5 bodies 1.54, 6 bodies 2.91. Six-body teams (Cassi & Issac) give
  2/3 of OOF. Mean fuel a turn rises ~10% per body.
- Round 1 is mostly dashers: Heart of Ruin ran out 44 of 82 times, Vendetta 37/76, Issac 42/128, Cassi 9/128.
- Random set, OOF-first turns (649):
  - By type: Heart of Ruin 30%, Issac 28%.
  - Innermost scope: p.plan 16% (31% of OOF-late turns).
  - Decide-level scope: farm 37%, act_end 21%, carry_bag 11%.
  - Self share: farm.loop 17.6%, strike_search 14.4%, make_field 3.7%, p.plan 3.5%.
- Post-loop work on OOF-first turns vs heavy turns:
  - farm.post: 26k vs 10.5k. The extra is travel (6.2k vs 1.3k), make_field (5.7k vs 0.75k) and route (4.5k vs 1.9k).
  - Per OOF-first turn: p.travel 8.8k (its plan 6.0k, ahead 1.6k).
  - carry_bag on OOF-first turns: 67k (the banking loop 32k; its post, with travel, 6.9k).
- Cause: the farm loop spends down to a reserve (walk_reserve + route search) that left out Pathing::travel.
  - A full plan is ~7.8k and the crossing trace (`ahead`) ~2.7k.
  - A full plan runs about once per dash cooldown, and 97% of full plans cast a dash.
  - Making the loop cheaper can't cut OOF, because the loop fills fuel down to the reserve whatever it costs.
- Worst map: gen-topo-gatehouse-1101507306, 3,382 OOF a game in the mirror. Champions 2-4 run out every round from
  650 to 1900 in the turn-end queue and so decide only on even rounds. It didn't reproduce under the census build.

**Shipped**
- 0971e929: instrument.py follows CHANGES 297.
  - Moved patterns: kill-bid leave, guard_work/carry_bag, chase, outmatched, step_goals.
  - New scopes for dash travel (travel, plan, ahead, route, crossings), turn-end acts and prices.
  - `scope_fn` now prints a skip instead of asserting.
  - Still skipped: beyond_spare, dash_towards, recall_line (two matches).
- 6d582724: `plan()` ORs each window's walls/avoid/guard and no-dash boards word by word before one row extraction.
  - Fuel only: about 450 a full plan.
  - 100M: identical replays on all 8 sets. Total fuel: wide -0.03%, oof -0.02%, mg -0.02%, q -0.11%, big -0.04%,
    fs -0.03%, fight -0.02%, tgt -0.02%.
- e95d13b0: the farm loop's reserve (and its `ample`) adds `travel_cost_estimate` = 12k when the dash is ready.
  - This fixes an existing gate's reserve; it adds no new gate. It is identical at 100M, where `ample` always holds:
    identical replays on all 8 sets, total fuel +0.00% to -0.08%.
  - Real-budget benches, OOF turns base → stack: wide 681→569, oof 1440→1293, mg 394→356, q 4392→2337,
    big 346→199, fs 2732→1985, fight 777→794, tgt 934→1201 (16 games). Total 11,696→8,734 (-25%).
  - A/B `fc4-census` (final stack, fresh-11000..11019): 49.3% of 10,240 (CI 48.4-50.3).
    - OOF: 66,944 vs 95,767 (-30.1%).
    - By round, CAND/REF: r1 7,742/10,707; 2-10 6,424/10,090; 11-60 10,088/14,126; 61-300 14,485/23,526;
      300+ 28,205/37,318.
    - Run lengths <10 / 10-49 / 50+: 44,226/20,793/1,925 vs 62,880/30,023/2,864.
    - Shortcuts 4.31M vs 4.22M:
      - farm-partial-evaluation 2.71M vs 2.32M: the loop stops earlier.
      - comms-stale-vision 377k vs 502k.
      - turn-order 261k vs 385k.
      - farm-no-route 67.7k vs 77.1k.
      - crow-flies-farm 82.4k vs 75.4k.
  - Confirmation on unused suites fresh-10100..10119: 50.0% of 10,240 (CI 49.0-50.9). OOF 64,929 vs 93,828 (-30.8%).
  - Both A/Bs together: 49.65% of 20,480.

**Dropped**
- Reading distance fields in place instead of via the host get (the chunked layout was verified on 90x90 and 59x59).
  - Replays identical, but total fuel went up 1.2-4.2% on every set: inlining bloats the code.
  - Field reads are only 24-44 a turn.
- Precomputing a window of field steps in `plan()`: the reads cost ~1.7k, a net loss.
- Widening `prices()`'s cache key: `best_emblem` reads upkeep, income and `bag_rounds_left`, which the key doesn't
  cover, so the change can't be exact.
- `start_recall`'s `recall()` never threw in 6,047 calls and is ~free. `travel_dash` is ~250 a call, 6.5 calls a turn
  (minor).

**Leads**
- Reserve only when travel will run, i.e. no visible enemy within travel_dash_clearance (vision + dash range). That
  would return fuel to the loop on fighting turns. Also, the 12k could be scaled to the plan's window.
- The same reserve gap probably exists in carry_bag's banking loop (its post also travels, 6.9k) and in the
  turn-end acts (act_end is 21% of OOF-first turns under `end_reserve` 10k).
- make_field inside the farm loop on OOF-first turns (5.7k against 0.75k on heavy turns; TODO 8).
- The gatehouse queue runaway (decides only on even rounds for 1,250 rounds).
- 6-body teams: per-body fixed costs (comms, turn order) scale with crew size.

## Fuel gates (worker; branch fc4-gates)

No gate removed: every plain removal still raises OOF well past noise. Three gates fire much less at the same OOF:
their reserves were set well above the measured cost of what they guard (commits 75939c61, b35752a6, 51bb9f12).
All three are identical at 100M (the checks always pass there): 274/274 replays and total fuel identical on wide,
oof, mg, q, big, fs, fight and tgt.

**Firings per bot, baseline mirror** (10,240 games, fresh-11000..11019; round buckets 1 / 2-10 / 11-60 / 61-300 /
300+): farm-partial-evaluation 2,318,754 (17k / 138k / 302k / 901k / 960k), comms-stale-vision 493,786, step-guard-entry
471,132, turn-order 384,788, prey-cut-short 93,272, farm-no-route 77,494 (mostly rounds 1-60), crow-flies-farm
73,677, ward-no-bushes-clusters 69,005 (95% in rounds 1-60), step-guard-look 63,556, static-descend 28,604,
farm-kept-target 6,379, step-guard-sim 3,783, siege-route-fuel 2,081, farm-no-attack-tiles 1,203, spell-clear-no-tiles
960, siege-no-tiles 241.

**Fuel left when each fires** (a copy printing `fuel()` in `note_shortcut`, ~1,700 games, q10 / q50 / q90):
farm-partial-evaluation 22.7k / 29.7k / 42.5k; step-guard-entry 22.8k / 40.6k / 57.3k; comms-stale-vision 3.7k /
7.7k / 9.4k; turn-order 2.4k / 7.1k / 9.5k; prey-cut-short 21.6k / 36.6k / 54.2k; farm-no-route 6.9k / 14.6k /
19.8k; ward-no-bushes-clusters 11.0k / 25.4k / 30.8k; static-descend 6.3k / 13.3k / 17.3k.

### Plain removals (A/B against fc4b, stopped at ~1,700-1,850 games: all far past noise)

OOF candidate / reference in the same games: comms-stale-vision +8.2% (15,226 / 14,073; rounds 2-10 +29%), turn-order
+46% (20,728 / 14,165; runs of 50+ 107 -> 1,452), ward-no-bushes-clusters (unbounded growth) +6.9% (15,240 / 14,259;
round 1 +34%, 2-10 +30%), static-descend +6.2% (15,288 / 14,391; runs of 50+ 50 -> 454), farm-no-route +8.6%
(16,939 / 15,595; round 1 +31%, but crow-flies-farm 12,661 -> 7,541). A baseline copy that only prints (noise
check) read 14,043 / 14,131.

### Kept: reserves matched to the measured cost (10,240-game A/Bs against fc4b unless named)

- **comms-stale-vision, 10k -> 5k** (75939c61). `World::observe` after moving costs 1.2k median, 2.1k p90, 3.4k
  p99, 4.3k p99.9, 5.2k p99.99, 7.2k max (506k refreshes); the old comment said observe + send <= 6.3k. Sweep:
  7.5k: firings 494,198 -> 223,639, OOF 97,481 / 97,461, win 50.1%; **5k: 493,297 -> 88,239 (-82%), OOF 97,495 /
  97,376, win 50.1%**; 3.5k: 42,129 (-91%) but OOF 98,351 / 97,250 (+1.1%, rounds 2-10 +3.6%). Every other tag
  unchanged but farm-partial-evaluation +0.3% (the queue gets less).
- **step-guard-entry: `costliest` decays on an entry cut too** (b35752a6; FUEL-AUDIT finding C: the estimate decayed
  only after a completed placing, so one dear placing kept the guard off while enemies stayed near). Entry 470,822 ->
  431,610, look 63,524 -> 78,073, sim 4,173 -> 5,367: guard tags 538,519 -> 515,050 (-4.4%); OOF 96,938 / 96,979;
  win 50.4%.
- **ward-no-bushes-clusters, growth floor 15k -> 5k** (51bb9f12). What follows a ward (turn order, comms) has its own
  checks. On top of the two above: 10k: 68,975 -> 57,912 (-16%), OOF 97,007 / 97,580; **5k: 68,922 -> 47,079 (-32%),
  OOF 96,244 / 97,543, turn-order level (387,110 / 387,620), win 50.6%**.
- All three (fc4g-c3): main suites as the 5k ward run above. **Unused suites fresh-11100..11109** (5,120 games): OOF
  44,584 / 45,105 (-1.2%), win 50.5%. The first two alone: OOF 96,627 / 96,932, win 50.4%.
- Benches (real budget, indicative), base -> c3: OOF wide 681 -> 714, oof 1,440 -> 1,393, mg 394 -> 364, q 4,392 ->
  4,488, big 346 -> 349, fs 2,732 -> 2,728, fight 777 -> 710, tgt 934 -> 1,253 (one diverged pair,
  mut-the-pack-1101701851 a/b 150/133 -> 329/229; without tgt 10,762 -> 10,746); comms-stale-vision 31,356 -> 6,739,
  step-guard-entry 28,595 -> 26,554, ward-no-bushes-clusters 2,383 -> 1,496, farm-partial-evaluation 148,627 ->
  151,934.

### Dropped (measured)

- **step-guard-entry without `fight_cost_estimate`** (entry needs act_reserve + costliest; the per-sim and per-look
  gates keep theirs). On cut turns the entry floor is fight estimate 22k median (the 2k + 2k-a-champion floor, up to
  52k) + 20k + costliest 7.7k median, while a placing costs 5.2k median, 12k p90, 19k p99, 46k max. Entry 471k ->
  93k but sim 3.7k -> 157k, look 63k -> 146k, and OOF 100,844 / 97,036 (+3.9%), win 50.0%: the placing work itself
  is what those turns cannot afford.
- **turn-order 10k -> 7.5k** (on c3): firings 385,523 -> 214,401 (-44%) but OOF 95,649 / 95,026 (+0.66%, ~2 points
  worse than c3's own ratio), comms-stale-vision back up 88k -> 105k, win 49.8%. Its cost with under 30k left: 0.8k
  median, 3.6k p90, 7.4k p99, 11.6k p99.9, 23k max.
- **farm-no-route and static-descend reserve 10k -> 5k** (on 75939c61): OOF 100,789 / 95,591 (+5.4%), though
  farm-no-route -65%, static-descend -56%.
- `fight_cost_estimate` is not inflated: sampled `trade` costs 2.9k median, 6.8k p90, 10.8k p99, 20.9k max, and
  cost / estimate is 0.22 median, 0.91 p99, 1.56 max. Guard and prey gates need cheaper sims (TODO Fuel 2).

### Where the big ones spend (profiles on real-budget A/B copies; leads)

- **farm-partial-evaluation is the loop's own cost, not an empty turn.** On cut turns the loop starts with 69k
  median (q10 49.6k), spends 37.6k median (q90 49.8k) and is cut after k = 13 of n = 28 groups (34% of cuts are
  banking calls; 1.6% cut at k = 0). By stage, a cut turn's loop (34.9k): plan_crew in the crewable branch 17.4k
  (2.6 calls at 6.7k), the claimed branch 9.0k (1.8 at 5.0k: crew_work + plan_crew), clearing estimates 4.2k (2.0 at
  2.1k), steps / pre-clear prune 2.8k (3.1 at 0.9k), head skips 1.0k (2.3 at 0.44k), from_here fields 0.5k. Inside:
  plan_crew 10.9-11.6k a cut turn (4.7 calls), of which share_damage 4.9k (5.8 calls, ~850 each: its ally loop
  3.5k, sort 0.4k, fill 0.9k) and min_camp_damage 2.2k (6.8 calls, 5 cache hits, 0.4 re-sorts). After the cut, the
  rest of decide spends 12.1k median (q90 20.8k, p99 30.9k) and decide ends with 16.9k median left (q10 8.5k): the
  15k + walk reserve matches that tail, so loosening it buys ~3 groups, not a full loop. To fire much less, the loop
  must be about half as dear: share_damage's ally loop per call (most plan_crew calls price once, so reuse within a
  call saves little), plan_crew's repeated claimer/availability loops, and an exact bound before plan_crew in the
  claimed branch.
- **turn-order**: costly calls (>3k, mean 4.3k) are offer_kills 1.2k, plain_priority 1.0k, may_escape 0.8k, setup
  0.5k; over 9k (812 of ~36k): offer_kills 4.6k, offer_escape 2.0k, may_escape 1.9k. Bound offer_kills
  (side_damage and real_distance per enemy) and the escape pair before lowering the reserve.
- **ward-no-bushes-clusters**: unbounded growth costs 14k median on round 1 and up to 61-92k on rounds 1-2 on
  blob / band / cluster-carpets maps (the whole map's run labelling plus a big cluster's index, ~8 a tile); later
  calls ~0.8k (the window's board ops). A cheaper index (SIMD stores for long runs) and labelling in the queue's
  first turns would let the floor go.

Open minor items: comms send could skip `observe` when we moved but no camp tile entered view (needs a proof that
nothing else reads the refreshed champions before the next update); `share_damage` reads `my_record()` per call
(~40 a cut turn).

## Merge round 1 (merge agent)

fc4-census (0971e929, 6d582724, e95d13b0, 5f914734) and fc4-gates (75939c61, b35752a6, 51bb9f12, e389a53f) merged
into fuel4-orch whole, then main (tools/tune). Nothing dropped. Frozen: `fuel4/bots/variants/astraeus-fc4-m1`.

**Review.**
- 0971e929: tools only (census patterns).
- 6d582724 (fuel only): `window::bits` is shifts, masks and ORs of the four chunk words, so it distributes over OR:
  bits(A) | bits(B) == bits(A | B) word by word. The new per-board loop ORs the same four words under the same bounds
  tests as the old `word` lambda (c, c+1 in [0, down), a, a+1 in [0, across)); `i00` is formed in size_t, so a
  negative c or a only wraps and is read only when its bound test passes, where the sum is the old index. Null
  boards are skipped, as the old `if (avoid)` / `if (guard)` / `veto ?` were; the `across <= 0` path ORs the same
  tiles. `camps_into(no_dash)` still runs before the no-dash extraction. Exact.
- e95d13b0 (behaviour change at the real budget only): `travel` reads the dash slot, `my_can_cast` and its cooldown,
  none of them fuel, and enters only `loop_reserve` and `ample`, whose three uses are the loop's existing fuel tests
  (the `left >= ample || left >= loop_floor + loop_reserve()` stop and the two `fuel_ok(... + loop_floor +
  loop_reserve())` field checks). At 100M those always pass, so play is unchanged (confirmed below). No new gate: it
  makes an existing reserve cover work that runs after the loop (Pathing::travel's plan and crossing trace).
- 75939c61: `refresh` keeps its one `fuel_ok`, floor 10k -> 5k (`refresh_floor`); observe after a move measured 5.2k
  p99.99, 7.2k max, and `late_floor` still guards what follows. At 100M always true.
- b35752a6: `costliest -= costliest / 8` on the entry cut path only, which is never taken at 100M. The estimate is
  only read by that gate, so lowering it can only let the guard run more often; the decay matches the existing one.
- 51bb9f12: `ward_bushes`' existing floor 15k -> 5k (`end_reserve / 2`); never binds at 100M.
- The interaction the orchestrator flagged (298 leaves more fuel after the loop; 299 and 301 lower later reserves):
  m1's OOF ratio to the reference (0.696) equals the census branch's alone (0.699), and comms-stale-vision falls
  further than with the gates alone (-89% against -82%), so the gates spend part of the fuel 298 frees without
  running out. Step 5 (dropping a gates commit) was not needed.

**100M** (base -> m1, `MAIN/replays/fuel/fc4/m1-*-100M.json`; all replays identical):

| set | identical | total | mean | p90 | p99 | max | over 100k | round 1 mean / max |
|---|---|---|---|---|---|---|---|---|
| wide | 52/52 | +0.00% | 52980 -> 52982 | 86731 -> 86735 | 111528 -> 111485 | 261428 -> 261428 | 5183 -> 5165 | 221798 -> 221669 / 413799 -> 413528 |
| oof | 48/48 | +0.01% | 54525 -> 54528 | 87735 -> 87738 | 156636 -> 156614 | 676847 -> 676896 | 14312 -> 14314 | 241834 -> 241830 / 500770 -> 500548 |
| mg | 24/24 | +0.01% | 56677 -> 56682 | 87429 -> 87431 | 134404 -> 134379 | 393583 -> 393190 | 4020 -> 4024 | 231835 -> 231737 / 354060 -> 353669 |
| q | 48/48 | -0.08% | 63023 -> 62974 | 99390 -> 99366 | 152926 -> 152938 | 474400 -> 474451 | 28427 -> 28382 | 268151 -> 268039 / 540763 -> 540814 |
| big | 32/32 | -0.00% | 61870 -> 61869 | 87985 -> 87988 | 128866 -> 128783 | 355241 -> 354848 | 5985 -> 5968 | 252676 -> 252635 / 412102 -> 411711 |
| fs | 24/24 | -0.01% | 94869 -> 94860 | 132962 -> 132949 | 198786 -> 198794 | 618918 -> 618936 | 22384 -> 22371 | 548166 -> 547970 / 662730 -> 662379 |
| fight | 30/30 | +0.01% | 48679 -> 48683 | 86086 -> 86085 | 118657 -> 118659 | 381306 -> 381306 | 5372 -> 5374 | 195813 -> 195891 / 277080 -> 276689 |
| tgt | 16/16 | +0.01% | 54264 -> 54269 | 87243 -> 87242 | 123290 -> 123308 | 329884 -> 329884 | 3033 -> 3035 | 230569 -> 230445 / 371463 -> 371483 |

The plan cut shows on q (-0.08%); elsewhere 298's three dash reads a farm turn and codegen in the flattened
`farm_turn` about cancel it (+~5 fuel a turn; most turns are dearer by a few fuel).

**Real budget benches** (base -> m1; small, indicative: a diverged game swings hundreds):

| set | OOF | farm-partial-evaluation | comms-stale-vision | step-guard-entry | turn-order | ward-no-bushes-clusters |
|---|---|---|---|---|---|---|
| wide | 681 -> 538 | 11828 -> 13561 | 2677 -> 296 | 2918 -> 2467 | 1877 -> 1202 | 181 -> 148 |
| oof | 1440 -> 1496 | 17040 -> 19271 | 5432 -> 916 | 9350 -> 8199 | 3925 -> 3799 | 278 -> 233 |
| mg | 394 -> 529 | 6302 -> 7805 | 1926 -> 237 | 2256 -> 1328 | 1456 -> 1348 | 223 -> 154 |
| q | 4392 -> 2279 | 52245 -> 58209 | 6409 -> 1093 | 2340 -> 2519 | 9505 -> 7045 | 268 -> 252 |
| big | 346 -> 207 | 17689 -> 21323 | 2018 -> 260 | 377 -> 408 | 1616 -> 1196 | 228 -> 194 |
| fs | 2732 -> 1999 | 39299 -> 41451 | 9226 -> 1658 | 372 -> 307 | 8633 -> 6702 | 1119 -> 565 |
| fight | 777 -> 746 | 882 -> 1400 | 2129 -> 389 | 10159 -> 8577 | 1249 -> 1226 | 83 -> 46 |
| tgt | 934 -> 1126 | 3342 -> 4238 | 1539 -> 409 | 823 -> 974 | 1304 -> 1523 | 97 -> 92 |
| all | 11,696 -> 8,920 (-23.7%) | | | | | |

(census alone: 8,734; gates alone: 12,015.)

**A/B** (fresh-11000..11019, own drafts, real budget, fast runner, 10,240 games; `fuel4/replays/batch-*-ab-fc4-m1-*`,
`MAIN/replays/fuel/fc4/ab-fc4-m1.log`):

| bot | OOF | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p50 / p90 / p99 | >= 100k |
|---|---|---|---|---|---|---|---|---|---|
| mirror fc4b (per bot) | 97,011 | 10,705 | 10,093 | 14,126 | 23,262 | 38,825 | 62,977 / 29,172 / 4,862 | 50,621 / 49,050 / 86,450 / 92,950 | 0.29% |
| **m1** | **66,239** | 7,746 | 6,455 | 9,997 | 14,321 | 27,720 | 43,960 / 20,456 / 1,823 | 50,589 / 49,050 / 86,350 / 92,950 | 0.23% |
| fc4b (ref) | 95,128 | 10,707 | 10,089 | 14,073 | 23,139 | 37,120 | 62,907 / 29,421 / 2,800 | 50,649 / 49,050 / 86,450 / 92,950 | 0.29% |

Win 49.6% (48.7-50.6). OOF -30.4% against the reference, -31.7% against the mirror; every round bucket -25 to -38%,
runs of 50+ -35%. Shortcuts per bot, m1 / fc4b: farm-partial-evaluation 2,703,675 / 2,321,472; step-guard-entry
428,583 / 476,124; turn-order 261,417 / 383,022; prey-cut-short 100,342 / 98,893; crow-flies-farm 78,516 / 73,653;
step-guard-look 75,665 / 61,960; farm-no-route 67,774 / 77,555; comms-stale-vision 55,850 / 500,462;
ward-no-bushes-clusters 48,791 / 69,176; static-descend 21,637 / 28,966; farm-kept-target 6,098 / 5,800;
step-guard-sim 5,622 / 4,716; siege-route-fuel 2,216 / 2,106; spell-clear-no-tiles 991 / 997; farm-no-attack-tiles
953 / 1,221; siege-no-tiles 256 / 252. Total without out-of-fuel 3.86M / 4.11M (-6.0%).

**For round 2.** OOF 66k: 300+ (27.7k) and 61-300 (14.3k) are 63%. farm-partial-evaluation is now 70% of the
remaining shortcuts and rose 16%: the census leads (the banking loop's and turn-end acts' reserves, which likely
miss travel the same way; make_field in the loop) and the gates worker's loop profile (plan_crew / share_damage at
~11k a cut turn) are the next targets. Round 1 is still 7.7k.

## Farm loop (worker; branch fc4-farm, round 2)

Baseline `astraeus-fc4-m1`. Target: farm-partial-evaluation (fpe), the `room()` cut of `farm_turn`'s group loop.
Result: **fpe -24.6%** in the 10k A/B (2.69M -> 2.03M a bot), OOF -6.8%, two exact commits; the -33% aim was not
reached (what remains is below).

**Profile** (debug copies with raw `fuel()` laps per loop stage, one A/B suite of 512 games against m1; scripts
`/tmp/fc4/farm/prof*.py`, `an*.py`). Cut non-banking turns: the loop starts with 69k, spends ~27k and is cut after
13 of 38 groups. Before: crewable groups 2.4 a cut turn reached plan_crew (whole iteration ~5.2k, plan_crew ~2.6k
a call), and **1.64 of those plan_crew calls a cut turn had no claimer and no available ally** (the free list
empty): plan_crew then prices us alone, output == strength, and its plan is never taken. Of plan_crew calls
reaching the crew value on cut turns, 547k of 768k were such no-crew calls. share_damage was ~900 a call (its pool
build ~460, self arrival ~220, fill ~180, sort ~60), its crew bound's ally loop ~700 a group. After both commits
(true laps, cut non-banking turn, ~24.5k): pre-facts head ~6k (14 passes: loop head 104, the later-turn prune
~300 a group of which `rated_below` + `soonest` ~220), facts ~3.7k (8.3 groups; steps_known 266), steps/trip
~2.4k, claimed ~3.9k (crew_work 1.5k and plan_crew 2.6k a pass), clearing ~2.5k (4.4 groups), crewable ~5k
(bound ~700 x 2.8, plan_crew ~3.3k x 0.9). Banking cut turns (34% of cuts) weigh ~20 groups to facts.
Usefulness (a group past the trip prune changes best, shared or from_altar_value), per cut non-banking turn,
useless/useful: claimed 0.92/0.43, alone 0.59/0.92, crewable without a plan 1.41/0.23, crewable with a plan
0.52/0.27. Loop budget on cut turns: q10 1.4k, q25 11k, q50 25k, q75 36k; k/n under 0.1 on 22% of cuts (no loop
saving can help those: the reserve takes the turn), over 0.66 on 25%.

**Commits** (byte-identical at 100M on all 8 sets after each):
- b962aaa0: the crewable branch's bound loop counts plan_crew's members (claimers seen lately, and with `expect`
  the allies crew_available admits: the same tests plan_crew's claimer loop and free list apply); with none,
  plan_crew's crew is us alone (output == strength) and the `plan.output > strength` test never takes it, so it is
  not called. plan_crew's only side effects are memos (crew_arrival's kept steps, min_camp_damage's slots), which
  return the same values later.
- b0766f85: `CrewAllies`, per farm call (a static table, reset on first crew need; nothing in the loop moves us,
  changes beliefs or claims): each ally's claim and "seen" (plan_crew's claimer test) once, and on first need its
  camp_output, crew_available's g-independent part (never / unless it claims g / by the distances to g's centre:
  the harmless claim's centre and the cleared group it stands on) and share_damage's pool entry (score, weight,
  taken, budget, usable at the call's recall line), plus one `my_record` read. The bound loops, plan_crew and
  share_damage read it in ally order, so every float sum and the pool's order (std::sort sees the same comparisons
  on the same input order) are the old ones. The table is static because vec2 zero-initialises (+111 fuel a call
  as a local); a fuller eager build (pos, self, in_view, sighted per ally) cost ~720 a call and was slimmed.

100M against m1 (`/tmp/fc4/farm/b/f2d-*-100M.json`):

| set | identical | total | mean | p90 | p99 | max | over 100k | round 1 mean / max |
|---|---|---|---|---|---|---|---|---|
| wide | 52/52 | -1.85% | 52982 -> 52000 | 86735 -> 86443 | 111485 -> 107416 | 261428 -> 261428 | 5165 -> 4064 | 221669 -> 218547 / 413528 -> 396508 |
| oof | 48/48 | -1.09% | 54528 -> 53931 | 87738 -> 87542 | 156614 -> 143169 | 676896 -> 555660 | 14314 -> 12714 | 241830 -> 240044 / 500548 -> 466258 |
| mg | 24/24 | -0.99% | 56682 -> 56122 | 87431 -> 87301 | 134379 -> 126103 | 393190 -> 373215 | 4024 -> 3580 | 231737 -> 230574 / 353669 -> 345977 |
| q | 48/48 | -3.90% | 62974 -> 60515 | 99366 -> 90192 | 152938 -> 138317 | 474451 -> 471625 | 28382 -> 18666 | 268039 -> 262295 / 540814 -> 510220 |
| big | 32/32 | -1.91% | 61869 -> 60690 | 87988 -> 87515 | 128783 -> 119661 | 354848 -> 327988 | 5968 -> 4164 | 252635 -> 248454 / 411711 -> 400739 |
| fs | 24/24 | +0.03% | 94860 -> 94887 | 132949 -> 132819 | 198794 -> 197024 | 618936 -> 611791 | 22371 -> 22522 | 547970 -> 548327 / 662379 -> 663002 |
| fight | 30/30 | -0.03% | 48683 -> 48669 | 86085 -> 86074 | 118659 -> 118605 | 381306 -> 381306 | 5374 -> 5350 | 195891 -> 195790 / 276689 -> 277074 |
| tgt | 16/16 | -0.64% | 54269 -> 53920 | 87242 -> 87132 | 123308 -> 120817 | 329884 -> 329884 | 3035 -> 2719 | 230445 -> 229728 / 371483 -> 366246 |

By commit (total): b962aaa0 wide -1.55%, oof -0.68%, mg -0.62%, q -2.68%, big -1.48%, fs -0.10%, fight -0.20%,
tgt -0.64%; b0766f85 on top wide -0.31%, oof -0.41%, mg -0.37%, q -1.25%, big -0.43%, fs +0.13%, fight +0.17%,
tgt +0.00% (p99 down on every set but fight +0.1%). Dearer turns: mostly turn-end-queue turns at ~85k (the queue
fills to the emulated budget, so cheaper work before it adds a warm-up unit) and fs/fight farm calls that price one
crew only (the table's build is not repaid).

Real budget benches (m1 -> f2d; small, indicative): OOF wide 538 -> 677, oof 1496 -> 1291, mg 529 -> 416, q 2279 ->
2764, big 207 -> 176, fs 1999 -> 2025, fight 746 -> 751, tgt 1126 -> 899 (all 8920 -> 8999, +0.9%, noise); fpe
13561 -> 9564, 19271 -> 17051, 7805 -> 6877, 58209 -> 50118, 21323 -> 18449, 41451 -> 42390, 1400 -> 1433, 4238
-> 3951 (all 167,258 -> 149,833, -10.4%).

**A/B** `fc4-farm` (variants/fc4f-2d = b0766f85 against variants/astraeus-fc4-m1, fresh-11000..11019, 10,240
games, real budget, own drafts, fast runner): **win 50.5% (49.5-51.4)**. OOF 64,368 / 69,041 (-6.8%); by round
1 7,130 / 7,753, 2-10 6,154 / 6,474, 11-60 9,607 / 10,147, 61-300 13,422 / 14,551, 300+ 28,055 / 30,116; runs
<10 / 10-49 / 50+ 41,173 / 20,484 / 2,711 vs 44,288 / 21,063 / 3,690. Fuel a play turn mean 50,023 / 50,535, p50
48,550 / 49,050, p90 86,150 / 86,350, p99 92,550 / 92,950, at/over 100k 0.23% / 0.24%. Shortcuts per bot:
**farm-partial-evaluation 2,030,942 / 2,692,538 (-24.6%)**, step-guard-entry 428,203 / 434,230, turn-order
211,060 / 262,781 (-19.7%), prey-cut-short 91,497 / 93,556, step-guard-look 77,007 / 75,701, crow-flies-farm
72,992 / 71,744, farm-no-route 52,128 / 67,331 (-22.6%), comms-stale-vision 48,031 / 56,179, ward-no-bushes-clusters
45,151 / 48,765, static-descend 19,774 / 24,394, step-guard-sim 6,381 / 7,454; total without out-of-fuel 3.09M /
3.85M (-19.6%). (b962aaa0 alone was not A/B'd; b0766f85's fuller eager build read fpe 2.10M / 2.70M, OOF 65,260 /
67,281, 50.2%; a lazy variant reading every ally belief per group, 2.18M / 2.69M, 66,124 / 69,167, 50.4%.)

**Dropped (measured):**
- The crewable bound over plan_crew's discrete outputs (claimers, then a prefix of the available allies nearest
  first, to the cap) instead of crew_rate's continuous [lo, hi]. Exact (0 useful plans pruned in 303k checked), and
  it prunes 44% of the plans that end up useless (25% of plan calls), but building the sorted list and up to 5
  rates for every crewable group cost more than the ~0.9 plan a cut turn it saves: q +0.84%, wide +0.39%, every set
  dearer (out of line, q +1.13%).
- The rated bound (`beaten`, the opening's) at the trip prune on later turns after the plain ratio fails: exact (no
  best/shared/from_altar change in ~2M checks; only `risky` moved, which is read only with no best), prunes 0.75
  (non-banking) / 1.92 (banking) groups a cut turn, but costs ~200 a group passing the plain test on every turn:
  100M q -0.05%, wide +0.16%; A/B fpe 2.13M / 2.69M (no better than without it), OOF 64,192 / 68,724, 50.0%.
- Scanning the remaining groups at the cut for pre_upper / stop skips (exact: best only rises): at the cut 81-87%
  of turns still have 4+ groups no cheap bound skips, ~2% none. Not built.

**What remains needs a redesign.** The loop's cost is now spread: every group past the pre-facts prune pays ~1k
before its clearing (head ~400 including the later-turn prune's ~220 of rated_below and soonest, facts ~450, steps
and trip ~350), and per cut turn ~3.5 fully evaluated groups change nothing (1.4 crewable groups with no plan
~2.6k each, 0.5 with a plan ~6k each). Exact bounds tight enough to prune those cost about what they save when
checked group by group (both drops above). The redesign that could halve the loop: (1) per group, keep across
turns the position-independent parts of its value (worth with weights, the alone clear's rounds, damage and trips
by belief version and our health, its kited/spell rounds; these are already in group_facts) and an exact claimer
and available-ally histogram per call, so one vectorised pass (pre_prune_upper's f32x4 tables) gives every group a
bound within a few % of its value; (2) evaluate in bound order and stop when the next bound is below the best. That
needs the loop's results made order-independent first: ties (`value > best_value` keeps the first; shared, risky,
help_group take the first at equal steps) compared on (value, position in today's order), and help_group, risky
and from_altar_value computed for the groups they read regardless of the stop.

Open minor items: crew_work's camp_output per claimer could read the table (~100 a claimer); may_expect (~135 a
crewable or claimed group) loops enemies per group, a per-call list of enemies in sight would do; the later-turn
pre-facts prune's rated_below/soonest (~220 a pass, ~1.4k a cut turn).

## Rules and assumptions (worker; branch fc4-rules)

Base m1 (338b4458). The engine contradicted nothing in cambc-rules.yaml. No exact cut was worth shipping. One lift
shipped.

**Shipped: walk_allies_in delays an ally a one-turn walk away (2f3fd2a8, behaviour lift).** Before this change, an
ally one step from striking range joined the fight at once, "to keep most sims on the plain fast path". turn.walk
moves a step a turn, so that ally actually joins a turn late.
- Main A/B vs m1 (10,240 games, fresh-11000..11019): 50.2% (CI 49.2-51.2). OOF 67,429 vs m1 66,711 (+1.1%), all of it
  in rounds 300+ (29,009 vs 27,921). Rounds 61-300 were lower (14,282 vs 14,611).
- Confirmation on suites no A/B had used (fresh-10120..10139, 10,240 games): 49.9% (CI 49.0-50.9). OOF 65,056 vs
  66,108 (-1.6%).
- Pooled: 50.07% of 20,480, OOF 132,485 vs 132,819.
- Fuel per turn vs m1 (main A/B): mean 50,566 vs 50,541, p90 and p99 equal, turns at or over 100k 0.24% vs 0.23%.
- Shortcuts (main A/B): 3.93M vs 3.91M (+0.4%). Most of the rise is step-guard-entry and crow-flies-farm.
- 100M benches. Replays diverge, as expected for a behaviour change: identical replays wide 25/52, oof 18/48,
  mg 13/24, q 33/48, big 25/32, fs 20/24, fight 3/30, tgt 3/16.

  | Set | Mean | p99 |
  |---|---|---|
  | wide | -0.1% | +0.0% |
  | oof | +3.1% | +0.7% |
  | mg | +6.5% | +12.7% |
  | q | +0.3% | — |
  | big | +0.1% | — |
  | fs | +0.0% | — |
  | fight | +0.2% | -1.4% |
  | tgt | -5.3% | -1.7% |

  These benches are small, and the A/B is the judge.
- Real-budget bench OOF vs m1 (indicative, divergent games):

  | Set | m1 | walk |
  |---|---|---|
  | wide | 538 | 595 |
  | oof | 1,496 | 1,725 |
  | mg | 529 | 735 |
  | q | 2,279 | 2,390 |
  | big | 207 | 204 |
  | fs | 1,999 | 1,998 |
  | fight | 746 | 728 |
  | tgt | 1,126 | 1,295 |

  The 10k A/Bs do not show this rise.

**Dropped: Heart of Ruin's passive at every hit (TODO Fuel 2, first item).** The rule: "All its damage x (1 + 0.5 x
missing health fraction)". The lift rescaled a Ruin fighter's damage in take/hurt, with incremental quiet_damage, and
added a play_ruin quiet stretch. The hard part is the early exits: their_cap, their_rest, overwhelmed and our_bounds
assume damage per hit is fixed. Valid bounds have to assume up to 1.5x, and then they rarely certify an exit.

Six variants, each a 10,240-game A/B vs m1:

| Variant | Bounds | Win | OOF (cand / m1) | OOF change |
|---|---|---|---|---|
| ruin | loose 1.5x, quiet bail | 50.6% | 70,780 / 66,173 | +7% |
| ruinb | old bounds at current strength (not valid) | 50.1% | 68,498 / 65,847 | +4.0% |
| ruinc | loose, incremental quiet | 50.7% | 69,706 / 65,849 | +5.9% |
| ruind | old bounds, incremental | 49.8% | 67,993 / 66,280 | +2.6% |
| ruine | always tight, via most_dealt | 50.2% | 73,029 / 66,258 | +10% |
| ruinf | staged: current, then top, then tight | 50.7% | 72,191 / 66,998 | +7.8% |

Paired sim cost on HoR trades (fight set, same inputs, old model vs new):

| Variant | Old | New | Change |
|---|---|---|---|
| ruind | 5.8k | 6.1k | +5.5% |
| ruinc | 5.8k | 7.0k | +20% |
| ruinf | 5.8k | 7.2k | +23% |
| ruine | 5.8k | 7.9k | +35% |

A faithful model with valid bounds costs at least 20% more on HoR sims and 6-8% more OOF, for no measurable win.
Lifting it needs a bound that stays tight under rising damage, for example a closed form for the quiet stretch.
Diffs are in /tmp/fc4/rules/ (safety-ruinc.cc, safety-ruinf.cc, ruin-v2.diff).

**Dropped: tracking prune skipped by Chebyshev extent.** Each tracked enemy kept a bounding box. When the box missed
our vision (personal and champion radius 8, ward radius 6), prune was skipped.
- Exact: all 8 sets identical at 100M.
- Dearer on every set: wide +0.45%, oof +0.47%, mg +0.37%, q +0.33%, big +0.30%, fs +0.14%, fight +0.61%, tgt +0.42%.
- On oof it saves 227 a turn in rounds 2-10, but keeping the box costs 118-270 a turn later.
- Lap profile, oof set, rounds 2-10, per turn: enemy_unseen 9.4k, of which grow 4.0k, prune 0.8k, turns_between
  1.2k, lineage copy 0.5k, liveness 0.7k. In later rounds it is 1.6-1.8k.
- Prune was never the cost. grow and lineage copies are where the cost is.

**Dropped: Reach::build tile-set reuse near camps, keyed on the live camp-member mask ("Monsters never move").**
Exact (fight 30/30, mg 24/24, oof 48/48, tgt 16/16), but dearer by 0.00% to +0.02%.

**Checked, not waste:** thrown and caught cambc::error in my_damage (Cassi's stun slot) and in HoR landing's
my_damage_to. These counted zero catches on the fight set (own drafts) and the wide set (test drafts).

**Open minor items (estimates per call or turn):**
- refresh() reads far camp members (~200-600 a refresh; needs a view check).
- enemy_cast counts far tracked unseen enemies for area casters (1-3k on some calls).
- real_distance re-casts ward vision (~300 a call).
- A non-dasher lineage copies a dasher's undashed set (~0.5-1.5k a turn in rounds 2-10).
- A known-dead champion's reads could be skipped until its respawn at D+60 (~50-150).
- publish_turn_order re-reads our own priority (~20-40).
- Model lifts still open, all needing a cheap bound first:
  - walk_allies_in ignores walls (needs a capped field per enemy).
  - Camp hits go to our weakest once we fall.
  - Ground AoE, Varg splash, HoR landing and Ren reflection are single-target.
  - Landings do not price unseen enemies.

## Merge round 2 (merge agent)

fc4-farm (b962aaa0, b0766f85, bfefee3a) and fc4-rules (2f3fd2a8, d5cfcc60) merged into fuel4-orch whole (merges
f7154a93 and 168d3bd6; NOTES conflict resolved by keeping both sections). main had not moved. Nothing dropped; the
walk lift is kept (A/Bs below). Frozen: `fuel4/bots/variants/astraeus-fc4-m2f` (m1 + the farm commits) and
`astraeus-fc4-m2` (+ the walk lift = fuel4-orch's bot). CHANGES 302 (farm, fuel only) and 303 (walk lift).

**Review.**
- b962aaa0 (fuel only): the crewable bound loop's `members` counts exactly plan_crew's possible members: claimers
  (not self, alive, claim == g, seen within crew_seen_rounds: plan_crew's claimer test) and, with the same
  `expect`, allies crew_available admits (it returns false for self, the dead and claim == g, which the loop's
  branches also exclude). With none, plan_crew's output stays `my_output` = strength (its free list is empty, so
  no `more` is priced) and `plan.output > strength` fails; `plan` is read nowhere else. The check sits inside the
  `worth > 0 && g != mono_group` block, so other groups call plan_crew as before. plan_crew's skipped side effects
  are memo fills (crew_arrival, min_camp_damage), which return the same values when filled later. Exact.
- b0766f85 (fuel only):
  - What the table caches is constant over a farm call. The ally beliefs (pos, visible, alive, health, pos_round,
    facts), `comms::claim_of` (`posts.claims`, read at turn start; self is never read through the table's claim),
    camp state (`on_cleared`), `farms_gold`, `world.round` (== farm_turn's `round`), our record (here, health, max)
    and `line` (a const local of farm_turn) are only written by observe/refresh, comms reads and actions, and
    the loop has none (its existing comment: nothing in the loop moves us). Every reader (the claimed branch's
    others, the crewable bound, the two plan_crew calls) is inside the group loop; the post-loop code still reads
    `claim_of` directly.
  - Lazy entries (`crew_output`, `read_avail`, `read_pool`) compute from the same inputs as the old inline code:
    `read_avail` keeps crew_available's test order (avail 0 = never, 1 = true unless claim == g, 2 = by distance),
    the claim == g test still comes before every `true`, and `harmless_claim` (claim >= 0 && harmless) is the old
    `claim < n && strength <= 0` branch, reached only with claim >= 0. `allies.here` is `my_record`'s position, the
    old `my_position()`/`my_record()` reads.
  - Order: every reader walks `allies.at[0..n)`, which is `world.allies` in order (n = allies.size(), at most 6
    bodies against a capacity of 16), so float sums are unchanged; share_damage's pool holds pointers in the old
    insertion order and std::sort sees the same comparisons, so its permutation and the water-filling are the old
    ones. plan_crew's `allies.at[free[i].second]` relies on `world.allies[k].index == k` (world.cc sets
    `b.index = i`), as the old `world.allies[free[i].second]` did.
  - Staleness and reentrancy: `crew_read` is a local, so each farm_turn call refills the table before its first
    read and resets every `has_*` flag; nothing reads entries past n. Each template instance (<true>, <false>,
    <false, true>) has its own static. The only nested call, farm_turn<false> -> farm_banking ->
    farm_turn<false, true>, is a different instance and returns before the outer call fills its table; `farm()`
    calls are sequential, never recursive. Cassi and Issac are separate WASM instances (memory.instances).
    Exact; confirmed below.
- 2f3fd2a8 (behaviour): `strike(a, ...).reach` is the ally's one-turn reach with its walk (and dash) included
  (safety.h: "a dash, or a walk on the first of two turns"), so `walk` = distance beyond it is the number of whole
  walking turns before its striking turn; by turn.walk (one step a turn) walk 1 strikes on its second turn,
  `arrives_at = 1`, as walk >= 2 already did. Strictly more faithful. No loop is added and `arrives_at` only takes
  values the sims already handled (1 to the existing walk); sims with a late ally leave the plain fast path more
  often, so fuel per sim can rise (bounded by the existing sim limits; the A/Bs show no OOF cost).

**100M** (m1 -> m2f, `MAIN/replays/fuel/fc4/m2f-*-100M.json`; all replays identical, the same numbers as the farm
worker's f2d):

| set | identical | total | mean | p90 | p99 | max | over 100k | round 1 mean / max |
|---|---|---|---|---|---|---|---|---|
| wide | 52/52 | -1.85% | 52982 -> 52000 | 86735 -> 86443 | 111485 -> 107416 | 261428 -> 261428 | 5165 -> 4064 | 221669 -> 218547 / 413528 -> 396508 |
| oof | 48/48 | -1.09% | 54528 -> 53931 | 87738 -> 87542 | 156614 -> 143169 | 676896 -> 555660 | 14314 -> 12714 | 241830 -> 240044 / 500548 -> 466258 |
| mg | 24/24 | -0.99% | 56682 -> 56122 | 87431 -> 87301 | 134379 -> 126103 | 393190 -> 373215 | 4024 -> 3580 | 231737 -> 230574 / 353669 -> 345977 |
| q | 48/48 | -3.90% | 62974 -> 60515 | 99366 -> 90192 | 152938 -> 138317 | 474451 -> 471625 | 28382 -> 18666 | 268039 -> 262295 / 540814 -> 510220 |
| big | 32/32 | -1.91% | 61869 -> 60690 | 87988 -> 87515 | 128783 -> 119661 | 354848 -> 327988 | 5968 -> 4164 | 252635 -> 248454 / 411711 -> 400739 |
| fs | 24/24 | +0.03% | 94860 -> 94887 | 132949 -> 132819 | 198794 -> 197024 | 618936 -> 611791 | 22371 -> 22522 | 547970 -> 548327 / 662379 -> 663002 |
| fight | 30/30 | -0.03% | 48683 -> 48669 | 86085 -> 86074 | 118659 -> 118605 | 381306 -> 381306 | 5374 -> 5350 | 195891 -> 195790 / 276689 -> 277074 |
| tgt | 16/16 | -0.64% | 54269 -> 53920 | 87242 -> 87132 | 123308 -> 120817 | 329884 -> 329884 | 3035 -> 2719 | 230445 -> 229728 / 371483 -> 366246 |

m2 (`m2-*-100M.json`) against m2f: replays diverge where the lift fires, with the same identical counts as the
rules worker's: wide 25/52, oof 18/48, mg 13/24, q 33/48, big 25/32, fs 20/24, fight 3/30, tgt 3/16; identical
games' total fuel +0.00% everywhere (the lift costs nothing where it doesn't fire). All games, m2f -> m2: mean wide
-0.0%, oof +3.2%, mg +6.7%, q +0.3%, big +0.1%, fs +0.0%, fight +0.3%, tgt -5.3%; p99 oof 143169 -> 150876, mg
126103 -> 149475 (+18.5%), fight -1.4%, tgt -2.3%; over 100k oof 12714 -> 16957, mg 3580 -> 7781, others level or
lower; round 1 unchanged.

**Real budget benches** (m1 / m2f / m2; small, indicative):

| set | OOF | farm-partial-evaluation | step-guard-entry | turn-order | prey-cut-short | comms-stale-vision |
|---|---|---|---|---|---|---|
| wide | 538 / 677 / 714 | 13,561 / 9,564 / 9,900 | 2,467 / 2,791 / 3,031 | 1,202 / 1,074 / 1,140 | 634 / 725 / 720 | 296 / 300 / 321 |
| oof | 1,496 / 1,291 / 1,594 | 19,271 / 17,051 / 18,657 | 8,199 / 8,741 / 10,920 | 3,799 / 3,836 / 7,033 | 2,102 / 2,398 / 6,978 | 916 / 762 / 826 |
| mg | 529 / 416 / 622 | 7,805 / 6,877 / 8,421 | 1,328 / 1,789 / 3,767 | 1,348 / 1,772 / 5,015 | 238 / 720 / 5,200 | 237 / 184 / 225 |
| q | 2,279 / 2,764 / 2,869 | 58,209 / 50,118 / 50,049 | 2,519 / 2,768 / 2,446 | 7,045 / 8,573 / 8,582 | 496 / 632 / 622 | 1,093 / 981 / 954 |
| big | 207 / 176 / 182 | 21,323 / 18,449 / 18,572 | 408 / 294 / 392 | 1,196 / 988 / 1,020 | 61 / 46 / 66 | 260 / 219 / 223 |
| fs | 1,999 / 2,025 / 2,026 | 41,451 / 42,390 / 42,390 | 307 / 291 / 293 | 6,702 / 6,620 / 6,619 | 83 / 79 / 79 | 1,658 / 1,595 / 1,596 |
| fight | 746 / 751 / 776 | 1,400 / 1,433 / 1,588 | 8,577 / 8,361 / 8,925 | 1,226 / 1,152 / 1,157 | 1,968 / 1,907 / 2,109 | 389 / 351 / 367 |
| tgt | 1,126 / 899 / 1,245 | 4,238 / 3,951 / 4,460 | 974 / 697 / 984 | 1,523 / 1,259 / 1,475 | 495 / 279 / 432 | 409 / 303 / 380 |
| all | 8,920 / 8,999 / 10,028 | 167,258 / 149,833 / 154,037 | 24,779 / 25,732 / 30,758 | 24,041 / 25,274 / 32,041 | 6,077 / 6,786 / 16,206 | 5,258 / 4,695 / 4,892 |

m2's bench rise is mostly one game: mut-the-pack-600201800 seat a (in both the oof and mg sets) goes OOF 52 -> 120,
prey-cut-short 467 -> 4,529, turn-order 436 -> 3,002 under the lift. The 10k A/Bs don't show it.

**A/Bs** (fresh-11000..11019, own drafts, real budget, fast runner, 10,240 games each; batches
`fuel4/replays/batch-*-ab-fc4-{m2,m2f,m2-vs-m2f,m2-vs-fc4b,m2f-vs-fc4b}-*`, logs `MAIN/replays/fuel/fc4/ab-*.log`).
OOF per bot; fuel = a play turn's (`fuelstats.py`).

| run: bot | win | OOF | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p50 / p90 / p99 | >= 100k |
|---|---|---|---|---|---|---|---|---|---|---|
| fc4-m2f: m2f | 50.5 (49.5-51.4) | 64,368 | 7,130 | 6,154 | 9,607 | 13,422 | 28,055 | 41,173 / 20,484 / 2,711 | 50,023 / 48,550 / 86,150 / 92,550 | 0.23% |
| fc4-m2f: m1 | | 69,041 | 7,753 | 6,474 | 10,147 | 14,551 | 30,116 | 44,288 / 21,063 / 3,690 | 50,535 / 49,050 / 86,350 / 92,950 | 0.24% |
| fc4-m2: m2 | 50.1 (49.1-51.1) | 65,003 | 7,129 | 6,161 | 9,461 | 13,234 | 29,018 | 41,115 / 19,704 / 4,184 | 50,031 / 48,550 / 86,250 / 92,550 | 0.23% |
| fc4-m2: m1 | | 68,685 | 7,754 | 6,482 | 9,978 | 14,681 | 29,790 | 44,354 / 20,087 / 4,244 | 50,553 / 48,950 / 86,350 / 92,950 | 0.24% |
| m2-vs-m2f: m2 | 49.7 (48.7-50.7) | 64,195 | 7,130 | 6,154 | 9,442 | 12,917 | 28,552 | 41,149 / 19,233 / 3,813 | | |
| m2-vs-m2f: m2f | | 64,396 | 7,132 | 6,149 | 9,456 | 13,020 | 28,639 | 41,538 / 19,024 / 3,833 | | |
| m2-vs-fc4b: m2 | 50.3 (49.3-51.3) | 66,082 | 7,127 | 6,142 | 9,541 | 13,324 | 29,948 | 41,081 / 19,680 / 5,321 | 50,070 / 48,550 / 86,250 / 92,550 | 0.23% |
| m2-vs-fc4b: fc4b | | 95,949 | 10,707 | 10,073 | 13,990 | 23,540 | 37,639 | 63,029 / 29,026 / 3,894 | 50,655 / 49,050 / 86,450 / 92,950 | 0.29% |
| m2f-vs-fc4b: m2f | 50.7 (49.8-51.7) | 66,392 | 7,128 | 6,146 | 9,709 | 13,571 | 29,838 | 41,100 / 19,808 / 5,484 | 50,063 / 48,550 / 86,250 / 92,550 | 0.23% |
| m2f-vs-fc4b: fc4b | | 97,007 | 10,708 | 10,073 | 14,248 | 23,396 | 38,582 | 63,118 / 28,559 / 5,330 | 50,640 / 49,050 / 86,450 / 92,950 | 0.29% |

fc4-m2f reproduces the farm worker's fc4-farm A/B exactly (same bots, deterministic games).

Shortcuts per bot (without out-of-fuel):
- fc4-m2f, m2f / m1: 3.09M / 3.85M (-19.5%). farm-partial-evaluation 2,030,942 / 2,692,538; step-guard-entry
  428,203 / 434,230; turn-order 211,060 / 262,781; prey-cut-short 91,497 / 93,556; step-guard-look 77,007 / 75,701;
  crow-flies-farm 72,992 / 71,744; farm-no-route 52,128 / 67,331; comms-stale-vision 48,031 / 56,179;
  ward-no-bushes-clusters 45,151 / 48,765; static-descend 19,774 / 24,394; farm-kept-target 6,397 / 6,113;
  step-guard-sim 6,381 / 7,454; siege-route-fuel 2,038 / 2,111; farm-no-attack-tiles 1,014 / 1,023;
  spell-clear-no-tiles 603 / 948; siege-no-tiles 263 / 263.
- fc4-m2, m2 / m1: 3.13M / 3.84M (-18.6%). farm-partial-evaluation 2,043,572 / 2,691,438; step-guard-entry
  428,686 / 429,193; turn-order 216,836 / 262,446; prey-cut-short 98,065 / 99,367; step-guard-look 80,203 / 73,370;
  crow-flies-farm 73,489 / 71,588; farm-no-route 52,525 / 67,149; comms-stale-vision 47,521 / 56,000;
  ward-no-bushes-clusters 45,139 / 48,762; static-descend 23,342 / 24,783; step-guard-sim 7,138 / 6,345;
  farm-kept-target 6,448 / 5,978; siege-route-fuel 2,093 / 2,227; farm-no-attack-tiles 1,014 / 1,023;
  spell-clear-no-tiles 630 / 948; siege-no-tiles 236 / 264.

**The walk lift: kept.** m2 is level on win rate (50.1% against m1, 49.7% head to head against m2f) and on OOF:
against m1 65,003 vs m2f's 64,368 (+635, inside the ~800 noise; -5.4% vs -6.8% to their own m1 sides), head to
head 64,195 / 64,396, against fc4b 66,082 vs m2f's 66,392. The rules worker's two A/Bs against m1 pooled 50.07%, OOF
level. The lift's cost shows in single games (the bench's mut-the-pack, m2's 300+ bucket and runs of 50+ in the m1
A/B) and in the 100M benches' oof/mg p99 and over-100k; it lands in the prey and turn-order gates, not in OOF.

**Cumulative against the baseline fc4b** (direct A/B m2 vs fc4b above; the mirror and m1's from earlier sections):

| bot | win vs fc4b | OOF / fc4b side | r1 | 2-10 | 11-60 | 61-300 | 300+ | fuel mean / p90 / p99 | >= 100k | shortcuts |
|---|---|---|---|---|---|---|---|---|---|---|
| fc4b mirror | 50 | 97,011 | 10,705 | 10,093 | 14,126 | 23,262 | 38,825 | 50,621 / 86,450 / 92,950 | 0.29% | 4.09M |
| m1 | 49.6 | 66,239 / 95,128 (-30.4%) | 7,746 | 6,455 | 9,997 | 14,321 | 27,720 | 50,589 / 86,350 / 92,950 | 0.23% | 3.86M / 4.11M |
| **m2** | **50.3** | **66,082 / 95,949 (-31.1%)** | 7,127 | 6,142 | 9,541 | 13,324 | 29,948 | 50,070 / 86,250 / 92,550 | 0.23% | 3.13M / 4.11M (-23.9%) |

m2's shortcuts against fc4b's in the same games: farm-partial-evaluation 2,047,946 / 2,322,708 (-11.8%),
comms-stale-vision 47,697 / 499,184 (-90.4%), step-guard-entry 434,786 / 476,099, turn-order 214,453 / 384,955
(-44.3%), prey-cut-short 100,009 / 103,562, crow-flies-farm 74,811 / 78,700, step-guard-look 75,809 / 62,404,
farm-no-route 52,206 / 77,178 (-32.4%), ward-no-bushes-clusters 45,126 / 68,917 (-34.5%), static-descend 22,038 /
26,497, step-guard-sim 6,496 / 4,079, farm-kept-target 6,436 / 5,964.

Against fc4b the round-2 gain barely shows in total OOF (m1 66,239 -> m2 66,082): every bucket up to round 300 is
lower (r1 -8%, 2-10 -5%, 11-60 -5%, 61-300 -7%) and runs under 50 fall 64,416 -> 60,761 (-5.7%), but runs of 50+
rise 1,823 -> 5,321 from two new turn-end-queue runaways, the same in m2f's run (so from the farm cut's real-budget
divergence, not the lift): gen-fortress-1101902231 (seat 12, champion 5, 940 OOF turns from round 59, all in the
queue on alternate rounds) and gen-dash-lattice-1100707609 (seat 12, champions 2, 4 and 5, ~640 each from rounds
240-690). Like the census's gatehouse lead, a queue that runs out every other round for 1,000+ rounds; fixing
these two is worth ~3.5k OOF in this A/B.

**For round 3.** The queue runaways above (`OOF <round> queue` on alternate rounds; reproduce with bench.py on the
two maps, m2 vs fc4b, seat 12). farm-partial-evaluation is still 2.05M (65% of shortcuts): the farm worker's
redesign (bound-ordered evaluation) is the remaining lead. 300+ (~29k) is 45% of OOF.

## Worst-case tail (worker; branch fc4-tail, round 3)

Baseline m2 (`variants/astraeus-fc4-m2`). A/Bs: real budget, own drafts, fast runner, 10,240 games on
`maps/fresh-11000..11019` against m2; confirmation on `maps/fresh-11240..11259` (new, `mapgen suite --seed 11240+i`).
Runaway set: the five maps in the round-2 notes and the census (fortress-1101902231, dash-lattice-1100707609,
topo-gatehouse-1101507306, wild-1100006217, topo-split-1100506510), m2 vs fc4b, both seats.

**The "queue" runaways were decide overruns.** `OOF <r> <phase>` names the last phase that *started*. A late turn
(one that follows an out-of-fuel turn) finishes its decide in the next round and then runs the turn-end queue, so
a decide that keeps overrunning shows up as `queue` on alternate rounds. The queue's room() floor was never the cause.
- **fortress, seat 12, champion 5 (m2 941 OOF, lost):** the champion stands on (16,18), a camp tile of wolf group
  2, which is respawning and due (capture.respawn: the occupied tile holds the group back). Every attack tile of the
  group is held by an ally, so the farm walk's `goals` is empty. After the loop it still spends ~2.3k on an
  unreachable route, ~20.7k on `make_way` (label_through walks the crowd of allies, ~5k each), the within-adjacent
  route, then walk_on's descend plan (~4.3k, run twice). Every decide overruns.
- **dash-lattice, seat 12, champions 2/4/5 (m2 1,915 + 384):** bank branch. `label_through` runs after a walk-parted
  search (`route_label_cap_ == -1`), which labelled nothing, so it walks the allies at ~5k each and finds nothing.
- **Fix (7500d8d4, exact):** `make_way` returns at once on empty goals; `label_through` returns unreachable when
  the search was walk-parted. These are exact: both paths could not find a label.
  - At 100M the replays are identical on all 8 sets and the runaway set. Total fuel: wide -0.15%, oof -0.26%, mg
    -0.18%, q -0.16%, big -0.28%, fs -0.06%, fight -0.43%, tgt -0.10%. Runaway set: -4.30%, p99 201,870 -> 127,737.
  - Runaway set at real budget (OOF a/b side, m2 -> A): fortress 941/4 -> 0/4, dash-lattice 1,915/384 -> 8/6,
    gatehouse 45/46 -> 83/34, wild 32/6 -> 11/229, topo-split 39/2 -> 37/30. The gatehouse runaway (census, against
    a different opponent) does not reproduce here. wild side b is a new stall from divergence (below).
  - A/B fc4t-a (tail-a vs m2): 50.2% (49.3-51.2).

    | measure | tail-a | m2 |
    |---|---|---|
    | OOF | 62,263 | 64,097 |
    | r1 / 2-10 / 11-60 / 61-300 / 300+ | 7,132 / 6,183 / 9,451 / 12,837 / 26,660 | 7,131 / 6,158 / 9,433 / 13,132 / 28,243 |
    | runs <10 / 10-49 / 50+ | 41,038 / 19,847 / 1,378 | 41,339 / 19,970 / 2,788 |
    | shortcuts | 3.180M | 3.199M |
    | fuel mean / p50 / p90 / p99 | 49,930 / 48,350 / 86,150 / 92,450 | 50,055 / 48,550 / 86,250 / 92,550 |
    | turns at/over 100k | 0.22% | 0.23% |

    Shortcuts: farm-partial-evaluation 2,044,492 / 2,046,949, static-descend 18,490 / 21,165, turn-order
    202,777 / 212,501.
- **Still open (behaviour, not fuel):** in fortress the team keeps the respawn blocked for ~1,900 rounds and m2
  loses the game with or without the fix. It needs a rule: a champion steps off a due respawning group's camp tile
  when none of the group's attack tiles is free.

**Round 1: the opening reserve missed the attack-tile decode.** World init costs ~80k. The opening farm loop then
stops at ~36.8k left, its reserve. After the loop, `farm_attack_tiles` decodes the chosen group's tiles for ~16.5k
(index block ~7.9k, sight ~0.3k a member, decode ~1.9k a member). Then come the route (~3.5k) and travel (~12.6k),
and the turn runs out. On the fuel-stress maps world init alone is over 187k.
- **Fix (86b5b53d, behaviour):** on the opening turn only, the farm loop's reserve adds the decode the walk will
  pay: `attack_tiles_cost` is 0 when the group is cleared, already kept or not drafted, otherwise (indexed ? 0 :
  9,000) + 2,500 per live member whose tiles aren't ready. Its `ample` test adds the map's largest-group bound.
  - At 100M the replays are identical on all 8 sets. Total fuel: wide -0.14%, oof -0.25%, mg -0.15%, q -0.16%, big
    -0.28%, fs -0.05%, fight -0.42%, tgt -0.06% (A included).
  - Real-budget bench OOF (m2 / A / A+C): wide 714/636/1,444, oof 1,594/1,457/1,412, mg 622/490/434, q
    2,869/3,017/3,484, big 182/195/177, fs 2,026/2,012/1,993, fight 776/770/780, tgt 1,245/1,257/899. The wide and q
    rises are single diverged games: 01boss-battle side a has 693 OOF (below), and mega-groups and topo-necks diverge.
  - A/B fc4t-c5 (A+C vs m2): 49.5% (48.5-50.5); confirmation fc4t-c5-conf: 50.4% (49.4-51.3).

    | measure | A+C | m2 | A+C (conf) | m2 (conf) |
    |---|---|---|---|---|
    | OOF | 59,553 (-7.9%) | 64,634 | 60,013 (-6.6%) | 64,248 |
    | round 1 | 4,038 | 7,139 | 3,586 | 6,439 |
    | rounds 2-10 | 6,568 | 6,182 | 5,971 | 5,636 |
    | rounds 11-60 | 9,531 | 9,558 | 9,203 | 9,201 |
    | rounds 61-300 | 13,218 | 13,388 | 13,580 | 13,711 |
    | rounds 300+ | 26,198 | 28,367 | 27,673 | 29,261 |
    | runs <10 / 10-49 / 50+ | 38,150 / 19,430 / 1,973 | 41,358 / 19,584 / 3,692 | 36,563 / 21,996 / 1,454 | 39,365 / 22,359 / 2,524 |
    | fuel mean / p50 / p90 / p99 | 49,941 / 48,350 / 86,150 / 92,450 | 50,083 / 48,650 / 86,250 / 92,550 | 49,849 / 48,250 / 86,150 / 92,550 | 50,020 / 48,550 / 86,150 / 92,550 |
    | at/over 100k | 0.23% | 0.23% | 0.23% | 0.23% |

    Shortcuts: 3.167M vs 3.196M. farm-partial-evaluation is 2,051,632 vs 2,042,295; it is +7.4k in round 1 and
    +7.1k in rounds 2-10, where the opening loop now evaluates less. turn-order is 196,941 vs 213,523, round 1 3,692 vs
    10,410.
  - About +390 of the round-1 saving moves to rounds 2-10: the decode is put off a turn rather than avoided.
- **Dropped:**
  - **The same reserve on every turn** (c, with B): A/B 49.8%, OOF 61,612 vs 64,484, round 1 4,045, rounds 2-10
    6,232, but farm-partial-evaluation 2.357M vs 2.034M (+16%). After the opening the turn-end queue has already
    decoded the near groups, so the reserve only shortens the loop.
  - **The reserve for the first 10 rounds** (c4): 49.8%, OOF 59,477 vs 63,864, round 1 4,013, rounds 2-10 6,182
    (level), but farm-partial-evaluation 2.154M vs 2.038M (+5.7%).
  - **The opening reserve without the ample bound** (c3): 49.2% (48.3-50.2), OOF 59,475 vs 64,003, round 1 4,009,
    rounds 2-10 6,547. It is equivalent to the kept form, but round 1 at 100M costs +0.2-1.2% against the kept
    form's +0.1-0.5%.
  - **B, a spare failed-route cache** (3 slots, so standoffs reuse more failed searches): identical at 100M, but
    total fuel +0.03-0.09% on every set except q (-0.28%), and round 1 +~350. A/B fc4t-b 49.9%, OOF 61,890 vs 63,985:
    level with A within noise.

**Census of tail-c (128 worst games, `instrument.py --fine --trace`).**
- Where the first OOF turn of a streak runs out, by decide branch: farm 44%, act_end 14%, carry_bag 12%,
  strike_search 10%.
- Last check passed: farm.cc's `search` check (~line 1810) in 12.5% of OOF turns, with a mean of 25k left. After it
  come the `camp_cast` path (~7k) and `farm_attack_tiles`, which the reserve doesn't count. The farm walk check
  accounts for 8.8%.
- `camp_cast` profile (24 maps), through the members loop: p50 1.4k, p90 4.4k, p99 8.2k.

**Leads (not done).**
- **The post-loop reserve on later turns.** It doesn't count `camp_cast` or an attack-tile decode for a group the
  queue hasn't reached. Reserving these on every turn cost farm evaluation (c above), so make them cheap instead:
  cache `camp_cast` per group per round, and decode only the tiles the walk needs.
- **Repeated failing searches in standoffs** (wild-1100006217 side b, 229 OOF under A, and fc4b's 753 in m2's A/B):
  - Banking with farm group 9, a two-wolf group in a 1-wide corridor. Its only near attack tile is held by an ally.
  - Each turn: route 7.5k, the adjacent search, plan 3k twice, and the wide retry at cap here+6*max_detour (97,
    16.4k). That is ~50k after the loop, against a ~25k reserve.
  - A per-(goal set, cap) failure memo that lasts while allies hold the tiles would make these turns exact.
  - Spare cache slots alone (B) didn't help.
- **01boss-battle side a, champion 0, from round 483 (693 OOF under A+C, from divergence):** bank branch. Traced at
  round 600: update 89k left -> d_home 61k (want_home ~27k) -> b_farmed 57k -> a_decided 3.3k. So `bank_gems`/act
  after carry_bag spends ~54k, with a step-guard-look shortcut. The turn runs out around pre_ward/place_lock and
  finishes in round 601. This is the fight-gates worker's area (step guard), so it isn't traced further.
- **walk_on runs the descend plan twice** (~4.3k each) when the first one fails.
- **The respawn-blocking rule** (fortress, above).
- **World init over 187k on fuel-stress maps,** so the first turn has almost nothing for the opening loop.

## Merge round 3a (merge agent)

fc4-tail (7500d8d4, 986638dc, 86b5b53d, 8b94b82f) merged into fuel4-orch whole (merge 2c81e907), then main's
600a866b (tools/tune league.py; merge 0258a602, no conflicts). Nothing dropped. Frozen:
`fuel4/bots/variants/astraeus-fc4-m3` (= fuel4-orch's bot). CHANGES 304 (A, fuel only) and 305 (C, behaviour).

**Review.**
- 7500d8d4, `label_through` (exact): with `route_label_cap_ == -1` (set only by a walk-parted `route_around`),
  `route_label(p)` returns unreachable for every tile, since `steps_at` is never negative. Both the neighbour scan
  and the crowd walk only lower `best` on a label other than unreachable, so the old function always returned
  unreachable; the new one returns it at once. The only side effect skipped is the crowd walk's `guard()` read,
  which is a lazy memo: a later reader (`try_move` before any guarded move, `route`) computes it from the same
  captured inputs.
- 7500d8d4, `make_way` with empty `goals` (exact on every path that labels): no ally is on a goal. A fresh search
  with no roots labels nothing, and a walk-parted one sets the cap to -1 (above). A failed search reused because
  `within_failed` holds (empty goals are within any failed set) was checked, under the same cap, labels and
  `avoid`, to have no adjacent ally off the goals with a `label_through` other than unreachable. That is
  `labelled_ally_beside`'s test with no goals, and make_way's own loop only skips more allies (guard). So the old
  code returned false with `opened` false, and `route_exhausted_ &= !opened` left the flag alone. The new code
  returns false and leaves it alone too. The pocket path (`me == pocket_at_ && enclosed`) returns before setting
  the cap, but `enclosed` requires no adjacent ally, so the old loop found none.
  - One path differs in principle: `round_fails` returns before searching, after the cap is set. `route_field_`
    then holds whatever `keep_round` swapped in, which is a different failed search's labels. With empty goals,
    the old code could read those stale labels and step aside. Hitting it needs three walking-round searches: one
    failing on other goals, then two with no goals. The old read was of labels that belonged to no search of
    these goals, so skipping it is a fix, not a regression. The 100M benches (all identical) never hit it.
- 86b5b53d (behaviour at the real budget only):
  - `tiles_reserve()` is `if constexpr (opening)`, and `decode_bound` is 0 unless `opening`. So only the first
    turn's existing reserve (`loop_reserve`, read by the `room` check and the two existing `fuel_ok` gates in the
    loop) and the existing `ample` threshold grow. There is no new `fuel()` read. Both raise what the opening
    loop keeps back for a cost the walk then really pays (~16.5k decode), rather than choosing worse elsewhere.
  - At 100M, `left >= ample + decode_bound` always holds, so `loop_reserve` is never read from `room`. The
    `fuel_ok` gates pass. `attack_tiles_cost`'s only state change is `attack_slot`'s lazy creation of empty
    entries, which is fuel only.
  - Refactor: `attack_tiles_kept` is the old inline key test, with `alive` filled only while `keeps`. The kept
    union moved from a function-local static (one per `farm_turn<opening, banking>` instance) to one global. A
    hit now also serves another instance, for the same group, range and live members, and so the same union
    (member tiles are static once prepared). It can differ only where the other instance's `prepare` would have
    returned null under its floor (real budget). There, the cache now hands it the tiles: better, not worse.
  - `attack_tiles_cost_bound`'s static is per instance and per game (the map is fixed).
- 986638dc: tools only.

**100M** (m2 -> m3, `MAIN/replays/fuel/fc4/m3-*-100M.json`, `bench.py compare`). All replays identical. The
round-1 rise is C's reserve arithmetic plus `attack_tiles_cost`.

| set | identical | total | mean | p90 | p99 | max | round 1 mean |
|---|---|---|---|---|---|---|---|
| wide | 52/52 | -0.14% | 51993 -> 51922 | 86456 -> 86452 | 107655 -> 107530 | 276779 -> 276779 | 218547 -> 218812 (+0.1%) |
| oof | 48/48 | -0.25% | 55636 -> 55497 | 88330 -> 88274 | 150876 -> 151024 | 555660 -> 555660 | 240044 -> 240510 (+0.2%) |
| mg | 24/24 | -0.15% | 59862 -> 59769 | 89753 -> 89649 | 149475 -> 149301 | 373215 -> 373046 | 230574 -> 230995 (+0.2%) |
| q | 48/48 | -0.16% | 60683 -> 60586 | 90573 -> 90522 | 139031 -> 139065 | 438412 -> 438574 | 262295 -> 262773 (+0.2%) |
| big | 32/32 | -0.28% | 60730 -> 60561 | 87516 -> 87504 | 120066 -> 119952 | 327988 -> 327345 | 248454 -> 248910 (+0.2%) |
| fs | 24/24 | -0.05% | 94901 -> 94852 | 132727 -> 132686 | 196759 -> 196636 | 611791 -> 611791 | 548327 -> 551107 (+0.5%) |
| fight | 30/30 | -0.42% | 48794 -> 48589 | 86049 -> 85997 | 117003 -> 116906 | 380956 -> 380956 | 195790 -> 195990 (+0.1%) |
| tgt | 16/16 | -0.06% | 51042 -> 51010 | 86741 -> 86747 | 118052 -> 118209 | 263572 -> 263572 | 229728 -> 230068 (+0.1%) |

**A/B m3 vs fc4b** (fresh-11000..11019, own drafts, real budget, fast runner, 10,240 games; batches
`fuel4/replays/batch-20261103-092334-ab-fc4-m3-vs-fc4b-*`, log `MAIN/replays/fuel/fc4/ab-fc4-m3-vs-fc4b.log`):
50.3% (49.3-51.2), OOF 59,134 / 93,635 (-36.8%). The m2-relative A/Bs are the worker's ("Worst-case tail").

**Cumulative against the baseline fc4b** (direct A/Bs; the mirror, m1 and m2 rows from earlier sections):

| bot | win vs fc4b | OOF / fc4b side | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p90 / p99 | >= 100k | shortcuts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fc4b mirror | 50 | 97,011 | 10,705 | 10,093 | 14,126 | 23,262 | 38,825 | | 50,621 / 86,450 / 92,950 | 0.29% | 4.09M |
| m1 | 49.6 | 66,239 / 95,128 (-30.4%) | 7,746 | 6,455 | 9,997 | 14,321 | 27,720 | | 50,589 / 86,350 / 92,950 | 0.23% | 3.86M / 4.11M |
| m2 | 50.3 | 66,082 / 95,949 (-31.1%) | 7,127 | 6,142 | 9,541 | 13,324 | 29,948 | 41,081 / 19,680 / 5,321 | 50,070 / 86,250 / 92,550 | 0.23% | 3.13M / 4.11M (-23.9%) |
| **m3** | **50.3 (49.3-51.2)** | **59,134 / 93,635 (-36.8%)** | 4,028 | 6,561 | 9,461 | 12,925 | 26,159 | 38,476 / 18,284 / 2,374 | 49,911 / 86,150 / 92,450 | 0.22% | 3.16M / 4.18M (-24.3%) |

fc4b's side in this run: r1 10,706, 2-10 10,146, 11-60 13,912, 61-300 23,423, 300+ 35,448; runs 62,808 / 28,007 /
2,820; fuel 50,666 / 86,450 / 92,950, 0.29%.

- m3's OOF is -10.5% of m2's against the same baseline (66,082 -> 59,134).
  - Round 1 fell 7,127 -> 4,028, from C.
  - Runs of 50+ fell 5,321 -> 2,374, from A: the fortress and dash-lattice runaways are gone.
  - 300+ fell 29,948 -> 26,159.
  - Rounds 2-10 rose 6,142 -> 6,561, the decode C puts off a turn (worker: ~+390).
- Shortcuts (m3 / fc4b): farm-partial-evaluation 2,056,658 / 2,314,384, step-guard-entry 429,355 / 474,592,
  turn-order 197,048 / 381,362, prey-cut-short 98,606 / 94,619, step-guard-look 74,745 / 61,775, crow-flies-farm
  66,287 / 74,281, ward-no-bushes-clusters 51,387 / 68,891, farm-no-route 50,528 / 77,421, comms-stale-vision
  44,390 / 498,943, static-descend 18,024 / 25,751.

**Still open** (from the worker's leads): farm-partial-evaluation (2.06M, 65% of shortcuts); the post-loop reserve
on later turns (camp_cast, decode for groups the queue hasn't reached); standoff repeated failing searches
(wild-1100006217); the fortress respawn-blocking rule (behaviour); 300+ is 44% of OOF.

## Exact repeated work (worker; branch fc4-exact2, round 3)

Baseline m2 (`variants/astraeus-fc4-m2`). Both commits are byte-identical at 100M on all 8 sets (x2a = commit 1,
x2b = both).

**1. walk_down: the second descent after a failed search (75157745).** walk_on (farm) and the siege seal walk ran
`descend(field) || step_towards(field)`; step_towards's own `descend_with` repeats the first one (with a ready dash,
its plan, ~4.3k) after its search fails, on a static-descend shortcut, or straight away when we are off the field.
`Pathing::walk_down` passes step_towards a token of the first failure and skips the repeat while nothing it reads
changed: `acts_` (bumped in `invalidate()`, which every successful move/dash, every hidden-blocker bump and an outside
dash runs) and the guard state (`guard_`, `guard_fn_`). A failed descent acts on nothing (try_move/dash_to/take fail
without moving); a guard refusal or a caught error changes no state; plan, closer_neighbours and travel_dash read only
position, bumps, guard, world beliefs and static boards, none of which a failed search changes.
- 100M total fuel vs m2: wide +0.01%, oof -0.02%, mg -0.06%, q -0.03%, big +0.01%, fs +0.01%, fight -0.03%,
  tgt +0.01%. Small: the repeat needs a ready dash and a failed walk. The + sets are ~+10 a turn of codegen (round 1
  +9-15).

**2. camp_cast reads out-of-reach members only for sole_finish (f9222370).** A member beyond every ready slot's hit
(unit: range; ground: min(range, ability_range)+1, as best_ground clamps; landing: dash_range + radius) is no target:
unit casts skip it, best_ground draws no centre for it, best_landing adds it to no cell (its sums are unchanged). It
still decides `sole_finish` (all visible and exactly one alive): those members are read (visibility, has_camp,
sdk_camp, health) only while `all_visible && live < 2`; once either fails, sole_finish is false whatever the rest
say. Without a post-basic cast all_visible starts false, so they are not read at all. Attackers-only (spell clear)
reads every member as before (its floor is the minimum over all). The stun exposure loop and pushes are in-reach only.
- 100M total fuel vs x2a: wide -0.02%, oof -0.02%, mg -0.02%, q -0.04%, big -0.01%, fs -0.01%, fight -0.03%,
  tgt -0.10%. Fight round-1 mean +161 (codegen), others round 1 level or lower.

**Both vs m2 (100M):** total wide -0.01%, oof -0.04%, mg -0.08%, q -0.07%, big 0.00%, fs 0.00%, fight -0.06%,
tgt -0.09%. p99: wide 107,655 -> 107,573, q 139,031 -> 138,633, tgt 118,052 -> 117,427, others within +-0.1%.
Turns over 100k: wide 4,019 -> 4,006, oof 16,957 -> 16,906, mg 7,781 -> 7,757, q 18,550 -> 18,466, big 4,123 ->
4,110, fs 22,527 -> 22,525, fight 4,876 -> 4,856, tgt 2,458 -> 2,434. Real-budget bench OOF (m2 -> x2b, diverged
games, indicative): wide 714 -> 855, oof 1,594 -> 2,002, mg 622 -> 988, q 2,869 -> 2,709, big 182 -> 177, fs 2,026 ->
2,037, fight 776 -> 812, tgt 1,245 -> 996.

**A/B fc4-exact2 (x2b vs m2, 10,240, real budget):** 49.9% (48.9-50.9). OOF 62,569 vs 64,907 (-3.6%; rounds 1
7,103/7,131, 2-10 6,100/6,158, 11-60 9,273/9,494, 61-300 12,911/13,121, 300+ 27,182/29,003; runs >=50 2,973/4,196,
so most of the gap is runaways and may be noise). Shortcuts 3.187M vs 3.188M (static-descend 21,305/22,308,
farm-no-route 50,560/52,341, crow-flies-farm 75,220/74,590). Fuel mean 50,055 vs 50,079, p50 48,550/48,650, p90
86,250 both, p99 92,550 both, at/over 100k 0.23% both.

**Not done.** Lead 3 (a failure memo for standoff searches keyed on goals, walls/occupancy, tile and cap): not
attempted. camp_cast's remaining cost after the members loop (other groups' `draw_alive_members` per ground slot,
`landing_threats`) is per slot and could be shared between the two slots (open minor, est. <0.5k a cast).

## Turn-order gate (worker; branch fc4-order)

Baseline m3 (`variants/astraeus-fc4-m3`). Profile: a copy printing raw `fuel()` laps around `set_turn_order` inside
`debug_block`, classed by state at entry, real budget, 1,024 games (fresh-11000..11001) against m3.

**Where the gate fires** (20,569 firings in 1,024 games): 60% (12,424) on turns with no enemy in sight, not a
healer, no channel ending, not the first round ("quiet"); then seen+near+built 4.0k, seen+near 1.5k, seen+built 1.1k.
Whether a tracked enemy's `possible` reaches within Strike::max_reach barely matters (excluding those leaves 12,059),
nor does `safety.built()`.

**What a quiet call costs** (3.19M calls that ran): p50 639, p90 868, p99 2,481, p99.9 4,059, p99.95 4,768, p99.99
6,690, p99.999 10.6k, max 18.7k; over 5k 0.044%, over 6k 0.020%. With no enemy in sight the bid skips offer_kills and
offer_heal, may_escape takes damage_ceiling's unseen path and offer_escape's out_of_reach exit, so the work is
camp members (find_members when first built here: 3.5% of calls, p50 0.8k, p99.9 7.2k) and the tracked enemies'
loops. The tail is late rounds on moated-altars / altar-rich / mega-groups maps. The check itself is a cached
`enemy_seen`, the facts, and one `my_record()` + channel-time read, only on turns under the 10k reserve. Of the quiet
firings, fuel left is >= 3k / 4k / 5k / 6k / 7k on 54 / 51 / 47 / 42 / 35% of all firings.

**Kept (fc4-order): a quiet turn runs at a 6k reserve** instead of 10k. Exact at 100M (the gate always passes): 274/274
replays identical on wide, oof, mg, q, big, fs, fight, tgt (checked on the 5k build; the reserve is one constant);
total fuel -0.00%, p90/p99/max/round 1 unchanged; dearer turns only 1 in big and 4 in fight.

A/Bs, 10,240 games, real budget against m3 (cand / ref in the same run):

| measure | 5k (fc4o-a) | m3 | 6k (fc4o-b, kept) | m3 |
|---|---|---|---|---|
| win | 50.0% (49.0-51.0) | | 50.0% (49.1-51.0) | |
| OOF | 59,311 (+0.74%) | 58,876 | 59,256 (+0.25%) | 59,110 |
| r1 / 2-10 / 11-60 / 61-300 / 300+ | 4,039 / 6,765 / 9,532 / 13,157 / 25,818 | 4,038 / 6,579 / 9,594 / 13,010 / 25,655 | 4,039 / 6,657 / 9,520 / 13,185 / 25,855 | 4,038 / 6,580 / 9,581 / 13,107 / 25,804 |
| runs <10 / 10-49 / 50+ | 38,708 / 19,321 / 1,282 | 38,694 / 19,163 / 1,019 | 38,507 / 19,421 / 1,328 | 38,806 / 19,226 / 1,078 |
| turn-order | 108,833 (-45%) | 198,916 | 119,230 (-40%) | 199,281 |
| comms-stale-vision | 58,375 (+33%) | 43,979 | 53,904 (+23%) | 43,967 |
| shortcuts | 3.123M | 3.194M | 3.130M | 3.199M |
| fuel mean / p50 / p90 / p99 | 49,939 / 48,350 / 86,150 / 92,450 | 49,943 / same | 49,934 / 48,350 / 86,150 / 92,450 | 49,942 / same |

At 5k the turn-order call took fuel the comms refresh (5k floor) needed: comms-stale-vision rose 14.4k for 90k fewer
turn-order firings. 6k keeps more of the refresh for 10k fewer turn-order removals. OOF is within noise in both,
but runs of 50+ rose ~250 in both runs (the reference's own moved 1,019 -> 1,078 between runs): worth a look on a
fresh suite before merging.

Open: the non-quiet firings (seen+near, ~40%) are the dear tail (offer_kills, threats_at); bounding them is the
earlier leads' work. The quiet tail is find_members built first at the turn's end: building it earlier moves, not
saves, the cost.

## Per-tile step guard (worker; branch fc4-guard, round 3)

Baseline m2 (`astraeus-fc4-m2`). The fight worker's redesign 1, built and measured four times: **not a win**. The
guard's shortcut firings fell by half, and the win rate held level. But out-of-fuel turns rose 6-8%, about 4-5k
in 10,240 games against ~800 noise. Commits 7600e529, d160d4f8, 387ec9ee, 656f1ce1. Scratch: `/tmp/fc4/guard/`
(`pts.py`; `probe-guard.cc` is the probe's guard.cc).

**Design.**
- `Pathing::defer_guard` takes an optional `GuardTileFn`. `step_guard_tile` and `work_guard_tile` answer for one
  tile q:
  - the bound test, then q's exact look (`GuardFoes::exposure`), then q's own fight key (the m == 1 path of
    `step_guard`);
  - then the memo, or a memoised fight that covers the key (`Safety::fight_covered`, the same monotone rule as
    step_guard's `covers`), or one `new_fight`.
- `work_guard_tile` adds hold_outlasts and keep_out, as `work_guard` does.
- `Pathing::guarded(p)` caches each answer in two 25-bit masks, carried in `GuardState`. An answer of -1 ("no foe
  reaches, nothing kept out") resolves the whole guard to null at once.
- Users:
  - try_move, steppable, label_through, make_way's allies, siege's endpoints and quote_escape_walk;
  - route(): a bare search, then its first steps are tested in order until one is off the guard. If all are
    guarded, they are walled and the search runs again;
  - descend: try_move tests the guard lazily, and travel() filters all its steps.
- The strike search, dash_landings and know_failure keep the whole-guard path with its unions and its old entry.
- The entry check is now one fight of q's size: `act_reserve + query_cost_estimate() + 2000 + 2000 x (foes near q
  + allies at q)`. It replaces F (the champions prior) + 20k + costliest. Its cut is still labelled
  `step-guard-entry`.

**Faithfulness.**
- For tile q, the whole guard's verdict is "q's own fight lost, or we fall there and it counts". The whole guard
  reaches that verdict through the unions U1/U2, which pool every enemy reaching any exposed tile, and through the
  `covers` inference.
- The per-tile path simulates q's key itself: the enemies whose Reach hits q this round. Reach is built from
  `cambc-rules.yaml`'s walk, dash (2 king steps), ability range 4, attack ranges 1/3, and the turn order Safety
  models. Their unseen partners are added by `fight_key_with`, and so are the allies at q.
- It only infers through a memoised fight under the same monotone rule. Where the whole guard would have settled q
  by a union win, the per-tile path gets the same answer or a finer one.
- route walls only guarded first-step tiles. A walk this turn ends on its first step, so with a dash ready the old
  walls on tiles 2 away were stricter than "where a step can end". Dash landings still read the whole guard.

**Measured** (10,240-game real-budget A/Bs, fresh-11000..11019, CAND vs m2 (REF); "OOF" is out-of-fuel turns):

| try | what | win | OOF CAND / REF | entry | look | turn-order |
|---|---|---|---|---|---|---|
| pt1 7600e529 | end_reserve + one fight | 49.6% | 77,327 / 62,543 (+24%) | 261k / 430k | 21k / 75k | 279k / 209k |
| pt2 d160d4f8 | + act_reserve, memo cover, failed-route labels | 50.0% | 73,869 / 64,691 (+14%) | 397k / 440k | 21k / 76k | 270k / 211k |
| pt3 387ec9ee | + -1 resolves a null guard once | 49.7% | 67,404 / 63,706 (+5.8%) | 377k / 433k | 26k / 76k | 235k / 211k |
| pt4 656f1ce1 | + only the steps tried are resolved | 50.3% | 68,648 / 63,729 (+7.7%) | 238k / 435k | 26k / 76k | 233k / 209k |

- pt4 shortcuts: step-guard-sim 4.0k vs 5.7k; the three guard tags together 268k vs 516k (-48%).
  comms-stale-vision 51.9k vs 47.8k.
- pt4 OOF by round: 1: 7,392 / 7,132; 2-10: 6,323 / 6,172; 11-60: 9,764 / 9,562; 61-300: 14,465 / 13,477;
  300+: 30,704 / 27,386. Runs of 50 or more OOF turns in one champion-game: 4,510 / 3,194.
- fuelstats: mean 50,208 / 50,042, p90 equal, over 100k 0.24% / 0.23%.
- pt1's +1.1k OOF in round 1 came from failed routes. A failed bare route left `failure_known_` false, so
  make_way searched the whole map again whenever an ally stood beside us (always on spawn). pt2 fixed it.
- pt1 and pt2 also paid a GuardFoes build on every new tile while no foe reached. pt3 fixed that (-1).

**Where the OOF is not.** A probe copy of pt3 printed one line per per-tile resolution. Its 2,048-game A/B:
CAND OOF 12,848 vs 12,078 (`PTS round champion estimate cost fuel-left verdict`).
- 233k resolutions:
  - cost 4.6k mean, 2.9k median, 10.3k p90, 16.5k p99, against an estimate of 11.9k mean (3.2% over it);
  - fuel left after a resolution: under 20k on 0.09% (the entry holds);
  - 31% guard the tile.
- Only 903 of the 12,848 OOF lines fall in a round where the team ran a per-tile resolution.
- In pt3, turns resolved 1 tile 60.7k times, 2 tiles 35.7k and 3 tiles 33.4k. So a turn could pay ~14k where U1 paid
  ~7k. pt4 resolves only the steps tried, and that cut entry firings further. OOF stayed level with pt3 (+7.7%
  against +5.8%, within run-to-run noise).

So the extra OOF is not the guard's own spending. The pattern points to the behaviour change:
- the guard now resolves on turns it used to skip, and guards a tile on 31% of them;
- turns near enemies get longer, and runaway runs grow (50+-turn runs +1.3k);
- turn-order and comms-stale-vision fire more, because work spends down later in those turns.
Not proven: a census on pt4 would name the stacks.

**100M benches** (pt4 against m2's JSONs; behaviour change, so identical replays: wide 30/52, oof 16/48, mg 9/24,
q 31/48, big 26/32, fs 12/24, fight 2/30, tgt 6/16):

| set | mean | p99 | over 100k | round-1 mean | fuel, identical games |
|---|---|---|---|---|---|
| wide | 51,993 -> 52,129 | 107,655 -> 105,407 | 4,019 -> 3,541 | 218,547 -> 218,721 | +0.21% |
| oof | 55,636 -> 55,385 | 150,876 -> 150,001 | 16,957 -> 16,616 | | -0.00% |
| mg | 59,862 -> 59,710 | | 7,781 -> 7,571 | | -0.11% |
| q | 60,683 -> 60,637 | 139,031 -> 138,025 | 18,550 -> 18,470 | | +0.37% |
| big | 60,730 -> 61,076 | | 4,123 -> 4,141 | | +0.34% |
| fs | 94,901 -> 94,916 | | 22,527 -> 22,519 | | +0.22% |
| fight | 48,794 -> 48,214 | 117,003 -> 115,239 | 4,876 -> 4,637 | | +0.24% |
| tgt | 51,042 -> 53,464 | 118,052 -> 117,963 | 2,458 -> 2,461 | | +0.08% |

- Round 1 is +0.0-0.2% on every set: the route branch, plus codegen.
- Real-budget bench OOF, m2 -> pt4 (indicative only): wide 714 -> 675, oof 1,594 -> 1,500, mg 622 -> 556,
  q 2,869 -> 3,392, big 182 -> 188, fs 2,026 -> 1,979, fight 776 -> 741, tgt 1,245 -> 978. Sum 10,028 -> 10,009.
- pt1 at 100M was +0.5% to +3% fuel. pt4 removed most of that.

**Open leads.**
- Run the census on pt4 vs m2 to find which stacks gained OOF.
- Try an entry of `F` (keeping the champions prior) + act_reserve without `costliest`. It cuts fewer, and shows
  whether the OOF follows the extra resolutions or the per-tile semantics.
- The strike search and dash_landings still place the whole guard (the remaining ~238k entry cuts are mostly those
  plus per-tile cuts). Splitting the label would show which.

## Merge round 3b (merge agent)

fc4-exact2 (75157745, f9222370, ce41ca87; merge 2a37deb2) and fc4-order (f66d63ec, d4e3f422; merge 698bd4af) were
merged into fuel4-orch whole. fc4-guard's notes commit 96e9d58a was cherry-picked (670b6cd3), without its code. All
NOTES sections were kept. One fix of mine: 2db40854 (below). Frozen: `fuel4/bots/variants/astraeus-fc4-m4` (=
fuel4-orch's bot). CHANGES 306 (exact cuts, fuel only) and 307 (turn order, behaviour at the real budget).

**Review.**
- 75157745, walk_down (exact, with 2db40854).
  - Between the two descents, step_route's search can change their inputs only through `try_move` / `move_to`
    (moved or bumped), `dash_to` (always) and an outside dash (`dashes_seen_`, checked in `my_pos` / `blocked`).
    Each of these runs `invalidate()` and so bumps `acts_`. A lazy guard resolved by the search changes `guard_` /
    `guard_fn_`, which are in the token. `make_way` only asks allies to move. `closer_neighbours`, `plan` and
    `travel_dash` read position, `blocked()`, bumps, guard, cooldown and world beliefs, and none of these change
    otherwise.
  - The gap: the repeat's `ahead()` (with a ready dash and crossings) re-stamps the approach field's trace as the
    latest in `traces_` (4 slots, least recent replaced). `travel()`'s `ahead()` on the route field stamps a
    different slot in between. Skipping the repeat flipped the two slots' order, so a later replacement could evict
    a different trace. A rebuilt trace inherits the slot's `last` direction, so behaviour could differ.
  - 2db40854 fixes this: `walk_down` records the trace the first `ahead()` read, and the skip stamps it with
    `++trace_clock_`. The repeat would have found it kept (k = 0, its count >= 2 since horizon >= 1) and stamped it,
    and `travel()`'s allocation can't have evicted it, being the latest. Relative order is all `used` serves.
- f9222370, camp_cast (exact).
  - Reach per slot: unit `range()` (the unit loop skips `dist > range()`). Ground `min(range, 4) + 1`, as
    `best_ground` clamps the range to `ability_range` and skips targets beyond range + 1. Its `harmful` test needs a
    member within 1 of an in-range centre. Landing `dash_range + radius`, the cells `best_landing` sums. Non-damage
    slots (reset, plain dash, heal) only widen the bound, which is safe.
  - Out-of-reach members add to no cell, so the sums and the summation order over the cells read are unchanged.
  - `sole_finish`: `live` counts exactly what `members.size()` did (health > 0 after the same tests). A member is
    skipped only once `all_visible` is false or `live >= 2`, either of which already settles sole_finish false.
  - A sole live member out of reach: the old code found no cast and returned an empty Cast; the new code returns
    `{}` at `members.empty()`.
  - Attackers-only reads every member (its floor is the minimum over all).
- f66d63ec, turn order: behaviour at the real budget only.
  - It only narrows the existing gate: `short_of_fuel` gains `&& !(fuel_ok(6000) && quiet(world))`. The new
    `fuel()` read lets the call run, so it never chooses worse. `quiet` is a cached `enemy_seen`, the facts, and one
    `my_record()`, evaluated only under 10k.
  - The 6k bound matches the worker's distribution (p99.99 6,690, over 6k 0.020% of 3.19M calls).
  - The quiet bid skips `offer_kills`, `offer_heal` and the cancel, so a sub-6k call can't reach the dear offers.

**100M** (m3 -> m4, `MAIN/replays/fuel/fc4/m4-*-100M.json`, `bench.py compare`): all 274 replays are identical.

| set | identical | total | mean | p90 | p99 | max | over 100k | round 1 mean |
|---|---|---|---|---|---|---|---|---|
| wide | 52/52 | -0.01% | 51922 -> 51919 | 86452 -> 86447 | 107530 -> 107443 | 276779 -> 276792 | 4,002 -> 3,989 | 218812 -> 218844 |
| oof | 48/48 | -0.04% | 55497 -> 55476 | 88274 -> 88271 | 151024 -> 151026 | 555660 -> 555669 | 16,880 -> 16,830 | 240510 -> 240433 |
| mg | 24/24 | -0.07% | 59769 -> 59725 | 89649 -> 89577 | 149301 -> 149290 | 373046 -> 373058 | 7,759 -> 7,734 | 230995 -> 231016 |
| q | 48/48 | -0.07% | 60586 -> 60546 | 90522 -> 90393 | 139065 -> 138656 | 438574 -> 438608 | 18,524 -> 18,447 | 262773 -> 262663 |
| big | 32/32 | +0.00% | 60561 -> 60562 | 87504 -> 87500 | 119952 -> 119861 | 327345 -> 327360 | 4,100 -> 4,087 | 248910 -> 248914 |
| fs | 24/24 | +0.00% | 94852 -> 94855 | 132686 -> 132691 | 196636 -> 196715 | 611791 -> 611791 | 22,470 -> 22,467 | 551107 -> 550887 |
| fight | 30/30 | -0.06% | 48589 -> 48562 | 85997 -> 85980 | 116906 -> 116891 | 380956 -> 380991 | 4,820 -> 4,796 | 195990 -> 196135 |
| tgt | 16/16 | -0.09% | 51010 -> 50964 | 86747 -> 86744 | 118209 -> 117584 | 263572 -> 263616 | 2,464 -> 2,438 | 230068 -> 230092 |

**A/Bs** (real budget, own drafts, fast runner, 10,240 games each; batches
`fuel4/replays/batch-20261103-095307-ab-fc4-m4-{vs-m3,conf,vs-fc4b}-*`, logs `MAIN/replays/fuel/fc4/ab-fc4-m4-*.log`).
fresh-10140..10159 don't exist. The confirmation used fresh-10000..10019, which no campaign-4 A/B had used.

| measure | m4 vs m3, fresh-11000..11019 | m3 | m4 vs m3, fresh-10000..10019 | m3 | m4 vs fc4b | fc4b |
|---|---|---|---|---|---|---|
| win | 50.3% (49.4-51.3) | | 50.0% (49.1-51.0) | | 50.0% (49.0-50.9) | |
| OOF | 58,042 (-3.1%) | 59,882 | 60,742 (-3.0%) | 62,640 | 57,482 (-38.5%) | 93,462 |
| r1 / 2-10 / 11-60 / 61-300 / 300+ | 4,036 / 6,582 / 9,278 / 12,999 / 25,147 | 4,038 / 6,581 / 9,577 / 13,301 / 26,385 | 3,862 / 6,350 / 9,185 / 13,484 / 27,861 | 3,863 / 6,350 / 9,409 / 14,064 / 28,954 | 4,026 / 6,561 / 9,161 / 12,568 / 25,166 | 10,706 / 10,143 / 13,874 / 23,445 / 35,294 |
| runs <10 / 10-49 / 50+ | 38,032 / 18,786 / 1,224 | 38,721 / 19,803 / 1,358 | 37,392 / 20,276 / 3,074 | 37,984 / 21,481 / 3,175 | 38,048 / 17,384 / 2,050 | 62,798 / 28,407 / 2,257 |
| fuel mean / p90 / p99 | 49,928 / 86,150 / 92,450 | 49,944 / 86,150 / 92,450 | 50,206 / 86,250 / 92,650 | 50,189 / 86,250 / 92,650 | 49,904 / 86,150 / 92,350 | 50,659 / 86,450 / 92,950 |
| at/over 100k | 0.22% | 0.23% | 0.23% | 0.23% | 0.22% | 0.29% |
| shortcuts (with OOF) | 3.124M | 3.194M | 3.124M | 3.204M | 3.074M | 4.182M |
| turn-order | 117,332 | 199,352 | 123,688 | 213,334 | 114,787 | 382,705 |
| comms-stale-vision | 53,249 | 44,427 | 55,761 | 46,642 | 53,055 | 498,293 |
| farm-partial-evaluation | 2,066,221 | 2,065,529 | 2,069,772 | 2,062,842 | 2,050,173 | 2,309,636 |
| step-guard-entry | 440,426 | 437,056 | 451,215 | 450,801 | 427,524 | 476,212 |
| static-descend | 19,388 | 18,180 | 19,162 | 20,074 | 17,926 | 27,490 |

**Turn-order kept.** Over the two m4-vs-m3 runs, OOF is -1,840 and -1,898 (noise ~800), the win rate is level, and
the cut is spread over 11-60, 61-300 and 300+. The worker's +250 runs of 50+ didn't recur (-134, -101). Against fc4b,
m4 is -2.8% of m3's OOF (59,134 -> 57,482). 300+ fell 26,159 -> 25,166 and 61-300 12,925 -> 12,568.

## Attack-tile decode (worker; branch fc4-decode)

Baseline m4 (`variants/astraeus-fc4-m4`). What is cached already: each member's tiles per range
(`Pathing::attack_slot`, once per instance), the index per block of 8 groups, and farm's kept union (group, range,
live members). So the decode is paid once per (member, range) per champion, the index once per block.
- **Where the cost is (debug-build `fuel()` laps in `drafted_attack_tiles`, idle opponent, 40 rounds):** per call,
  sight (`sight_off_bushes`: shadow cast, and, allocation) ~0.35-0.65k; it is the whole cost on maps without bushes
  near members (mega-groups 912 calls 345k, boss-battle 936 calls 246k). The bush-bit decode, for members with bits,
  is ~0.65-0.9k a call: 00ambush 60 calls 39.3k (193 bush tiles), 00oasis 70 / 64.2k (430), 00gem-fields 120 / 83.4k
  (504), 00lost-world 126 / 94.8k (510). The index is 11-65k a game across all instances, once per block.
- **Change (dd618ce3, exact):** the bush bits are read a chunk at a time (popcount of the chunk's masked bushes,
  one or two `get`s) and laid onto the bushes in ctz order, the order `each_in_square` read them one by one; range 1
  masks the chunk to its square instead of a per-tile `dist`. A debug check that built both versions on the four
  bushy maps matched on all 376 decodes with bits.
  - The per-bush loop was not the cost: in the same debug laps the decode moves 39.3k -> 38.0k, 64.2k -> 57.7k,
    83.4k -> 86.3k, 94.8k -> 95.5k. The ~0.65k a call is fixed overhead (debug codegen inflates it; release not
    measured per call).
  - At 100M the replays are identical on all 8 sets (274/274 games). Total fuel: wide -151,810 (-0.001%), oof
    -908,645 (-0.006%), mg -287,420, q -75,401, big -349,875, fs -47,333, fight -118,953, tgt -155,585 (all
    under -0.01%). p90 / p99 / over-100k unchanged within ±3 / 0 / ±1 (fs 22,467 -> 22,466). Round-1 mean: wide +3,
    oof -249, mg -85, q -33, big -117, fs -61, fight -80, tgt -165.
  - Real-budget bench OOF (m4 / decode): wide 1,404/1,404, oof 2,819/2,792, mg 1,794/1,793, q 3,056/3,060, big
    168/179, fs 1,978/1,996, fight 844/816, tgt 899/899.
  - A/B fc4-decode (vs m4, mirror, 10,240): 50.0% (49.0-51.0). OOF 58,382 vs 58,467; round 1 4,011 vs 4,036, 2-10
    6,521 vs 6,583, 11-60 9,311 vs 9,288, 61-300 12,918 vs 13,018, 300+ 25,621 vs 25,542; runs <10 / 10-49 / 50+
    37,871 / 18,897 / 1,614 vs 37,996 / 18,857 / 1,614; fuel mean 49,911 vs 49,920, p50 / p90 / p99 48,350 / 86,150
    / 92,450 both, at/over 100k 0.22% both. Shortcuts 3.107M both (farm-partial-evaluation 2,058,334 vs 2,059,049).
- **Open:** the decode's remaining cost is fixed per call (sight and the call itself), not per bush. Next: a
  fuel-exact release trace (replay harness) of one first-turn `farm_attack_tiles` to split sight, index and the
  decode's fixed part before cutting further; the 16.5k first-turn figure should be re-measured that way.

## Per-tile step guard, follow-up (worker; branch fc4-guard2)

fc4-guard's pt4 (four code commits) ported onto m3 (1ec978f5) without conflicts: a7884964, 8f2cf848, 4d298302,
09e7467e. Two fixes tried, **neither fixes the OOF**: 4d47b0c7 (entry), 26ed30b5 (route). Do not merge as a fuel win.
Scratch `/tmp/fc4/guard2/`.

**A/Bs** (10,240 games, real budget, fresh-11000..11019, CAND vs `astraeus-fc4-m3`):

| try | win | OOF CAND / REF | guard entry / look / sim | turn-order | comms-stale-vision | all shortcuts |
|---|---|---|---|---|---|---|
| port (pt4 on m3) | 50.3% | 63,694 / 60,605 (+5.1%) | 234k / 26k / 4.0k vs 441k / 77k / 7.3k (-49%) | 218k / 198k | 48.4k / 44.5k | 2.97M / 3.21M |
| 4d47b0c7 entry F + act_reserve | 50.2% | 63,487 / 60,544 (+4.9%) | 279k / 26k / 4.0k vs 441k / 76k / 7.0k (-41%) | 216k / 197k | 47.8k / 44.4k | 3.01M / 3.20M |
| 26ed30b5 + all-guarded route walls the whole guard | 50.1% | 62,435 / 59,618 (+4.7%) | 291k / 37k / 4.5k vs 440k / 75k / 6.9k (-36%) | 217k / 196k | 47.7k / 43.8k | 3.03M / 3.19M |

- OOF by round (1 / 2-10 / 11-60 / 61-300 / 300+), CAND vs REF:
  - port: 4,136 / 6,737 / 9,903 / 14,126 / 28,792 vs 4,038 / 6,592 / 9,495 / 13,440 / 27,040;
  - 4d47b0c7: 4,136 / 6,737 / 9,977 / 14,028 / 28,609 vs 4,038 / 6,589 / 9,599 / 13,359 / 26,959;
  - 26ed30b5: 4,139 / 6,741 / 9,910 / 13,758 / 27,887 vs 4,038 / 6,596 / 9,559 / 13,122 / 26,303.
- Run sizes (<10 / 10-49 / 50+): port 40,016 / 21,686 / 1,991 vs 38,693 / 19,416 / 2,496; 4d47b0c7 40,286 / 20,972 /
  2,230 vs 38,598 / 19,311 / 2,635; 26ed30b5 40,371 / 20,247 / 1,817 vs 38,692 / 19,534 / 1,392. Runaways are not
  the excess: it is in short runs.
- fuelstats (mean, p50, p90, p99): every try is mean +135 to +170, p50 +200 to +300, p90 +100, p99 +200. Over 100k
  0.23% for both.
- Rounds 1 and 2-10 are +100 and +150 in all three, identical to the turn (deterministic). This is the codegen or
  route-branch overhead, where no guard resolves.

**Census** (`--fine --trace --lenient`, plus scopes `g.step_whole`, `g.work_whole`, `g.step_tile`, `g.work_tile`;
port and m3 census copies each against m3, 4,096 games, fresh-11000..11007). OOF 19,562 vs 18,978.
- No new stack. OOF-first decide-level scopes all grow in proportion: farm +304, strike_search +128, turn_order +68,
  act_end +59; carry_bag -121.
- **All the extra OOF-first turns are near enemies**: 6,842 vs 6,362 with an enemy within 6, and 7,037 vs 7,074
  without one.
- The guard is not dearer. Guard scopes per near turn: 2,056 against m3's 3,351. The fuel ran out inside the guard on
  240 turns against 164 (+76).
- But on OOF-first turns the guard spends 1,010 a turn against 712: the per-tile path resolves on tight turns that
  m3's entry (F + act_reserve + costliest) cut. 4d47b0c7 raised the per-tile entry to F + act_reserve and **OOF did
  not move**. So OOF does not follow the extra resolutions.
- At equal enemies within 6 (1-5):
  - the number of turns is the same;
  - the mean turn costs +150 to +230;
  - OOF-first is +7-11%, and turns at 90k or more are +6-12%.
  - It is a heavier tail per fight turn, not more fight turns.
- On OOF-first turns near enemies (inclusive, per turn), farm and pathing work is up: goal +1.4k, farm +1.0k,
  walk_on (farm's fuel-short walk) +0.7k, step_goals +0.6k, step_field +0.5k, p.route +0.4k, route searches +0.3k,
  strike_search +0.5k. The fights are down: retreat -0.8k, s.bound -0.6k, want_home -0.5k.
- On all near turns, route searches are +13% a turn (the per-tile route's re-searches). 26ed30b5 capped them at one
  extra search and **OOF did not move** either.
- With no enemy near, decide is +300 a turn (p.route self +150; p.travel +85, its calls +19%), taken back out of the
  turn-end queue. OOF there is level.

**Reading.** The excess is neither the guard's own spending nor its entry check, nor the route re-searches. What is
left is the behaviour change. With the same enemies around, the per-tile guard's answers lead to dearer turns. They
are dearer in farm's walk and step paths and in the strike search (self +144 a near turn, with the same number of
calls). With a dash ready, the old guard walled guarded tiles 2 away from every route; the per-tile route walls first
steps only, so routes can run beside tiles the old guard kept them off. That is the untested candidate. Testing it
means walling the radius-2 tiles too, which brings back most of the whole-guard cost for Cassi and Issac (both
dash).

**Open leads.**
- Per-tile route with a dash ready: wall the guarded radius-2 tiles too, or use the whole guard. This tests the
  behaviour hypothesis.
- A census with the strike search split (`plan.cc` resolve_guard / `S.guarded`), to see why its self fuel rises with
  the guard unchanged.
- The CTR trace came back empty under fastrunner (`trace.py`: 0 traced turns). Check whether `--trace --lenient`
  still matches the current bot.
