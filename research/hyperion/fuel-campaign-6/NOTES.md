# Fuel campaign 6 notes

## veto

Area: `work_veto` / `leaves_at` (combat/guard.cc), `stand_lost_at` / `drawn_home` (combat/fight.cc), `Safety::stand_roster` / `stand_trade`.

### Where the fuel went (d6e74b6f, 48 osc games, real budget, `debug_block` census)
- On OOF-first turns the veto runs on 68% of turns, at 19k a turn and 1.56 calls. `lv.stand` (want_home plus the veto) costs ~26k a turn.
- Per-call cost by path: nobody believed ~1.4k; no fight ~4k; trade with walkers 16-18k, mostly `fight_of` with `late` (6-8k); memo hit 5-6.6k.
- About 10% of asked tiles are vetoed. The cleared ones are walked to (61k of 65k), so the asks aren't wasted.
- The memo-hit cost is the inputs, not the trade: the hold (`hold_rounds`, `hold_outlasts`), lethal, the recall line, and the pursuit terms were all computed before the 8-entry `StandsRead` lookup, whatever its verdict.

### Shipped (both byte-identical at 100M on wide oof mg q big fs fight tgt osc)
1. 9e226d61 — `leaves_at` works out the recall line and the hold only when the verdict reads them. `HoldAt` is lazy (rounds and keeps on first read). `drawn_home` tests the cheap health bound first: both recall lines are at most `recall_health_fraction`.
2. 27312ab5 — `stand_lost_at` reads lethal and pursuit only where its roster does. It is split into `Safety::stand_reach` (the seen and believed walks) and `stand_roster(p, reach, …)`. With a hit, the roster reads neither `pursued` nor `unseen`, so neither is computed then. Lethal is computed lazily, at most once.
   - One trap: `own_ground` (inside `pursued`) builds the ally spawn field on first need, and farm (`economy/farm.cc:947`) and camps (`camps.cc:373`) price by a bound until that field exists. So `pursued` stays computed while `!from_ally_spawn_ready()`.

### Tip versus d6e74b6f
- At 100M: mean −0.3 to −0.9% per set; p99 −0.2 to −1.1%; max up to −2.3% (big); round 1 −0.3%. Over-100k turns 136,541 → 133,347 (−2.3%).
- Real budget, summed over the 9 sets: OOF turns 34,374 → 29,500 (−14%). tgt is the only set that rose: 1,486 → 1,872. That set is 16 games, and the threshold effect moves turns either way.
- 10k A/B (`fc6veto-tip`, fresh-66101..66120, own drafts): 50.2% (49.3–51.2). OOF 198,559 vs 224,498 (−11.6%); mean fuel a play turn 52,516 vs 52,876; at or over 100k 0.50% vs 0.55%. The tip before the field guard read 50.3%, OOF −11.7%.
- Share left after v2 (OOF-first turns): `s.lethal` fell 7k → 2.2k. Reach builds moved into `lv.reach`, ~10.8k a turn (r.build 4.3k at 2.7 a turn, r.blow 4.9k at 7.4 calls, r.dist 3.8k at 5 calls). `lv.trade` is 15k, of which `fight_of` is 14.5k.

### Dropped (numbers from the osc census)
- Cross-turn memo of `simulate` inputs: only 3-6% of trades repeat, even with an unbounded LRU. In the veto: 3%, 1.5M of 89.5M.
- Reusing last turn's (here, tile, verdict): 1.4% repeat.
- Keeping `StandsRead` across observations within a round (a shadow memo): it answers 72 of 93k fresh stands.
- Memo of `Safety::lethal(p)` per observation: 1% of calls repeat.
- c1, computing `pursued` only when a walker exists (`reach.walking`): not exact. 6 of 322 replays differed (q 3, big 2, osc 1). The cause is the spawn-field side effect above (first divergence: the HOPS / farm pricing line on round 27). Even with the field guard it would only save `paying_soon` on no-walker turns, which is small.
- `in_pack_zone`: 2.6k a turn on 71% of OOF-first turns, but 1.6k of that is the pack member list, already made once a round. The per-call remainder is ~470, so there's not much to cut.

### Open leads
- `fight_of` with `late` inside `stand_trade` (14.5k a turn) is now the veto's bulk. Trades rarely repeat, so it needs a cheaper simulate, not a memo.
- Reach builds per enemy per turn (`lv.reach` ~10.8k): r.blow is called 7 times a turn. A per-turn blow cache keyed by (enemy, tile) is untested.
- `wh.camp_trapped` in want_home: 4.5-6k on 37-45% of OOF turns.

## econ

Worker: economy side (opening, round 1, turn-end queue). Branch `fc6-econ`.

### Where 337's econ-side fuel went
- **Round 1 is the veto.** At 100M, round-1 mean rose 243k→256k (oof), 301k→324k (q), 202k→209k (osc)
  from 088bf3f to d6e74b6. The census puts the rise in `farm.post`, at the first work step's
  `work_veto`→`leaves_at`: ~20k per affected body on the real budget (20-48k at 100M). That is
  `Safety::lethal` ~12.5k (struck 6k, the ceiling's first most_damage 3.9k, damage_bound's
  any_within ~2.5k), `ally_spawn_field` 3.8-15.5k (built by own_ground; the queue's warm-up would
  build it anyway, so moved rather than added), drawn_home 2-7k, stand_lost 1-3k. Round-1 OOF is that
  post overrunning the farm loop's reserve, which had no veto term.
- **The queue OOF phase is mostly an artifact.** In the 20k batch, phase "queue" in round 1 reads
  32,842 vs 9,235, but the phase is the last one reached after the resume. Census: the queue itself
  overruns rarely (6 of 2,792 turns where it ran out first); enemy_reach::warm_up is fuel-guarded.
- world/update is flat (~14-16k both sides).
- Over the whole game on the real budget (osc+oof, 96 games), OOF went 4,541→13,959; the non-veto
  stacks are level (farm self 731 vs 720, farm.post 541 vs 691, siege_kite 230 vs 173), and the veto
  stacks make up ~4.5-5k of the rise. Most veto OOF turns have enemies in sight: the fight worker's area.
- Runaways (≥50 OOF turns for one champion in one game): 7,282 of 18,173 OOF turns. Veto 36%;
  step_field/make_way 11% (gen-topo-island-986606600-a Ren: 448 OOF turns, each turn the same 3
  failing step_towards plus walk_on's step_field, 4 make_way calls ~47k); step_field/route 4%;
  walk_on/descend 4%.

### Shipped on the branch
1. `Safety::lethal` precheck (bc97c3bc + fixup 3b42530f, exact). With no enemy in sight, not all of
   them known, the camps' damage under health and no unseen enemy's possible tiles within
   Strike::max_reach of p, return false without the enemies' strikes. damage_bound then equals the camp
   damage (every blow is none), so the original answers false too; only caches are skipped. The first
   version also ran with enemies in sight and cost +0.1% mean (+27 a call, +140-190 when it failed);
   restricting it to `!seen_` cut that to +0.0-0.1%.
2. label_through's memo goes from 4 to 16 entries (43b65379, exact: same key, more of it kept). A
   standoff asks ~9 walks a turn under 2-3 caps, so 4 entries thrashed. Census q+osc real budget:
   OOF turns ending in make_way 808→131, make_way per call 11.0k→3.2k, label_through per call 3.8k→1.7k;
   whole-set OOF 13,324→12,547.
3. Farm loop reserves the veto's measured cost (real budget only; not exact). vetoed() measures each
   veto_fn_ ask; the loop's reserve and `ample` add the dearest recent ask, decaying by a quarter an
   ask. Identical replays at 100M on all 9 sets (+0.02-0.04% total for the measuring).

### Bench, all 9 sets (100M identical replays throughout)
1+2 (econ-a2) vs base: round-1 mean -0.7..-2.0%, p90 -0..-3.9%, max -1.1..-3.6%; total +0.02..+0.06%
(q -0.15%). Real-budget OOF turns summed over sets: base 35,622, econ-a2 35,283, econ-b1 33,597;
round-1 OOF 749→652. Per-set real-budget numbers diverge by game, so single sets are noise
(tgt 1,545→2,025 under b1, fight 3,633→3,092).

### A/B, branch tip (econ-b1) vs d6e74b6, maps/fresh-66101..66120, own drafts, real budget
- 50.4% of 10,240 (CI 49.4-51.3): level.
- OOF turns 205,538 vs 222,406 (-7.6%); round-1 OOF (batch_oof, shared gems skipped) 13,303 vs 17,320
  (-23%), all F branch; per-turn fuel mean 52,882 vs 52,866, p99 96,150 vs 96,550, at/over 100k
  0.52% vs 0.54%.
- Shortcuts: farm-partial-evaluation 2.84M vs 2.51M (+13%: the loop stops earlier for the veto's
  reserve), farm-no-route 49k vs 77k, comms-stale-vision 111k vs 140k, turn-order 308k vs 364k.

### Dropped
- beyond_strikes with enemies in sight (first version of 1): exact but +0.1% mean, see above.

### Open leads
- make_way/step_field repeating the same failed searches each turn in a standoff (after the memo,
  route repeats remain): a per-turn failure memo keyed by goals/walls/me would be exact.
- walk_on after a strike search (`struck && farm_group >= 0`) asks the veto ~13k a tile, ~1.5 tiles.
- siege_kite's first builds ~10k in round 1 (predates 337).

## runaway

Branch fc6-runaway from 0eae0574. Runaway = the same heavy work repeated every turn of a standoff.

### What the runaways are (main's round-1 A/B, bot 1, 197k OOF)
- Most OOF comes in short streaks: 106k in runs of 1, 84k in runs of 2-4. The 50+ OOF games are mostly
  long fights with intermittent OOF (arena 16.7k), "?" branch 83% of first-in-streak.
- True standoffs are few but huge (topo-necks-6621607043 ~900 turns in B, topo-shortcut-6621506918,
  mut-vault). Census of 30 runaway games, per OOF turn: route 7.2k, label_through 5.3k, step_route
  3.9k, make_way 1.1k; strike_search 10.8k, chase 8k, fight_of 7.6k, veto 4.8k.
- topo-shortcut-6621506918: six allies queued in a one-wide dead end (x=5, y=61..66) from round ~30
  to ~750. The front one searches the whole map fresh (19-21k, caps 118/115/195) every turn; the rest
  reuse spares (2-2.5k) and pay label_through 3-5k. ~22% of fresh-search fuel is a wider re-search
  after a cut-off failure (same me, goals, walls). A behavioural deadlock: left alone.
- Bank-branch runaways on fresh-663xx (arena-6631702600, fortress-6630402214, hole-maze-6631207507,
  topo-necks-6631407008, clusters-only-6631105700): period-2 repetition, identical costs every other
  round (carry_bag → chase 35k → channels 16-18k, then bg → step_safely → step_field → descend →
  vetoed → fight_of). The repeated work is inside prey/chase_trade and the veto's fight_of: the other
  worker's area, so not touched.

### Shipped
1. 0cb28b5a, label_through's walks survive a failed search taken back from the spares, and serve
   lower caps (fuel only). route_gen_ bumped on every swap; now each field carries an id that moves
   with it through swaps (spares, kept routes, round labels), so a memo entry stays valid while its
   field is the current one. The walk's result at cap c is min{s+1+d : s <= c}, so an entry also
   answers a lower cap c' when the label it used is <= c' (unreachable stays unreachable).
   Topo-shortcut jam: label_through per OOF turn 13.2k→7.3k (a), 9.8k→3.8k (b).
2. aaf26702, a wider failed search drops its spares under lower caps first (fuel only): a spare of the
   same me/goals/walls under a lower cap (or any cap, once failed_ ran dry) answers nothing failed_
   doesn't, so its slot is freed before the LRU evicts a useful one. Route per OOF turn in the jam
   38k→33.6k (a), 36k→27.9k (b).
   1+2 (rw-a) bench vs fc6-m1: 100M identical on all 9 sets and the 30-game runaway set; total
   +0.01..+0.02% (q -0.20%, osc -0.04%). Real OOF summed 30,504→30,939 (noise).
3. 930cbc3f, farm's loop keeps back the work veto's unmeasured first ask (real budget only). CHANGES
   342 reserves veto_cost_, which is 0 before the first ask, so the first turns reserved nothing
   (round-1 census: first ask median 3.7k, p90 4.9k excluding the field; ally_spawn_field median
   4.6k, max 40.8k). Now 5k plus full_field_cost_estimate() while the spawn field is missing. 100M
   identical on all sets; bench OOF in rounds 1-5 1,627→1,360 (round 1 633→490).

### A/B, rw-d (tip) vs fc6-m1, fresh-66301..66320, own drafts, 10,240 games
- 49.9% (CI 49.0-50.9): level. OOF 200,640 vs 203,481 (-1.4%). Fuel mean 52,433 vs 52,481, p99
  96,150 vs 96,050, at/over 100k 0.51% both. Shortcuts 4.48M vs 4.44M (farm-partial-evaluation
  2.77M vs 2.74M).
- batch_oof: 196,043 vs 198,919; runs of 1: 7,479 vs 11,798 (round-1 singles); 300+ 109k both;
  50+ games 101.9k vs 102.5k.
- rw-a alone (fc6run-a): 49.9%, OOF 204,352 vs 204,991, round-1 11,808 vs 11,797.

### Dropped
- Reusing blocked() as route walls when no act happened since: +0.02-0.03% beyond rw-a on most sets.
- The field estimate from the map extent (search_cost_estimate(max(w,h))) instead of
  full_field_cost_estimate(): rounds 1-5 OOF 1,391 vs 1,360, no better.

### Open
- Bank runaways: chase/prey and the veto's fight_of repeat identical work every other round; a memo
  keyed on the fight's inputs belongs with the stand/fight_of work.
- Cut-off-then-wider re-searches (22% of fresh-search fuel in the corridor jam): searching wide first
  when the last search of the same key was cut off would be exact only if the narrow answer is never
  read.
- The corridor deadlock itself (behaviour).
- Round-1 world init averages 68.5k (88k on OOF turns): static_camps 18.5k (25k on OOF turns),
  init_beliefs 11.3k, crossings 5-10k, hops. After 3, round-1 OOF turns end mostly past farm.cc's
  step check (48%: ally_spawn_field, plan, travel) or in world init (25%: hops, crossings).

## stand

Round 2 (fc6-stand, from 0eae0574). Nothing shipped: the one idea worked out, settle bounds for the fight sim, is exact but costs more than it saves. Its last form is in `stand-settled-s5.diff`.

### Census (main, real budget, osc+fight, 78 games; per OOF-first turn)
- veto (leaves_at) 19.6k at 1.67 calls; want_home's stand 15.3k.
- lv.reach 11.2k: build 4.4k at 2.8 calls, blow 4.8k at 8.5, distance 3.9k at 5.2.
- lv.trade 15.3k; f.trade 9.8k, about 7.3k a sim; st.trade 8.6k; f.fill 1.8k; s.lethal 2.2k.
- wh.camp_trapped 3.7k on 40% of turns.
- The sims themselves are about 2% of all fuel, but 8-10k on OOF-first turns.
- Veto sims end at exit 4 (self falls while all of theirs stand) 53% of the time, for 44% of their fuel (mean 3.7k, t≈7).

### Settle bounds (dropped)
A Python float32 port of simulate<true> (checked against 76.5k sims) was used to test exits that settle a sim before it plays out. They are proven by the order in which our side falls: without our shields or heals, or their Ren, we fall weakest first and a linked partner falls free.
- **B (falls_first):** their least damage by turn k passes what it takes to fell self, while our most damage stays short of their weakest. It fires on about 28% of veto sims, mostly at t=0.
- **A (outlives):** short_of against the damage needed to fell self. It fires on about 3-5%.
- **C (kills first):** no lost verdict. It fires on about 2% (1.6k of 70k).
- **D (B after their deaths):** about 1k fires.
- **All-fall fallback** for when our heals or shields break the order: +1.3k fires.

All versions gave identical replays at 100M, but every one cost more fuel than main (fight / osc):
- At every alive-change checkpoint, inside the loop (lambda): AB +0.62/+0.71%, ABC +1.40/+1.55%.
- Out of line (noinline settled()): AB +0.55/+0.62%, ABC +1.32/+1.46%. C also costs through the memo, because falls=true askers miss and recompute.
- At t=0 only, with cheap prefilters: +0.12/+0.15%.
- With the call present but disabled: +0.18% on fight. Only being in simulate costs about 100 fuel a turn on half of all turns (codegen).
- Gated off for want_home's own tile (s5): +0.03/+0.03%. It saved 11.7M on turns over 1k cheaper, but lost 7.4M on turns over 1k dearer, plus +3..12 on nearly every turn.

Cost per settled() call (fight, 100M), by how far the call got:
- 41k stop at m<0: 225 each.
- 31k stop at their-damage precheck: 362.
- 10k stop at damage_to_fell's order bail: 563.
- 24k get to least_dealt: about 1.23k each, of which 15k fire.

A sim it settles at t=0 would have cost about 1.3-3k. So it pays only when far more of its calls fire than here.

### camp_trapped (fight, 100M)
It runs on 33% of turns at 2.6k mean.
- 12.2k of 13.2k calls return at the `health > bound` test.
- camp_exit_way's field costs 1.5k on the 7% of calls that build one.
- exit_hits almost never runs.

So little is left to cut without changing what it decides.

### Open leads
- lv.reach's blow/distance repeats: 8.5 blow and 5.2 distance calls a turn on OOF turns. Sharing them across the veto's tiles would be exact; not measured.
- A settle bound pays only if it costs far less than ~1k per non-firing call, e.g. by reusing least_dealt's sums across one turn's sims of the same roster.

## share

Round 3 (fc6-share, from 192a6efb). Area: work repeated across a turn's consumers and across turns (the enemy
Reach, the recall continuation, round 1's world init). The duplication the round-2 leads pointed at is mostly not
there; one exact fix shipped, in the Reach's distance.

### Census (fc6-m2 instrumented, real budget, osc+fight+oof, 126 games, 9,321 OOF-first turns)
Probe labels relabel each call by whether a cache keyed exactly on what it reads would have answered it.
- **Reach builds**: 2.2 a turn, ~1.45k each. None is rebuilt within a turn (one Safety a turn, `reached_` per
  enemy; only `invalidate()` after a kill clears it: `rb.same_round` 0.004 a turn). Across turns, 11% of builds have
  inputs identical to the same enemy's previous build (`rb.same1` 0.23 a turn, 300 fuel), 2% to one of its last
  four.
- **Reach::at misses**: 4.7 a turn, ~600 each. Answerable from an earlier build with the same inputs, tile, ward and
  bush visibility: 6% (`rx.a1` 0.28 a turn, 160 fuel; older builds +45). The 64-slot memo never collides.
- **distance**: 3.8 calls a turn, ~700 each. Exact repeats of (from, p, act, dasher, limit) within a round: none;
  across rounds 0.74 a turn (434 fuel), same key with another limit 0.31 (185). A cross-turn memo is also awkward:
  `far` vs `limit + 1` depends on which walk steps earlier calls built.
- So the stand worker's lead (sharing blow/distance across the veto's tiles) is closed: within a turn the at() memo
  already answers every repeat, and distance has none.
- **channels** (continue_recall) 15.6k on 82% of OOF-first turns is want_home (`cr.home` 13.9k), whose verdict
  decide already reuses (`home`): nothing is computed twice. Of the rest only `wants_shop` is notable (855 a call on
  81%); decide asks it again only on the farm branch after the search, from a tile and health that may have changed.
- **Round 1**: world init 60k on these sets (static_camps 15.4k, static_boards 5.4k, crossings 7k when built,
  init_beliefs 10.4k, update 15k). Round-1 OOF turns here all end in the farm (38 of 83 in farm.post), not world
  init, so cutting world init mostly lets the farm loop evaluate more before its reserve, not run out less.
  - Fuel-stress maps (214 groups, 432 members): world init alone is ~187k of the 200k first turn, so every body runs
    out inside it. static_camps 113k (~100 a member, ~75 a group for the centre and lane reads, ~70 a group head),
    the draft plan's decode_steps 54k (~250 a group: the plan is not indexed at that size), crossings 25k. These
    are instruction counts (~2.5 fuel an instruction), not a hot spot; the A/B suites hold ~1% fuel-stress maps.
  - Round-1 OOF in the m2 A/B (rw-d batches) is spread over every map class, ~0.73 a game.

### Shipped
1. c9d232cc, enemy_reach's `walk_from` checks the slot last found for its key (a 64-entry hint) before scanning
   all 24 walks. The scan was ~470 of distance()'s ~680 a call (profile: the loop after it is ~1 iteration, ~210).
   A slot matches only once made and no two made slots share a key, so the hint returns the slot the scan would,
   with the same `used` update (fuel only). within() shares it.
   - 100M, all 9 sets: identical replays; total -0.01% (fs) to -0.45% (fight), -0.43% osc, -0.29% oof; p99 -1.0%
     fight, -0.9% osc, -0.5% oof; round 1 +3..10 fuel; round 2 mean 133,490 -> 133,486.
   - Real budget (indicative): OOF summed over the 9 sets 30,775 -> 29,072.
   - Census of the tip (same 126 games): distance on OOF-first turns 2,725 -> 1,721 a turn (miss 754 -> 541 a call,
     repeat 585 -> 251); census OOF turns 15,157 -> 14,262.
   - A/B `fc6share-a` vs fc6-m2, fresh-67201..67220, own drafts, 10,240 games: 50.2% (49.2-51.2). OOF 182,662 vs
     192,005 (-4.9%). Fuel a play turn mean 52,326 vs 52,377, p99 95,850 vs 95,950, at/over 100k 0.47% vs 0.49%.
     Shortcuts 4.33M vs 4.37M (turn-order 293k vs 302k, step-guard-entry 564k vs 571k, prey-cut-short 138k vs
     142k). batch_oof bot 1 vs bot 2: 178,758 vs 188,012; round 1 7,514 both, 2-10 12,651 both, 11-60 16,843 vs
     17,427, 61-300 42,247 vs 44,802, 300+ 99,503 vs 105,618; games with 50+ OOF 89,080 vs 96,294.

### Measured and dropped
- Cross-turn Reach reuse (keep a build's memo while its inputs, ward and bush visibility hold): ~460 a turn on
  OOF-first turns at most (above). Not built.
- Cross-turn distance memo: after the hint a repeat costs ~250, so ~250 a turn at most. Not built.
- `rank_turns`: 2.3k on 94% of OOF-first turns, 1.9k on 49% of heavy ones. Ranks really change on 82% of calls (our
  turn order reorders allies; the opponent's payload bits change its priorities). Profiled at ~0.7-1k a call once
  the probe's reads are taken out, spread over gather, sort and write: a rewrite would save ~300.
- Reach::build profiled (fight/osc, 51k builds): ally slots per round ~230, the occupied loop ~270, camp tiles in
  the window ~330 (90% of builds have one, so the tile sets are rebuilt), recipe check/ways ~260, next_turn_round
  and turns_before_ours ~200. No single part over ~350.
- Reach::at misses profiled: ~200 base, ~200 a way tested (1.2 a call), ~250 for the far sight shift.

### Open
- walk_from's miss path still scans the 24 walks for the oldest (~470): a compact `used` array would save ~200 a
  new walk.
- Fuel-stress round 1: static_camps and decode_steps scale with groups (~500 a group together); only a
  restructuring (fewer instructions a member, or an indexed plan at 200+ groups) would let a body act in round 1
  there.

## tail

Round 3 (fc6-tail, from 192a6efb = fc6-m2). Area: the work after a turn's last fuel check. Scratch `/tmp/fc6/tail/`.

### Where each OOF turn's budget broke (main, real budget)
Census: fc6-m2 with `instrument.py --fine --trace --lenient` (census.h now keeps the last passed check past the
printed window, and prints CLC/CLF lines for finished turns). 150 games against astraeus-d6e74b6 on the osc, oof and
fight sets plus the 20 maps with the most OOF in main's round-2 A/B (`/tmp/fc6/tail/cen-maps.txt`). 20.8k OOF play
turns, 12.2k traced. `py tools/fuel/census/tail.py DIR 1166 1169`:

| last passed check | OOF turns | % | fuel left there p50 | needed p50 | veto after it (turns / asks / fuel p50) | OOF inside the veto |
|---|---|---|---|---|---|---|
| none in the whole turn | 5,693 | 46.5 | - | - | 33% / 1.43 / 21.0k | 1,578 |
| farm.cc walk search (`funded`) | 1,393 | 11.4 | 28.3k | 15.4k | 88% / 1.97 / 18.7k | 697 |
| prey (fight.cc) | 1,266 | 10.3 | 43.4k | 36.9k | 81% / 1.53 / 16.0k | 757 |
| walk_on's approach (pathing.cc:389) | 1,108 | 9.1 | 25.2k | 11.8k | 94% / 1.49 / 17.4k | 783 |
| farm loop `room()` | 1,055 | 8.6 | 40.9k | 31.2k | 22% / 1.03 / 1.7k | 101 |
| static-descend (pathing.cc) | 954 | 7.8 | 23.6k | 15.1k | 84% / 1.61 / 15.5k | 526 |
| farm.cc cleared-group search | 405 | 3.3 | 22.4k | 15.8k | 60% / 1.29 / 3.7k | 102 |
| step-guard-sim | 171 | 1.4 | 45.8k | 38.0k | 88% / 2.27 / 23.6k | 95 |
| turn order | 112 | 0.9 | 11.2k | 10.0k | 0 | 0 |

- **The walk sites' tail is the work veto.** After farm's walk searches, walk_on's approach and static-descend the
  veto took 64-70% of the fuel left at the check (~1.5-2 asks); about half of those turns ran out inside it. Their
  checks kept back only `end_reserve` after the search.
- **The farm loop**: it ran in 31% of OOF turns and was cut in 22%. Cut, it had ~22k left against ~32k needed: the
  pass before overshot. Where its check was the last passed, the next pass cost 34.6k median (one group's cold
  facts: clear_fire_sort 14.6k in 74%, the static StandReach build 14.3k in 30%, min_camp_damage 6.1k, crew_work
  6.7k in 40%); 356 of 1,017 ran out inside it. Finished turns (CLF): after a cut loop decide spent 17.2k p50, 27.0k
  p90, 38.3k p99 against a reserve of ~25k beyond the floor.
- **No check passed at all (46.5%)**: 76% with 3+ enemies within 6. Every gate that ran had failed (step-guard-entry
  first in 2,386, prey 958). Phase costs (first entry to next): continue_recall + want_home ~25k mean, the strike
  search 31k mean (p90 56k), then the post-strike walk_on 21.7k p50 (last phase entered in 32%: descend plus veto).
  Nothing there reads fuel, so only cheaper or bounded fight work (FUEL-GATES rule 2) reaches them.

### Shipped (branch fc6-tail)
1. d0477e9c, **the work veto reads our own tile's leave only for a tile it would veto** (fuel only). `work_veto` is
   `!leaves(here) && leaves(tile)`; ~9 asks in 10 clear, so `leaves(here)` now runs only after `leaves(tile)` holds.
   Until the ally spawn field exists the old order stays (own_ground builds it on first need and farm prices by it).
   100M identical on all 9 sets; total -0.04% to -0.09%, p99 and over-100k slightly down, round-1 mean -0.1..-0.4%.
   Dearer only where our tile leaves too (fight max 368,355 -> 385,115: both stands now run).
2. 7da7a2bc, **the walk's searches keep back the veto's ask of their step** (real budget only). walk_on's
   `prepare_approach`, farm's two `funded`/`search` checks and static-descend add `Pathing::veto_reserve()` (0
   while no veto is set). Their fallbacks still step (and ask the veto), but skip the search. A/B vs (1) alone
   (tail-b), fresh-67101..67120: **50.3% (49.3-51.2), OOF 186,121 / 199,598 (-6.8%)**; static-descend 74k -> 134k,
   farm-no-route 53k -> 88k, crow-flies-farm 11.7k -> 19.6k. (fc5's v3, a flat 14k near-enemy reserve at these
   sites, was +1.2%: this one is the veto's measured ask, only while a veto is set.)
3. 1f120c80, **prey keeps back the veto's ask** (real budget only). Without prey the farm walks next, vetoed (the
   chase itself walks under the strike guard, unvetoed, so it reads `veto_cost()`, set or not). A/B vs (1)+(2)
   (tail-c): **50.0% (49.0-50.9), OOF 174,098 / 189,695 (-8.2%)**; prey-cut-short 160k -> 253k.
- Tools: d9385d0a, 15174407 (census.h's kept last check, CLC/CLF lines and the farm loop's dear passes; tail.py).

### Tip (tail-d = 1f120c80) against fc6-m2
- 100M: identical on all 9 sets; total -0.02% (osc) to -0.07% (wide, big); mean -14..-45 a turn; turns over 100k
  133,953 -> 133,680; round-1 mean -0.1..-0.4%.
- Real-budget benches, OOF summed over the 9 sets: 30,775 -> 26,901 (-12.6%; tgt 2,428 -> 1,606, osc 13,260 ->
  10,735, q 3,839 -> 4,183).
- **A/B, fresh-67101..67120, 10,240 games: 50.4% (49.4-51.3). OOF 174,323 / 201,647 (-13.6%).**
  - Fuel a play turn: mean 52,264 / 52,344, p90 86,550 / 86,650, p99 95,650 / 96,050, at/over 100k 0.46% / 0.51%.
  - batch_oof (shared gems skipped), tip / m2: r1 6,512 / 6,954, 2-10 11,345 / 12,123, 11-60 16,785 / 18,940,
    61-300 39,245 / 47,016, 300+ 95,862 / 111,290; games with <10 / 10-49 / 50+ OOF: 19,235 / 68,065 / 82,449 vs
    18,928 / 72,978 / 104,417.
  - Shortcuts without OOF 4.25M / 4.14M (+2.8%): prey-cut-short 248k / 155k, static-descend 130k / 73k,
    farm-no-route 89k / 52k, crow-flies-farm 19.6k / 11.7k, farm-partial-evaluation 2.62M / 2.64M, turn-order
    274k / 310k.
- Census of the tip (same 150 games): OOF play turns 20.8k -> 18.1k; the walk sites' and prey's classes halved
  (approach 1,108 -> 684, prey 1,266 -> 584, static-descend 954 -> 559), the farm search's stayed (1,393 -> 1,288,
  now ~2.1 asks after it), and no-check turns rose to 63% (6,954: gates that now fail).

### Dropped
- **Farm loop keeps back the next group's last cold pass** (`tail-cold-reserve-a3.diff` is the last form). Each
  group kept the fuel of its last pass that worked its clearing out; room() added it while the group's clearing was
  stale. Identical at 100M, but the per-pass bookkeeping cost +0.2..+2.4% (fs) until the measuring moved into the
  clearing block and a fast path (`ample_most`) took it to +0.04-0.06%.
  - a1 (whole pass from room()): **48.7% (47.8-49.7)**, OOF -4.1%, farm-partial-evaluation +27%.
  - a2 (a1, not our choice or claim): 48.3% (47.3-49.3), OOF -3.4%, partial +27%.
  - a3 (the clearing call only, not its first: the first also builds the static StandReach tables, and a1's
    measures of those kept a group out for good): 49.8% (48.8-50.7), OOF -0.7%, partial +5.5%.
  Cutting the loop sooner costs farm quality faster than it saves OOF (as campaign 4 found for its floors).
- **The walk sites keep back the veto's whole turn** (`tail-veto-turn-e6.diff`): `veto_tail()` = max(another ask,
  the dearest recent turn's asks less this turn's so far). Vs the tip: 49.6% (48.7-50.6), OOF -1.9%, shortcuts
  +77k (farm-no-route +47k, static-descend +30k).

### Open
- The no-check class (63% of OOF after this) is fight work with no check before it: want_home's stand (via
  continue_recall), the strike search, and the post-strike walk_on's veto. Only cheaper or bounded work reaches it.
- The farm walk search's class kept ~2.1 veto asks after it (the step guard is often skipped for fuel there, so its
  tiles reach the veto): a cheaper second ask would land there.
- Static StandReach tables (camps.cc `stand_reach`) built mid-game for groups never evaluated before: 3% of OOF turns
  hold one (~10-13k); building them in the turn-end queue would be exact.
- One group's cold clearing (clear_fire_sort's full sort when more than 8 members moved) is 14.6k on carpets:
  an exact incremental re-sort needs std::sort's tie order.

## big

Large maps and the opening (world init, static tables, mid-game static rebuilds). Base: fc6-m3 (`variants/fc6-m3r`).

### Shipped (fuel only, identical at 100M on all 9 sets and on `hopset`)
- **494099ad: hops share pockets and remember barren ones; the ring is listed by stamp.** `make_hops` re-flooded
  the same connected pocket for every altar / camp source in it, and listed the ring with `std::find`. A flood from
  any tile of a component under the same walls is that component, so a hop whose pocket already holds the source
  is copied with the new altar; a pocket with no landings goes into `barren_` (and the camp branch's static
  `barren`) and is never flooded again. Hops per body: topo-shortcut 644k -> 95k, backdoor 245k -> 144k, odd-spawn
  90k -> 73k, island 31.6k -> 19.6k.
- **a19d5f7a: `flood_into`.** A whole-map `reachable_tiles_into` costs `(layers+2)*span + chunks` with no cap
  (~169 a layer on 100x100); a distance field is capped at 40k. Where the map's layers would cost more, the hops'
  pocket / walk / camp floods, dash_flood's no-foot path and add_group_hop's `theirs` use the field (same set).
- Together vs m3 at 100M: q round 1 mean 316,405 -> 285,753 (-9.7%), p90 474,773 -> 430,224 (-9.4%), max
  1,146,735 -> 597,900; round 2 level everywhere; other sets' round 1 within +-0.05% (codegen). Real budget: q OOF
  3,728 -> 3,241; other sets level (+-8). Dearer turns: +20-42k on backdoor / shortcut / island are queue
  reshuffles (the cheaper first turn lets the queue warm more; backdoor-a team-a: -522k in round 1, -19k after).
- 10k A/B (big-b3 = tip vs fc6-m3r, fresh-67501..67520, own drafts): **49.9% (48.9-50.9)**; OOF 158,146 / 157,878
  (bot 1 census 154,692 / 154,424); round-1 OOF 7,030 / 7,112 (F 6,724 / 6,799); fuel mean 52,398 / 52,393, p90,
  p99 and >=100k level; shortcuts 4.373M / 4.370M. Topology maps are ~2% of those suites, so the A/B can only show
  it is level.

### Dropped
- **bank.cc's altar-walk flood through `flood_into`:** q round-1 p90 -2.1% more, but +23 a turn on almost every
  turn (+0.04% total on every set): bank.cc is flattened into farm_turn and the call changed its codegen.
- **enemy_reach `walk_from` with packed keys / `used` stamps** (24 slots, one u32 compare): identical but +0.02 to
  +0.09% total (oof, fight, osc worst): the hint path pays the key packing on every call.
- **crossings' striking-member board from the smaller side** (clear + set the strikers when fewer than half strike;
  camp_tiles is exactly the members' union, so exact): fs round 1 -0.6% (~3.5k), but +0.1 to +0.4% round 1 p90/p99
  on the other seven sets.
- **clear_fire incremental re-sort:** not exact (std::sort's tie order among clusters reaches decisions).
- StandReach builds in the turn-end queue: measured at real budget (osc+oof+tgt, ~540k turns), mid-game builds are
  ~2.2-2.6k mean and <=280 fuel a turn on average (round 1 3.5k a turn): too small for the reserve and ordering.

### Open
- fs world init is now the round-1 worst case: build_static to 223k (static_camps to 121k), init_beliefs to 39k
  (camps 25.6k, ChampionBelief ~750 each, mostly two board allocations), crossings ~29k, bush_cluster to 72k.
  fs plans carry no index (`write_index` needs used + fixed + steps_bits <= 8192), so decode_steps runs ~60k a
  body there.
- static_camps per-group overhead (~4k typical, 20-30k on fs): pre-read the kinds.
- bank.cc rebuild_altar_access's `std::find` over `a.blocks` per tile.
- `theirs` = foot() reflected by the symmetry: exact but rare (undrafted only).

## fight

Round 4, branch `fc6-fight` from 19508cb8. Target: OOF turns that pass no fuel check (63% of the 10,738 traced
OOF turns on the 150 census games; 4,593 of the 6,785 have 3+ enemies within 6).

Where the fuel goes on no-check OOF turns with ne>=3 (census and lap scopes, debug costs):
- want_home's stand_lost_at: 1.62 calls a turn at 18.5k (stand_reach 6.8k, stand_trade 11.5k, roster 1.9k,
  drawn_home 2.5k). The reach machinery under it: 21 blow calls a turn at ~475, 9 Reach::at misses at ~430.
- strike search: read 12.6-15k, grow 4-7k, price 11-13k a call. 53% of searches pick nothing (len 0). Its sims
  are ~0 a turn: step_guard fails at its entry gate.
- post-strike walk_on: 41% of turns, 21.8k a call. Its work veto is where the extra stands are: a vetoed ask costs
  10-13k; a cleared one ~1.9k (unstruck) or ~7.5k (struck).
- new_fight setup outside the trade: p50 4.4k (fill ~1.4k, build + fill + walk_allies_in ~3k).

Oracle: m3 with no veto on the struck branch's walk_on (`set_veto(nullptr)`) has 16,699 OOF play turns against
22,750 on the census maps at real budget (-27%). That is the most the post-strike veto can give.

Shipped:
- a28721f3 (not exact) `more_exposed`: after the strike search, where want_home kept us (stays_here), a work step
  that meets a strike our tile does not, or more blow damage (GuardFoes bound, then exposure, as no_worse), is
  refused without the stand. 17,684 post-strike asks are vetoed. Of the asks that fail this test, 70% are vetoed
  by the stand anyway (13,946 of 19,781, 260M fuel). Of the asks that pass, 12% are vetoed (2,633 of 21,622).
  It only adds refusals, so it can't send us where the stand would not: one verdict for stepping and leaving
  (337) stays the stand's for every step that is no more exposed. A/B fc6fight-p1 (10,240 games, fresh-67401..20)
  vs fc6-m3r: 49.6% (CI 48.6-50.5). OOF 155,180 vs 173,477 (-10.5%). At/over 100k 0.42% vs 0.46%.
  step-guard-entry 623k vs 590k, static-descend 110k vs 130k, prey-cut-short 229k vs 239k.

Dropped:
- Exact walk_allies_in table (an ally x enemy step row per Safety, filled on first need): byte-identical on all
  9 sets, but fuel went up 0.03-0.24% (fight +0.22%, osc +0.24%). Rows are filled for enemies the fights never ask
  about, and most Safeties make only one or two fights. Diff in /tmp only; not worth keeping.
- Skipping prepare_approach on a post-strike walk_on that can't move (47% of them): not exact. strike_after's
  goal_field reads approach_ready, and walk_on's fallbacks write memory.
- Per-turn veto-count caps: K=2 binds on 2.6% of turns with asks, K=3 on 0.78% at 4.5k a binding turn.
- Cheap pre-filters on "no enemy closer" or "no new strike in range": they catch 41M of 403M post-strike veto fuel
  and only 336 of 17,684 vetoes. The exposure test above separates them far better.

Open:
- The oracle's -27% against the shipped -10.5% (different samples: census vs fresh A/B). The asks that pass
  more_exposed still cost ~123M on census, and the cleared struck asks ~7.5k each. A cheaper exact "the stand
  can't move from here" (roster unchanged from want_home's stand, which StandsRead's no_worse almost covers) is
  the next lead.
- Unstruck asks (198k, 480M on census) are mostly cleared at ~1.9k: 96% pass more_exposed. Refusing their 4%
  would be the same rule outside the post-strike walk, untested.

Merge (round 4): a28721f3 not shipped. With 350-351 against d6e74b6f (fresh-67601..67640, 20,480 games) 49.0%
(48.3-49.7); against 350-351 alone 49.7% (49.0-50.4), OOF -11.3%. osc_detect on 2,048 traced games against v69: episode
turns +3.3% (pingpong +14%, stuck_fail +24%, jitter +13%, wander +10%), more episodes tagged `veto`; the fuel-only
350-351 moved the total 0.0%. The extra refusals are wasted turns (EXPERIMENTS "Fuel campaign 6, round 4").

## exact

Round 5, area exact (branch fc6-exact): the strike search and the work veto's stands, fuel-only. Census on 150
real-budget games (75 maps, `fc6-m4b` vs d6e74b6f), OOF-first turns with 3+ enemies near (~4.1k turns):
`st.lost` (stand_lost_at) 32.9k a turn at 1.85 calls, of which `s.new_fight` (building the sides) 13.6k and
`s.stand_reach` 8.8k (`s.blow` 24.9 calls a turn at ~420); `strike_search` 21.6k (`sp.read` 7.6k, `sp.price` 7.1k,
`sp.grow` 3.6k, `ss.aim`/chase_aim 1.4k); veto 13k. Ranged walkers with no strike made up 35% of searches and 31% of
search fuel (18.6k mean): a stay leaf and walk-alone leaves only, but read and grow ran in full.

Shipped (both byte-identical at 100M on all 9 sets plus `cen75`, the 75 census maps at 100M, 150/150; mean against
fc6-m4b: fight -0.6%, osc -0.6%, oof -0.4%, cen75 -0.5% (p90 -0.7%), other sets -0.0 to -0.1%; round 1 -0.1%):
- **walk-only search** (4660fd95): strike_free code 4 for a ranged walker with no foe in reach of any strike from any
  end tile. read() takes only health, Heart of Ruin and kill bits, and the root settles without grow. The ranged attack
  bound is now max(range, range + walk with a reset, range + dash with an attack): a ranged walk spends the attack and
  a dash takes the one cast. With the loose bound (attack + walk + dash) code 4 fired on 54% of rw no-strike searches
  (the misses were mostly at nearest foe 4-6); the tight bound took fight/osc from -0.09/-0.07% to -0.21/-0.21% total.
- **lazy stand walkers** (bf8df313): stand_reach takes the hits only; stand_walkers works out the walks
  (approach / enemy_reach::distance) only when the tile is hit or pursued. Unpursued and unhit, stand_roster drops
  every walker anyway. Total -0.26% oof, -0.41% fight, -0.42% osc, -0.35% cen75.

A/B fc6exact-t1 (ex-t1 = tip vs fc6-m4b, fresh-67801..67820, 10,240 games): 49.6% (48.6-50.5). OOF 159,429 vs
160,537 (-0.7%); mean fuel a turn 52,329 vs 52,442, p99 95,350 vs 95,450, over 100k 0.43% both; shortcuts 4.32M vs
4.38M (prey-cut-short 217k vs 230k, step-guard-entry 555k vs 573k). The cuts are exact but small next to the fight
sims that fill these turns.

Open:
- `s.new_fight` (13.6k a turn on OOF-first turns, ~12.9k a call): building the sides for each stand dominates
  stand_lost_at. Sharing sides across stands with the same roster (only the anchor tile differs), or building
  incrementally, is the next big lever.
- `s.blow` at ~25 calls a turn: blow(e, p) per seen enemy per stand tile; a per-turn table keyed on (enemy, tile)
  would cut the repeats between want_home, the veto and the search.
- rd.foes (3.6k a call) in full searches still reads every foe's stun, stop and partner fields, even for foes beyond
  every strike tile's reach.
- chase_aim made lazy is not trivially exact: the pack zone snapshot reads `world.me().pos` at the round's first query.

Merge (round 5): 4660fd95 shipped (CHANGES 352), bf8df313 not. On 20,480 games against d6e74b6f (fresh-67921..67940,
fresh-66001..66020), paired by game against fc6-m4b's run: 4660fd95 alone +0.21 points (-0.22..+0.63), OOF -1.4%;
bf8df313 alone -0.73 (-1.42..-0.04), OOF +1.4%, though identical at 100M (EXPERIMENTS "Fuel campaign 6, round 5").

## audit

Round 5, branch `fc6-audit` from 3a53f03f. Question: did the real-budget reserves (342, 345, 348, 349) bring back the
wasted turns 337 removed (round 4 read d6e74b6f -> m3 +4.6% episode turns on gen + gen-s1)?

Method: traced copies (`trace.patch` here: osc-int-trace's hooks, adapted to 3a53f03f) of d6e74b6f, fc6-m1, -m2, -m3,
main (= m4b) and main with reserves reverted (`noloop` = 342+345, `no345`, `no348`, `no349`, `noall` = all four),
each against `baselines/v69` on fresh-67701..67720 (10,240 games, own drafts, `CAMBC_LOG_LIMIT=16000000`), real budget;
d6e74b6f, main and noall also at 100M. `osc_detect.py --bridge-oof`, compared with `tools/replay/osc_compare.py`
(paired by map and side; CI = bootstrap over games).

**The detector undercounted bots that run out of fuel.** An OOF turn prints no D line (the line is missing on that
round or the next), and `runs()` split the champion's run there: 7,426 of 7,590 OOF turns in round 4's m3 gen batch
broke a run, so 30-turn windows (claimflip, retreatchurn) never spanned them. `--bridge-oof` joins runs across those
rounds. Round 4's own data bridged: d6e74b6f -> m3 +4.6% -> **+0.7%** (+0.2% counting OOF turns as wasted), retreatchurn
+9.3% -> +0.9%. On the 10k games: main vs d6e74b6f +6.1% unbridged, +2.0% bridged, +1.4% counting OOF turns.

Episode turns, bridged (10,240 games; `all+oof` adds each OOF turn as one wasted turn):

| kind | d6e74b6f | m1 | m2 | m3 | main (m4b) | main + fix | noall | d6e74b6f 100M |
|---|---|---|---|---|---|---|---|---|
| claimflip | 4,662,125 | +0.7% | +1.0% | +0.9% | +1.0% | +1.0% | -0.3% | -11.3% |
| retreatchurn | 3,671,669 | +2.3% | +1.8% | +2.6% | +2.7% | +2.2% | +0.7% | +1.8% |
| goalflip | 2,321,417 | +0.7% | +0.7% | +1.3% | +1.4% | +1.1% | -0.2% | -3.4% |
| branchflip | 1,451,800 | +1.3% | +0.7% | +0.6% | +0.7% | -0.2% | +0.3% | +2.1% |
| wander | 523,332 | +1.1% | +0.7% | +1.9% | +2.1% | +1.1% | +0.6% | +6.1% |
| stuck_idle | 381,048 | +0.8% | **+9.5%** | +7.9% | +7.9% | +1.5% | +2.3% | -0.5% |
| stuck_fail | 218,679 | +3.5% | +2.5% | +9.4% | +8.2% | +3.4% | +3.5% | +4.6% |
| pingpong | 210,759 | +4.3% | +1.9% | +6.2% | +5.8% | +2.9% | +1.0% | +10.3% |
| jitter | 182,074 | +3.0% | +0.2% | +4.8% | +4.2% | +2.8% | +0.9% | +9.3% |
| preyflip | 40,853 | +5.4% | +2.7% | -0.3% | -1.4% | -0.8% | +2.2% | +18.4% |
| all | 13,663,756 | +1.3% | +1.4% | +1.9% | +2.0% | +1.3% | +0.3% | -3.1% |
| OOF turns | 226,783 | -17.1% | -19.6% | -33.4% | -33.5% | -33.0% | -18.4% | 0 |
| **all+oof** | 13,890,539 | +1.0% (-0.0..+2.1) | +1.1% (-0.0..+2.1) | +1.3% (+0.2..+2.4) | **+1.4% (+0.2..+2.5)** | **+0.8% (-0.3..+1.8)** | -0.0% (-1.0..+0.9) | -4.7% |

Each change reverted from main (all+oof vs main, 95% CI; OOF vs main):

| reverted | all+oof | OOF | read |
|---|---|---|---|
| 342+345 (noloop) | -1.43% (-2.39..-0.49) | +7.2% | the whole rise |
| 345 | -0.73% (-1.38..-0.09) | +1.3% | a livelock (below) |
| 342 alone (noloop vs no345) | -0.70% (-1.60..+0.17) | +5.8% | not significant |
| 348 | +0.37% (-0.53..+1.30) | +9.2% | no gameplay cost |
| 349 | +0.19% (-0.56..+0.96) | +7.6% | no gameplay cost |
| all four | -1.40% (-2.39..-0.34) | +22.7% | |

At 100M d6e74b6f, main, noall and main + fix give identical episode counts (every kind, 4,096 games): all
differences are fuel. Fuel shortage itself costs d6e74b6f +4.7% wasted turns against unlimited fuel.

**345's livelock** (fixed, 0ea39f0f, real budget only). While no veto ask was measured, the farm loop kept back 5k plus
a full field (the ally spawn field own_ground builds). With no group yet, weighing the first one may need a field from
here (`fuel_ok(full_field_cost_estimate() + loop_floor + loop_reserve())`): two full fields never fit on some large
maps, so no group is chosen, nothing walks, the veto is never asked and never measured, every turn. On
gen-gem-drought-6770405800 and gen-topo-shortcut-6770806907 all four champions sat on spawn from round 1 to the end
(farm-partial-evaluation every turn, fbest -9; 4 of 10,240 games, all lost; d6e74b6f won both gem-drought games).
m2 (345) is where stuck_idle jumps. The fix keeps the first ask back only for a group to walk to (`g >= 0` in
loop_reserve); later passes still keep it, so 345's opening reserve stays for the walk it protects.
- Rerun (fastrunner, tr-fixa vs v69, gem-drought -12): 215-257 moves per champion in rounds 1-300 (main: 0).
- Gameplay: main + fix vs main -0.63% (-1.14..-0.11) all+oof; vs no345 +0.11% (-0.54..+0.80); stuck_idle 411k -> 387k,
  stuck_fail -4.5%, pingpong -2.7%. Opening livelocks: 0 games (main 4; the 6 mut-gift-wrapping ones are every
  version's).
- 100M: identical (4,096 traced games, every kind).
- **A/B vs fc6-m4b** (`fc6audit-a`, fresh-67701..67720, 10,240): **49.9% (48.9-50.9)**; OOF 153,565 / 153,359; round 1
  7,853 / 6,954 (the first group of the opening is now weighed without the reserve), 2-10 11,197 / 11,565; fuel mean
  52,144 / 52,102, p50 51,350, p90 86,550, p99 95,250, at/over 100k 0.41% both; shortcuts 4.27M / 4.26M
  (farm-partial-evaluation 2.618M / 2.594M, static-descend 114k / 120k).

### Open
- 342's measured loop reserve: -0.7% wasted turns if dropped (CI crosses 0) for +5.8% OOF; its share is in claimflip,
  retreatchurn, goalflip and branchflip (a loop cut shorter weighs a different set of groups turn to turn). Not worth
  dropping on this evidence; a tighter reserve (only where the walk's landing is not already in the veto's cleared /
  vetoed boards) is the lead if a 20k run shows it.
- Remaining main + fix vs d6e74b6f: +0.8% (CI -0.3..+1.8) all+oof, with OOF -33%.
- Earlier rounds' osc_detect numbers (round 4's table, the oscillation streams' before/after) split runs at OOF turns:
  a change that cuts OOF reads as more episodes there. Rerun with `--bridge-oof` before relying on small deltas.

## init

Round 1 world init (fc6-init, from f82443d1; candidate init-a = db53f659). Fuel only. All 9 sets and fsx (20 fuel-stress
and 8 huge maps, area 8000+, from fresh suites outside 66000-68999: `replays/fuel/fc6/fsxset.txt`) give byte-identical
replays at 100M.

Where a fs body's ~229k world init went (6 bodies, profiled with raw-fuel probes): static_camps ~113k (member loop ~97k
at ~105 a member, the layout count walk 6.7k, resize 11k), plan decode ~54k (fs plans are indexed with no fixed steps,
so decode_steps runs at build), crossings ~25k (dashers), init_beliefs ~38k (camps 24.5k, champions 7.5k, health 5k),
boards ~7k. Now it is ~201k: a fs body still cannot finish round 1 inside 200k, and at 100M fs round 1 is ~580k a
body (decide ~300k), so no init cut gets fs bodies acting in round 1.

**Shipped** (one commit each):
- 7027112c decode_bounded and the offsets loop keep the reader, Rice parameter, boxes and data pointers in locals
  (clang reloaded them through `this` every group): fs ally 25.2k -> 23.7k, altar 14.0k -> 12.8k, offsets 13.8k -> 11.7k.
- 6ec794a8 build() takes the group count from `sdk_map_num_camp_groups` and derives the member count from the
  layout's length (the old walk stays as fallback if they disagree): fs -6.6k a body.
- 6e3073a1 find_crossings, with 24+ groups: dilate the crossable tiles (squares of radius 2 when few, else
  square_dilate), AND with camp_tiles, and test only those (up to 128) for striking groups, instead of copying
  camp_tiles, clearing every non-striker and dilating; fewer groups keep the old form (it is cheaper there). fs
  crossings 25k -> 13-15k a dasher, elk-arena -1k; small maps level.
- db53f659 `UnwrittenAllocator` for `groups` and `camps`: resize no longer runs the default member initialisers, build
  placement-news each group, and init_beliefs writes each 104-byte CampBelief with v128 stores from one prototype
  (memcpy compiles to memory.copy, 1 a byte). init_beliefs camps 24.5k -> 19.8k on fs.

Bench, m5b (fsx: init-m5b) -> init-a, 100M:

| set | round 1 mean | p90 | max | round 2 mean | total | dearer turns |
|---|---|---|---|---|---|---|
| wide | 230,722 -> 229,264 | 293,373 -> 291,929 | 516,327 -> 512,730 | 110,766 -> 110,786 | -0.004% | 227 (440 cheaper) |
| oof | 251,258 -> 248,480 | 370,096 -> 361,216 | 452,654 -> 448,987 | 122,258 -> 122,203 | -0.005% | 81 |
| mg | 249,277 -> 246,859 | 330,809 -> 323,031 | 443,947 -> 436,169 | 122,041 -> 122,079 | -0.006% | 59 |
| q | 285,759 -> 283,534 | 430,224 -> 424,796 | 597,905 -> 587,306 | 147,668 -> 147,645 | -0.004% | 76 |
| big | 284,098 -> 281,330 | 383,215 -> 377,867 | 476,145 -> 472,502 | 160,048 -> 160,048 | -0.005% | 2 |
| fs | 607,449 -> 578,852 | 676,939 -> 644,275 | 742,515 -> 709,952 | 280,010 -> 280,010 | -0.045% | 0 |
| fight | 199,389 -> 198,717 | 213,237 -> 212,772 | 315,420 -> 310,589 | 91,312 -> 91,248 | -0.001% | 56 |
| tgt | 249,705 -> 248,186 | 297,667 -> 295,041 | 355,497 -> 352,871 | 114,946 -> 114,934 | -0.004% | 22 |
| osc | 205,798 -> 205,315 | 238,324 -> 236,377 | 319,989 -> 317,363 | 97,001 -> 97,035 | -0.001% | 182 |
| fsx | 504,993 -> 485,474 | 667,351 -> 636,331 | 799,727 -> 772,406 | 230,916 -> 230,916 | -0.035% | 0 |

Dearer turns are a few fuel each: the frozen copies' codegen moves outside init. Real budget, round-1 turns at the 200k
cap: wide 31 -> 19 of 245, mg 34 -> 32, q 121 -> 113, big 90 -> 91, oof 83 -> 88, fight 10 -> 11, osc 25 -> 24, tgt 26
-> 26, fs 140 -> 140 of 140, fsx 291 -> 290 of 318. Real-budget games diverge, so their OOF totals are game noise.

**A/B** `fc6init-a` vs fc6-m5b, fresh-68101..68120, 10,240: **49.5% (48.6-50.5)**. OOF 160,548 / 157,701 (ab.py);
batch_oof round 1 7,274 / 7,751 (-6%), 2-10 10,387 / 10,524, 11-60 15,395 / 15,440, 61-300 36,737 / 36,173, 300+
85,857 / 82,871. The whole late excess is one game: gen-leaky-diagonals-6811007814 with init-a as A runs 2000 rounds at
~1.4 OOF a round from round ~450 (2,165 OOF; m5b as A wins in 534 with 15), bodies overrunning every turn in
step-guard / static-descend on branch B. Without it, OOF is +0.5%. Fuel per turn mean 52,293 / 52,306, p50 51,650,
p90 86,550, p99 95,350, at/over 100k 0.43% / 0.42%. fsx both sides (56 games): 42.9% (30.8-55.9), OOF 3,039 / 3,098,
round 1 289 / 291, mean 81,566 / 81,219.

**Dropped** (numbers on the fs profile maps):
- `camps.assign(n, prototype)`: 39.4k vs 37.75k. A trivial Raw constructor plus memcpy: much worse (memory.copy).
  Hand-written v128 with emplace_back: ~111 a group. Only the allocator that skips construction paid.
- Writing camp_tiles' storage words directly instead of set_tile: +8.6k on fs. A linear bit buffer plus
  ImportLinearBuffer: +3k. Host calls of few arguments cost ~13-16 ops; set_tile is near the floor.
- The first crossings form on every map: small maps regressed, partly `vec2 near[64]` writing every element (vec2's
  member initialisers, ~1k); hence the union buffer and the 24-group switch.
- Reading every camp type's stats before the member loop instead of testing a bit per member: fs -12k static_camps,
  but elk-arena +1.8k and atoll +2.2k (kind_of on unused types costs more than the tests save on small maps).
- Lazy altar steps (init-b: altar section moved after the offsets, decoded on first ask or warmed after round 1;
  plan version 10): identical replays, fs round 1 -5k more, but the per-call check makes 14k (fs) to 25k (fsx) turns
  dearer and fs total +0.046% against init-a; round 1 asks some body's altar steps on every profiled map anyway.
- Replacing draft ally steps with the spawn field: changes play (farm prices by a bound until the field exists).

**Open**
- The leaky-diagonals overrun state: reachable from m5b's code, not this change (identical at 100M); a fuel lead
  for step-guard / static-descend.
- fs member loop ~105 a member is near the floor; init_beliefs still ~93 a group (constant v128 stores with address
  adds, plus per-group f32.select slices).
- rebuild_altar_access's std::find (round 4's item): not taken; bank.cc is flattened into farm_turn.

## sides

Round 6, branch `fc6-sides` from f82443d1 (fc6-m5b). Area: the fight sides each stand builds (`new_fight`) and the
blows behind them. Nothing shipped: every repeat the leads assumed is already caught, and what is left is each
turn's first use of fighters, Reach and sims, which no exact cache removes.

### Measured (cen75 = the 75 census maps, `/tmp/fc6/tail/cen-maps.txt`, vs d6e74b6f; fuel deltas read inside
`debug_block`, ~18 a pair)
- **`s.new_fight` is mostly the sim, not the sides.** On real-budget OOF turns (13.9k turns), per `new_fight`: sim
  (`trade`) 8.5k; setup ~4.1k = `make_slot` 1.7-2.3k (~6 fighters made a fight at ~350-375 each, almost all of them
  the turn's first use: 0.8-1.1 fights an OOF turn), the two `fill` copies ~0.8k, `walk_allies_in` 1.6k
  (`next_turn_round` ~45 and the strike memo ~110 an ally). `make_fighter` compiles to ~150 straight-line instructions:
  no fat.
- **Within a turn no sim repeats.** Keyed exactly on the sides' content (every fighter field, kit contents, camp,
  `they_first`): 0.03% of 435k sims at 100M repeat an earlier sim of the same turn, 0.12% (0.19% of sim fuel) ignoring
  the `falls` / `settle` flags. Safety's (key, late) memo already answers the rest; distinct rosters (anchor tile,
  allies within 4) really are distinct fights.
- **Across turns 6.5% repeat** (5.6% of sim fuel at 100M, mean age 1.9 turns; 9.3% of sims on OOF turns). A content
  key costs ~400-500 a sim (~110 words to hash, a compare on hit) against ~280-330 saved on average turns and ~700 on
  OOF turns. Not built (an earlier campaign dropped cross-turn fight memos for the same reason).
- **`blow` repeats: none to share.** Census (5,885 OOF-first turns with 3+ enemies near): 22.4 `blow` calls a turn;
  ~13 end at the Strike-square bound (~100 each), ~9 reach `Reach::at`, whose memo answers repeats; the rest of
  `s.blow`'s 450 a call is first-turn Reach builds (2.75 a turn at 1.65k). This matches round 3: a per-turn
  (enemy, tile) table has nothing left to catch.
- **No allocations** in the stand path: `Side`, `StandReach`, `StandRoster` and `StandsRead` are fixed arrays.
- **`stand_reach`** (2.06 calls an OOF turn at ~5k): `fight_reach` 0.9k a call (the turn's first `strike_foe`), hit
  enemies' approach 1.7k (mostly first Reach builds), the walks 1.55k, the rest ~0.8k. 45% of calls find no hit. The
  walks on unhit, unpursued tiles are round 5's lazy walkers (bf8df313, not redone).
- **The veto's asks on OOF turns** (12.5k turns): 0.78 asks a turn, 0.53 vetoed (68%). Stand exits per OOF turn,
  want_home / veto tile: no fight 0.37 at 6.5k / 0.14 at 4.8k; StandsRead 0.00 / 0.21 at 4.6k; sim 0.46 at 25.6k /
  0.45 at 18.2k; out of sight 0.07 / 0.05 at ~1.4-2k. `leaves_here` almost never runs (`stays_here`).
- **`drawn_home`** (1.47k a call): the round's pack members on first use, then cheap per-tile tests.

### Tried and dropped
- `walk_allies_in` reading the fight's enemies once (and returning at an unseen enemy, where every ally's walk is 0
  and no arrival changes): identical at 100M on fight, osc and cen75; total -0.00% / -0.01% / -0.01%, more turns dearer
  than cheaper. The first form (a `std::array<vec2, 16>`) was +0.07% everywhere: `vec2` zero-initialises, 128 bytes a
  call.

### Open
- The levers left are not in the sides: the sim itself (8.5k a fight on OOF turns; earlier rounds found additions
  inside it read dearer through codegen), and the number of stands that reach a sim (0.91 an OOF turn, a
  decision-level change).
- `rd.foes` (3.6k a full strike search): viewers ~760 a turn, partner ~420, the rest small; reading them per foe only
  when a strike tile can reach it is at most ~1k a search.
