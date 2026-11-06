# Fuel campaign 7 notes

Brief: [BRIEF.md](BRIEF.md). Base astraeus 5166d1c5 (`bots/variants/astraeus-5166d1c`). Each worker appends a
`## <area>` section on its branch; the merge agent keeps the merged file.

## fight

Branch `fc7-fight`. Target: OOF turns that pass no fuel check (strike search, `stand_lost_at`, step guard).

### Where the fuel goes (OOF-first fight turns, fine census, 56 games vs base at real budget, ~850 turns)

Per turn, inclusive:
- `stand_lost_at` 21.8k: `stand_reach` 7.9k (approach 4.8k: blows and Reach builds), `stand_trade` 10.4k
  (sim 7.5k, `fill` 2.4k at 1.2k a call, `walk_allies_in` 1.0k), lethal ~0.9k.
- strike search 25k: `Search::read` 9.8k (foes 2.5k at ~920 a foe in attack reach; `read_geometry` 4.9k with
  the guard cover), grow 6.7k (~1k a node), price 5.9k.
- step guard cover 3.2k, pack zone 2.7k (members 2.1k, unseen boxes 0.8k).

About one sim a turn: `fight_of` almost never hits, so fights repeat little within a turn. The sim already ends
trivially safe or lost fights at once (`cap.short_of`, `overwhelmed`), so the 7.5k sims are real fights. Foes
past attack reach in `rd.foes` are 0.14 a turn, so a tighter read reach is worthless.

### Shipped

- **21e8c139: `stand_lost_at` reads walks and pursuit only when its roster reads them.**
  - `stand_reach` now tests only the hits (approach()'s 0). The seen walkers' `enemy_reach::distance` waits for
    `stand_walks`, which runs only with a hit or a pursuit: without either, `stand_roster` drops every walker
    (walk >= 1 > approach 0).
  - `pursued` (`paying_soon`, `own_ground`) is read only when a walker could be kept by it. It is still read
    while the spawn field is unmade, as before.
  - A roster with no fight returns before `lethal()` is asked for `falls` (`stand_trade` returns `{}` there).
  - Every skipped call is a pure read or a memo.
  - 100M: identical on all six sets. Total fuel -0.04% (big) to -0.13% (heavy). Over-100k turns: def 704 to
    698, wide 3086 to 3068, pool 9367 to 9244, big 2523 to 2515, heavy 5556 to 5498, td 2744 to 2717.
  - On turns the base spent over 100k, the mean saving is 106-249 (pool -249, heavy -216, td -217). It fires
    at 1k or more on ~12% of them (p1 -2.4k to -3.3k). Dearer turns: p90 +170-210, under 0.5% at +1k.
  - Round 1 unchanged. p99 -0.04% to -0.2%.
  - Real budget (indicative): OOF pool 770 to 746, big 248 to 238, heavy 707 to 640, td 209 to 248; 1934 to
    1872 in all.
  - 10k A/B (`fc7-w`, real budget) against the base: 50.4% (CI 49.4-51.3), OOF 72,725 to 73,036 (-0.4%), shortcuts 2.223M to 2.247M,
    mean fuel per turn 51,118 to 51,125.
  - A first version that re-asked the blow in `stand_walks` had dearer p90 +324 on heavy turns. `walk_in`
    (approach past its blow test) fixed that.

### Dropped

- **Memoising `lethal(q)` per tile in `step_guard`'s last loop** (it asks twice on a k == 2 tile that falls):
  identical, but dearer everywhere. Total +0.00%, over-100k turns mean +17 to +32, with 2 turns of 9948 at 1k
  or more cheaper. The repeat is rare and the lambda costs on every tile.
- **Not tried, by reasoning:**
  - A `turns_before_ours` memo: already about once per Safety per enemy.
  - Skipping Reach rebuilds within a turn: `sets_reusable_` covers it.
  - A per-tile blow cache: `Reach::at` has one.
  - Moving `paying_soon` before `in_pack_zone` in `outmatched`: `rounds()` is read anyway, but
    `may_reach_within` would run on the common no-pack path.
- **Lazy unseen members in the pack zone** (~0.8k on 28% of fight OOF turns): left out as not provably exact.
  The zone outlives Safety rebuilds (`see_stuns`, `see_kills`), and the turn end changes `possible` before the
  queue's farm reads the zone, so a late resolution reads other inputs than the base's.

### Tools (scratch, not committed)

- `/tmp/fc7/fight/rt/runner`: a copy of the fast runner whose translator charges each fuel flush to its wasm
  function. It calls `fr_prof` at fuel flushes and `fr_enter` at entries, splits turns at the `yield` import,
  and skips fuel paused through `fuel_pause`/`fuel_resume`.
  - Its output is self fuel and calls per function on heavy and fight-heavy turns.
  - `fpan.py` reads it.
  - The per-offset line mode undercounts inlined code badly (`plan_strikes` is flattened), so it is not to be
    trusted below function level.

### Open

- Rebuilding Safety after our stun (`see_stuns`, `see_kills`) remakes fighters, strikes, members and threats.
  `read_stuns` changes only the stunned enemies, so a reuse keyed exactly on the changed beliefs could save
  ~2-3k on stun turns. Needs care: our own state (health, cooldowns) also changes after the hits.
- `Search::read`'s full foe read (~920 a foe): `kill_stops`, `stun_worth` and `partner_bound` could be read on
  first use by a leaf.
- `__cxa_allocate_exception` runs ~0.9 times per fight-heavy merged turn. These are presumably the stale-turn
  throws after an OOF, charged to the next turn; unverified.

## farm

Worker: farm turns and big maps. Branch `fc7-farm` (1f7d0344, c1a1e46d); frozen tip `variants/fc7-farm-h`.

### Where the farm loop's fuel went (base, real budget, bigR + heavyR)
- **The flood from here.** Until warm_centres has every centre field (rounds 2-60 on big maps: the queue
  rarely has the ~47k its floor and field estimate need), each farm loop that needs our steps to a group
  without a centre field floods a whole field from our tile (`from_here`, 18k median, 95 layers on 100x100)
  and throws it away. bigR: 1,932 such loops in 32 games (one in three cut), 3.4 groups read it a loop; only
  850 distinct (champion, group) pairs over all of them. Census: make_field 12.8k a heavy big-map farm turn
  (63% of them). None of these groups is pruned by distance, even with the exact steps (14 of 6,557).
- Loop stages (round > 60, debug fuel brackets; non-banking / banking, per loop): ~23 / 20 groups, 14.7k /
  20.6k a loop. Cut at the pre-facts bounds ~12 groups at ~250 (20% / 13%); valued 1.8 / 3.8 groups at ~1.9k
  (23% / 37%); trip/respawn stage 1.3 / 2.9 at 1.1k; claimed branch ~1.8 at ~2.6k (bound 1.7k incl. the crew
  table's first read, crew_work 2.5k, plan_crew 5.5k). No single repeatable part dominates.

### Shipped (identical at 100M on def, wide, pool, big, heavy, td)
1. 1f7d0344 + c1a1e46d: **the loop's first two groups without a centre field make theirs** (pathing.centre_field,
   kept for good: the same steps by walking symmetry) in place of the flood from here; a third floods as before.
   Groups that read the flood are marked (`want_centre`) and go first in the next warm_centres. Same flood count
   for K <= 2 groups (one centre + the flood before), one more for K >= 3, and fields are work the queue does
   anyway. Not on the first turn (round-1 p99 rose 1% with it there).
   - 100M vs base: total fuel -0.10% (wide) .. -0.6% (big, p50 -1.5%); p99 -0.2..-0.8% (big 104,092 ->
     103,256, pool 107,853 -> 106,307); turns over 100k 23,980 -> 23,100 (-3.7%); round 1 unchanged; max up on
     big (287k -> 333k), pool, heavy: early turns making two or three fields.
   - Real budget benches, OOF base -> tip: big 248 -> 221, heavy 707 -> 629, pool 770 -> 721, td 209 -> 192
     (1,934 -> 1,763, -8.8%); farm-no-route 1,456 -> 1,096, crow-flies-farm 905 -> 593; farm-partial-evaluation 34,454 -> 34,598.
   - **A/B fc7-w (10,240 games), farm-h vs 5166d1c: 50.3% (49.3-51.3), OOF 71,316 / 72,708 (-1.9%)**; OOF rounds
     2-10 4,765 / 6,131 (-22%), runs of 50+ OOF 814 / 1,345; fuel mean 51,094 / 51,164, p99 92,650 / 92,950;
     farm-no-route 28.6k / 37.0k, crow-flies-farm, farm-kept-target down; farm-partial-evaluation 1.048M /
     1.039M. The first-group-only form (farm-d): 50.4% (49.4-51.3), OOF 71,320 / 72,557.

### Dropped
- warm_centres with the farm-wanted groups first, alone (farm-a): identical, OOF level (bigR 248 -> 241): the
  queue almost never has the fuel for a field in those rounds. Kept as part of 1.
- Centre field only while the fuel also pays for the flood (2x full estimate + reserve): fired on 114 loops of
  1,932 (bigR), no gain.
- warm_centres' field estimate min(field_cost_estimate, full_field_cost_estimate): identical, no change at
  all (the costliest field already makes the bound as large).
- kept_steps tolerating 12 changed tiles, not 4 (route recomputes: 19k of 84k bigR searches had 5+ changed
  tiles): identical, but +0.14..+0.25% total and more turns over 100k (the extra checks rarely save a search).
- A second kept route per crossing mode for other goals (35k of 84k route searches had other goals than the
  kept route; 30% of those matched goals searched 1-7 searches earlier): identical, +0.2% total on every set,
  round 1 +0.2%: the alternate rarely passes kept_steps (its walls are older), so its check is mostly cost.

### Open
- K >= 3 loops still flood from here (sim on base data: ~230 of 1,932 bigR loops); a third centre field
  instead saves little more (944 -> 891 builds in the sim) for a third field's spike.
- Route searches in farm.post on big maps (route 12.5k + p.route 5k self a heavy turn after round 60):
  goals-differ is the main recompute cause (42%), then 5-11 changed wall tiles; an exact reuse needs the
  label readers (step_field's cap, travel's l.d, route_label) to see the same field as a fresh search.
- The claimed branch's plan_crew (5.5k a call, ~0.3 a loop) and the crew table's first read.
- `fc7-w`, `fc7-m`, `fc7-f` merged dirs held one broken `*.map26a` link (made before the suites existed);
  fc7-w was relinked to its 5,120 maps by this worker, fc7-m and fc7-f still need it.

## merge 1

Merged `fc7-fight` (21e8c139) and `fc7-farm` (1f7d0344, c1a1e46d) as CHANGES 424; nothing dropped. Frozen as
`bots/variants/fc7-m1`.

Review:
- fight: `stand_reach`'s new hit test is approach()'s only 0 (its lost-turn branch returns 1 or more), and
  `stand_walks` gives every pending walker approach()'s value (`walk_in` is approach past its blow test). Without a
  hit or a pursuit, `stand_roster` drops every walker (walks >= 1 > 0), so the walks and `pursued` are unread; with no
  roster, `stand_trade` returns `{}` (not lost, no fall), so skipping `lethal()` gives the same false. The skipped
  calls are reads or exact memos.
- farm: `centre_field` floods the same static walls (`blocked_for_us`, `dash_walls` or `landing_dash_walls`) as
  `from_here`, uncapped. Those walls are impassable tiles, the enemy spawn and crossable holes and altars only, so our
  tile and a camp centre are always open, and the king-step graph over open tiles is undirected (corner rule):
  `centre->at(here) == from_here->at(centre)`. Neither reads allies, camps or dynamic blockers. Each extra field
  is behind the same `fuel_ok(full_field_cost_estimate() + loop_reserve())` as the base's one flood, so the higher
  100M max (2-3 fields on early turns) can't make a new out-of-fuel turn class at the real budget; round 1
  (`opening`) is untouched. There is one real-budget difference: a second group whose check fails now `break`s
  where the base read the flood it already had. This doesn't change play at 100M and the A/B is level.
  `want_centre` bits clear only once their group's field is made (a `return false` keeps the current bit), and
  centre fields never change, so the bits can't go stale.

100M, all six sets byte-identical to `base-*-100M.json` (`m1-*`):

| set | total | mean | p99 | max | over 100k | round 1 mean |
|---|---|---|---|---|---|---|
| def | -0.32% | 51,433 -> 51,265 | 97,736 -> 97,593 | 215,787 -> 215,897 | 704 -> 693 | -12 |
| wide | -0.19% | 50,497 -> 50,400 | 103,147 -> 103,099 | 268,444 -> 266,018 | 3,086 -> 3,079 | +22 |
| pool | -0.42% | 53,464 -> 53,237 | 107,853 -> 106,012 | 356,280 -> 372,173 | 9,367 -> 8,454 | +4 |
| big | -0.70% | 61,397 -> 60,969 | 104,092 -> 103,159 | 287,312 -> 332,533 | 2,523 -> 2,355 | +10 |
| heavy | -0.28% | 52,013 -> 51,864 | 119,186 -> 118,918 | 360,603 -> 378,318 | 5,556 -> 5,459 | +29 |
| td | -0.31% | 53,524 -> 53,358 | 100,172 -> 99,350 | 275,080 -> 271,890 | 2,744 -> 2,615 | -3 |

Real budget (indicative), OOF base -> m1: pool 770 -> 761, big 248 -> 281, heavy 707 -> 641, td 209 -> 213 (1,934 ->
1,896). farm-no-route 1,456 -> 1,056, crow-flies-farm 905 -> 593.

The test-draft sets `wide` and `td` share the copy `bots/variants/bench-td-<tag>`: run together (`ALL=1`), their
builds raced and failed (std::span errors), so they were rerun one after the other.

A/B `m1` (`fc7-m`, 10,240 games, real budget) against the base: **49.9% (48.9-50.9)**. OOF 69,970 / 71,830
(**-2.6%**), by rounds: 1: 6,277 / 6,276, 2-10: 5,049 / 6,395 (-21%), 11-60: 9,241 / 9,365, 61-300: 16,412 / 16,472,
300+: 32,991 / 33,322. Runs of 50+ OOF 987 / 1,139. Fuel a turn mean 51,062 / 51,149, p50 48,750 / 48,850, p90
86,550 / 86,550, p99 92,650 / 92,950, at or over 100k 0.25% / 0.26%. Shortcuts 2.220M / 2.271M: farm-partial-
evaluation 1,059k / 1,067k, step-guard-entry 584k / 590k, prey-cut-short 157k / 162k, turn-order 132k / 134k,
step-guard-look 75.3k / 75.5k, out-of-fuel 70.0k / 71.8k; farm-no-route 28.5k / 37.1k, crow-flies-farm 15.6k / 22.8k.

Open leads (both workers):
- Rebuilding Safety after our stun or kill (`see_stuns`, `see_kills`): reuse keyed on the changed beliefs, ~2-3k on stun turns.
- `Search::read`'s full foe read (~920 a foe): `kill_stops`, `stun_worth`, `partner_bound` on first use by a leaf.
- `__cxa_allocate_exception` ~0.9 a fight-heavy turn (presumably stale-turn throws after an OOF); unverified.
- Lazy unseen members in the pack zone (~0.8k on 28% of fight OOF turns), if it can be made exact.
- Farm loops with 3+ groups that have no centre field still flood from here (~230 of 1,932 bigR loops).
- Route searches in farm.post on big maps (route 12.5k + p.route 5k a heavy turn): goals-differ 42% of recomputes;
  an exact reuse needs every label reader to see what a fresh search would give.
- The claimed branch's plan_crew (5.5k a call, ~0.3 a loop) and the crew table's first read.

## world

Branch `fc7-world` on merge 1 (0f74957e): d6560807, aa699484; frozen tip `variants/fc7-world-a`.
Area: the fixed cost every turn pays (World::update, track, camps, channels) and the carry.

### Where World::update's fuel goes (heavy set, real budget, debug brackets, 208k turns)
- 7.2k a turn on average, 9.6k on the 24% of turns with a visible enemy. It is spread thin, with no part over 1.4k:
  - allies: 1.3k (253 a call, 5.2 a turn);
  - visible camps' update_camp: 1.1k (1.0k a call);
  - priorities: 821;
  - settled camps: 556 (219 a group);
  - rank_turns: 541 (1.45k on visible turns);
  - untracked enemies: 427 (105 each);
  - camp view: 355;
  - altars: 628 (lock memory loop 274, in view 262, locks 92);
  - visible enemy: 280;
  - track: 275 (1.3k a call, 0.21 calls a turn).
- update_champion's sections cost about 40-65 each. rank_turns spends about 265 on the gather, 360 on the sort
  and 97 on the writes per pass. The order changes on most passes, so a sorted-check gains nothing.
- Function profiler, all turns: place_lock costs 396 a turn (0.8% of all fuel). It tested every altar's
  distance twice, on every turn.
- Round 1 costs about 100k on heavy maps: build_static 49k, ally_spawn_field up to 40k, init_beliefs 13.6k,
  update 17k. Round-1 OOF is set by the farm loop's tail (fc6), so a cheaper init does not help.

### Shipped (identical at 100M on def, wide, pool, big, heavy, td; 342/342 replays; measured together against m1)
1. d6560807: **update_altars skips the lock memory loop and the ally-tribute proof while no altar holds a lock
   belief.** Only the lock read sets either flag, so with none held both loops clear nothing (`lock_beliefs_`).
2. aa699484: **place_lock lists the altars in its reach once** (falling back to every altar past 8), and
   returns when none is in reach. `here` does not change within the call, and both passes keep their checks.
- Total fuel: def -0.63%, wide -0.64%, pool -0.40%, big -0.45%, heavy -0.56%, td -0.36%. p50 -0.5% to -0.9%,
  p99 -0.2% to -0.4%; round 1 -0.1%.
- Over-100k play turns: def 693 to 676, wide 3079 to 3031, pool 8454 to 8348, big 2355 to 2315, heavy 5459 to
  5391, td 2615 to 2582. In all, 22,655 to 22,343 (-1.4%).
- No A/B was run: about 300 fuel a turn is too small to read in 10k games. Leave it to the merge A/B.

### Dropped (measured)
- **A2, one `board_awake_camp_occupancy` read a turn.** update_camps already reads per member, a cheaper
  route on the camps seen (the code comment says so). There is nothing to take.
- **Windowed track dilation** (the diff is saved at `/tmp/fc7/world/track-window.diff`: dilate_window, ChunkWindow,
  StaticMap::dash_open):
  - About 950 a call for about 3 chunks in our own code. It beats the host's whole-board ops only on 100x100
    growth with no dash (about 700 saved) and ties for dashers.
  - Track itself is 275 a turn, so the gain is about 0 per turn.
  - It also had 4 mismatches in 57k growths (lakes and ladder maps, 144 chunks): see the open leads.
- **SIMD counting sort in rank_turns:** 1,355 a call against 1,031. Reverted.
- **Stale resume (A6):**
  - Heavy set at the real budget: 506 StaleTurn throws over 700 OOF turns.
  - Resume to catch costs 4.7k on average (p50 3.4k, p90 8k, p99 25k).
  - Its floor is about 2.1k, the exception unwind itself. That cannot be cut without replacing the exceptions.
- **Route cache** (big + heavy sets, 183k misses, 24G fuel in all):
  - 94.7k misses have different goals, at about 4.1k each. A 6-entry history would catch only 1.4% of them.
  - 43k misses fail the cap of 4 changed wall tiles; 16k of those would pass kept_steps with no cap. The net
    gain is about 20M fuel. Dropped.
- **Lazy `undashed` copy in track:** not tried. Track is 275 a turn, too little to matter.

### Open leads
- `possible_box` may not bound `possible` in track. The windowed dilation, which trusts the box, disagreed 4 times
  in 57k growths. If the box is loose, readers that clip to it (if any) are silently wrong.
- The 2.1k floor of the stale unwind (a status-return path instead of throw), worth it only if OOF turns stay
  common.
- update_camp on visible camps (1.0k a call) and ally updates (253 each, 5.2 a turn) are the largest parts left;
  neither has an obvious repeated piece.

## path

Worker: pathing and movement checks. Branch `fc7-path` (38df6695); frozen tip `variants/fc7-path-b`.

### Where route fuel goes (instrumented copy, real budget vs base, heavy + big maps, both sides, 82 games)
- A host distance field costs (layers + 16) x chunks (cap 40k; fast runner's `api_defs.rs`), whatever the cap
  when it succeeds (ComputeTo stops at us), and a field copy costs 16 x chunks too. 561M of route-search fuel:
  farm.post 64% (53% found, 11% failed), step_safely 17%, untagged 10%, siege_kite 3%, chase 3%, carry_bag 2%.
- **Exact repeats are 0.7%** (same tile, goals, walls, crossing mode): the failed/spare/round/pocket memos
  already catch them. Fresh farm.post searches by the previous route call of the same champion: same goals
  last turn 28% of all route fuel (kept_steps refused the kept field), other goals last turn 15%, other goals
  same turn and tile 9%, other goals older 6%.
- **The zero-layer failures were empty goal boards**: 34.5k searches, ~59M (10.5%), one goal hash per map
  size. Farm's goals off its zone (`off_zone`) come out empty; each such step_towards cost ~3.8k (walls ~2k,
  search 16 x chunks, retries).
- Function profile on heavy self-play turns (base): pathing is small at function level (route_around 1.1k a
  heavy turn, plan 0.8k, closer_neighbours 0.5k); step_guard_cover 8.3k a call (2.8k a heavy turn), mostly the
  foes' Reach (the fight's). On siege turns the siege functions cost ~1.2k + altar_usable 1.4k: the census's
  siege_kite self (9.7k on 42% of OOF-first turns) is not the siege code itself.

### Shipped (identical at 100M on def, wide, pool, big, heavy, td)
1. 38df6695 **a route to no goals ends before its walls and search**, as `walk_parted` already does (exhausted,
   no labels: `route_label_cap_ = -1`). Exact: no search labels a tile from an empty goal board, at any cap;
   route()'s cover logic around it (guard_skipped_, failure_known_, route_cover_) runs as before; only the
   exact memos' contents (failed_, spares, pocket) differ. Costs one board_empty per route_around past the
   on-goal test.
   - 100M vs base: total -0.23% def, -0.19% wide, -0.19% pool, -0.32% big, -0.23% heavy, -0.13% td; p50
     -0.3..-0.9%; p99 -0.0..-0.1% (big 104,092 -> 103,955, heavy 119,186 -> 119,087); max +0.1% at most; round 1
     +0.0..+0.1%.
   - Real budget (indicative, games diverge): OOF pool 770 -> 845, big 248 -> 255, heavy 707 -> 824, td 209 ->
     207 (1,934 -> 2,131); within the benches' noise for a 0.2% fuel cut. No 10k A/B run (gain too small to read).

### Dropped
- (A) The same, skipping only the empty search (a flag travelling with route_field_ through spares and the
  round memo, readers answering unreachable): identical, total -0.06..-0.23%; superseded by 1.
- (C) kept_steps accepting a walled tile below our steps whose successors keep another open predecessor (exact
  by the lowest-changed-label argument; only on the walking kept route and beyond the dash window, as the tile
  keeps its stale label): measured first. Kept-route refusals are 95M of 561M route fuel; the rule would accept
  ~3M of them under the 4-change limit, ~12M with none (which costs more checks, as farm round 1 found). Not built.
- (E) ward_bushes memo of "no better cluster" keyed on tile, ward, work tile and the allied wards (exact: bushes
  and clusters are static): identical, -0.00..-0.03% total, more turns dearer than cheaper: it seldom repeats.
- (F) step_field skipping its search when its static field proves the live route (no extra blocker b with
  S(b) + dist(me, b) <= S(me), crossings shut, no dash plan reading the labels): step_field's fresh searches are
  42M (7.5% of route fuel), the provable non-dash ones ~8M (1.4%). Not built.

### Open
- Fresh searches for other goals than the kept route (farm.post: 30% of route fuel) remain the bulk; an exact
  reuse needs a field for the new goals, which only a search gives.
- dash_turns::across loops (123 a call, ~10 a plan turn, 1.2k on plan-heavy turns): a closed form would save ~1k
  there.
- blocked()/occupied_into rebuilds (~11 whole-board operations) after each move or kill: a key on acts_, round,
  can_attack, can_cast and ward cooldown would let several routes share one, but a move reveals units, so only
  same-tile repeats qualify.

## merge 2

Merged `fc7-path` (38df6695) and `fc7-world` (d6560807, aa699484) as CHANGES 425; nothing dropped. Frozen as
`bots/variants/fc7-m2`.

Review:
- path: an empty goal board is the search's own roots board (walls never touch it), so no search labels a tile at
  any cap. Every reader then behaves as after the empty search: `route()` gets `steps == unreachable` either way
  (its cover branch, `pocket_at_` restore and `failure_known_` run as before); `make_way` returns at once on empty
  goals; `label_through` reads no labels (`route_label_cap_ = -1`, as `walk_parted`); `route_exhausted_` is read
  only by `step_towards(Field)`, whose goals are non-empty whenever it searches (`here != unreachable`), and the
  walk round saves and restores it. The base's own empty-goal paths were not all exhausted (a `round_fails` hit
  returned exhausted false with stale labels, a `within_failed` hit took another goal set's labels), but none of
  their readers is reached with empty goals. Only the exact memos (failed_, spares, round labels, pocket) keep
  other contents: misses cost a search, never a different answer.
- world: the only writes that set `ally_lock` / `enemy_lock` are the `sdk_altar_locks` read in `update_altars`,
  which sets `lock_beliefs_` before them. Lock sightings are not shared through comms, and our own `place_lock`
  does not write a belief (the next read does). The flag only over-approximates (seen-altar resets and tribute
  proofs leave it set until the next forgetting pass), so it is safe across an out-of-fuel resume. With no belief,
  the forgetting loop and the tribute proof clear nothing. `place_lock`'s list is ascending altar order, and with
  more than 8 in reach it falls back to every altar in order: the same order and checks as before. With none in
  reach, the old loops did nothing.

100M, all six sets byte-identical to `base-*-100M.json` (`m2-*`; 342/342; also identical to `m1-*`):

| set | total vs base | total vs m1 | mean | p99 | max | over 100k | round 1 mean |
|---|---|---|---|---|---|---|---|
| def | -1.18% | -0.85% | 51,433 -> 50,824 | 97,736 -> 97,205 | 215,787 -> 215,699 | 704 -> 668 | -82 |
| wide | -1.02% | -0.83% | 50,497 -> 49,979 | 103,147 -> 102,788 | 268,444 -> 265,846 | 3,086 -> 3,010 | -29 |
| pool | -1.01% | -0.58% | 53,464 -> 52,924 | 107,853 -> 105,804 | 356,280 -> 372,172 | 9,367 -> 8,337 | -13 |
| big | -1.47% | -0.78% | 61,397 -> 60,490 | 104,092 -> 102,702 | 287,312 -> 332,559 | 2,523 -> 2,278 | +21 |
| heavy | -1.07% | -0.79% | 52,013 -> 51,453 | 119,186 -> 118,580 | 360,603 -> 378,220 | 5,556 -> 5,370 | -63 |
| td | -0.80% | -0.49% | 53,524 -> 53,095 | 100,172 -> 99,170 | 275,080 -> 271,720 | 2,744 -> 2,573 | -14 |

Over 100k in all: 23,980 (base) -> 22,655 (m1) -> 22,236 (m2). Real budget (indicative), OOF base -> m1 -> m2: pool
770 -> 761 -> 810, big 248 -> 281 -> 249, heavy 707 -> 641 -> 619, td 209 -> 213 -> 193 (1,934 -> 1,896 -> 1,871).
`ALL=1` ran cleanly with the prebuilt test-draft copies.

A/B `m2` (`fc7-m`, 10,240 games, real budget) against the base: **50.3% (49.4-51.3)**. OOF 68,314 / 71,023
(**-3.8%**; m1 read -2.6%), by rounds: 1: 6,281 / 6,276, 2-10: 4,998 / 6,408 (-22%), 11-60: 9,267 / 9,626, 61-300:
15,928 / 16,294, 300+: 31,840 / 32,419. Runs of 50+ OOF 1,066 / 819 (m1: 987 / 1,139; noisy). Fuel a turn mean
50,744 / 51,136, p50 48,150 / 48,850, p90 86,450 / 86,550, p99 92,450 / 92,850, at or over 100k 0.25% / 0.26%.
Shortcuts 2.197M / 2.267M: farm-partial-evaluation 1,056k / 1,071k, step-guard-entry 576k / 586k, prey-cut-short
153k / 162k, turn-order 127k / 133k, step-guard-look 76.9k / 75.0k, out-of-fuel 68.3k / 71.0k; farm-no-route 28.2k /
37.2k, crow-flies-farm 15.5k / 22.8k, ward-no-bushes-clusters 23.8k / 29.9k.

Open leads (both workers, with merge 1's still open):
- `possible_box` may not always contain `possible` in track: a windowed dilation that trusted the box disagreed 4
  times in 57k growths (lakes and ladder maps). Probe later whether readers that clip to the box are wrong; not
  fixed here.
- Fresh route searches for other goals than the kept route (farm.post ~30% of route fuel; goals differ in 42-52% of
  recomputes): an exact reuse needs every label reader to see what a fresh search would give.
- kept_steps accepting a walled tile below our steps that keeps another open predecessor (~3M of 95M refusals
  under the 4-change cap, ~12M uncapped); step_field skipping its search when the static field proves the route
  (~8M, 1.4% of route fuel).
- blocked()/occupied_into rebuilds (~11 whole-board ops) after each move or kill: same-tile repeats only.
- dash_turns::across closed form (~1k on plan-heavy turns).
- The 2.1k floor of the StaleTurn unwind (a status-return path instead of a throw), and
  `__cxa_allocate_exception` ~0.9 a fight-heavy turn.
- update_camp on visible camps (1.0k a call) and ally updates (253 each, 5.2 a turn).
- Rebuilding Safety after our stun or kill, keyed on the changed beliefs (~2-3k on stun turns).
- `Search::read`'s full foe read (~920 a foe): `kill_stops`, `stun_worth`, `partner_bound` on first use.
- Lazy unseen members in the pack zone (~0.8k on 28% of fight OOF turns), if exact.
- Farm loops with 3+ groups and no centre field still flood from here; the claimed branch's plan_crew (5.5k a call).

## goal

Branch `fc7-goal` on main f9ff0caa (merges 1-2). Area: the fight turn's goal after the strike search (siege_kite,
farm's walk, prey). Frozen tip `variants/fc7-goal-d`.

### Where the goal's fuel goes (census with labels inside siege/kite/altar access; heavy + big + 32 pool + 36
Monolith, Monolith-only and shared-gems maps; real budget vs the base)
- `siege_kite` ~9.6k on 44% of OOF-first turns (4.2k on half of the heavy finished ones): siege 8.8k, kite 5.7k
  on 17%.
  - Inside siege, `siege_candidate` 7.2k, nearly all `altars_sealed` (8.1k when present). That is
    `rebuild_altar_access`: 14k a rebuild on 23% of OOF-first turns. Its flood from spawn (`flood_altar_walk`,
    an uncapped `reachable_tiles_into`) costs 20-33k on 100x100.
  - The rest: `kite_plan` 2.2-2.6k a call, flat; `siege_ready` 1.9k on 8%; the siege body 13k on 4% (its
    stand loop, `fire_at` per goal tile x member).
- **The mask's price is (layers + 2) x the chunks within its reach** (fast runner `api_defs.rs`,
  ReachableMask). An uncapped call pays every chunk for every layer, so a short flood near a few tiles is
  cheap only with a small reach.
- Floods after camp returns (ACC trace, 8 maps): 504 floods. 500 of them came after returns alone that cut
  no walk: the new flood equalled the old walk minus the returned tiles. `round_returns` and the else-branch
  test only connect the tiles beside the returns through those tiles. Through the rest of the walk they
  connected within 8-16 layers in 92 cases, 32 in 106, 64 in 168 and more in 130. Only 8 floods were real
  cuts.
- prey 12-13k on 29% of OOF-first turns (self 3.7-7k). `preyable` costs ~930 a call, most of it the round's
  first pack build, which the walks read anyway. `team_pressed` costs 1.2k a call even with 2 visible
  enemies: plain loop cost.
- Farm's walk on struck turns (`walk_on`, 9.6k on 25%): `search_approach` 6k, `walk_down` 11k, descend 6k.
  No repeat of the strike search's work was found there: the step guard is reused already
  (`strikes_known`), and the walk's route searches have other goals than the search's.

### Shipped (identical at 100M on def, wide, pool, big, heavy, td and on the fires-set: 8 rebuild-heavy maps
plus 12 each of Monolith, Monolith-only and shared-gems, 88 games)
1. 33806d81 **altar_access drops returned camps from the walk when the tiles beside them stay connected through
   the rest of it** (`returns_go_round`: flood within `ours` minus the returns from one such tile, reach 16
   then 64, else the flood from spawn as before).
   - Exact: every path through a returned tile enters and leaves it by tiles beside it. These lie on
     `ours` minus the returns and connect there, so the walk with the returns as walls is `ours` without
     them.
   - Holds with `ours` behind on deaths (it is the flood for `ours_live`), so it joins `round_returns` in
     `lazy` and the existing catch-up adds the deaths.
   - Fires-set: turns cheaper by 1k+ 2,762, mean -6.1k; heavy turns 440 at -13.2k. 592 turns are dearer by
     1k+, where both reaches fail (+11k on 100x100).
2. 9a5a8559 kite_plan sums the station output from each reach once a round (small; superseded in effect by
   3).
3. 434bec5f **kite_plan keeps each group's plan while the group's version and the team's station output
   hold.** The version moves with every state or health write, and the plan reads nothing else.
   Fires-set: mean -492 a turn, 81k turns cheaper by 1k+ (mean -3.5k).
4. ae8089bc team_pressed loops over the visible enemies only, its board test last. Small: heavy-turn mean
   -48.
5. 83445fc6 **siege() works team_power out once a call.** Nothing it reads changes before siege() acts; the
   burst test asked it once per live Monolith. Fires-set: mean -154 a turn, 25.8k turns cheaper by 1k+
   (mean -2.7k).
- All five, 100M (`goal-d-*`), all six sets byte-identical to `base-*-100M.json`:

| set | identical | total vs base | total vs m2 | mean m2 -> d | p99 m2 -> d | max m2 -> d | over 100k base / m2 / d | round 1 mean vs m2 |
|---|---|---|---|---|---|---|---|---|
| def | 16/16 | -1.25% | -0.08% | 50,824 -> 50,785 | 97,205 -> 96,879 | 215,699 -> 215,520 | 704 / 668 / 649 | +12 |
| wide | 52/52 | -1.22% | -0.20% | 49,979 -> 49,877 | 102,788 -> 102,421 | 265,846 -> 265,753 | 3,086 / 3,010 / 2,959 | -97 |
| pool | 128/128 | -1.17% | -0.17% | 52,924 -> 52,834 | 105,804 -> 105,425 | 372,172 -> 372,183 | 9,367 / 8,337 / 8,156 | -61 |
| big | 32/32 | -1.68% | -0.21% | 60,490 -> 60,364 | 102,702 -> 101,411 | 332,559 -> 332,570 | 2,523 / 2,278 / 2,132 | -153 |
| heavy | 50/50 | -1.25% | -0.18% | 51,453 -> 51,359 | 118,580 -> 118,267 | 378,220 -> 378,220 | 5,556 / 5,370 / 5,290 | -33 |
| td | 64/64 | -0.93% | -0.14% | 53,095 -> 53,022 | 99,170 -> 98,727 | 271,720 -> 271,199 | 2,744 / 2,573 / 2,495 | -85 |

- Over 100k in all: 22,236 (m2) -> 21,681 (-2.5%).
- Turns the base spent 95k+ on, against m2: mean -325 to -1,503 a set (big -1,503). Cheaper by 1k+:
  3-10% of them (mean -5.5k to -16.6k). Dearer by 1k+: under 2%, the p99 +12k on big being returns where
  both reaches fail.
- Fires-set, m2 -> d: total -1.42%, heavy turns mean -1.1k, over 100k 8,498 -> 8,046 (-5.3%), p99 -0.9%.
- Real budget (indicative), OOF base / m2 / d: pool 770 / 810 / 775, big 248 / 249 / 243, heavy 707 / 619 /
  574, td 209 / 193 / 230 (1,934 / 1,871 / 1,822). Shortcuts m2 -> d 66.5k -> 65.8k.
- No 10k A/B run: the gain sits on Monolith, sealed and shared-gem maps, too thin to read in OOF on `fc7-w`.

### Dropped / not built
- `Search::read`'s per-foe reads, by reasoning: `kill_stops` is a channel test. `stun_worth` runs only with
  a stun armed, `partner_bound` only for Cassi and Issac. The ~920 a foe is the live record, buff and
  recall reads, `viewers` and `turns_before_ours`, which every leaf needs.
- Bounded-then-closed floods for `walk_deaths`. A death's new region is mostly a few tiles, whose uncapped
  mask already costs ~1k, so a reach-8 mask plus a closure check (~3 board ops) saves ~200 and loses on
  large regions.
- Reach (16, 32) instead of (16, 64) in `returns_go_round`, from the oracle: saves ~5.0M against 7.2M on the
  8 rebuild maps.

### Open
- `walk_deaths` and the no-open branch of `rebuild_altar_access` still flood uncapped from each dead camp or
  opened tile: (layers + 2) x all chunks.
- The siege body's stand loop (`fire_at` per goal tile x member, 13k on 4% of OOF-first turns) could test
  members by reach box first.
- `siege_candidate` / `altars_sealed` self (~0.9-1.3k on 22-42% of heavy turns) is spread over many small
  reads.
- prey's own loop (self 3.7k on 29% of OOF-first turns) and chase's walk after it.

## r1

Round 1 at the real budget (worker r1, branch `fc7-r1`). Harness: 2,048 maps sampled from
`maps/suites/merged/ast-ocean-40k`, both sides, two rounds, candidate against `fc7-m2` (4,096 games, 22,806
round-1 bodies); scripts in `/tmp/fc7/r1/tools/` (`r1run.py`, `r1sum.py`). m2 runs out on 1,970 round-1 bodies.

**Round-1 fuel cuts round-1 OOF.** Burning fuel at the start of round 1: +5k -> 2,335 OOF, +15k -> 3,083, so
~74 round-1 OOF per 1k fuel a body on this harness (the farm loop's `room()` decides how many groups it
evaluates; most round-1 OOF turns are the farm tail or the first group's evaluation running out). Saving
fuel before the loop counts as much as saving it in the loop.

The profiler skipped each instance's first two turns (`s->turns >= 2`), so round-1 start-up was invisible;
a copy with `FR_PROF_MIN` sets the skip. Round-1 meters (finished turns): decide 96k, build_static 34k
(camps 18k, boards 6k, b.plan 5k, b.sort 1.9k), update 13k, init_beliefs 11k, siege 7.7k (altars_sealed
4.7-13k), prices 5.8k, ally_spawn_field 3.8k. SDK start-up we can't reach: champion_designs 1.9k,
ability::initialize 1.7k, champion ctor 1.3k, draft buffer resize 1.1k.

Shipped (each byte-identical at 100M on the harness, 4,096/4,096; round-1 OOF at the real budget, cumulative):
1. `2641d5d7` drafted attack tiles decode a chunk word's bush bits at once: -66 a body; 1,970 -> 1,948.
2. `e94cdbd3` `[[clang::no_destroy]]` on every global (unity.cpp pragma): no `__cxa_atexit` registrations
   (~32 each, ~80 on the first turn). -2.5k a body (p50 -3.6k), and ~-90 on every later turn; -> 1,569.
3. `6f02c318` the Instance is a `constinit` global, not on main's stack (zeroing it, with DraftPlan's 1 KB
   and crew_ban, cost ~2.2k): -2,188 on every body; -> 1,452.
4. `2e895b63` team B's landing tiles sort as packed mirrored keys (the comparator mirrored both tiles per
   comparison); team A keeps the plain sort (keys cost it +77 at p50 when used for both): -1.25k on B; -> 1,391.
5. `c5e5dbfc` Pathing's 4 trace tile arrays left unzeroed (only the first `count` are read): -804; -> 1,327.

Total 1,970 -> 1,327 round-1 OOF (-33%) on the harness. Bench (`r1-e` = tip) against m2, all six sets 100M
identical (16/52/128/32/50/64): round-1 mean -2.3 to -2.8% (pool 231,765 -> 226,419, big 267,558 -> 260,046,
heavy 251,481 -> 244,448), p99 -1.6 to -3.3%; all-turn mean -86 to -93, total fuel -0.16 to -0.20%; over 100k
668 -> 659 def, 3,010 -> 2,979 wide, 8,337 -> 8,258 pool, 2,278 -> 2,258 big, 5,370 -> 5,334 heavy, 2,573 -> 2,544
td. Real-budget round-1 bodies at 200k: pool 97 -> 80/704, big 68 -> 59/192, heavy 56 -> 56/258, td 55 -> 40/328.

Dropped or left: the draft lever is weak (`memory.draft` is full: attack tiles fill greedily, leads, dash
steps, wards and the index take the rest, and none of the big round-1 items has a compact output); the camp
build (18k) is already SIMD and scales with members; Neighbours/steps_of zeroing (64 bytes a call) too small.
Area 2 (the stale unwind) not tried: it only touches late turns, and a status-return path is a wide refactor.
Open: siege's altars_sealed in round 1 (4.7-13k) and init_beliefs (11k) are the largest remaining round-1 items.

A/B `r1-e` (`fc7-w`, 10,240 games, real budget) against the base: **50.9% (50.0-51.9)**. OOF 67,429 / 73,352
(**-8.1%**; m2 read -3.8%), by rounds: 1: 4,741 / 6,270 (**-24%**; m2 6,281), 2-10: 4,277 / 6,115, 11-60: 8,646 /
9,205, 61-300: 15,550 / 16,182, 300+: 34,215 / 35,580. Fuel a turn mean 50,600 / 51,064, p50 48,050 / 48,750, p99
92,450 / 92,950, at or over 100k 0.25% / 0.26%. Shortcuts 2.157M / 2.251M.

## nocheck

Branch `fc7-nocheck`. Target: out-of-fuel turns that pass no fuel check (66% of the base census's OOF turns).

### Where those turns run out (base census, `cen/`, OOF-first, no check passed: 1,538 turns)

Scope sequence from the CTR traces (`/tmp/fc7/nocheck/tools/seq.py`): world (~15k) -> channels -> want_home's stand
(entered ~78k) -> strike search (entered p50 52k, p10 29k) -> post_search -> goal (chase/prey/siege_kite/farm) ->
strike_after -> act_end -> turn order. Last scope entered when fuel ran out:
- the goal after the search 49%: farm 446 (struck turns' `walk_on`, entered p50 18.5k), prey 108, siege_kite 102,
  carry_bag 40;
- the strike search 22% (338): price loop 184, grow 74, read 28, execution 24;
- the tail 17%: act_end 148 (entered ~0.7k), strike_after 46, turn_order/publish 62;
- retreat 90, the stand itself 70 (concentrated-wealth maps: one stand sim 23-28k).
- Fuel left at the search's end against the turn running out (all 72k searches): 0-5k 32%, 5-10k 27%, 10-15k 15%,
  15-20k 7%, 20-25k 3%, 25-30k 1%.

### Dropped: anytime strike search (cb652921, `variants/fc7-nocheck-a`)

- The search grows no node past the second and prices no tile or Reach query below a floor, then plays its best
  plan so far (unpriced tiles keep their Strike price, as with `max_exact_queries`). Floor 20k for the main
  search and keep_bid, 6k for strike_after; the grow keeps 5k more for the price loop. Tags `strike-grow-cut`,
  `strike-price-cut`.
- 100M: all six sets byte-identical to the base (fuel as m1's).
- Real budget (indicative), OOF m1 -> a: pool 761 -> 637, big 281 -> 252, heavy 641 -> 558, td 213 -> 184
  (1,896 -> 1,631, -14%).
- **A/B fc7-w (10,240): 50.4% (49.5-51.4), OOF 65,338 / 74,988 (-12.9%)**; rounds 300+ 30.4k / 36.2k, runs of 10+
  OOF 18.8k / 24.7k; strike-price-cut 47.1k, strike-grow-cut 33.9k; mean fuel 51,021 / 51,153.
- **Confirmation on fresh 770401-770440 (`maps/suites/merged/fc7-nc-conf`, 20,480): 50.1% (49.4-50.7), OOF
  121,876 / 138,281 (-11.9%)**. Level: not a keeper under the "significant win rate" bar.
- Its census (`replays/fuel/fc7/nc-cen`): no-check OOF-first 1,538 -> 886; 578 turns cut the search and still ran
  out, spending the 20k left thinly (siege_kite 3.8k a turn, prey 2.4k, prices 1.2k, ...).

### Why no other fallback was run

- a removed 12-13% of OOF turns, a third of the no-check class, and read level twice (50.4% / 50.1%). The gate-view
  oracle (`research/ideas-2026-11-05/fuelbud.md`) put all of astraeus's OOF at ~0.5 points (ocean's at ~1.6), so a
  12% cut is worth ~0.1: no fallback that leaves most OOF turns can show a win rate significantly above 50% at
  20k games (half-width ~0.7). ocean's watchdog (-23% OOF, lost) and fixed strike floor (-8%, level) agree.
  The cheap-verdict stand and goal-floor designs reach fewer OOF turns than a, so they were not built.
- The stand under fuel pressure: it runs at ~78k left, early in the turn; a fuel-aware stand would have to fire on
  ordinary turns to matter.

### Open (exact only)

- Function profile of heavy fight turns (m1, heavy set, 436 heavy turns): plan_strikes self 11.4k, the sim's
  `act<false>` 7.3k (14 calls), `World::update_champion` 6.4k (22 calls), Reach build/at 8.9k, grow 3.7k,
  `step_guard_cover` 3.3k, `turns_before_ours` 1.5k (10.8 calls at 143), `strike_memo` 1.5k (15.6 calls),
  `next_turn_round` 1.2k (25 calls).
- `siege_kite` (siege() + kite() on the goal's path) spends 3.8k a turn on cut-then-OOF fight turns and 12k self on
  the base's no-check OOF turns; it is not in the profile's top functions (inlined into its callers): a census
  label inside `siege_candidate`/`altars_sealed`/`altar_usable` would place it.
- Round 1 is 9% of A/B OOF turns (6.3k of 70k), all no-check (world build + first farm loop): not touched here.

## runaway

Branch `fc7-runaway`. Target: OOF concentrated in streaks (runaway games).

### What the streaks are (fc7-m1 vs base, 1,280 games on every 8th map of fc7-w, real budget, replays kept)
- OOF is not concentrated in streaks. oof_bot's "champion-game run sizes" counts OOF *turns*, not champion-games:
  in m1's 10k A/B, champion-games with 50+ OOF hold 987 of 69,970 OOF turns (1.4%); <10 hold 70%. In the 1,280-game
  batch: first-in-streak 7,547 of 8,741 (86%); gaps between a champion's OOF turns: 1 round 1,172, 2 rounds 768,
  3-5 623, 6-20 943, 21+ 2,702. The 300+ share (45%) is the share of turns played there, not streaks.
- Games with 50+ OOF (all bodies) hold 27%, with the same branch / search mix as the rest (F with and without a
  strike search, R, C, B): no state class of their own.
- The real streak mechanism is the late turn. A turn that runs out (round r) is abandoned at resume (~3k median
  lost, p10 6k) and replayed as late; a late turn that runs out finishes in r+1 (CHANGES 217), consuming that round,
  and the next is late again: a fight state costing >100k a turn acts every other round (mut-elk-arena-77020417032,
  body 7, rounds 1184-1222). Late turns run out at ~20% against ~0.18% for others; their OOF are 18% of all
  (1,172 replays, 439 after a late finish), mostly fight turns (fc7-cen: stand check 19k on 75%, strike search
  22k on 57%), i.e. the no-check class `fc7-nocheck` works on.
- No exact repeats to memo: of 189k SRCH lines, 549 equal their body's previous search (within 2 rounds), 4 on OOF
  turns; 2,472 equal in structure with fuel within 200 (8 on OOF turns). In the elk-arena runaway the search's
  structure repeats but its fuel moves by up to 1.8k turn to turn (inputs differ). Exact cross-turn memos are dead
  here as elsewhere.

### Dropped
- **late-margin (881894bb, `variants/fc7-runaway-b`)**: while deciding a turn after one that ran out (not the
  first turn), fuel_ok and the decision's raw fuel floors (`fuel_left()`) read 15k less. Never set at 100M: six sets
  byte-identical; mean fuel +0.1-0.2% against m1 (the margin's add in every fuel_ok). A first form shifting fuel()
  itself cost +0.4% mean (meters read it). Real benches OOF 1,794 (base 1,934, m1 1,896). **10k A/B fc7-w: 50.4%
  (49.4-51.4), OOF 69,650 / 72,770 (-4.3%; m1's own share ~-2%)**, runs of 50+ 695 / 1,342, finish gap 2: 249 /
  446, mean fuel 51,173 / 51,144, p99 92,550 / 92,850. Level on win rate: not a keeper under the revised bar.
- **late-margin 30k (`variants/fc7-runaway-c`, same code, `late_margin = 30000`)**: 10k A/B fc7-w 50.2% (49.2-51.1),
  OOF 70,177 / 73,348 (-4.3%), finish gap 2: 181 / 441, mean fuel 51,156 / 51,128. Level: dropped. Both margins
  halve the late finishes and take ~2 points of OOF beyond m1, with no win-rate gain: an OOF late turn still acts,
  one round late, so saving it is worth little. Reverted on the branch (881894bb, reverted next commit).

### Open
- The late turn's stale tail (~3k median, 6k p10 before its first `throw_if_stale`) is pure waste, but a check in
  the hot loops costs every turn.
- Late turns are mostly the stand check and strike search with no fuel check (`fc7-nocheck`'s area); a late-turn
  trigger could raise its floors, but a margin alone did not move win rate.

## merge 3

Merged `fc7-goal` (33806d81, 9a5a8559, 434bec5f, ae8089bc, 83445fc6) and `fc7-r1` (2641d5d7, e94cdbd3, 6f02c318,
2e895b63, c5e5dbfc) as CHANGES 426; nothing dropped. `fc7-nocheck` and `fc7-runaway` brought notes only (their bot
commits are reverted on their branches). Frozen as `bots/variants/fc7-m3`.

Review:
- `returns_go_round`: `ours` is the flood from spawn for `ours_live`'s walls (also while behind on deaths), so a
  path to any tile of it lies in it. A path through a returned tile enters it from a tile beside it and leaves to one,
  both on `ours` minus the returns (king steps; `square_dilate` by 1 is the 8-neighbourhood, and the test flood is
  the same `reachable_tiles_into` with the same corner rule as the walk's). With those connected through `ours`
  minus the returns, every tile of it stays reached: the new walk is `ours` minus the returns, and the catch-up adds
  the deaths as before. Returned tiles off `ours` only add tiles to `beside`, which makes the test stricter. Map
  edges: tiles off the board are never in `ours`. A capped flood that reaches all of `beside` proves connection, so
  the caps only decide when to fall back.
- `kite_plan` memo: the plan reads the station output (key), the group's state and member health (`c.version`), and
  static map data (members, `standable`); no champion position or health. Every write of `state` or `health` is in
  `world.cc` (`update_camp`, `restore`, `note_capture`, `init_beliefs`) and bumps the version when the value changes;
  the version never goes down, so no stale hit. The `output_from` sums add in the old loop's order: same floats.
- `team_pressed` / `pressed`: pure conditions reordered; at most 6 enemy bodies against 16 slots. `team_power` reads
  allies' alive flag, Strength and Focus, which nothing in `siege()` changes before it acts; it is at least 1 an
  ally, so the -1 sentinel never collides.
- `drafted_attack_tiles`: `PlanReader::get` is LSB-first, so a word's popcount bits deposited on its set bits in
  ascending order are the old per-tile reads; the bits are consumed whatever the range, as before; the range mask is
  the square of radius `range` (indices clamped, `l > h` returns).
- `constinit` Instance and `no_destroy`: `main()` loops forever and never returns, so no static destructor ever
  ran (no exit-time flush was relied on: printf output goes out through the engine at each turn end as before).
  Every member of `Instance` (TurnEndQueue, DraftState, Memory, two null `unique_ptr`s) has an initialiser or is an
  empty vector: the same state as the stack object, now with no start-up code.
- B-side landing keys: (y << 20 | x << 8 | index), coordinates under 4096 and at most 64 tiles; spawn tiles are
  distinct, so the keys are distinct and sort in the comparator's (y, x) order.
- Trace tiles: every read (`on`, the copy down, the walk's last tile) is below `count`, and each tile is written
  before `count` covers it.

100M, all six sets byte-identical to `base-*-100M.json` (`m3-*`; 342/342), and the goal worker's fires-set
(`/tmp/fc7/goal/accset.txt` + `siegeset.txt`, 41 distinct maps, 82/82 identical):

| set | total vs base | total vs m2 | mean base -> m3 | p99 base -> m3 | max base -> m3 | over 100k base / m2 / m3 | round 1 mean vs base |
|---|---|---|---|---|---|---|---|
| def | -1.44% | -0.27% | 51,433 -> 50,695 | 97,736 -> 96,731 | 215,787 -> 215,456 | 704 / 668 / 639 | -2.5% |
| wide | -1.41% | -0.39% | 50,497 -> 49,787 | 103,147 -> 102,248 | 268,444 -> 265,539 | 3,086 / 3,010 / 2,923 | -2.4% |
| pool | -1.35% | -0.34% | 53,464 -> 52,748 | 107,853 -> 105,265 | 356,280 -> 372,030 | 9,367 / 8,337 / 8,076 | -2.3% |
| big | -1.84% | -0.37% | 61,397 -> 60,273 | 104,092 -> 101,291 | 287,312 -> 331,323 | 2,523 / 2,278 / 2,111 | -2.8% |
| heavy | -1.44% | -0.38% | 52,013 -> 51,266 | 119,186 -> 118,143 | 360,603 -> 374,296 | 5,556 / 5,370 / 5,246 | -2.8% |
| td | -1.11% | -0.31% | 53,524 -> 52,937 | 100,172 -> 98,566 | 275,080 -> 271,081 | 2,744 / 2,573 / 2,467 | -2.5% |
| fires | -2.83% | -1.60% | 52,571 -> 51,088 | 110,736 -> 107,320 | 360,603 -> 374,296 | 9,538 / 8,498 / 7,975 | -2.3% |

Over 100k in the six sets: 23,980 (base) -> 22,236 (m2) -> 21,462 (m3). Real budget (indicative), OOF base -> m2 ->
m3: pool 770 -> 810 -> 709, big 248 -> 249 -> 229, heavy 707 -> 619 -> 534, td 209 -> 193 -> 230 (1,934 -> 1,871 ->
1,702).

A/B `m3` (`fc7-m`, 10,240 games, real budget) against the base: **50.3% (49.3-51.3)**. OOF 63,798 / 70,795
(**-9.9%**; m2 read -3.8%), by rounds: 1: 4,985 / 6,272 (-21%), 2-10: 4,413 / 6,398 (-31%), 11-60: 8,916 / 9,541
(-7%), 61-300: 14,872 / 16,362 (-9%), 300+: 30,612 / 32,222 (-5%). Runs of 50+ OOF 654 / 1,010. Fuel a turn mean
50,535 / 51,184, p50 47,850 / 48,850, p90 86,450 / 86,550, p99 92,250 / 92,850, at or over 100k 0.24% / 0.26%.
Shortcuts 2.128M / 2.262M: farm-partial-evaluation 1,011k / 1,061k, step-guard-entry 571k / 589k, prey-cut-short
154k / 163k, turn-order 121k / 133k, step-guard-look 75.0k / 76.4k, out-of-fuel 63.8k / 70.8k; farm-no-route 26.1k /
37.1k, crow-flies-farm 14.4k / 22.8k, farm-kept-target 958 / 3,840.

Open leads (batch 3, with merges 1-2's still open):
- `walk_deaths` and the no-open branch of `rebuild_altar_access` still flood uncapped from each dead camp or opened
  tile ((layers + 2) x all chunks); `returns_go_round`'s fallback costs ~11k on 100x100 when both reaches fail.
- The siege body's stand loop (`fire_at` per goal tile x member, 13k on 4% of OOF-first turns): test members by
  reach box first. `siege_candidate` / `altars_sealed` self (~1k on 22-42% of heavy turns); altars_sealed in round 1
  (4.7-13k) and `init_beliefs` (11k): the largest round-1 items left.
- prey's own loop (self 3.7k on 29% of OOF-first turns) and chase's walk after it.
- Heavy fight turns (function profile): plan_strikes self 11.4k, the sim's `act<false>` 7.3k, `update_champion` 6.4k
  (22 calls), Reach build/at 8.9k, `step_guard_cover` 3.3k, `turns_before_ours` 1.5k, `strike_memo` 1.5k,
  `next_turn_round` 1.2k.
- The late turn's stale tail (~3k median before its first `throw_if_stale`) and the StaleTurn unwind's 2.1k floor
  (a status-return path instead of a throw).
- Fuel gates are not worth building: the anytime strike search (-12% OOF) and late-margin (-4%) both read level on
  win rate (nocheck, runaway); OOF overall is worth ~0.5 points.

## r1b

Rest of round 1 and rounds 2-10 (worker r1b, branch `fc7-r1b` from `fc7-r1` 50dbf6a2). Same 2-round harness
as r1 (4,096 games, 22,806 round-1 bodies, against `fc7-m2`), plus a 10-round one on the same 2,048 maps;
references are r1-e's runs. Scripts in `/tmp/fc7/r1b/` (`h.sh`, `h10.sh`, `r10sum.py`, `cmp.sh`).

Shipped (each byte-identical at 100M on the harness, 4,096/4,096, and on all six bench sets, 16/52/128/32/50/64):
1. `0d8daec8` the SDK's `champion_designs` (13 champions and their abilities read from the host) and
   `draft_memory` vector are never built: `src/sdk_skip.cpp` defines their guard variables
   (`_ZGVN5cambc16champion_designsE`, `_ZGVN5cambc12draft_memoryE`) as 1, overriding the weak COMDAT ones, so
   `__wasm_call_ctors` skips both initialisers; draft.cc reads its own `DraftPlan` bytes once at start
   (`capture_draft_memory`) and writes through the raw import. -6,061 on every round-1 body (22,805 of
   22,806 cheaper); round-1 OOF 1,327 -> 1,153. Bench vs r1-e: round-1 mean -2.3 to -2.8%, p99 -1.4 to -1.9%,
   total -0.01%; real-budget OOF pool 854 -> 812, big 240 -> 220, heavy 578 -> 587, td 239 -> 193.
2. `09746f6a` `may_reach_within` and `credible_enemy_may_hit_within` skip an enemy farther than
   `Strike::max_reach + turns` (visible: from where it acts; unseen: its possible box) before building its
   foe (~1.5k each, recall_line's `strike_foe` ran ~11k on rounds 2-10 OOF turns). 10-round harness at 100M:
   4,096/4,096 identical, mean -118 a turn; real budget OOF round 1
   1,154 -> 1,100, rounds 2-3 357 -> 305, 4-10 170 -> 153. Bench vs (1): total -0.01 to -0.02%, round-1 mean
   to -0.2% (td p99 -1.9%); real OOF pool 812 -> 800, big 220 -> 264, heavy 587 -> 483, td 193 -> 213 (small
   sets: noise either way).

A/B `fc7-r1b-e` (= 09746f6a) on `fc7-w` against `astraeus-5166d1c`: **50.8% (49.9-51.8)**, 10,240 games (r1-e
read 50.9%). OOF 64,972 / 71,959 (-9.7%; r1-e 67,429, so -3.6% on r1's), by rounds: 1: 4,120 / 6,269 (r1-e
4,741: -13%), 2-10: 3,296 / 6,097 (r1-e 4,277: -23%), 11-60: 8,673 / 9,214, 61-300: 15,550 / 15,827, 300+:
33,333 / 34,552. Fuel a turn mean 50,572 / 51,056, p50 47,950 / 48,750, p99 92,350 / 92,850, at or over 100k
0.24% / 0.25%.

Dropped:
- b: recall_line's first-round `enemy_within_strike` shortcut on every round. 100M identical, rounds 2-3
  OOF 357 -> 241, but total fuel +0.12% (pool: ~280k turns dearer against 22k cheaper; the shortcut's own
  test costs more than the foes it saves on most turns). Replaced by (2).
- b3: (2) with the full `possible_within` test in place of the box bound: no gain over (2) (mean +0.7).
- c: `cambc::detail::check` forced always_inline (forward declaration with the attribute in unity.cpp, ~190
  calls a turn): mean +1,136 a turn, p99 +39k, wasm +344 KB (worse codegen around it). Reverted.

Round-1 census (`variants/fc7-r1b-cen`, 400 maps, 100M; heavy turns spend ~119k before the farm loop):
world 78k (build_static 42k: static_camps 25k, crossings 4.4k; update 13k; init_beliefs 12.4k: champions 6.7k,
camps 5.5k; ally_spawn_field 6.7k), siege 11.7k (altars_sealed 9.6k: rebuild 6k, live 2.6k), prices 6.9k,
hops 6k, comms 2k. farm_turn's own pre-loop (marks, 4,276 turns): 15k, of which `prices()` 8.6k (best_emblem's
first evaluation: current_emblem over every candidate, income_prior, upkeep), exposure table 2.0k, the drafted
lead order 1.0k, `room` setup 0.7k; the rest under 0.3k each. Not movable out of round 1: from_ally_spawn
(the loop reads it), crossings (dashers' static walls are read pre-loop), siege's access.

Rounds 2-10 OOF turns (CTR traces, 10 rounds): update ~19k (the first track of an enemy ~8k), approach_walk
20-38k (round 1's queue never prepared it), recall_line's strike foes ~11k (now (2)), prices ~3k,
nearest_groups and group_hops/hops ~18k in round 3. Most is round-1 queue work that ran out of room.

Open: `prices()`' first evaluation (8.6k in round 1; could be computed for the pinned learned emblem only,
but its passive candidates read other prices, so exactness needs care); `in_camp_pocket`'s spawn shortcut
(pockets are off the walk, the walk holds the spawn: exact, but may move hops cost to round 2);
ChampionBelief built from a template copy (~1.5-2k a body); raw imports for the hottest SDK getters
(~190 `check` calls a turn at ~6 each) instead of forcing the inline.

## front

Branch `fc7-front` (on merge 3, 2f7ac39a). Area: the fight turn's decision before the strike search (`channels`,
`want_home`, the world update). **Nothing shipped**: no exact lever of 1k or more was found that earlier workers had
not already taken; the measurements below say where the fuel goes and why each lead is dead.

### What `channels` is

- `start_recall` begins a feint recall at every turn end (bot.cc), so nearly every turn opens recalling, and
  `continue_recall` runs `want_home` first, whatever follows. The census's `channels` is therefore want_home (the
  stand) plus a little: on OOF-first turns with channels >= 5k (heavy + 16 pool maps, real budget, 878 turns),
  channels 28.5k = `want_home` 26.6k + the rest of continue_recall ~1.3k when it is over 1k (36% of them).
- `home` is cached and read by decide's `leave`: want_home runs once a turn, again only after a ward
  (`place_ward`, `reveal_ward`) or shards (`home.reset()`): decide's own `want_home` scope is over 1k on 5% of
  those turns (~20k then). That second run reads the ward's new sight, so it cannot be skipped exactly; nor can the
  ward go first (a channel refuses it, and a restarted recall is a turn longer).
- continue_recall after want_home (`cr.after`, census 4, 22,951 turns): ~540 a turn over all turns. Of it,
  `farm_reprice` (the 404 re-pick during a kept recall, a full farm turn, 19-38k when it runs) ~110, wants_shop ~45,
  recall_to_bank ~80, holding_capture ~110. Reordering the shop test's cheap `channel < steps` before `wants_shop`
  is not exact: `prices()` keeps hysteresis state, so skipping a call changes later prices.

### Where want_home's fuel goes on fight turns (census 2/3, heavy set, OOF-first with channels >= 5k)

- stand_lost_at 21-22.6k: the trade 10-10.7k (the sim through fight_of/new_fight 9.2k, the direct walker/camp path
  2.1-2.5k on ~20%); stand_reach 6.5-7k (Reach builds 4.5k, about one per visible enemy: 2.4 builds a turn with
  3-6 in sight, so no repeats; blows and unseen approaches the rest); roster 1.5k, walks 1.0k, lethal 1.0k.
- drawn_home 2.6k on 72% (nearly all `in_pack_zone`), camp_trapped 2.0k on 58% (find_members on first use, the
  exit field). The finer labels inflate these: a census scope costs ~100-170, and `pz.*` / `sr.*` run per enemy.
- The world update before it: 13.4k (enemies 3.2k at 6 calls, allies 2.0k at 5.7 calls, camps 3.8k, rank_turns
  2.1k on 92%).

### Leads checked and dropped (measured or by argument)

- **`update_champion`'s 22 calls**: the profiler's heavy turns are out-of-fuel turns merged with their late
  continuation (two updates). Census: allies 5.7 + enemies 6.0 calls a turn = one full update of every champion plus
  one observe (see_again, comms send's refresh). No champion is re-read with unchanged inputs: observe() already
  returns after the stats for one seen this turn. ~340 a call is a dozen host reads; the line profile is flat (the
  largest pieces: the `items_key` float compare ~13 a call, a second `damage_scale` ~12). Too small to bench.
- **find_members repeats across Safety rebuilds** (2-4 a fight turn, ~600 each): a debug copy hashed each call's
  output (members and tie-only hits). 217,782 calls on 12 heavy maps; 3,406 equal the previous call of the same
  turn. Dead.
- **Reach rebuilds**: at most one build per visible enemy a turn (above); `sets_reusable_` already covers the rest.
- **Lazy `camp_exit_field` in camp_trapped** (a field-free bound first): the field is memoised per round, champion
  and cap with the camp area of the Safety it was first built with; built later (after a see_again) it reads other
  members and differs. And the only field-free bound (cap steps out) is far looser than the field's.
- **Pack members' boxes**: `pack_members_of` is once per round and vision; `possible_box`'s loop is ~180 a turn.
- **wants_shop reorder** in continue_recall: not exact (prices' hysteresis), and ~45 a turn.

### Function profile (fc7-m2 self-play, heavy set, 693 heavy merged turns)

Self per heavy turn: plan_strikes 10.2k, act<false> 8.2k (14.8 calls), update_champion 7.4k (22), Reach::build 6.0k
(4.3), farm_turn 4.6k, Reach::at 4.5k (13.3), simulate 4.2k, find_members 3.8k (1.8), rank_turns 3.4k, update_camp
3.1k (3.3), set_turn_order 3.0k (0.8), grow 3.0k, step_guard_cover 2.8k, update_camps 2.4k, Safety::blow 2.2k (22.7),
pack_members_of 2.0k (3.0), team_pressed 2.0k, turns_before_ours 2.0k (13.9), strike_memo 1.9k (20). A -g line
profile (`/tmp/fc7/front/prof-g`) is flat: the largest lines are `World::slot` 1.0k, `teleport_pending` 0.9k,
`struck` 0.7k and `raw_output` 0.7k a heavy turn, spread over hundreds of calls.

### Open (small, exact)

- update_champion: one `damage_scale` (keep the value for the end), a bitwise `items_key` compare (all positive
  finite values): ~25 a visible champion, ~250 a fight turn.
- `output()` (`raw_output`, 0.7k a heavy turn) memoised per champion on (type, strength, focus) bits.
- `set_turn_order` (3.9k a call, the turn's tail): not in this area; nobody has profiled it this campaign.

## merge 4

Merged `fc7-r1b`'s own commits (0d8daec8, 09746f6a, notes a4bca177; its base `fc7-r1` was in merge 3) and
`fc7-front`'s notes (f7ec0a02) as CHANGES 427, plus one merge commit: draft.cc pins `cambc::champion_designs` and
`cambc::draft_memory` by name and type (`static_assert`), so an SDK that renames or retypes them fails to compile
rather than silently building them again. Nothing dropped. Frozen as `bots/variants/fc7-m4`.

Review:
- SDK skip (0d8daec8): in `sdk/cpp/cambc.h` the two globals are only defined, never read; no SDK function reads
  either (the only readers are `sdk/cpp/tests`). Building a design (`champion(champion_type)` → `load_design`) is
  per object, with no shared cache, so skipping the 13 builds leaves no other SDK state unset. The bot reads neither
  (grep over `bots/astraeus/src`): the draft bot writes its plan through the raw `sdk_bc_submit_draft_memory` (the
  old `operator=` added only an `is_draft()` check, and `write_plan` runs only in the draft), and every instance reads
  its `DraftPlan` through `capture_draft_memory` at the top of `main()`, before any `read_draft_plan` (its one
  caller is World's spawn read in play): the same bytes as the SDK's start-up snapshot, since nothing writes draft
  memory between start-up and `main()`. Toolchain: wasm uses the 32-bit (ARM) guard ABI; unity.o's guards are weak
  (`w O DATA .hidden`, size 4), sdk_skip.o's global; `wasm-ld --trace-symbol` resolves both to sdk_skip.o, and in
  the built `bot.wasm` / `bot-injected.wasm` the guards' data bytes (102784, 102788) are 1 and the two
  `__cxx_global_var_init` test bit 0 and branch over the build. `cmake/CMakeLists.txt` globs `src/*.cpp`, so the
  ladder build compiles sdk_skip.cpp too.
- Reach bound (09746f6a): both functions return true only within `strike.reach` (+ turns / radius), or
  `fight_reach` + turns - 1; every Strike is clamped to `Strike::max_reach` (compute_strike's `add`, the widened
  strike's `min`, the ahead strike's max of two clamped ones), and `max_reach` (6) is one past the table's widest
  one-turn reach (static_assert). `enemy_reach::within` returns false past Chebyshev x, and `possible_within`
  tests `possible_box.meets` itself (monotone in r), so the skip drops only enemies that could not return true.
  Building the foe later is the same foe: Safety's beliefs are fixed for its life (see_again / see_stuns rebuild it);
  `known_`'s other reader (`lethal`'s no-threat shortcut) and `credible_unseen`'s `counted_` shortcut give the
  same answers either way.

100M, all six sets byte-identical to `base-*-100M.json` (`m4-*`; 342/342):

| set | total vs base | total vs m3 | mean base -> m4 | p99 base -> m4 | max base -> m4 | over 100k base / m3 / m4 | round 1 mean vs base / m3 |
|---|---|---|---|---|---|---|---|
| def | -1.47% | -0.03% | 51,433 -> 50,684 | 97,736 -> 96,653 | 215,787 -> 215,456 | 704 / 639 / 638 | -5.2% / -2.7% |
| wide | -1.44% | -0.04% | 50,497 -> 49,776 | 103,147 -> 102,233 | 268,444 -> 265,539 | 3,086 / 2,923 / 2,918 | -5.2% / -2.8% |
| pool | -1.37% | -0.02% | 53,464 -> 52,744 | 107,853 -> 105,242 | 356,280 -> 372,030 | 9,367 / 8,076 / 8,080 | -5.0% / -2.7% |
| big | -1.86% | -0.03% | 61,397 -> 60,263 | 104,092 -> 101,203 | 287,312 -> 323,434 | 2,523 / 2,111 / 2,105 | -5.1% / -2.3% |
| heavy | -1.47% | -0.03% | 52,013 -> 51,259 | 119,186 -> 118,089 | 360,603 -> 374,296 | 5,556 / 5,246 / 5,242 | -5.2% / -2.5% |
| td | -1.13% | -0.02% | 53,524 -> 52,932 | 100,172 -> 98,552 | 275,080 -> 271,081 | 2,744 / 2,467 / 2,460 | -5.2% / -2.8% |

Over 100k in the six sets: 23,980 (base) -> 21,462 (m3) -> 21,443 (m4). Against m3, more turns read dearer than
cheaper (codegen; tens of fuel) while round 1 is ~6.1k cheaper on every body. Real budget (indicative), OOF base ->
m3 -> m4: pool 770 -> 709 -> 715, big 248 -> 229 -> 213, heavy 707 -> 534 -> 489, td 209 -> 230 -> 222 (1,934 ->
1,702 -> 1,639).

A/B `m4` (`fc7-m`, 10,240 games, real budget) against the base: **50.8% (49.9-51.8)**. OOF 62,822 / 70,569
(**-11.0%**; m3 read -9.9%), by rounds: 1: 4,233 / 6,274 (-33%; m3 4,985), 2-10: 3,415 / 6,358 (-46%; m3 4,413),
11-60: 8,809 / 9,341 (-6%), 61-300: 15,100 / 16,322 (-7%), 300+: 31,265 / 32,274 (-3%). Runs of 50+ OOF 525 / 702.
Fuel a turn mean 50,476 / 51,098, p50 47,850 / 48,750, p90 86,450 / 86,550, p99 92,250 / 92,850, at or over 100k
0.24% / 0.25%. Shortcuts 2.125M / 2.270M: farm-partial-evaluation 1,012k / 1,071k, step-guard-entry 574k / 588k,
prey-cut-short 153k / 164k, turn-order 120k / 133k, step-guard-look 75.1k / 75.5k, out-of-fuel 62.8k / 70.6k.

Open leads (batch 4, with merges 1-3's still open, deduplicated):
- Round 1: `prices()`' first evaluation (8.6k; exactness needs care: passive candidates read other prices),
  `altars_sealed` (4.7-13k) and `init_beliefs` (11-12k; ChampionBelief from a template copy ~1.5-2k a body),
  `build_static`'s static_camps 25k; `in_camp_pocket`'s spawn shortcut.
- Rounds 2-10 OOF turns: approach_walk 20-38k and nearest_groups / group_hops ~18k (round-1 queue work that ran out
  of room), the first track of an enemy ~8k.
- `walk_deaths` and the no-open branch of `rebuild_altar_access` flood uncapped; `returns_go_round`'s fallback ~11k
  on 100x100.
- The siege body's stand loop (`fire_at` per goal tile x member, 13k on 4% of OOF-first turns); `siege_candidate` /
  `altars_sealed` self ~1k on 22-42% of heavy turns.
- prey's own loop (3.7k on 29% of OOF-first turns) and chase's walk after it.
- Heavy fight turns: plan_strikes self 10-11k, `act<false>` 7-8k, Reach build/at 9-10k, `step_guard_cover` ~3k,
  `set_turn_order` (3.9k a call, unprofiled), `turns_before_ours` / `strike_memo` / `next_turn_round` 1-2k each.
- Small and exact: update_champion's second `damage_scale` and a bitwise `items_key` compare (~250 a fight turn),
  `raw_output` memoised per champion (0.7k a heavy turn), raw imports for the hottest SDK getters (~190 `check`
  calls a turn; forcing the inline lost).
- The late turn's stale tail (~3k before its first `throw_if_stale`) and the StaleTurn unwind's 2.1k floor.
- Fuel gates are not worth building: the anytime strike search and the late margin read level on win rate.

## tail

Branch `fc7-tail` on main 2f7ac39a (merges 1-3): e92af917, 765d317c, 8506f4b7, 70e44288; frozen tip
`variants/fc7-tail-b` (tail-a = e92af917 alone). Area: the turn's tail (turn order, the update's rank work) and the
stale-turn unwind.

### Where the fuel goes (function profile, real-budget self-play, heavy + 64 pool maps, all turns)
- Per turn over all turns: `read_priorities` 671, `rank_turns` 601, `plain_priority` 386, `comms::receive` 375,
  `comms::send` 360, `may_escape` 131, `set_turn_order` self 103, `live_enemies` 101, `live_self` 74, `danger` 67,
  `publish_turn_order` 63 (copy with the turn-order parts `noinline`). set_turn_order and its parts are ~1.1-1.3k a
  turn, spread over a dozen functions of 50-400 each; on heavy turns ~2.7k (may_escape 389, offer_kills 346,
  side_damage 343, live_enemies 305, danger 289, plain_priority 264, ally_next_rank 495 at 2.8 calls).
- **`rank_turns` was 2.4k a call on 6v6 maps** (5 picks + Cassi & Issac) with both teams' ranks stale (62% of
  updates there), 1.1k with one: ~550 a pass for 6 champions. Debug-bracket timings, one elk-arena game: insertion
  sort as in the base 1,064 a side; the same loops unvectorised 1,210; counting ranks in scalar 64-bit keys 1,421,
  in a 16-lane SIMD loop 1,400; two straight i32x4 vectors (below) 852. A memo of each pass's inputs would hit 11%
  (allies) to 34% (enemies): payloads change every turn.
- **A stale throw costs 2,085 from throw to catch (p10 2,079, p90 2,894; 432 throws, heavy set, real budget)**:
  `__gxx_personality_wasm0` ~520-590 a call and 2.2 calls a throw (aph::play_turn's `catch (std::exception)`
  around act, then main's run()), dlmalloc ~200 and `__cxa_allocate_exception` ~125, then the free. 96% of the
  throws come from inside act. A personality call's cost is mostly fixed: moving run("decide") into a small
  noinline function cut 255 (2,085 -> 1,830), not the ~500 a short handler list would.

### Shipped (identical at 100M on def, wide, pool, big, heavy, td: 342/342 against base-* and m3-*)
1. e92af917 **rank_turns counts the champions ahead of each with two i32x4 vectors** (`rank_by`: per champion, a
   splat, gt and eq bitmasks, popcount of those ahead or tied at a lower index), not an insertion sort; up to 8 a
   team, a scalar loop past that. Exact: the base's sort is a full sort under the strict order (priority
   descending, index ascending), so each rank is the count of those before it; next ranks copy this round's on the
   same `same` test, and `turn_order_` (only the sort's start) is gone. Bench (tail-a): total vs m3 -0.10% (big)
   to -0.25% (pool), over 100k 21,462 -> 21,104.
2. 765d317c **a StaleTurn thrown in act (or in see_stuns/set_turn_order) is caught at that try block, which
   returns**: the same frames unwind and the same destructors (`unuse`, `safety`, the decide meter) run in the same
   order, and play_turn returns as the exception did (run()'s StaleTurn handler does nothing; Instance::play_turn
   then sees `is_stale()` as before). One personality call and no second unwind: **2,085 -> 1,093 (p50) a throw**.
   At 100M it never fires. Real budget (heavy set, m3 + this alone, `tail-st-heavy-real.json` against
   `m3-heavy-real.json`): 18 of 50 games identical; all 32 others first diverge after an out-of-fuel turn, 19 of
   them at a late turn exactly 991 cheaper (the unwind), the rest at late turns that spend the fuel kept.
3. 8506f4b7 **our own slot this round and next is kept from the update** (`my_slot_now/next`): only update() moves
   ranks (read_priorities' prev_rank, rank_turns) and `round`, so slot(me(), round) and slot(me(), round + 1) are
   fixed until the next update. Used by next_turn_round, turns_before_ours, threat checks, update_champion's
   shield/channel expiry, hold_start and now() (all after the update sets them).
4. 70e44288 update_champion works out the damage scale again only where `dealt` may have changed (the emblem read);
   the emblem key is compared as bits (stats are never NaN or -0, and a needless re-read reads the same emblems).
- All four, 100M (`tail-b-*`), 342/342 identical:

| set | total vs base | total vs m3 | mean m3 -> b | p99 m3 -> b | max m3 -> b | over 100k base / m3 / b | round 1 mean vs m3 |
|---|---|---|---|---|---|---|---|
| def | -1.90% | -0.47% | 50,695 -> 50,455 | 96,731 -> 96,110 | 215,456 -> 213,822 | 704 / 639 / 617 | -0.16% |
| wide | -1.88% | -0.48% | 49,787 -> 49,549 | 102,248 -> 101,532 | 265,539 -> 264,018 | 3,086 / 2,923 / 2,793 | -0.12% |
| pool | -1.86% | -0.52% | 52,748 -> 52,470 | 105,265 -> 104,239 | 372,030 -> 371,898 | 9,367 / 8,076 / 7,648 | -0.15% |
| big | -2.03% | -0.20% | 60,273 -> 60,153 | 101,291 -> 100,714 | 331,323 -> 329,790 | 2,523 / 2,111 / 2,048 | -0.24% |
| heavy | -1.91% | -0.47% | 51,266 -> 51,022 | 118,143 -> 117,398 | 374,296 -> 374,130 | 5,556 / 5,246 / 5,038 | -0.15% |
| td | -1.56% | -0.46% | 52,937 -> 52,692 | 98,566 -> 97,927 | 271,081 -> 269,619 | 2,744 / 2,467 / 2,360 | -0.21% |

- Over 100k in the six sets: 21,462 (m3) -> 21,104 (a) -> 20,504 (b), -4.5%.
- Real budget (indicative), OOF base / m3 / a / b: pool 770 / 709 / 709 / 627, big 248 / 229 / 194 / 233, heavy
  707 / 534 / 557 / 467, td 209 / 230 / 225 / 171 (1,934 / 1,702 / 1,685 / 1,498). Shortcuts m3 -> b 63.6k ->
  60.7k (turn-order 3,686 -> 3,324).

### Dropped / not built
- **An earlier staleness test on the resume path is not exact.** A turn that ran out resumes wherever wasm ran
  dry; the base runs its stale tail on to the next `throw_if_stale`, and what that tail writes on the way
  (Memory fields such as `claim`, Pathing's kept routes, World notes) is read by later turns. Abandoning it sooner
  writes less, so it changes play. A free detector exists (a fuel read above the last one means a new budget,
  checked against the round only then), but it can only be a behaviour change judged by A/B; the stale tail is
  ~0.05% of turns.
- Avoiding the exception's allocation: `__cxa_allocate_exception` and the free sit in libc++abi's object with
  `__cxa_throw`, and `aligned_alloc`/`free` in wasi-libc's dlmalloc object with `malloc`: neither can be
  overridden alone. `std::rethrow_exception` allocates a dependent exception. ~350 a throw left.
- Run("decide") in its own noinline frame (-255 a throw on the 4% of throws not from act): left out, it changes
  the flattened play_turn for little.
- A memo of rank passes keyed on their priorities: 11-34% hits (above).
- plain_priority's unseen-enemy binary search: 0.05 candidates a call; the loop is 234 a call, mostly the
  `possible_within` box tests. Moving `credible_unseen` first would build foes' strikes for enemies the board test
  drops.

### A/B
`tail-b` (`fc7-w`, 10,240 games, real budget) against the base: **50.3% (49.3-51.2)**. OOF 59,232 / 72,016
(-17.8%; m3's was 63,798 / 70,795), in 6,659 / 7,104 games. Mean fuel a turn 50,281 / 51,120, p99 91,850 / 92,850,
at or over 100k 0.23% / 0.26%. Logs `replays/fuel/fc7/ab/tail-b.*`.

### Open
- `read_priorities` (~70 a champion, 1.4k a heavy 6v6 turn, two host reads each) and `update_champion` (250 a call,
  26 a heavy turn) are the update's largest parts left; no repeated piece found.
- `ally_next_rank` (287 a call, 2.8 a heavy turn, n^2 inside `side_damage`): one rank pass per packed value.
- The tail on OOF-first turns (act_end entered with ~0.7k): place_lock, place_ward/ward_bushes are where they run
  out; set_turn_order's parts are each a few hundred.

## merge 5

Merged `fc7-tail` (branched from merge 3, so cherry-picked onto merge 4's tip; the code applied cleanly, NOTES.md
kept both sides) as CHANGES 428: e92af917 (`rank_turns` by counting), 765d317c (StaleTurn caught in
`aph::play_turn`), 8506f4b7 (`my_slot_now/next`), 70e44288 (damage scale inside the emblem read, bitwise key), and
its notes (ed65175d, 6227ed91, bfb0fa7d). Nothing dropped. Frozen as `bots/variants/fc7-m5`.

Review:
- rank_turns: the base's insertion sort is a full sort under a strict total order (priority descending, index
  ascending), so its result does not depend on the starting order and each rank is the count of members strictly
  before it: `p[j] > p[i]`, or equal with `j < i`, which `rank_by` counts (both the i32x4 path, with lanes from n on
  masked by `valid`, and the scalar path past 8). Dead champions are ranked as before (nothing filters by `alive`),
  both teams and Cassi & Issac (two allies) go through the same loop, the cap of 16 is unchanged, and the
  `same` copy of ranks into next ranks is the old passes 2/3 copy. `turn_order_` had no reader other than the sort
  itself (grep). The lanes past n are an uninitialised `Unwritten` union, read only through the intrinsic load and
  masked out.
- StaleTurn catch: `StaleTurn` is not a `std::exception`, so before it left `aph::play_turn` past both handlers;
  now the handler returns. The same frames inside act unwind; play_turn's locals (`unuse`, then `safety`) are
  destroyed in the same order on return as on the unwind; the lambda's `FuelMeter{"decide"}` ends as before.
  run()'s StaleTurn handler was empty, and run("decide")'s result is unused. Both throw sites require
  `is_stale()` (`round_now() != turn_round()` with `finish_late()` false; `turn_round()` is World::update's round);
  `finish_late()` is set only in Instance::play_turn, so after the return `finish_late() = late && resumed()` is
  still false and `Instance::play_turn` returns at `world->is_stale()`, skipping the turn end, comms send, debug and
  queue exactly as before. The only differences are the exception's free happening before the destructors (malloc,
  outside the arena) and the fuel; real-budget divergence after an OOF turn is the expected fuel-only effect.
- my_slot_now/next: `slot()` reads `round`, `team_a_`, `ally_count_`/`enemy_count_` and the self's
  `rank`/`next_rank`/`prev_rank`. `round` is written only at the top of `update()`; ranks only in
  `read_priorities` (prev_rank, priorities) and `rank_turns`, both in `update()` before the new line; counts and
  team in `init_beliefs`. A priority written this turn (`set_turn_order`/`publish_turn_order`) changes no belief
  (the readers of `next_priority` in turn_order.cc and comms.cc only read), and applies next round
  (rounds.team_order). An out-of-fuel resume runs no update, so round and ranks, and the cached slots, are those of
  the turn's own update. No user (`now()`, `hold_start`, update_champion's expiry, `grow`/`camp_settled`) runs
  before the slots are set inside update (read_vision, tributing_enemies and read_priorities call none); if update
  throws before them, the turn returns at `run("world")`.
- Emblem key: `std::array<float, 4>` has no padding; bits differ from `!=` only for NaN (engine stats are never
  NaN) and ±0 (only a needless re-read of the same emblems). Between update_champion's first `scale` and the old
  last line only `dealt` can change (health and max health are written above it, the channel block returns
  earlier), so the scale is recomputed only inside the emblem read, with the same expression.

100M, all six sets byte-identical to `base-*-100M.json` (`m5-*`; 342/342):

| set | total vs base | total vs m4 | mean base -> m5 | p99 base -> m5 | max base -> m5 | over 100k base / m4 / m5 | round 1 mean vs base |
|---|---|---|---|---|---|---|---|
| def | -1.93% | -0.47% | 51,433 -> 50,446 | 97,736 -> 96,045 | 215,787 -> 213,822 | 704 / 638 / 614 | -5.3% |
| wide | -1.91% | -0.48% | 50,497 -> 49,539 | 103,147 -> 101,564 | 268,444 -> 264,018 | 3,086 / 2,918 / 2,790 | -5.3% |
| pool | -1.88% | -0.52% | 53,464 -> 52,467 | 107,853 -> 104,230 | 356,280 -> 371,898 | 9,367 / 8,080 / 7,644 | -5.1% |
| big | -2.05% | -0.20% | 61,397 -> 60,144 | 104,092 -> 100,703 | 287,312 -> 322,789 | 2,523 / 2,105 / 2,046 | -5.3% |
| heavy | -1.93% | -0.47% | 52,013 -> 51,016 | 119,186 -> 117,339 | 360,603 -> 374,130 | 5,556 / 5,242 / 5,034 | -5.4% |
| td | -1.58% | -0.46% | 53,524 -> 52,688 | 100,172 -> 97,890 | 275,080 -> 269,619 | 2,744 / 2,460 / 2,354 | -5.4% |

Over 100k in the six sets: 23,980 (base) -> 21,443 (m4) -> 20,482 (m5). Real budget (indicative), OOF base -> m4
-> m5: pool 770 -> 715 -> 619, big 248 -> 213 -> 244, heavy 707 -> 489 -> 501, td 209 -> 222 -> 216 (1,934 ->
1,639 -> 1,580).

A/B `m5` (`fc7-m`, 10,240 games, real budget) against the base: **50.9% (49.9-51.8)**. OOF 57,360 / 71,382
(**-19.6%**; m4 read -11.0%), in 6,677 / 7,180 games, by rounds: 1: 4,196 / 6,274 (-33%), 2-10: 3,276 / 6,371
(-49%), 11-60: 7,887 / 9,091 (-13%), 61-300: 13,495 / 16,469 (-18%), 300+: 28,506 / 33,177 (-14%). Runs of 50+
OOF 731 / 813. Fuel a turn mean 50,255 / 51,100, p50 47,550 / 48,750, p90 86,450 / 86,550, p99 91,950 / 92,850, at
or over 100k 0.23% / 0.26%. Shortcuts 2.051M / 2.268M: farm-partial-evaluation 987k / 1,069k, step-guard-entry
552k / 590k, prey-cut-short 141k / 161k, turn-order 112k / 134k, step-guard-look 76.2k / 74.8k, out-of-fuel
57.4k / 71.4k.

Open leads (batch 5, with merges 1-4's still open, deduplicated):
- Round 1: `prices()`' first evaluation (8.6k; passive candidates read other prices), `altars_sealed` (4.7-13k),
  `init_beliefs` (11-12k; ChampionBelief from a template copy ~1.5-2k a body), `build_static`'s static_camps 25k;
  `in_camp_pocket`'s spawn shortcut.
- Rounds 2-10 OOF turns: approach_walk 20-38k and nearest_groups / group_hops ~18k (round-1 queue work that ran out
  of room), the first track of an enemy ~8k.
- `walk_deaths` and the no-open branch of `rebuild_altar_access` flood uncapped; `returns_go_round`'s fallback ~11k
  on 100x100.
- The siege body's stand loop (`fire_at` per goal tile x member, 13k on 4% of OOF-first turns); `siege_candidate` /
  `altars_sealed` self ~1k on 22-42% of heavy turns.
- prey's own loop (3.7k on 29% of OOF-first turns) and chase's walk after it.
- Heavy fight turns: plan_strikes self 10-11k, `act<false>` 7-8k, Reach build/at 9-10k, `step_guard_cover` ~3k,
  `strike_memo` 1-2k.
- The update: `read_priorities` (~70 a champion, 1.4k a heavy 6v6 turn) and `update_champion` (250 a call, 26 a
  heavy turn); set_turn_order's parts (~1.1-1.3k a turn, 2.7k heavy, a dozen functions of 50-400); `ally_next_rank`
  (287 a call, n^2 inside `side_damage`).
- Small and exact: `raw_output` memoised per champion (0.7k a heavy turn), raw imports for the hottest SDK getters
  (~190 `check` calls a turn; forcing the inline lost).
- The tail: the late turn's stale tail (~3k before its first `throw_if_stale`; an earlier staleness test is a play
  change, A/B only), the throw's ~350 of allocation left (not overridable), run("decide") in its own frame (-255 on
  4% of throws); OOF-first turns run out in place_lock, place_ward/ward_bushes.
- Fuel gates are not worth building: the anytime strike search and the late margin read level on win rate.

## r1c

Branch `fc7-r1c` from r1b's tip (a4bca177); tip 7c58b49b, frozen as `variants/fc7-r1c-i`. Seven exact
changes, mostly zero-fills: in WASM, memory.fill and memory.copy cost a fuel a byte, so value-initialising
a struct (`make_unique<T>()`, `resize`/`emplace_back` with a defaulted constructor, `{}` member
initialisers on arrays) is paid in full. Members read only after they are written can be left unwritten.

Deltas are on the 2-round harness (4,096 games against fc7-m2), 100M, mean fuel a body in round 1. Every
change was 4,096/4,096 identical.
- 4c4e6da1: `current_emblem` computes the current build's upkeep terms (`UpkeepBasis`) and fight scale once,
  not once a candidate: -418.
- 63cd6be3: an enemy without a dash builds no `undashed` board (`ChampionBelief(Walker)`): -357.
- 980680f4: StaticMap::build reads the enemy spawn's and altars' tiles into static 64-tile buffers
  (positions_into; falls back to positions() beyond 64): -285. A local array cost +242, because vec2's
  initialisers zero it.
- 10f22588: a spawn that fills its bounding box writes landing_tiles row by row from the box (for team B,
  the mirrored box, mirrored back), without the sort: -249 (B -461, A -37).
- dcc82a5a: World and StaticMap are made with `new T` (default-initialised; the bump arena hands out zeroed
  memory and the constructors set what they need): -658, p50 -1,300 (StaticMap alone -327).
- efd92caa: ChampionBelief's default constructor is user-provided; `tracked_` drops its `{}` (read only
  below tracked_count_): -520, p50 -833.
- 7c58b49b: StandReach (camps.cc) has a user-provided constructor and leaves exposed (in an anonymous
  union, because pair<vec2,vec2> zeroes), exposed_box, kind_strength and kind_bits unwritten. They are read
  only below n_exposed or kinds, and the build writes them: -1,568, p10 -4,560. The resize had been zeroing
  108 bytes a group, on every stand_reach table.
- Total against r1b-e: -4,054 a body (p50 -5,491).

Real budget, against r1b-e:
- 2-round harness: round-1 OOF 1,099 -> 839.
- 10-round harness: 100M is 4,096/4,096 identical, -511 a turn over rounds 2-10. Real-budget OOF by
  rounds: round 1 1,100 -> 844, rounds 2-3 305 -> 277, rounds 4-10 153 -> 119.

Bench at 100M, against r1b-b2. All sets are identical, and turns are -0.06% to -0.11% overall.
- Round-1 mean: def -2.1%, wide -1.7%, pool -1.8%, big -2.9%, heavy -2.8%, td -2.1%.
- Round-1 p99: -2.2% to -2.6% on every set.
- Real sets (single games diverge, so this is noise): OOF pool 800 -> 736, big 264 -> 226, heavy
  483 -> 718, td 213 -> 255.

A/B on fc7-w against astraeus-5166d1c, 10,240 games: 50.5% (CI 49.6-51.5). OOF turns: 64,037 vs 72,889
(r1b-e read 64,972 vs 71,959). Turn mean 50,566 vs 51,062, p99 92,350 vs 92,950.

Dropped:
- a: camp_tiles read via import_linear_buffer: +144 mean.
- g: StandReach with only `StandReach() {}`: 0 change, because the members' own `{}` still zero.
- The profiler isn't usable for round 1 (it plays whole games).

Census, round-1 means: build_static 32k (sc.loop 17k, about 40 a member, already tight), init_beliefs
11.6k, champion_enemy 8.7k (board ops in prune/track), siege_candidate 7.9k (altars_sealed 6.4k), prices
5.9k, ally_spawn_field 5k (host field).

Open leads, mostly outside round-1 world/economy (taken from disassembly bulk ops by function):
- Pathing route, step_route and travel copy 76-byte Route structs (memory.copy 76, six a step_route) on
  every walking turn.
- Other fills: World::World 89; the Pathing constructor 100+108; farm_turn 128 twice; altar_usable 88;
  HomeBoard 257 and home_fires 256.
- The fight Search's fills: read_spells 648, touch1 324, trade copies 381 and 768, plan_strikes.
- near_enemy_spawn draws a square per tile; live_camps assigns draw_all.
- Round-1 OOF stacks: farm.loop about 64, farm.post (attack tile decode, walk_on) about 60, turn_order and
  offer_escape about 30.
- Rounds 2-10 OOF turns: make_field_cap 13.6k, track 9.2k, group_hops 6.5k, approach 6.4k.

## merge 6

Merged `fc7-r1c` (from r1b a4bca177, whose code came in with merge 4; r1c's own commits cherry-picked onto merge
5's tip, the code applied cleanly, NOTES.md kept both sides) as CHANGES 430: 4c4e6da1 (`current_emblem`'s
`UpkeepBasis` and fight scale once), 63cd6be3 (no `undashed` board for an enemy without a dash), 980680f4 (enemy
spawn and altar tiles into static 64-tile buffers), 10f22588 (a spawn filling its box gets `landing_tiles` from
the box's rows), dcc82a5a (World and StaticMap made with `new T`), efd92caa (ChampionBelief's user-provided
default constructor; `tracked_` loses `{}`), 7c58b49b (StandReach's exposure and kind arrays unwritten), notes
e0774ba2. Nothing dropped. Frozen as `bots/variants/fc7-m6`.

Review:
- UpkeepBasis: each hoisted term is the old sub-expression in the old evaluation order (`now_dealt` = the old
  numerator, `camp_turn` = `camp_taken / turns` evaluated first as before, `fight_scale` = `fight_weight *
  fight_share()` before the `max`); WASM has no FMA contraction, so every price is bit-identical.
- `undashed` (Walker): every read or write is behind `has_dash()` of the belief's fixed type (`also_undashed`,
  `mark_fixed`, `fix`, `grow`'s `undashed_read`/`undashed_kept`, the lineage copy in `track`, the prune at 2409);
  `facts(type)` is a static per-type table, set at the emplace from the same `type`, and beliefs are never copied
  (copies deleted), only moved.
- Static buffers: the spans are read only inside `build` (enemy centre, box, near_enemy_spawn; the altars loop);
  `positions_into` gives `positions()`' order; past 64 tiles the old `positions()` (spawns have 9-16 tiles).
- Landing order: for a spawn filling its box, sorting by (y, x) is the box's rows; for B the sort key is the
  mirror tile, and every symmetry maps a box to a box, so the keys in order are the mirrored box's rows and the
  tiles their mirrors: the old sort's order (= `cambc-rules.yaml` recall.landing). Spawns not filling their box
  take the old sorts. Empty spawn: old path.
- `new T`: the arena is a bump allocator that never reuses memory (`give` frees only malloc'd blocks), World is
  made once (`if (!world)`), StaticMap once per instance (`if (!static_)`, retried after a throw into fresh arena
  memory; the draft instance builds its own once). Every StaticMap, World, ChampionBelief, PlanHeader, PlanIndex,
  DraftSteps, TileBox, GrowBox and Moment member has an initialiser or a constructor, so value-initialisation's
  zero fill was overwritten everywhere; `World::Tracked` entries are written whole before being read below
  `tracked_count_`. StandReach: `kind_strength` read only below `kinds`, `kind_bits` assigned `{}` by the build,
  `exposed`/`exposed_box` only below `n_exposed` (counts set before the arrays are filled; the tables are built
  once a group, never rebuilt since groups never change). No struct here is compared, hashed or memcmp'd whole
  (the defaulted `==` in the bot are on other keys and compare members).
- Empirical check: a copy with every arena allocation filled with 0xA5 (`fc7-m6-poison`, deleted) was also
  byte-identical to the base on all six 100M sets (342/342), so nothing reads the bytes left unwritten.
- Out-of-fuel during StandReach's build: a half-built table (slot assigned) is returned later, as before; its
  counts only grow after their entries are written, except `n_exposed++` a few instructions before `exposed[k]`'s
  write (fresh arena memory there is zero, as before). Pre-existing, not widened.

100M, all six sets byte-identical to `base-*-100M.json` (`m6-*`; 342/342):

| set | total vs base | total vs m5 | mean base -> m6 | p99 base -> m6 | max base -> m6 | over 100k base / m5 / m6 | round 1 mean base -> m6 |
|---|---|---|---|---|---|---|---|
| def | -2.05% | -0.11% | 51,433 -> 50,393 | 97,736 -> 95,765 | 215,787 -> 213,822 | 704 / 614 / 596 | -7.2% (m5 -2.0%) |
| wide | -2.01% | -0.10% | 50,497 -> 49,493 | 103,147 -> 101,367 | 268,444 -> 264,018 | 3,086 / 2,790 / 2,750 | -6.9% (-1.7%) |
| pool | -1.97% | -0.09% | 53,464 -> 52,426 | 107,853 -> 104,093 | 356,280 -> 371,898 | 9,367 / 7,644 / 7,570 | -6.9% (-1.8%) |
| big | -2.11% | -0.06% | 61,397 -> 60,115 | 104,092 -> 100,363 | 287,312 -> 322,789 | 2,523 / 2,046 / 2,011 | -8.0% (-2.9%) |
| heavy | -2.03% | -0.10% | 52,013 -> 50,972 | 119,186 -> 117,144 | 360,603 -> 374,130 | 5,556 / 5,034 / 4,994 | -8.1% (-2.8%) |
| td | -1.67% | -0.09% | 53,524 -> 52,648 | 100,172 -> 97,647 | 275,080 -> 269,619 | 2,744 / 2,354 / 2,321 | -7.3% (-2.1%) |

(Round 1 here is the bench JSON's round-1 mean over all bodies; "(m5 ...)" is m6 against m5.) Over 100k in the six
sets: 23,980 (base) -> 20,482 (m5) -> 20,242 (m6). Real budget (indicative), OOF base -> m5 -> m6: pool 770 -> 619
-> 653, big 248 -> 244 -> 209, heavy 707 -> 501 -> 409, td 209 -> 216 -> 192 (1,934 -> 1,580 -> 1,463).

A/B `m6` (`fc7-m`, 10,240 games, real budget) against the base: **50.7% (49.7-51.6)**. OOF 55,547 / 70,513
(**-21.2%**; m5 read -19.6%), in 6,547 / 7,177 games, by rounds: 1: 3,354 / 6,272 (-47%; m5 -33%), 2-10: 2,947 /
6,384 (-54%; m5 -49%), 11-60: 7,778 / 8,980 (-13%), 61-300: 13,541 / 16,385 (-17%), 300+: 27,927 / 32,492 (-14%).
Runs of 50+ OOF 895 / 756. Fuel a turn mean 50,210 / 51,086, p50 47,450 / 48,750, p90 86,450 / 86,450, p99 91,850
/ 92,850, at or over 100k 0.23% / 0.25%. Shortcuts 2.007M / 2.249M: farm-partial-evaluation 968k / 1,059k,
step-guard-entry 545k / 585k, prey-cut-short 138k / 158k, turn-order 109k / 133k, step-guard-look 73.9k / 74.8k,
out-of-fuel 55.5k / 70.5k.

Open leads (batch 6, with merges 1-5's still open, deduplicated):
- Round 1: `build_static` 32k (static_camps 25k; sc.loop 17k, ~40 a member), `init_beliefs` 11.6k,
  champion_enemy 8.7k (board ops in prune/track), `prices()`' first evaluation (6-8.6k), `siege_candidate` /
  `altars_sealed` 6.4-13k, ally_spawn_field 5k (host field); `in_camp_pocket`'s spawn shortcut.
- Round-1 OOF stacks: farm.loop ~64, farm.post (attack tile decode, walk_on) ~60, turn_order and offer_escape ~30.
- Rounds 2-10 OOF turns: make_field_cap 13.6k, approach_walk 6-38k, nearest_groups / group_hops 6.5-18k, the first
  track of an enemy 8-9k (round-1 queue work that ran out of room).
- Bulk copies and fills: Pathing route / step_route / travel copy 76-byte Route structs (six a step_route) on every
  walking turn; World::World 89, the Pathing constructor 100+108, farm_turn 128 twice, altar_usable 88, HomeBoard
  257, home_fires 256; the fight Search's (read_spells 648, touch1 324, trade copies 381 and 768, plan_strikes);
  near_enemy_spawn draws a square per tile; live_camps assigns draw_all.
- `walk_deaths` and the no-open branch of `rebuild_altar_access` flood uncapped; `returns_go_round`'s fallback ~11k
  on 100x100.
- The siege body's stand loop (`fire_at` per goal tile x member, 13k on 4% of OOF-first turns).
- prey's own loop (3.7k on 29% of OOF-first turns) and chase's walk after it.
- Heavy fight turns: plan_strikes self 10-11k, `act<false>` 7-8k, Reach build/at 9-10k, `step_guard_cover` ~3k,
  `strike_memo` 1-2k.
- The update: `read_priorities` (~70 a champion), `update_champion` (250 a call); set_turn_order's parts (~1.1-2.7k
  a turn); `ally_next_rank` (287 a call, n^2 inside `side_damage`).
- Small and exact: `raw_output` memoised per champion (0.7k a heavy turn), raw imports for the hottest SDK getters.
- The tail: the late turn's stale tail (~3k before its first `throw_if_stale`; an earlier test is a play change),
  the throw's ~350 of allocation, run("decide") in its own frame; OOF-first turns run out in place_lock,
  place_ward/ward_bushes.
- Fuel gates are not worth building: the anytime strike search and the late margin read level on win rate.

## strike

Branch `fc7-strike` (on merge 5, 3c09e6d1). Area: the strike search (`plan_strikes`: read, grow, price).

### Where the search's fuel goes (debug marks in a copy, heavy + td sets at 100M, 14.7k searches)

Mean per search 22.1k; 38.7k on the 27% over 25k; 56.5k on the 8% over 40k (all / >25k / >40k):
- The step guard is the largest item, and it is not the search's own: the cover (`step_guard_cover` from
  `read_geometry`) 2.8k / 4.5k / 4.9k; the guard worked out in the price loop 2.0k / 7.1k / 16.7k, plus the
  pre-loop `sure < 2` resolve (most of `tile_init`: 1.0k / 2.2k / 3.4k).
- grow 5.0k / 8.9k / 12.3k: children 3.3k / 5.7k / 7.7k (attacks 1.0-2.0k, dash 0.5-1.3k, walk 0.4-0.6k,
  ~750 a node), settle/offer 1.6k / 3.2k / 4.6k (~260 an offer).
- Reach queries (`blow`) 1.5k / 3.2k / 4.1k; per priced tile (camps, gather, striker ranking) 0.9k / 1.6k / 2.1k;
  tile selection 0.6k / 1.0k / 1.3k.
- The foe read ~900 a foe: `viewers` ~400 of it (ward lookup ~115 a search, the row loop ~230; the viewer rows
  always hit their game cache), `partner_bound` 85, the record and buffs 70, `Unit{}` 46, the rest 10-60 each.
- `pathing.blocked()` 924 a search (rebuilt with ~10 whole-board ops when not fresh; shared with the goal's
  routes, which read it next), `terrain_grid` 263 (first use per centre), Search's constructor and the record ~400.
- Second searches in a turn (strike_after, keep_bid) are rare: 414 of 11.7k turns.

### Shipped

- **0d45161a: the search reads the deferred guard's cover on first need, not in `read_geometry`.**
  - Its readers: a tile under `grid_r` from us selected by the price loop (the guard's radius is 1 or 2), the
    `sure < 2` pre-check when fewer than 2 tiles are surely uncovered (the start tile and tiles 3 away), the
    capped tail, and the debug check. Each reads it before the base would have used it.
  - Exact: the cover is a pure function of (world, Safety, here, radius), and nothing between `read_geometry` and
    the price loop changes them (grow only reads). The base's resolve decisions are unchanged: the pre-check
    counts the base's `sure` whenever it could fall below 2, and the loop reads the cover before testing the
    tile's bit. So no guard is ever left deferred that the base worked out (which would let it be worked out
    later from post-hit inputs). Its side effects are memos (Safety's struck foes, Reach builds) and
    `first_pass`, still set while `GuardInputsHeld` holds. No later reader reuses the search's cover:
    `restore_guard` resets route()'s cover memo, and `work_cover` calls `step_guard_cover` again.
  - 100M, all six sets byte-identical to base (342/342), against m5: total -0.01% (big) to -0.06% (wide). Over
    100k m5 -> b: def 614 -> 611, wide 2,790 -> 2,755, pool 7,644 -> 7,596, big 2,046 -> 2,040, heavy 5,034 ->
    5,005, td 2,354 -> 2,331. It fires on ~1% of turns at -2.9k to -3.2k each. On turns the base spent over 100k:
    mean -146 to -223 (big -83), p1 -4.7k to -5.6k, p99 +364 to +530.
  - Dearer: 0.8-1% of turns by 300+ (heavy 1,905 of 228k; 375 by 1k+). Late cover reads cost ~360-430 more
    than early ones (elk-arena, the cover call itself no dearer), and no memo or cache was found that explains
    it (Reach::at's memo is 64 tiles by x, y mod 8). Searches skipping the cover save 3.3-3.5k; on elk-arena
    244 skip it and 310 still read it.
  - Real budget (indicative, against m4 before the rebase), OOF pool 715 -> 690, big 213 -> 230, heavy 489 -> 507,
    td 222 -> 217.
  - **A/B (`fc7-w`, 10,240) of m5 + this against the base: 51.3% (50.3-52.3), OOF 55,424 / 71,125 (-22.1%).** The m5
    control on the same suite: 50.7% (49.8-51.7), OOF 57,524 / 71,418 (-19.5%), so about -3.6% beyond m5. By
    rounds, cand / m5: 1: 4,045 / 4,045, 2-10: 2,988 / 3,003, 11-60: 7,476 / 7,722, 61-300: 12,336 / 12,931,
    300+: 28,579 / 29,823. Fuel a turn mean 50,242 / 50,303, p99 91,750 / 91,850. Shortcuts 1.984M / 1.993M.
    (Before the rebase, m4 + this: 50.9% (49.9-51.9), OOF 60,697 / 72,241.)

### Dropped

- **Resolving the guard only when a covered tile would become the best** (and refunding the query cap's count
  for tiles found guarded): not exact. When the search leaves the guard deferred where the base worked it out,
  the goal or `guard_work` works it out after our hits (`see_stuns` rebuilds Safety in place, a kill or our move
  changes the inputs), which can give another guard and another walk. Not built.
- **Dropping the pre-loop `sure < 2` resolve**: the decision would be unchanged (the progress gain is 0 at the
  start tile, and common to one tile's candidates), but it skips a resolve the base made, so it is not exact for
  the same reason.
- **Reading the cover before pricing when the top-bound tile may be covered** (a variant): ~230 dearer again on
  the searches that read it.
- **A memo of the cover across a turn's callers** (search, route, work cover): 6% of calls repeat a key
  (1,334 of 22,702 on heavy, 337k of 20.3M fuel).
- **Transpositions in grow**: 1.6% of nodes repeat a state (Node fields and unit healths, ignoring the action
  stack, which hoisting reads too). Dead.
- **Skipping the Reach queries when one tile and one candidate are left** (no cut against best_total = -1e30,
  no other arg): 23% of searches, ~264 of queries each, ~60 a search, and later Reach users would rebuild.
- **Cheaper bounds in grow or settle**: no admissible bound exists before pricing (leaf values only gain the
  tiles' blows in the price loop), and the Front already drops dominated offers.

### Open (exact, each under ~300 a search)

- `viewers`: the ward lookup (`sdk_wards`, ~115) once per round rather than per search, if a ward placed between
  searches can be ruled out or keyed; the row loop (~230).
- `Unit{}` per foe (46) and the Search constructor's zeroing (`unit_cell{}` is written for every unit before
  grow reads it).
- `pass_`: the enemy occupancy and camps boards are built again after `blocked()` built them (~2 whole-board ops).
- The late-cover penalty (~400 on searches that still read it): its cause is unexplained.
- The step guard the search works out (in-loop 7-17k on heavy searches) is the search's biggest cost and is
  needed for exactness: only a cheaper `step_guard` can shrink it.

## bytes

Branch `fc7-bytes` from r1c's tip (e0774ba2). Census of every memory.fill / memory.copy (bulk ops, a fuel a byte)
by how often it runs: the profiler's runner (`runner-prof.diff`) patched to log bytes and counts per bulk op
(`fr_bulk`, in `/tmp/fc7/bytes/prof-runner`), 89 maps (heavy + pool) of self-play at the real budget, joined with
`llvm-objdump -d` of the same wasm (wabt's objdump can't read it). 759k turns after each body's first, 1,237 heavy.
- **The lever is small.** Bulk ops total 179 bytes a turn (0.4% of the ~46k mean) and 1,252 a heavy turn (0.8%);
  of the heavy part ~600 is round-1 start-up merged into OOF turns (StaticMap::build, init_beliefs, constructors).
- The big sites in the disassembly hardly run: trade's 381/768 copies never ran; read_spells' 648 (`near`, only
  with foes + unseen > 8) ran 0 times a turn; touch1's 324 0.01 a heavy turn; Route's 76-byte copies in
  route/step_route (Willow's guard paths) ~0. The fight search's bulk ops sum to ~300 a heavy turn
  (grow's 72-byte Node copies ~115, plan_strikes' copies ~57, Search's 212-byte member zeroing 61, concrete 30).
- Top sites a turn: Route's value-initialised first_steps (route_around 46, step_route 14, travel), home_fires' 256
  (27), farm's centre_steps.assign (24), live_camps 3.

Kept (both byte-identical at 100M on all six sets, 342/342 games):
- 1075b19e Route::first_steps and Neighbours::tiles in anonymous unions with user-provided constructors: read only
  below count, which the search writes.
- 478798c3 home_fires zeroes only min(64, spawn tiles) fire entries: read only for k below the spawn's tile count.
- Together, against r1c-i: total -0.16% to -0.19% on every set (mean -90 a turn, p50 -0.3%, p99 -0.1%), over 100k
  def 641->637, wide 2932->2906, pool 8174->8114, big 2217->2195, heavy 5284->5254, td 2502->2478.

Open (each under ~30 a turn): farm centre_steps reset only the entries set (flattened farm_turn: codegen risk);
Search::unit_cell{} (read() returns early before writing it, so not obviously exact); Node copies in grow.
Not bytes but seen: __cxa_allocate_exception 0.54 a heavy turn (~3.9k each, ~2k a heavy turn): who throws on
heavy turns is worth a look.

## merge 7

Merged `fc7-strike` (on merge 5) and `fc7-bytes` (on r1c e0774ba2, in main since merge 6) as CHANGES 431,
cherry-picked onto merge 6's tip (code applied cleanly; NOTES.md kept both sides): 0d45161a (the strike search
reads the deferred guard's cover on first need, not in `read_geometry`), 1075b19e (Route's `first_steps` and
Neighbours' `tiles` left unwritten), 478798c3 (home_fires zeroes only min(64, spawn tiles) fire entries), notes
ef2bede6 and 9151e3ac. Nothing dropped. Frozen as `bots/variants/fc7-m7`.

Review:
- Lazy cover: `step_guard_cover` reads the world (const), the Safety the guard was deferred with (same object;
  rebuilt only by `see_again` / `see_stuns`, neither of which runs inside `plan_strikes`), and the deferred
  `guard_here_` / `guard_radius_`. Every new read site (sure < 2 pre-check, price loop, capped tail, debug) comes
  before `held.release()` and the carry-out, so no move, hit or kill falls between the old and new read.
  `may_cover` (tile within grid_r - 1 of here) is a superset of the cover: the radius is 1 or dash_range = 2 < grid_r
  = 3, and the cover path needs `moves`, which only searches from the tile `guard_steps` deferred from take
  (`strike_after` is anchored; bot.cc re-defers after a move). So wherever the base had a `maybe_guarded` bit the
  cover is read first, the pre-check recounts exactly as the base, and `resolve_guard` runs at the same points with
  the same inputs. `maybe_guarded` is read only in `plan_strikes`, not in grow. `GuardInputsHeld` is taken before
  `S.read()`, so every cover read is still under it and `step_guard` shares the first pass as before.
  `route()`'s per-round `route_cover_` points at the same static board: after the search, `set_guard(nullptr)` /
  `restore_guard` reset its round, and the early return after a failed `S.read()` leaves the board holding the
  same inputs' result. The late-read ~400: not found; Safety's `strike_of` memo is warmed by the strikers loop
  before a late read (cheaper, not dearer), so most likely codegen in the flattened `plan_strikes`; play identical.
- Bytes: `first_steps` is written below `count` (route_around's fill and insertion sort; route() only shrinks
  count) and read only below it (spans of `count`, the move loops, `[0]` behind `count > 0`); `Route around` in
  travel stays count 0 when walk_round returns early. Neighbours: insertion sort writes below count, readers use
  begin/end or a span of count. No whole-struct compare, hash or memcmp; copies are bytewise. home_fires: `fire[k]`
  read only for k below `ally_spawn_tiles.size()` (and below 64), written only after the fill.
- Empirical: a copy filling every arena allocation, each Route's and Neighbours' union and HomeBoard::fire with 0xA5
  before use (`fc7-m7-poison`, deleted) was byte-identical to the base on all six 100M sets (342/342).

100M, all six sets byte-identical to `base-*-100M.json` (`m7-*`; 342/342):

| set | total vs base | total vs m6 | mean base -> m7 | p99 base -> m7 | max base -> m7 | over 100k base / m6 / m7 | round 1 mean base -> m7 |
|---|---|---|---|---|---|---|---|
| def | -2.26% | -0.22% | 51,433 -> 50,282 | 97,736 -> 95,610 | 215,787 -> 213,965 | 704 / 596 / 591 | -7.1% (m6 +0.1%) |
| wide | -2.25% | -0.24% | 50,497 -> 49,371 | 103,147 -> 100,989 | 268,444 -> 264,004 | 3,086 / 2,750 / 2,696 | -6.9% (-0.0%) |
| pool | -2.17% | -0.21% | 53,464 -> 52,317 | 107,853 -> 103,841 | 356,280 -> 371,823 | 9,367 / 7,570 / 7,466 | -6.9% (-0.0%) |
| big | -2.29% | -0.18% | 61,397 -> 60,009 | 104,092 -> 100,172 | 287,312 -> 322,644 | 2,523 / 2,011 / 1,986 | -8.1% (-0.1%) |
| heavy | -2.25% | -0.22% | 52,013 -> 50,861 | 119,186 -> 116,969 | 360,603 -> 373,981 | 5,556 / 4,994 / 4,941 | -8.1% (-0.0%) |
| td | -1.88% | -0.22% | 53,524 -> 52,534 | 100,172 -> 97,402 | 275,080 -> 269,705 | 2,744 / 2,321 / 2,285 | -7.4% (-0.0%) |

Over 100k in the six sets: 23,980 (base) -> 20,242 (m6) -> 19,965 (m7). Real budget (indicative), OOF base -> m6
-> m7: pool 770 -> 653 -> 624, big 248 -> 209 -> 208, heavy 707 -> 409 -> 541, td 209 -> 192 -> 192 (1,934 ->
1,463 -> 1,565; small real benches swing once games diverge).

A/B `m7` (`fc7-m`, 10,240 games, real budget) against the base: **50.3% (49.4-51.3)**. OOF 51,059 / 70,013
(**-27.1%**; m6 read -21.2%), in 6,475 / 7,168 games, by rounds: 1: 3,331 / 6,272 (-47%), 2-10: 2,913 / 6,384
(-54%), 11-60: 7,339 / 8,997 (-18%; m6 -13%), 61-300: 12,435 / 16,106 (-23%; m6 -17%), 300+: 25,041 / 32,254
(-22%; m6 -14%). Runs of 50+ OOF 384 / 782 (m6 895 / 756). Fuel a turn mean 50,101 / 51,080, p50 47,350 / 48,750,
p90 86,450 / 86,550, p99 91,650 / 92,850, at or over 100k 0.22% / 0.25%. Shortcuts 1.982M / 2.243M:
farm-partial-evaluation 962k / 1,060k, step-guard-entry 540k / 581k, prey-cut-short 135k / 157k, turn-order 104k /
132k, step-guard-look 73.8k / 75.6k, out-of-fuel 51.1k / 70.0k. Cumulative OOF against the base by merge: m1
-2.6%, m2 -3.8%, m3 -9.9%, m4 -11.0%, m5 -19.6%, m6 -21.2%, m7 -27.1%. The step down from m6 is the lazy cover
(the strike worker read -22.1% on m5 + it, against -19.5% for m5 alone, on `fc7-w`): fight turns past round 10.

Open leads (batch 7 added to merge 6's list, deduplicated):
- Strike search: `viewers`' ward lookup (`sdk_wards` ~115) once per round if a ward placed between searches can be
  keyed, its row loop (~230); `Unit{}` per foe (46) and the Search constructor's zeroing (`unit_cell{}`; read()
  returns early before writing it, so not obviously exact); `pass_` rebuilds the enemy occupancy and camps boards
  after `blocked()` built them; the late-cover ~400 (unexplained); `step_guard` itself (7-17k in the loop on heavy
  searches) is the search's biggest cost.
- Bytes: farm's `centre_steps` reset only the entries set (flattened farm_turn: codegen risk); grow's Node copies;
  `__cxa_allocate_exception` 0.54 a heavy turn (~2k a heavy turn): who throws on heavy turns.
- Merge 6's list stands otherwise (round 1's `build_static` / `init_beliefs` / `champion_enemy`, round-1 and
  rounds 2-10 OOF stacks, uncapped floods in `walk_deaths` / `rebuild_altar_access`, the siege stand loop, prey's
  loop, heavy fight turns' plan_strikes self / `act<false>` / Reach, the update's `read_priorities` /
  `update_champion` / `ally_next_rank`, `raw_output` per champion, the stale tail); fuel gates not worth building.

## guard

Branch `fc7-guard` from `fc7-strike` (ef2bede6). Area: `step_guard` and `step_guard_cover` (combat/guard.cc).
Commits 51103683, 5a6b2517, 55059c17; frozen tip `variants/fc7-guard-d` (a = 51103683, c = a + 5a6b2517).
Benches against `base-*` and `strike-b-*`. I left the guard's struct copies (GuardFoes, FirstPass) to myself; the
`bytes` worker's fill/copy sweep need not touch them.

### Where a resolve's fuel goes (debug copy, heavy set at 100M, 18.8k resolves, 8.1k covers)

- Resolves (`step_guard`): mean 4.9k. 62% cost under 2k (no foe in reach: the GuardFoes build alone, ~360). The
  974 over 20k (37% of the guard's fuel) average ~36k:

| part | all | > 20k |
|---|---|---|
| GuardFoes build | 418 | 640 |
| expose_here | 188 | 608 |
| first loop (bound per tile) | 547 | 1,715 |
| unions' keys (`fight_allies`, `fight_enemies_any`; the threat build lands here) | 302 | 1,479 |
| first union sim | 1,926 | 10,779 |
| exact exposures | 869 | 10,936 (Reach::at 6.5k at 9.8 calls, Reach builds 2.3k, keys 1.2k) |
| second union, sort | 44 | 570 |
| last loop (settle, `lethal` 655, sims) | 520 | 7,492 |

  Sims are 16.9k of a heavy resolve (1.84 a resolve, ~9.2k each); every one is needed for exactness (below).
- Covers: mean 1.7k; ~245 a tile of the 5x5 square per cover in the tile-by-tile loop (r2: 2.4k a cover).
- Repeats: no resolve in a turn repeats another's inputs (5.3k second resolves in 50 games, all after a move or a
  new Safety). But 1,299 resolves outside the search followed a cover (the route's) with the same Safety
  generation, tile and radius: 13.3k each, 2.35k of it the first pass the cover had already made.

### Shipped (identical at 100M on def, wide, pool, big, heavy, td: 342/342 against base-* and strike-b-*)

1. 51103683 **The cover and the step guard find the tiles more exposed than ours from rows of bits**
   (`GuardFoes::each_exposed`), not tile by tile.
   - Each row of the square is read from the packed open board in one load, masked to the columns in bounds,
     ANDed with the foes' window, and the centre is dropped.
   - The tiles a foe outside our own exposure reaches (`beyond`, the union of those foes' cells) are worse at
     once. Only the rest sum their damage, in the same foe order, so the float sums are the same.
   - Exact: it is the same predicate as `no_worse_at` after in_bounds/open, in the same cell order (bits
     ascending = dy then dx). `mask == 0` cannot occur on a cell of `w.any`. `mask & ~here_mask` is nonzero
     exactly on `beyond`'s cells.
   - vs strike-b: total -0.01..-0.02%; over-100k turns mean -82..-147, p10 -335..-540; over 100k 20,338 -> 20,232.
2. 5a6b2517 **The exact keys reuse the union read.** `fight_enemies_any` records, for each unseen or lost enemy,
   the first spot it hits; `fight_enemies_at(q, i, ...)` then skips the enemies that hit no spot or first hit a
   later one, and sets the one first hitting spot i without asking.
   - Exact: the union read every spot before an enemy's first hit and found misses; an enemy outside the union
     hits no spot. `fight_key_with(q, v)` is v | unseen hits | lost hits | allies. Its `& ~v` is kept as
     before: a lost enemy has a negative reach, so it is never a foe, but the formula is unchanged anyway.
   - At most one threat per enemy (build_threats), and lost enemies have none.
   - Fires only with unseen or lost enemies near: vs a, -0.3..-0.8 a turn, over-100k -10..-18, nothing dearer
     at p90/p99.
3. 55059c17 **The cover's first pass is reused outside the search too, keyed on Safety's generation, our tile
   and the radius.**
   - `Safety::generation()` is a static counter bumped by the constructor, `refresh()` and `invalidate()`.
   - The pass reads only Safety (its seen enemies, strikes and Reach builds, kept for its life and reset only by
     `invalidate`/a new one) and the enemies' beliefs (pos, teleport, tp_dest).
   - Beliefs change only through `observe()` or `read_stuns()`. `see_again` makes a new Safety after observe,
     `see_stuns`/`see_kills` make one whenever read_stuns changed anything, and comms send's observe runs after
     play_turn's Safety is gone. There is only one Safety (bot.cc's play_turn).
   - GuardInputsHeld keeps its meaning (held shares as before, and its constructor still invalidates).
     `release()` no longer clears `valid`, since the generation guards what follows.
   - The skipped work (GuardFoes, expose_here, the first loop) only fills memos that are already filled: Reach
     builds, and the Reach::at memo hits.
   - vs c: over-100k turns mean -104..-194, p1 -2.4k..-3.5k; every turn +6 (the counter; p50 +6). Total -0.3%
     (heavy, pool) to +0.07% (big). Over 100k 20,219 -> 20,082.
- All three vs strike-b, at 100M:

| set | total vs base | total vs strike-b | mean | p99 | max | over 100k base / strike-b / d | round 1 mean |
|---|---|---|---|---|---|---|---|
| def | -2.00% | -0.02% | 50,425 -> 50,415 | 95,963 -> 95,836 | 214,103 -> 213,526 | 704 / 611 / 602 | +6 |
| wide | -1.99% | -0.02% | 49,511 -> 49,500 | 101,388 -> 101,189 | 264,241 -> 263,857 | 3,086 / 2,755 / 2,734 | -13 |
| pool | -1.95% | -0.03% | 52,446 -> 52,430 | 104,129 -> 103,879 | 371,898 -> 371,904 | 9,367 / 7,596 / 7,462 | +6 |
| big | -2.08% | -0.01% | 60,136 -> 60,128 | 100,669 -> 100,453 | 322,789 -> 322,795 | 2,523 / 2,040 / 2,027 | +6 |
| heavy | -2.00% | -0.03% | 50,993 -> 50,980 | 117,253 -> 117,104 | 374,130 -> 374,136 | 5,556 / 5,005 / 4,952 | +6 |
| td | -1.65% | -0.02% | 52,665 -> 52,652 | 97,716 -> 97,560 | 269,774 -> 269,250 | 2,744 / 2,331 / 2,305 | +5 |

  - Over 100k in the six sets: 20,338 (strike-b) -> 20,082 (-1.3%).
  - On turns the base spent over 100k: mean -208 to -342, p1 -3.3k to -4.3k, p10 -430 to -794, p99 +18..+24.
- Real budget (indicative; OOF summed from per-game shortcuts, pool / big / heavy / td): base 930 / 379 / 802 / 296,
  m5 722 / 318 / 579 / 268, d 712 / 250 / 618 / 229 (1,887 -> 1,809 against m5).

### Dropped (measured)

- **walk_allies_in's inputs cached per Safety** (each ally's strike reach, each seen enemy's acts-from tile, keyed
  on `observations`): identical, but dearer, +18..+33 a turn mean (p50 +3, p90 +200 on fight turns). Most
  Safeties run one or two sims, so the fill costs more than it saves. Its 1k a call in the profile is the
  ally x enemy loop of 6v6 fights.
- **The cover answering a repeated ask from the kept pass**, with GuardInputsHeld removed, so the search's cover
  can reuse a pass from before the search under the generation key. Identical, but level: -9..+0.5 a turn,
  over-100k -1..-9.

### Not built, by argument

- **Skipping or reordering sims** (16.9k of a heavy resolve). Not exact, for two reasons:
  - The settled list makes the verdicts depend on which sims ran: a lost fight over-settles supersets.
  - A skipped sim leaves Safety's fight memo without an entry a later `fight_of` would have hit. Later sims can
    read changed own-state (our cooldowns, health after hits) while the memo is keyed by roster alone, so a
    recomputation could differ from the base's memo hit.
  - The fight sim itself (fill, make_fighter, simulate) belongs to the fight area.
- **Caching resolves across a turn**: the inputs never repeat (above).
- **Lazy Reach builds in exposure**: the search and blow() read the same foes' Reach after, so nothing is saved.
- **Reach::at** (~500 a miss for ~2.5 ways, 6.5k in heavy resolves, 4.7k self a heavy turn) is already tight
  code: the way loop with sight. A batched form (precomputed per-way hit windows for sightless ways) would
  touch the shared danger model.

### Open

- Reach::at per-way hit windows built once per Reach (dilations of each tile set by its range; sight ways still
  per tile): up to ~2k a heavy turn if a miss drops to ~200. Its exactness needs the sight and splash cases
  kept per tile.
- The first union sim (10.8k on heavy resolves) is needed; only a cheaper sim (fill, `simulate`) shrinks it.
- GuardFoes' build is ~400 on every resolve with an enemy in sight, even with none in reach. A Strike::max_reach
  box test before `strike_of` would not change the result, but the build is already short.

### A/B

`guard-d` (`fc7-w`, 10,240 games, real budget) against the base: **51.3% (50.3-52.3)**.
- OOF 55,064 / 72,002 (-23.5%), in 6,505 / 7,119 games. fc7-strike-b on the same suite read 55,424 / 71,125.
- By rounds, d / strike-b: 1: 4,044 / 4,045; 2-10: 2,993 / 2,988; 11-60: 7,380 / 7,476; 61-300: 12,084 / 12,336;
  300+: 28,563 / 28,579. Runs of 50+ OOF: 501 / 1,039 (base).
- Fuel a turn mean 50,241 / 51,068, p99 91,750 / 92,850, at or over 100k 0.22% / 0.26%.
- Shortcuts 1.990M / 2.243M: step-guard-entry 549k / 595k (strike-b 547k), step-guard-look 76.5k / 79.5k.
- Logs: `replays/fuel/fc7/ab/guard-d.*`.

## prey

Branch `fc7-prey` on merge 6 (7d78a411): caf0cf30, f8e27c10, f4b926dd, dccb2af8, a066d7d3, f3a267e9; frozen tip
`variants/fc7-prey-f`. Area: the mid-game goals after the strike search (prey, chase, siege, kite) and the
altar-access floods.

### Where the fuel goes (census of merge 6 with labels inside prey, siege, kite and altar access; heavy + 32 pool +
fires-set maps, real budget vs the base, 372 games; scripts `/tmp/fc7/prey/tools/`)
- prey 12-13k on 28% of OOF-first turns (8.5k on 8% of heavy ones). Its own loop is small: the candidates 3.0k
  (`preyable` 2.6k at 2.7 calls, of which `pack_covers` 2.7k on 21%: the round's first pack build), `team_pressed`
  1.9k at 1.5 calls, the fights' own code 0.35k. The rest is the fight itself: `fight_key` 9.9k at 1.8 calls (Reach
  builds for the enemies round the target, then `Reach::at`), `chase_trade` 11.5k at 1.6 calls (the sim). One prey
  a turn; the lost-fight memo already folds equal fights. No exact repeat or bound found.
- chase's walk 9.1k on 2.4% of OOF-first turns: a route search (pathing's).
- siege_kite 7.7k on 45% of OOF-first turns: altar access 12k on 22% (flood from spawn 29k on 4%,
  `returns_go_round` 9.4k on 5%, `walk_deaths` 9.1k on 3%, `round_returns` 2.1k on 12%); `siege_candidate` self
  0.5-1.1k on 40-57% (the monolith `consider`s 1.4k on 15-31%, at 3-4 calls); `siege_ready` 1.9k on 6-18%; the
  stand loop 4.7k on 1-3%.
- `returns_go_round` (13k calls): reach 16 settles 28%, reach 64 64%, 7% fail. The reach-64 mask pays every layer
  of its reach over the whole board (~11k on 100x100) wherever the tiles join.
- `walk_deaths`' floods (16k): 95% add at most 8 tiles, but each paid (layers + 2) x all chunks.
- Shared-gems maps: `kite_productive_action`'s pricing ~20k a call (8k calls in 8 games, ~1,000 a game): its
  damage loops ~10k (9 endpoints x 3 uses x 2 turns, two engagement tests an endpoint) and `exposure` ~8k
  (every member of the big group, every ally per member, for each endpoint), with 1-3 targets.
- `rebuild_altar_access`' no-open branch never ran on the fires-set (debug count): nothing to take there.

### Shipped (all identical at 100M on def, wide, pool, big, heavy, td: 342/342 against base-* and m6-*; and on the
fires-set, goal's `accset.txt` + `siegeset.txt`, 82/82)
1. caf0cf30 **walk_deaths floods within 8 steps first**, uncapped only when that flood holds more than 8 tiles.
   Exact: a flood cut at its reach holds a tile at every step up to it, so one of at most 8 tiles ended on its
   own. Fires-set: 127 turns cheaper by 1k+ (mean -2.8k), -0.3M.
2. f8e27c10 **returns_go_round searches past reach 16 with `compute_to`** (a field from the first tile beside the
   returns over `ours` minus them, stopping once it holds every tile beside them), in place of the reach-64 mask.
   Its price is its layers x the chunks, not the reach's. Exact: it reaches all of `beside` iff they are connected
   there (the field's king steps and corner rule are the mask's), and connection at any distance proves the
   returns cut no walk (merge 3's argument does not use the cap), so it may now settle what the base left to the
   flood from spawn. Fires-set: 477 turns cheaper by 1k+ (mean -8.4k), 288 dearer (mean +2.9k: tiles joined
   at 50-64 layers, and true cuts, which run to exhaustion), -3.1M; turns over 100k -48.
3. f4b926dd + f3a267e9 **kite_productive_action**: the allies that cover a member are listed once; a use whose
   cast cannot happen plays as no cast and is skipped; the engagement tests are read only when a cast needs
   them; each target's endpoints in attack and spell range are marked once; an endpoint no hit lands from
   prices 0 at once; exposure reads only the members within a step of their reach of us (every endpoint is
   within a step), by group in `groups_near` order and member order. Every skipped term was a pure read.
   Fires-set: -14.6M (3,865 turns cheaper by 1k+, mean -3.7k) then -39.2M (4,107 turns, mean -9.6k), 11 and 104
   dearer (under 3.3k).
4. dccb2af8 + a066d7d3 siege's stand loop lists the members that may hit once (reach capped by cover, the hit
   precomputed), only when the loop runs: fires-set -4.7M (468 turns cheaper by 1k+, mean -3.5k). The first form
   built the list on every siege() call and cost 26k turns a little each.

Tip f against m6, fires-set (100M): total -0.24% (-61.8M), mean 50,749 -> 50,637, p99 106,156 -> 105,984, turns
over 100k 7,522 -> 7,444; turns cheaper by 1k+ 5,131 (mean -11.7k), dearer by 1k+ 483 (mean +2.7k, max 11k).

100M, all six sets (`prey-f-*`), against base / m6:

| set | identical | total vs base | total vs m6 | p99 m6 -> f | over 100k base / m6 / f | base 95k+ turns, mean delta vs m6 |
|---|---|---|---|---|---|---|
| def | 16/16 | -2.06% | -0.01% | 95,765 -> 95,739 | 704 / 596 / 593 | -97 |
| wide | 52/52 | -2.02% | -0.01% | 101,367 -> 101,328 | 3,086 / 2,750 / 2,743 | -36 |
| pool | 128/128 | -1.98% | -0.02% | 104,093 -> 103,916 | 9,367 / 7,570 / 7,519 | -264 |
| big | 32/32 | -2.14% | -0.02% | 100,363 -> 100,038 | 2,523 / 2,011 / 1,969 | -591 |
| heavy | 50/50 | -2.04% | -0.01% | 117,144 -> 117,120 | 5,556 / 4,994 / 4,987 | -43 |
| td | 64/64 | -1.68% | -0.01% | 97,647 -> 97,520 | 2,744 / 2,321 / 2,296 | -206 |

Over 100k in the six sets: 20,242 (m6) -> 20,107. Round 1 unchanged (no change runs there). Real budget
(indicative), OOF base / m6 / f: pool 770 / 653 / 571, big 248 / 209 / 198, heavy 707 / 409 / 431, td 209 / 192 /
192 (1,934 / 1,463 / 1,392); shortcuts 64.3k / 58.8k / 58.3k.

A/B `prey-f` (`fc7-w`, 10,240 games, real budget) against the base: **50.9% (50.0-51.9)**. OOF 55,001 / 72,681
(-24.3%; m6 read -21.2% on `fc7-m`, another suite, so this A/B does not isolate prey's share), in 6,494 / 7,125
games, by rounds: 1: 3,321 / 6,269, 2-10: 2,817 / 6,105, 11-60: 7,593 / 9,115, 61-300: 12,848 / 15,782, 300+:
28,422 / 35,410. Fuel a turn mean 50,204 / 51,086, p50 47,450 / 48,750, p90 86,450 / 86,550, p99 91,750 / 92,950,
at or over 100k 0.23% / 0.26%. Shortcuts 1.972M / 2.237M: farm-partial-evaluation 927k / 1,037k, step-guard-entry
552k / 592k, prey-cut-short 133k / 153k, turn-order 109k / 135k, out-of-fuel 55.0k / 72.7k.

### Dropped / not built
- The cap-and-count trick in `rebuild_altar_access`' no-open branch: the branch never ran on the fires-set.
- A cheaper `prey`: its cost is the fight (`fight_key`'s Reach builds and queries at the target's tile after the
  strike search's Safety refresh, and `chase_trade`'s sim). Candidates are best first and lost fights are folded
  already; nothing in it repeats exactly within the turn.
- Skipping the reach-16 mask in `returns_go_round` (compute_to only): 72% of calls pass it, but where it settles
  (28%) it costs ~0.6k against ~4k for the field on 100x100. Not built.

### Open
- `returns_go_round` is dearer by ~3k where the tiles join at 50-64 layers or the returns cut a walk (compute_to
  runs to exhaustion): a reach-32 mask between, or the field from the beside tile nearest their middle.
- `kite_plan` 1.7-2.4k on 17-23% of fires-set heavy turns: recomputed on every hit (the version moves); the rounds
  sum could follow health incrementally.
- `team_pressed` ~1.2k a call at 1.5 calls (32% of OOF-first): the `near_enemy_spawn` test repeats per ally for the
  same enemy; read once per enemy. Small.
- Monolith `consider` in `siege_candidate` ~0.4k a call at 3-4 calls; `siege_ready` ~1.2-1.7k self on 12-18% of
  fires-set turns (the members x enemies tank loop, the pool loop). Small.
- prey's `fight_key` after a refresh rebuilds the Reaches round the target (fight's open item: reuse across Safety
  rebuilds keyed on the changed beliefs).

## merge 8

Merged `fc7-guard` (from fc7-strike ef2bede6, in main as merge 7) and `fc7-prey` (from merge 6 7d78a411) as CHANGES
432, cherry-picked onto main's tip (code applied cleanly; NOTES.md kept every side): guard 51103683 (`each_exposed`:
the cover's and step guard's over-exposed tiles from rows of bits), 5a6b2517 (`fight_enemies_any` records each
unseen/lost enemy's first hit spot, `fight_enemies_at` reuses it), 55059c17 (the cover's first pass reused outside
the strike search under `Safety::generation()`), notes 5f21179a, b8064dbd; prey caf0cf30 (`walk_deaths` floods
within 8 steps first), f8e27c10 (`returns_go_round` past reach 16 by `compute_to`), f4b926dd + f3a267e9
(`kite_productive_action`), dccb2af8 + a066d7d3 (siege stand loop's member list), notes 1203829f. Nothing dropped.
Frozen as `bots/variants/fc7-m8`.

Review:
- `each_exposed`: same predicate as `no_worse_at` after in_bounds/open, in the same cell order (bits ascending =
  dy then dx); `beyond` (the cells of foes outside `here_mask`) is exactly `mask & ~here_mask != 0`; the rest sum
  damage in the same foe order. A cell of `w.any` always has a reaching foe, and `here_damage >= 0` anyway. Columns
  in bounds by `lo/hi`, rows by `y`; the 4-byte word read stays inside `open_bits`' 8 bytes of padding; side <= 5
  (radius 1 or dash_range 2), so 25 cells fit the 32-bit window. A copy running the old loop beside it and printing
  any disagreement (every call, one full game) printed none.
- `fight_enemies_at`: one threat per enemy (build_threats), lost enemies have none and are never foes (negative
  strike reach); an enemy outside `any` hits no spot, one whose first hit is a later spot misses this one, and
  `first` is read only for enemies in `any`. Used only when `bounded > 1` (the union ran over the same spots, index
  i = spots[i] = exposed[i]); the `& ~visible_of(nears)` and the allies are as before.
- Generation key (55059c17): the first pass reads `seen_` (listed once per Safety), strikes (`known_`, never reset),
  Reach (`reached_`, reset only by `invalidate()`), `world.enemies` (pos, teleport) and `here`/`radius`.
  `world.enemies` changes only in `observe()` (see_again), `read_stuns()` (see_stuns) and the turn's `update()`, each
  followed by a new Safety (constructor bump); `refresh()` and `invalidate()` bump too, so kills and our stuns are
  covered conservatively. Comms' `note_capture` touches camps only. Our own move: the pass does not read our
  position except as `here` (Reach is the Safety's cache, the same object the base's recomputation would read), so
  the tile is enough. `GuardFoes::safety` is a reference to the Safety that made it: a new Safety (even
  construct_at at the same address) bumps the counter first. A uint32 bumped a few times a turn cannot wrap in a
  game; Cassi & Issac each run their own instance (and every turn makes a new Safety either way).
- `walk_deaths`: `reachable_tiles_into` includes its origin (checked: distance 0 gives 1 tile, distance 1 gives 9),
  so a region with a tile 9+ steps out holds a tile in each of layers 0-8 (a shortest path's tiles), i.e. 9+ tiles,
  and is flooded again uncapped; one of at most 8 tiles lies within 8 steps and the capped flood is whole. A BFS
  layer argument: holes and diagonal steps change nothing.
- `returns_go_round`: `compute_to` with `rest` as walls from `from` takes the same king steps and corner rule as the
  mask (rules `map.corners`); `seen == beside` only if every beside tile was reached. The old second mask was capped
  at 64 layers, `compute_to` is not: a true verdict past 64 layers now takes the lazy path, which the base already
  trusts for any true verdict (dropping returns that a walk goes round leaves exactly the flood), and a real cut
  still returns false and floods from spawn.
- `kite_productive_action`: a skipped `use` is one whose cast condition (`cast_at`, the loop's own expression)
  fails, so it plays as use 0; `held`/`reset_held` are pure reads (`engagement_near`) taken only where they decide;
  an endpoint with no target in basic or spell range scores 0 in every use; `covers` is the same ally filter, once;
  the `near` list holds every member that can hit an endpoint (endpoints lie within 1 of here, so d(here, m) <=
  reach + 1; `groups_near` lists groups by camp tiles within the radius), in member order, groups iterated in the
  endpoint's `groups_near` order as before, so the float sums match.
- Siege firers: `d > reach || cover < d` is `d > min(reach, cover)`; the list is made right before the stand loop,
  which changes neither health nor cover.

100M, all six sets byte-identical to `base-*-100M.json` (`m8-*`; 342/342):

| set | total vs base | total vs m7 | mean base -> m8 | p99 base -> m8 | max base -> m8 | over 100k base / m7 / m8 | round 1 mean base -> m8 |
|---|---|---|---|---|---|---|---|
| def | -2.29% | -0.03% | 51,433 -> 50,264 | 97,736 -> 95,522 | 215,787 -> 213,206 | 704 / 591 / 578 | -7.1% |
| wide | -2.29% | -0.04% | 50,497 -> 49,353 | 103,147 -> 100,765 | 268,444 -> 263,620 | 3,086 / 2,696 / 2,664 | -6.9% |
| pool | -2.22% | -0.05% | 53,464 -> 52,292 | 107,853 -> 103,502 | 356,280 -> 371,829 | 9,367 / 7,466 / 7,292 | -6.9% |
| big | -2.32% | -0.04% | 61,397 -> 59,987 | 104,092 -> 99,733 | 287,312 -> 322,650 | 2,523 / 1,986 / 1,934 | -8.1% |
| heavy | -2.28% | -0.03% | 52,013 -> 50,845 | 119,186 -> 116,728 | 360,603 -> 373,987 | 5,556 / 4,941 / 4,876 | -8.1% |
| td | -1.92% | -0.04% | 53,524 -> 52,514 | 100,172 -> 97,116 | 275,080 -> 269,181 | 2,744 / 2,285 / 2,230 | -7.4% |

Against m7 most turns are ~6 dearer (codegen) and the heavy ones cheaper (p99 -0.2 to -0.4%). Over 100k in the six
sets: 23,980 (base) -> 19,965 (m7) -> 19,574 (m8). Real budget (indicative), OOF base -> m7 -> m8: pool 770 -> 624 ->
583, big 248 -> 208 -> 169, heavy 707 -> 541 -> 499, td 209 -> 192 -> 163 (1,934 -> 1,565 -> 1,414).

Fires-set (`/tmp/fc7/goal/accset.txt` + `siegeset.txt`, 82 games, 100M) against `/tmp/fc7/prey/m6-x-100M.json`
(= base): **81/82 identical**, total -0.49% (vs m6), p99 106,156 -> 105,345. The odd game,
`gen-monolith-only-50917413001` side a, diverges at round 1063 (champion 0 steps to 19,6 instead of dashing to 18,6
before a recall). Bisect: m7 identical, m7 + 51103683 alone diverges, and **m7 plus only debug prints in
`step_guard` / `step_guard_cover` (no logic change) diverges at the same turn the same way**. So the base's play
already depends on the step guard's measured cost: `Pathing::route` picks its cover-first search when
`step_guard_costliest() >= cheap_guard` (15k, pathing.cc:763), a measured-fuel switch between two searches that are
not equivalent in every case (here, dash against step). Kept: the guard's logic is exact (the old-vs-new check
above), and any guard saving can flip that switch.

A/B `m8` (`fc7-m`, 10,240 games, real budget) against the base: **50.4% (49.4-51.3)**. OOF 50,582 / 70,161
(**-27.9%**; m7 -27.1%), in 6,406 / 7,203 games, by rounds: 1: 3,331 / 6,272 (-47%), 2-10: 2,912 / 6,371 (-54%), 11-60: 7,281 / 8,982 (-19%;
m7 -18%), 61-300: 12,117 / 16,161 (-25%; m7 -23%), 300+: 24,941 / 32,375 (-23%; m7 -22%). Champion-game runs of 50+
OOF 966 / 989 (m7 384 / 782). Fuel a turn mean 50,090 / 51,088, p50 47,350 /
48,750, p90 86,450 / 86,550, p99 91,650 / 92,850, at or over 100k 0.22% / 0.25%. Shortcuts 1.978M / 2.255M:
farm-partial-evaluation 959k / 1,064k, step-guard-entry 538k / 584k, prey-cut-short 136k / 160k, turn-order 103k /
132k, step-guard-look 74.2k / 76.1k, out-of-fuel 50.6k / 70.2k. Cumulative OOF against the base by merge: m1 -2.6%,
m2 -3.8%, m3 -9.9%, m4 -11.0%, m5 -19.6%, m6 -21.2%, m7 -27.1%, m8 -27.9%.

Open leads (batch 8 added to merge 7's list, deduplicated):
- `Pathing::route`'s `cheap_guard` switch reads the step guard's measured cost and its two searches can differ
  (dash vs step): any change to the guard's cost can change play at 100M. Making the cover-first search equal the
  guarded one in every case (or the switch independent of measured fuel) would keep future guard savings exact.
- Step guard: Reach::at per-way hit windows built once per Reach (up to ~2k a heavy turn; sight and splash kept per
  tile); the first union sim (10.8k on heavy resolves) shrinks only with a cheaper sim; GuardFoes' ~400 build.
- Prey/altar: `returns_go_round` dearer by ~3k where compute_to runs to exhaustion (a reach-32 mask between, or the
  field from the beside tile nearest their middle); `kite_plan` 1.7-2.4k on 17-23% of fires-set heavy turns
  (incremental rounds sum); `team_pressed` ~1.2k a call (`near_enemy_spawn` once per enemy); Monolith `consider` and
  `siege_ready` (~1.2-1.7k on 12-18% of fires-set turns); prey's `fight_key` Reach rebuilds after a refresh.
- Strike search: `viewers`' ward lookup once per round, its row loop; `Unit{}` per foe and the Search constructor's
  zeroing; `pass_` rebuilding boards `blocked()` built; the late-cover ~400; `step_guard` itself in the loop.
- Bytes: farm's `centre_steps` reset (codegen risk); grow's Node copies; `__cxa_allocate_exception` on heavy turns.
- Merge 6's list otherwise (round 1's `build_static` / `init_beliefs` / `champion_enemy`, round-1 and rounds 2-10 OOF
  stacks, `rebuild_altar_access`' uncapped floods, prey's loop, heavy fight turns' plan_strikes self / `act<false>` /
  Reach, the update's `read_priorities` / `update_champion` / `ally_next_rank`, `raw_output` per champion, the
  stale tail); fuel gates not worth building.

## reach

Branch `fc7-reach` from `fc7-guard` (b8064dbd). Area: the enemy Reach (`Reach::build`, `Reach::at`) and its lookups.
Commits a9b2bc21, e11035e7; frozen tip `variants/fc7-reach-d` (b = a9b2bc21 alone). Benches `reach-b-*`, `reach-d-*`
against `guard-d-*` and `base-*`. **No lever of 1k or more a heavy turn exists here**: the measurements below show
why, so the per-way window idea is dead.

### Where Reach's fuel goes (debug copy, 25 heavy maps vs base at 100M, ~30k misses; profiler on heavy + 32 td maps)

- Profiler, guard-d tip, fight-heavy turns (100M, self): `Reach::at` 6.1k (14 calls, 433 a call), `Reach::build`
  3.8k (3.2 calls, 1.2k a call), `build_ways` 0.9k, `sight_from` + `sight` + `static_window` ~0.6k. Over all turns:
  at 231 a turn, build 244.
- **A Ways set holds ~2.5 ways** (2.3-3.5 by caller), and a miss evaluates 1.1-1.3 of them past the bound and
  dominance tests: 97% of misses hit, at the first or second way. So a per-way hit window (a bit test in place of
  `tiles & box`) saves nothing: the box test is already O(1) (4 loads and ANDs), and sight is worked out only when
  the box test passes. A miss costs ~450 outside sight: ~100 of prologue (the box tables' row addresses, the locals),
  ~80 a way, the memo store; far sight (~half of misses) ~200 more (the ward check, `sight()`'s cached mask, the
  shift).
- The memo (64 tiles by x, y mod 8) never collides: 0-4 repeat misses in 30k. Memo hits cost ~25.
- **Queries do not repeat across builds within a round**: of ~10k misses, 25 asked a tile the same enemy's previous
  build had answered that round. Across rounds (same enemy, same tile, enemy unmoved) 31% repeat a tile and 19%
  repeat the answer: a cross-round memo would need keys on the sets, recipe, units, the ward's mask and our vision
  (bush tiles), for at most ~45 a turn.
- Misses by caller (heavy maps): `fight_key*`/`lost_in_reach` 2.2k (memo hits 9: every tile new), `tally` 2.0k,
  stand 1.5k, guard 1.4k, damage bounds 1.3k, search 0.9k, `threatened` 0.2k.
- Builds: ~1.5k each (debug). Entry to the reuse test ~560 (the ready slots, the ally refresh ~350 a round, the
  occupancy loop with `world.slot`), sets ~700 when built (the camps loop ~200 when camps are near, the dilations),
  ways ~300 (70% of builds reuse the recipe's ways). 40% of builds stand where the last build of that enemy stood,
  but only 16% have the same sets inputs, and 80% of those are refused by `sets_reusable_` (a camp in the window).

### Shipped (100M: identical but one td game, below)

1. a9b2bc21 **Reach works out its ways' bounds at the end of a build** (`bounds_`, one int8 a way) and at() tests
   them, not `bound(w)` per way and query; **a build with no dash skips the dash-only work**: `world.slot` for the
   last slot, the allies' `fixed` and `in_bushes` bits, and the camps' `solid` bits.
   - Exact: bound() reads extent_, units_, splash_ and the way, all set only by build. `pass` (the only reader of
     fixed, in_bushes and solid) is read only by `dash_from`, only with a dash. A non-dash build keys its sets on an
     empty `fixed`: the reuse test then compares kinds without a dash, whose sets do not read it.
   - Profiler (identical games): at -374 a heavy turn, build +84 (set_bounds).
2. e11035e7 **An ally's next turn (`next_turn_round`, `world.slot`) is worked out on first need**: by a dashing
   enemy's build with that ally within the window. Exact: the round's snapshot (positions, the alive / visible /
   not-self filter) is still taken at the first build; an ally's belief and the ranks change only in update()
   (observe skips allies read this round, `rank_turns` and `read_priorities` run only in update). Build -87 a
   heavy turn.
- Both, against guard-d at 100M (342 games; 341 identical):

| set | total | mean | p99 | max | over 100k guard-d / d (base) | on guard-d's over-100k turns: mean, p1, p10, p99 |
|---|---|---|---|---|---|---|
| def | -0.03% | 50,415 -> 50,400 | 95,836 -> 95,722 | 213,526 -> 211,590 | 602 / 597 (704) | -207, -1.8k, -662, +77 |
| wide | -0.04% | 49,500 -> 49,482 | 101,189 -> 101,015 | 263,857 -> 260,277 | 2,734 / 2,706 (3,086) | -268, -1.9k, -815, +158 |
| pool | -0.05% | 52,430 -> 52,404 | 103,879 -> 103,657 | 371,904 -> 371,904 | 7,462 / 7,357 (9,367) | -345, -2.2k, -895, +145 |
| big | -0.01% | 60,128 -> 60,122 | 100,453 -> 100,369 | 322,795 -> 322,795 | 2,027 / 2,016 (2,523) | -135, -2.0k, -332, +208 |
| heavy | -0.04% | 50,980 -> 50,962 | 117,104 -> 116,856 | 374,136 -> 374,136 | 4,952 / 4,914 (5,556) | -217, -2.1k, -728, +128 |
| td | -0.04% | 52,652 -> 52,616 | 97,560 -> 97,435 | 269,250 -> 267,910 | 2,305 / 2,273 (2,744) | -257, -2.1k, -734, +135 |

  - Over 100k in the six sets: 20,082 -> 19,863 (-1.1%). All turns: -6 to -26 a turn; p99 of the per-turn change
    +117..+223 (codegen); 0.1-0.25% of turns dearer by 1k+. Round 1 unchanged.
  - Real budget (indicative), OOF pool / big / heavy / td: guard-d 609 / 176 / 540 / 177, d 587 / 161 / 577 / 177
    (1,502 -> 1,502).
- **The td game that differs (gen-ladder-73102000067, side a) is a measured-cost decision in route(), not these
  changes' logic.** `Pathing::route` takes its two-search path (bare route, then the route around the cover) only
  while `step_guard_costliest() >= cheap_guard` (15,000; model/pathing.cc). That is the step guard's measured fuel,
  read whatever the fuel left, so it switches at 100M too. In that game it is 15,559 in round 370 for guard-d and
  14,785 for this branch (the guard's Reach queries are cheaper); the first non-fuel difference in stdout is that
  branch (`GCOST` trace, debug copies), and the routes differ from round 371. So the two paths do not always pick the
  same route, and **any change to the step guard's cost can change play at 100M**. guard-d's own benches missed it by
  luck. A fix (an exact equivalence of the two paths, or a decision not keyed on measured fuel) belongs to pathing
  and changes play: it needs an A/B.

### Dropped (measured)

- **Stopping at() once every way left is no worse than what already hits** (suffix maxima per Ways, worked out in
  build_ways): at -92 a heavy turn, build_ways +141. There is about one way left after the first hit.
- **Skipping the far sight's shift on a plain square** (no wall or bush within 4 of p: every way tile sees p, and
  sight_known marks it): sight_from -66, sight -20, at +64 (the inlined test). Level.

### Not built, by argument

- Per-way hit windows (above: the box test is already a bit test; sight is per tile anyway).
- A bigger or better-keyed memo: it never collides.
- Keeping the memo across rebuilds: in-round repeats are nil.
- A per-origin list of camp tiles for the camps loop: 60% of builds have a new origin, so the list would be built
  about as often as the loop runs (~100 a heavy turn at most).
- A hits-only at() for `fight_key` and friends (stop at the first hit, no memo write): ~1.2 ways left after the first
  hit, ~100 a query, and later full queries would miss the memo.

### Open

- The `cheap_guard` switch in route() (above): play depends on the guard's measured fuel.
- A cross-round Reach memo for an unmoved enemy (19% of misses repeat an answer), keyed exactly on the sets, recipe,
  units, the owner's ward mask and, for bush tiles, our vision: at most ~45 a turn.
- at()'s fixed cost (~100 of prologue a miss): a smaller common path (the bush and ward sight branches out of line)
  might cut ~50 a miss; additions to it read dearer so far.

### A/B

`reach-d` (`fc7-w`, 10,240 games, real budget) against the base: **51.1% (50.1-52.0)**.
- OOF 53,459 / 71,714 (-25.5%), in 6,456 / 7,111 games. guard-d on the same suite: 55,064 / 72,002 (-23.5%): about
  -2.6% beyond guard-d (cand/ref 0.745 against 0.765), within the suite's run-to-run noise of the ref.
- Fuel a turn mean 50,238 / 51,082, p99 91,650 / 92,850, at or over 100k 0.22% / 0.26%.
- Shortcuts 1.978M / 2.234M: step-guard-entry 543k / 591k (guard-d 549k), step-guard-look 76.0k / 78.8k.
- Logs: `replays/fuel/fc7/ab/reach-d.*`.

## sim

Branch `fc7-sim` from merge 7 (a59d0ab4); only `model/safety.cc`'s fight sim (simulate, act, decided), Reach untouched.
**Method: a corpus micro-bench.** A dump copy (`replays/fuel/fc7/simbench/dump-vs-a59d0ab4.diff`) prints every 4th
sim's inputs and results on heavy + td at 100M; `gen_corpus.py` samples 6,000 of them into a C array; a bench copy
(`sim_bench.inc`, `mkbench.sh`, `try.sh`) replays them all on its second play turn at a 2G quantum and prints each
sim's fuel and a result hash. Results match the game's exactly, fuel to a constant 138 a sim; one candidate reads in
about a minute, to 0.01%, with every sim's result checked. `profbench.sh` runs the bench under the profiler's runner
(self-play: both modules write one `p.<pid>`), `annot.py` maps its line counts onto `llvm-objdump -d`. All in
`replays/fuel/fc7/simbench/` (the corpus too).
- **The sim is small in total and is not the heavy-turn wall.** About 2% of all fuel. A real heavy marked turn
  (profiler, real budget) spends ~22k in the sim's functions: act<0> 9.6k (18.5 calls at 520), decided 2.6k
  (5.9 at 444), simulate's own loop 2.1k, act<1> 0.25k; around it walk_allies_in 1.8k (2 at 927), make_slot +
  make_fighter 3.4k (12.3 calls), fill 1.5k (3.9 at 373).
- In the corpus: 3,895 a sim at base, 6.7 acts a sim (65% of it), the early-end checks 11%, play_quiet 8%, ~80 a
  loop iteration. Acts: quiet 173 (One) ; plain 283 One, 518 multi ; non-plain 290 One, 539 multi. 45% of sims are
  lost fights played until our fighter falls; stuns are in nearly every kit, so a stun-free path buys nothing.

Kept (one per commit, each identical on the corpus; the tip byte-identical at 100M on all six sets, 342/342):
- 6a8b4033 the early end (`decided<Dealt>`, noinline, value arguments) runs before the loop and after an act only
  when `us.alive + 16*them.alive` changed (members fall only in act / hurt_by_camps; play_quiet never kills), and
  not on the last turn: corpus -2.50%.
- f1a339c3 decided returns its turns as an int (-1 undecided): no stack frame in simulate, -0.34%.
- f9ef1408 non-plain act calls stun_skips only when `self.stunned` is non-zero: -0.06%.
- 9f7101f7 act's member loops through `each<N>` (a fold for N=1, a NO_UNROLL loop otherwise), act<1> / act<0> by
  count: the same operations in the same order, cheaper codegen, -0.68%.
- Together corpus 23,370,409 -> 22,540,001 (-3.55%, -138 a sim). Against m7 at 100M: total -0.03% to -0.07% on
  every set, p99 -0.1% to -0.2%, over 100k def 591->584, wide 2696->2675, pool 7466->7358, big 1986->1971,
  heavy 4941->4905, td 2285->2253. Real budget OOF play turns pool 624->566, big 208->214, heavy 541->405,
  td 192->169 (games diverge there; read with the A/B).
- A/B (tip fc7-sim-b, = 9f7101f7, against astraeus-5166d1c on fc7-w, 10,240 games): 51.0% (CI 50.0-51.9), OOF
  turns 52,220 against 71,210, mostly merges 1-7 (m7 read 50.3% on fc7-m); mean 50,050 against 51,037 a turn.

Dropped (corpus, identical results; + is dearer): restrict on act -0.02% (noise); quiet act inlined in simulate
+0.51%; play_quiet noinline +0.24%; play_quiet only when the next side is quiet +1.90%; quiet test reordered
(goto) +1.45%, `next` first +1.25%; act<2> / act<3> unrolled +4.26% / +3.03%; no One specialisation +2.18%;
act split into noinline plain / mixed paths +1.90%; cast out of line for multi-member sides +6.42%. The sim's
codegen punishes every added branch or call: the lever left is fewer act calls, not cheaper ones.

Open: the 15% target is out of reach inside the sim (act's body is now mostly the member loop's loads and float
adds the result depends on). Larger, outside it: walk_allies_in + make_slot/make_fighter + fill (~6.7k a heavy
turn) build each fight's sides afresh; sharing them across the turn's fights is a design change, not a codegen one.

## merge 9

Batch 9: the reach worker's `fc7-reach` (a9b2bc21, e11035e7; notes 7e7eebc3, 7f82e869) and the sim worker's `fc7-sim`
(6a8b4033, f1a339c3, f9ef1408, 9f7101f7; notes f9c1cd41), cherry-picked onto merge 8 (f3f464e2). Only
`model/safety.{cc,h}` changes; NOTES conflicts (appended sections) resolved by keeping both. Frozen as
`variants/fc7-m9`. Nothing dropped.

Review (all exact):
- a9b2bc21: `bounds_` is filled by `set_bounds()` after both `build_ways` calls (the reused-sets path and the full
  build); bound() reads extent_, units_, splash_ and the way, written only in build. No refresh or invalidate touches
  a Reach. The no-dash path: `dash` is false both when the champion has no dash and when its dash is not ready on
  either turn (with uncertain cooldowns `ready` is all true, so `dash` is true); `fixed`, `in_bushes` and `solid` feed
  only `pass`, read only by `dash_from` under `dash`. The sets' key holds `dash` in `sets_kind_`, so a no-dash build's
  sets (keyed on an empty `fixed`) never serve a dash build; between no-dash builds the sets do not read `fixed`, so the
  extra reuse is exact. ways ≤ 14 = bounds_' size; bounds fit int8.
- e11035e7: `next_turn_round` / `world.slot` of an ally read its acted / visible / teleport / stun state and the ranks.
  Each champion is its own instance, so the static snapshot lives for one turn; within it those change only in
  update() (observe skips allies read this round), so the value worked out later in the turn equals the one the
  first build took. A new round (also after an out-of-fuel or StaleTurn turn) resets the snapshot as before.
- 6a8b4033 / f1a339c3: every health loss goes through `Side::take` (hurt, spill, hurt_one, hurt_by_camps), which
  decrements `alive` on a fall (and the linked body's); heals and shields only raise health; play_quiet and
  play_shielded break before any lethal hit (`takes` / `on_us < uh`). So `us.alive + 16*them.alive` changes exactly
  when the old per-iteration checks could newly fire; the checks after hurt_by_camps (inside the act step) still run.
  The start-of-iteration decided at t+1 moved to the end of t: no state changes between, and `t + 1 < 2*horizon`
  is the old loop's bound (also after play_quiet advances t). The forced first-act check (`alive = -1`) adds a
  decided call only where the old code returns at the same point, or with `them.count == 0`, which trade() never
  simulates. decided's int return gives the same pairs ({0,0}, {0,0} with falls_unknown, {0,horizon}).
- f9ef1408: stun_skips with `stunned == 0` loops zero times and returns 0. 9f7101f7: the fold runs f(0..N-1) in
  order; `continue` became `return` in the lambda; same float ops in the same order.

Identity (100M, against `base-*-100M.json`): def 16/16, wide 52/52, pool 128/128, big 32/32, heavy 50/50, td 63/64.
The td game `gen-ladder-73102000067` side a is the one the reach worker found: debug copies of merge 8 and merge 9
with a `GCOST` print at `Pathing::route`'s `cheap_guard` test (both replaying byte-identically to their bench games)
read `step_guard_costliest()` 15,559 (m8) and 14,695 (m9) in round 370, and after normalising fuel counters the first
difference in the whole trace is that switch (two-search vs single-search path). Kept: base fuel dependence, as in
merge 8.

| set | total vs base | mean base -> m9 (m8) | p99 base -> m9 (m8) | over 100k base / m8 / m9 | round 1 mean base -> m9 |
|---|---|---|---|---|---|
| def | -2.37% | 51,433 -> 50,227 (50,264) | 97,736 -> 95,105 (95,522) | 704 / 578 / 566 | 229,550 -> 213,189 |
| wide | -2.37% | 50,497 -> 49,309 (49,353) | 103,147 -> 100,494 (100,765) | 3,086 / 2,664 / 2,614 | 220,749 -> 205,411 |
| pool | -2.33% | 53,464 -> 52,231 (52,292) | 107,853 -> 102,916 (103,502) | 9,367 / 7,292 / 7,093 | 231,778 -> 215,782 |
| big | -2.36% | 61,397 -> 59,964 (59,987) | 104,092 -> 99,506 (99,733) | 2,523 / 1,934 / 1,908 | 267,537 -> 245,895 |
| heavy | -2.36% | 52,013 -> 50,803 (50,845) | 119,186 -> 116,367 (116,728) | 5,556 / 4,876 / 4,808 | 251,544 -> 231,105 |
| td | -2.01% | 53,524 -> 52,450 (52,514) | 100,172 -> 96,896 (97,116) | 2,744 / 2,230 / 2,174 | 234,695 -> 217,362 |

Over 100k in the six sets 23,980 (base) -> 19,574 (m8) -> 19,163. Round 1 is unchanged from m8. The max turn on pool,
big and heavy (371,829 / 322,650 / 373,987, above the base's) is merge 8's, unchanged here. Real budget (indicative), OOF
pool / big / heavy / td: base 770 / 248 / 707 / 209, m8 583 / 169 / 499 / 163, m9 567 / 191 / 399 / 186 (1,934 ->
1,414 -> 1,343).

A/B `m9` (`fc7-m`, 10,240 games, own drafts, real budget) against the base: **50.7% (49.8-51.7)**. OOF 48,321 /
71,064 (**-32.0%**; m8 -27.9%), in 6,293 / 7,213 games, by rounds: 1: 3,331 / 6,272 (-47%), 2-10: 2,909 / 6,374
(-54%), 11-60: 7,043 / 9,060 (-22%), 61-300: 11,614 / 16,211 (-28%), 300+: 23,424 / 33,147 (-29%). Champion-game runs
of 50+ OOF 103 / 904 (m8 966 / 989). Fuel a turn mean 50,054 / 51,075, p50 47,250 / 48,750, p90 86,450 / 86,550,
p99 91,450 / 92,950, at or over 100k 0.21% / 0.25%. Shortcuts 1.946M / 2.262M: farm-partial-evaluation 952k / 1,066k,
step-guard-entry 528k / 587k, prey-cut-short 133k / 160k, turn-order 99.5k / 133k, step-guard-look 72.5k / 75.7k,
out-of-fuel 48.3k / 71.1k. Cumulative OOF against the base by merge: m1 -2.6%, m2 -3.8%, m3 -9.9%, m4 -11.0%, m5
-19.6%, m6 -21.2%, m7 -27.1%, m8 -27.9%, m9 -32.0% (the suite's ref reads 70,161-71,064 across runs).

Open leads (batch 9 added to merge 8's list, deduplicated):
- `Pathing::route`'s `cheap_guard` switch reads the step guard's measured cost and its two searches can differ
  (dash vs step): any change to the guard's cost (now including Reach's) can change play at 100M. Making the
  cover-first search equal the guarded one in every case, or the switch independent of measured fuel, changes play
  and needs an A/B.
- Fight sides: walk_allies_in + make_slot / make_fighter + fill (~6.7k a heavy turn) build each fight's sides afresh;
  sharing them across the turn's fights is a design change. Inside the sim the lever left is fewer act calls.
- Reach: a cross-round memo for an unmoved enemy (19% of misses repeat an answer; keyed on sets, recipe, units, the
  owner's ward mask, our bush vision: at most ~45 a turn); at()'s ~100 prologue a miss. Per-way hit windows are dead
  (the box test is already O(1); 97% of misses hit at the first or second way).
- Step guard: the first union sim (10.8k on heavy resolves) shrinks only with a cheaper sim; GuardFoes' ~400 build.
- Prey/altar: `returns_go_round` dearer by ~3k where compute_to runs to exhaustion; `kite_plan` 1.7-2.4k on 17-23% of
  fires-set heavy turns; `team_pressed` ~1.2k a call; Monolith `consider` and `siege_ready` (~1.2-1.7k on 12-18% of
  fires-set turns); prey's `fight_key` Reach rebuilds after a refresh.
- Strike search: `viewers`' ward lookup once per round, its row loop; `Unit{}` per foe and the Search constructor's
  zeroing; `pass_` rebuilding boards `blocked()` built; the late-cover ~400; `step_guard` itself in the loop.
- Bytes: farm's `centre_steps` reset (codegen risk); grow's Node copies; `__cxa_allocate_exception` on heavy turns.
- Merge 6's list otherwise (round 1's `build_static` / `init_beliefs` / `champion_enemy`, round-1 and rounds 2-10 OOF
  stacks, `rebuild_altar_access`' uncapped floods, prey's loop, the update's `read_priorities` / `update_champion` /
  `ally_next_rank`, `raw_output` per champion, the stale tail); fuel gates not worth building.

## strike2

Branch `fc7-strike2`, from main 6f7bccaf (merge 9). Exact changes only. Final tip c988ef71, frozen as
`bots/variants/fc7-strike2-g`.

Profile (section marks in `plan_strikes`, heavy set, 5,864 searches, mean 22.1k a search):
- foe record 429, `Unit{}` 138, partner_bound 195, viewers 777;
- terrain 263, blocked rebuild and read_grid 1,432, pass_ 236;
- Search ctor 378 (mostly zeroing), read prologue 308, read_spells ~770 (find_centres 338);
- grow ~5k, spread out: settle/offers 1,546, attack children 1,081, reset and walk 452, dash 429, spells 542;
- guard: pre-loop 1,665, read_cover 673, resolve 2,422 (19.8k on searches over 40k);
- camp, gather and rank 894, blow queries 1,394, carry-out 527.

Searches run on about 4% of turns, so 200 a search is about 7 a turn. The guard's resolve and cover are the biggest
cost, but they are left alone: they must resolve where the base does, and they feed `step_guard_costliest`.

Shipped:
- **7d6af36d (C)**: the Search members `h` (UnitHealths) and `unit_cell` are no longer zeroed.
  - Why exact: both are written for every t < n in read() (the foe loop, read_camps, then unit_cell after
    read_camps), and read only below n. `opened()` reads unit_cell over `s.dead` bits, which are all below n.
    The walk-only path never reads either.
  - Saving: exactly 201 a search.
- **c988ef71 (A')**: on maps of 100 or more 8x8 chunks, read_grid and the pass board read the board storage in place
  (pathing.cc's `window::corner/gather/cut`), and the three pass boards are gathered together without or_into.
  `across` is worked out once a map. The box is drawn only when it is needed: small maps, or an unpacked terrain
  grid.
  - Why exact: the window gives the same bits as and-ing with the drawn, clipped square. On small maps the base
    path is unchanged.

100M, against `m9-*` (`bench.py compare`; per-turn deltas from a turn-paired script). Every set is byte-identical
to m9. Against base, every set is identical except td's gen-ladder-73102000067 side a, the known merge 8/9 game.
Round 1 is unchanged on every set.

| set | identical | total | mean a turn | heavy-turn (m9 >100k) mean / p1 / p10 | p99 | max | over 100k |
|---|---|---|---|---|---|---|---|
| def | 16/16 | -546k | -6.6 | -42 / -364 / -174 | 95,105 -> 95,076 | 209,781 -> 209,617 | 566 -> 566 |
| wide | 52/52 | -1.69M | -6.6 | -54 / -380 / -174 | 100,494 -> 100,405 | 259,749 -> 259,607 | 2,614 -> 2,609 |
| pool | 128/128 | -4.07M | -6.8 | -50 / -670 / -176 | 102,916 -> 102,869 | 371,829 -> 371,829 | 7,093 -> 7,075 |
| big | 32/32 | -1.65M | -8.4 | -68 / -1,179 / 0 | 99,506 -> 99,385 | 322,650 -> 322,650 | 1,908 -> 1,900 |
| heavy | 50/50 | -1.73M | -7.6 | -40 / -635 / -174 | 116,367 -> 116,356 | 373,987 -> 373,987 | 4,808 -> 4,803 |
| td | 64/64 | -2.12M | -7.8 | -66 / -893 / -174 | 96,896 -> 96,866 | 265,353 -> 265,189 | 2,174 -> 2,168 |

Turn-paired p90 and p99 deltas are 0 on every set. The p99 column above is the per-set percentile.

What each change gives on its own (both identical on all six sets):
- C (bench d, against m9): -6.4, -6.3, -6.1, -2.8, -4.8, -6.3 a turn (def, wide, pool, big, heavy, td).
  Heavy-turn means are -46, -56, -44, -17, -35, -48. Nothing is dearer at p90 or p99.
- A' (bench f against e: both carry C and E, so the difference is A'): -0.2, -0.4, -0.7, -5.5, -2.8, -1.5 a turn.
  - big: heavy-turn mean -50, p1 -900, p90 and p99 0.
  - Small maps: heavy-turn p90 and p99 +25..41. These are turn-end queue reshuffles; totals fall on every set.

Real budget (indicative; benches swing ±10-20% once games diverge). OOF play turns base / m9 / g:
- pool 770 / 567 / 548
- big 248 / 191 / 194
- heavy 707 / 399 / 387
- td 209 / 186 / 153
- in all 1,934 / 1,343 / 1,282 (-4.5% against m9)

Shortcut out-of-fuel firings m9 -> g: 655 -> 636, 237 -> 240, 472 -> 460, 227 -> 194. step-guard-entry rose on big
(603 -> 717) and fell on heavy and td.

A/B `strike2-g` (`fc7-w`, 10,240 games, real budget) against the base: **50.0% (49.0-50.9)**. OOF 49,518 / 72,274
(**-31.5%**). Other workers' tips on fc7-w: sim-b 52,220 / 71,210 (-26.7%), reach-d 53,459 / 71,714 (-25.5%).
- OOF by round: 1: 3,298 / 6,269; 2-10: 2,765 / 6,099; 11-60: 6,989 / 9,092; 61-300: 11,252 / 16,028; 300+:
  25,214 / 34,786.
- Runs of 50+ OOF turns: 692 / 833.
- Fuel a turn: mean 50,035 / 51,074, p50 47,250 / 48,750, p90 86,350 / 86,550, p99 91,450 / 92,850. At or over
  100k: 0.21% / 0.26%.
- Shortcuts 1.920M / 2.232M: step-guard-entry 531k / 587k, prey-cut-short 128k / 153k.
- The win rate is level. Both changes are exact at 100M, so play changes only where the real budget cuts a turn.

Dropped:
- **A, the ungated in-place read_grid**: identical. Totals -0.01% on big and heavy, but dearer on small maps.
  Heavy-turn means were def +27, wide +35, pool +20, big -52, heavy -19, td +7. Host whole-board ops cost 13 plus
  1 a chunk, which beats the fixed ~150-200 of an in-place read until a map has about 100 chunks. A' gates on that.
- **A-gated, the first gated version (bench c against d)**: big -5.7 a turn, but def and wide +0.1-0.2, and small-map
  heavy-turn p90 +52..88 and p99 +119. It still drew the box eagerly and worked out `across` on each read. A'
  replaces it.
- **B, lazy blocked parts in pathing**: B kept the boards blocked_ is built from (allies, enemies, camps, the
  rest, teleports) and joined them only on demand, so read_grid could read just what it needed. It was identical.
  - First version: p50 +21 a turn, dearer overall.
  - Restructured (b2): p50 +9, total +0.03% on def, and more turns over 100k on pool, def, wide and td. On big,
    heavy-turn mean -68 and p1 -1,558.
  - The per-turn upkeep outweighs the saving except on big maps, and A' takes most of the big-map gain anyway.
- **E**, two changes:
  - `heal_at` without its fill: a written-cells mask, unwritten cells read 0;
  - find_centres' hash table stamped, not zeroed.
  - It was identical and level against C (mean ±0.2 a turn; heavy-turn p90 +6, p99 +12). The fill fires only with
    a heal, and the extra cost of each probe cancels the saved memset.
- Not built, by reasoning or a measured section cost:
  - per-tile cover tests: they break FirstPass sharing and change the costliest measure that feeds cheap_guard;
  - shrinking Node: only 72-byte copies, about 5 a search;
  - caching ward lookups: ~115 a search, and `ward_info.disabled` semantics unverified;
  - sharing partner_bound: ~100, only for Cassi & Issac;
  - trimming `Unit{}`: ~90 a search, with codegen risk;
  - masking the `near` memset (648, only with foes plus unseen > 8) and the touch1 fill (324): the mask costs
    about what it saves;
  - grow micro-work: the cost is spread thin;
  - strike_memo: 94 a call, already cheap;
  - `__cxa_allocate_exception`: StaleTurn throws on merged OOF turns, ~125 a call, not a 100M lever.

Open:
- The guard's resolve on searches over 40k (19.8k mean there) is the one big lever left. Any change to it must keep
  the base's resolve points and `step_guard_costliest`.
- The blocked rebuild on big maps (B's measurement): a lazy join pays only if its upkeep is gated on map size like
  A'.

## camps

Branch `fc7-camps` on main f3f464e2 (merge 8). Area: camp work on fight turns, worst on pack maps. Frozen tip
`variants/fc7-camps-b`. **Hot-map set** `camps-hot` (`MAIN/replays/fuel/fc7/camps-hotset.txt`, 48 maps, 96 games
vs the base): the late worker's top 40 (`/tmp/fc7/late/hot40.txt`: 8 the-pack, 7 elk-arena, huge, hooks, ...),
ladder 02the-pack, 01elk-arena, 03the-front, 01hooks and 4 `p5-a` mut-the-front. m8 is byte-identical to the base
there (96/96). Scripts: `/tmp/fc7/camps/hot.sh` (the set at 100M / real), `tools/cp.py`, `tools/cpt.py` (debug copy
`variants/fc7-camps-dbg`: fuel scopes with self/inclusive, per-caller tags, CPS/CPT stdout lines).

### Where camp fuel goes (debug copy, hot set, 100M; 660k turns, 29.9k heavy turns >= 95k)

Per heavy turn, inclusive (all turns in brackets): update_camps 4.1k (2.85k: view 0.45k, camp_settled 0.7k at 157 a
call, update_camp 2.0k at ~94 a member read, loop self ~0.5-0.9k), find_members 2.8k (1.1k; 1.09 calls), min_camp_damage
2.9k (0.41k), camp_trapped 2.2-2.5k (mostly its first find_members; self 0.15k, exit way 0.33k, exit_hits 0.2k),
camp_damage 0.84k (2.1 calls, 25 members), escape_landings 0.35k, threats_near 0.21k, wake 0.2k, find_wakers 0.16k,
refresh 0.25k. About 11k of a heavy turn, spread thin: no exact lever of 1k was found.
- **The min_camp_damage tail**: 8.7% of heavy turns spend 10k+ there, 23k a turn (8.3 calls, 3 cache hits): clear_fire
  12.9k for 1.78 rebuilds (sort 7.6k, passes 5.3k), scalar loops 2.2k (5.1 calls, n ~10), stand_reach first builds
  2.5k, fill/order_holds the rest. By caller: farm's `known` 8.0k (2.7 calls), crew 6.4k (4.3), struggling 4.8k (0.39
  calls, 12k each: the ally's range class rebuilds its own order), affordable 2.4k. Rebuild causes there: first
  build of a (group, range) 0.76, a member died 0.70, an order flip or >8 moved 0.32. Spread over the game (not early).
- **Sort cost by size** (all heavy turns): n<6 26, n 6-23 150, n 24-47 385 (8.3k a sort), n 48+ 145 (13k a sort).
  Nearly every sort of 24+ has an exact tie (equal ratio and equal fire), and those sizes run libc++'s introsort.
- find_members on its heavy turns (4k+, 25% of heavy turns): 7.4k (1.18 calls, 1.45 groups): emit 4.6k (~240 a
  member, big groups), near filter 1.4k, others 0.7k, stir 0.4k; the small-group path only 0.3k a heavy turn.
  Per-group repeats within a turn (same inputs as the previous call's): 22 a heavy turn. Dead, as front found.

### Shipped (identical at 100M on def, wide, pool, big, heavy, td and camps-hot; 438/438 replays)

1. d49efddb **Search::find_wakers lists the champions within the group's widest reach of its members' box once per
   group**, allies then enemies as before. Exact: a member's `consider` rejects d > its reach <= the group's reach,
   and d >= the champion's distance to the box.
2. c68064ba **threats_near lists the other champions (tile, acts first) once**, not per camp member: the same
   filters and order; `world.slot` is a pure read.
3. 747d1691 **farm's passing() prices the clear (`affordable`, a min_camp_damage) after its cheap tests**: the result
   is their conjunction; every operand is a pure read (min_camp_damage's caches change no answer).
- Together vs m8 (= base) at 100M: total def -0.05%, wide -0.05%, pool -0.05%, big -0.01%, heavy -0.06%, td -0.05%,
  hot -0.06%; cheaper turns 10-20x the dearer ones; p99 -0.0..-0.2% (hot 122,737 -> 122,506); max unchanged but wide
  263,620 -> 265,931; round 1 unchanged. Over 100k: def 578 -> 576, wide 2664 -> 2657, pool 7292 -> 7267, big 1934 ->
  1932, heavy 4876 -> 4868, td 2230 -> 2226, hot 21,199 -> 21,025.
- Real budget (indicative), OOF m8 -> tip: hot 5,893 -> 5,632, pool 583 -> 566, big 169 -> 197, heavy 499 -> 560, td
  163 -> 170.
- A/B `camps-b` (`fc7-w`, 10,240 games, real budget) against the base: 51.4% (50.4-52.3). OOF 51,624 / 70,936 (-27.2%;
  m8 alone read -27.9% on fc7-m, so the three changes are within noise), by rounds: 1: 3,291 / 6,266, 2-10: 2,760 /
  6,098, 11-60: 7,338 / 8,942, 61-300: 11,911 / 15,718, 300+: 26,324 / 33,912; champion-game runs of 50+ 803 / 520.
  Fuel a turn mean 50,033 / 51,041, p50 47,250 / 48,750, p90 86,350 / 86,550, p99 91,550 / 92,850, at or over 100k
  0.22% / 0.25%. Shortcuts 1.939M / 2.233M.

### Dropped (measured)

- **find_members' small-group path filtered by box distance** (as the big path does; exact by the same box argument):
  identical but dearer, total +0.02..+0.11% (def +0.11%): the small path is 0.3k a heavy turn and the per-other box
  test costs more than it saves on common turns.
- **Incremental clear order** (the previous order minus the dead, re-sorted: insertion sort below 24 is stable, so with
  exact products (a strict weak order) and ties in member order it is std::sort's output): at most ~150 a heavy turn,
  since 70% of sort fuel is n >= 24, where libc++ partitions and nearly every sort has ties. Not built.
- **Run-length scalar damage** (exact integer sums when fires are whole and sums < 2^24): the scalar loop is 358 a
  heavy turn, 2.2k on tail turns. Not built.
- **Warming the other range class's stands in the queue**: stand_reach first builds are ~280 a heavy turn, 78% of it
  in rounds 1-99. Not built.
- Not built, by measurement: a cheaper escape_landings `danger` grid (0.35k a heavy turn; a 5x5 window per threat
  costs about what the per-tile loop does), update_camps' view tests skipped while our tile and ward hold (~150 a
  turn, needs a ward read), camp_settled's health_round writes made lazy (~80 a call, every reader would need it).

### Open (small, exact)

- camp_settled's per-member `health_round` writes (~260 a turn on hot maps, every turn): a lazy "settled through
  round" marker read by update_camp, camp_settled and farm's freshness tests.
- update_camp: a member read awake last round within reach of our end-of-turn tile stays awake (rules camps.sleep: that
  phase was occupied); its camp_awake read could go (~20 a member).
- `Safety::refresh` (0.25k a heavy turn): its camp_stunned loop changes only after our own stun casts.
- The ally-range rebuild in `struggling` (12k a call on tail turns) is real work: the ally's range class has its own
  stands, fires and tie order.

## late

Branch `fc7-late` on main f3f464e2 (merge 8). Area: out-of-fuel turns late in long games, and OOF streaks. **Nothing
shipped**: the diagnosis below says where late OOF fuel goes; the five exact ideas measured are dead or dearer.
Scripts in `/tmp/fc7/late/tools/` (`streaks.py`, `buckets.py`, `srchrep.py`, `cenlate.py`, `selfl.py`, `lab.py`,
`cst.py`, `mcd.py`).

### Diagnosis (m8 vs base, `fc7-w`, 10,240 games, real budget, replays kept; then a census and the profiler)

- **There are no streaks.** The `>=50` bucket of `oof_bot.py` counts the OOF turns of champion-games with 50+ OOF in
  all, not consecutive runs. In this run m8 had 11 such champion-games (659 turns), the base 12 (736). The longest
  consecutive run (gaps of 1-2 rounds, the late finish) is 14 turns for m8 and 8 for the base, in 10,240 games. A
  50+ champion-game is a long standoff game reaching round 2000 (`mut-the-pack`, `mut-elk-arena`, `gen-huge`,
  `mut-hooks`), with 50-86 OOF turns spread over 1,500 rounds.
- **The m7 384 / m8 966 swing is noise.** The bucket is ~6-15 champion-games, clustered (one the-pack game gives 4-5
  of them). The reference bot, the same code in every A/B, reads 593 to 1,444 across the campaign's A/Bs (m7's own
  ref 782, m8's 989); this rerun of m8 on `fc7-w` reads 659.
- **Late turns are not heavier.** OOF per 10k turns by round bucket, m8 / base: 2-10 120 / 250, 11-60 26 / 32,
  61-300 8.9 / 11.9, 300+ 8.1 / 10.5 (-23%). Rounds 300+ hold half the OOF because they hold 66% of the turns (32M
  of 49M). The early buckets fell 47-54% because rounds 1-10 had their own start-up work (r1, r1b, r1c); the late
  rate falls with the fight-turn work that every later round shares.
- **Hot spots.** Late OOF per 10k turns: the-pack 178, the-front 90, elk-arena 57, hooks 30, contest 26, sunburst
  25; ladder-class maps 5.6, but they hold the most (7.5k of 26k). The 40 maps with the most late OOF hold only 17%.
  6-body games (Cassi & Issac with 5 picks) hold 14.4k of 26k late OOF (8.4 per 10k against 4.9 for 4 bodies).
- **Branch of the late finish** (A/B D lines): farm 35%, retreat 23%, ran out inside decide 19%, bank 13%, chase 6%.
  86% of late OOF turns are first-in-streak; 14% are a late finish running out again.
- **Census** (`variants/fc7-late-cen` = m8 with `--fine --trace --lenient`, real budget vs the base, the top 40 late
  maps plus 60 random `fc7-w` maps, 200 games; `/tmp/fc7/late/cen`, tables `/tmp/fc7/late/cen-late.txt`): 3,060
  OOF-first turns past round 300. The stand (want_home 23k on 40%, or channels 26k on 60%: the same stand under a
  feint recall) and the strike search (41.5k on 56%) dominate, as on every fight turn. Signatures: want_home or
  channels + strike_search 39%, farm alone 9%, stand + retreat 10%. Self fuel on late OOF turns:
  - other maps: strike_search 20%, `wh.stand_lost` 7%, `s.new_fight` (the sim) 7%, route 3.7%, `s.reach_build` 3%;
  - the-pack + elk-arena (55% of the census's late OOF): strike_search 11%, `s.awake_members` 5.8% (75% of turns),
    the sim 5.5%, `wh.stand_lost` 5.3%, `clear_fire_sort` 4.8%, `camp` (update_camp) 4.7% (98%), siege_kite 4.3%,
    retreat 4.2%, `wh.camp_trapped` 3.1%. Inclusive on late OOF turns: `min_camp_damage` 23.4k on 21% (19k of it
    `clear_fire`), `wh.camp_trapped` 7.7k on 63%, `s.awake_members` 5.7k on 70% (7.4 calls), `dash_away` 23.7k on
    7% (22k self), `ss.wakers` 13.6k on 7%, `ss.centres` 11k on 9%.
- **Profiler** (m8 self-play on the top 40 late maps, 4,216 heavy merged turns, mean 164k): plan_strikes 10.6k,
  find_members 6.7k (1.8 calls, 3.7k a call), farm_turn 6.1k, update_champion 5.6k, act 5.4k, update_camp 5.2k (2.8
  calls, 1.9k), Reach build/at 7.8k, Search::wake 3.0k (0.4 calls, 7.3k), the clear_fire sort 2.6k + clear_fire 1.7k,
  update_camps 2.6k, pack_members_of 1.7k, exit_hits 1.3k, escape_landings 1.3k (9k a call), threats_near 1.0k (7.2k
  a call). Camp work is ~15% of a heavy turn on these maps.
- **Cross-turn repeats on late OOF turns**: of 17,288 strike searches on m8's late OOF turns, 124 (0.7%) have the
  same shape (every SRCH field but fuel) as the same champion's search 1-2 rounds before; over all late searches
  6.5%. Shape equality is only necessary for an exact repeat. Cross-turn memos are dead here too.

### Dropped (measured)

- **`camp_stunned` memo** (find_members' emit and Safety::refresh read a camp's buffs per member): debug count on the
  top 40 maps at 100M: 3.1 calls a late turn, 54 fuel a turn (240 on the-pack, p99.9 1.8k), 0.5 same-turn repeats a
  turn, and 334 repeats whose answer changed (our own stuns). Not worth a key.
- **Group-level health in update_camp** (skip member reads when a group's total is unchanged; camps never
  regenerate): the SDK has no group health read (`sdk_camp_group_*` give state, cooldown, capture only), and
  `sdk_camp`'s record has no awake state, so both per-member reads stay.
- **find_members** (debug brackets, 481k calls on the top 40 maps): 1.2k a call; the 12% over 3k average 5.6k, 3.6k of
  it the big-group emit loop for ~34 members (~105 a member, already SIMD and box-filtered); others 0.4k, stir 0.3k.
  No piece to take; front's within-turn repeat rate (1.5%) stands.
- **`min_camp_damage` / `clear_fire`** (debug brackets): on turns spending 10k+ there (3% of turns with a call, where
  OOF concentrates), 21k a turn: 3.6 recomputes, 3.2 sorts (2.2k a sort, n up to 48), sort 7.0k, second fire pass
  2.9k, first 1.9k, inner walk 2.1k, `order_holds` 1.1k. Recomputes never repeat inputs (key: group, range class,
  version; versions only rise). **Index sort** (sort one-byte indices with the same comparator, then permute: the
  same comparisons, so the same permutation, ties included; branchy introsort for both element types):
  byte-identical 80/80 on the top 40 maps at 100M, but dearer: total +0.03%, 28,360 turns dearer against 3,147
  cheaper, p99 +0.2%. The comparisons, not the 20-byte moves, are the cost. Reverted.
- Not built: `dash_away`'s second call (retreat, fight.cc 1208) repeating a failed first with the same inputs: 1.1
  calls a turn where present, so the repeat is rare.

### Open

- `threats_near` + `escape_landings` (7.2k + 9k a call, 1.6k a heavy turn on the hot maps): `danger()` is every
  landing (up to 25) x every awake member near. Summing per tile in hazard order (hazards outer, tiles in each one's
  reach inner) keeps the float sums; with a window test it might halve it. Also the Hazard's 28-byte `blow{}` zeroing
  and copy per camp member (unused for camps).
- `Search::find_wakers` (7.3k a call on 7% of late pack OOF turns): each sleeping member tests every ally and enemy
  and asks `world.slot`; a champion beyond the group's box by more than its widest reach can be dropped once per
  group (the same consider order), ~10-13k on those turns at most.
- `clear_fire`'s sort only shrinks with fewer comparisons, which changes tie order unless no two members tie.
- The late OOF class is the fight turn (stand + strike search + the sim) that fight, strike, guard, reach and sim
  own; nothing specific to late rounds or standoffs was found.

## sides

Branch `fc7-sides` on merge 8 (f3f464e2). Area: building each fight's sides for the sim (`make_slot` /
`make_fighter`, `fill`, `walk_allies_in`) and whether they repeat within a turn. **Nothing shipped**: the sides
are already shared where they repeat, and what is left is small and rebuilt from inputs that changed.

### Where the fuel goes (function profiler, fc7-m8 = `variants/fc7-sides-0`, heavy set self-play, real budget)
- 124k turns, 113 heavy (mean 145k, merged OOF turns), 60 fight-heavy (a sides function or the sim ran). Per
  fight-heavy turn: make_slot 902 + make_fighter 837 (6.4 builds at ~272), fill 726 (3.9 at 188),
  walk_allies_in 422 (1.9 at 222), new_fight 332, chase_trade 246, trade 201; the sim around them: act<0> 3.3k,
  simulate 2.5k, act<1> 0.85k. The sides are ~2.9k of a 142k fight-heavy turn (2%), ~140 a turn over all turns.
  `fighting_allies` (who joins) adds 680 (3.6 calls).
- Fighters are already built once per Safety and kept for its life (`made_` bits over `made_fighters`, kits kept
  across turns by `kit_of`); every fill copies them.

### Repeats (debug copy, `replays/fuel/fc7/sides/sides-dbg.diff`; heavy set + 12 heavy maps, self-play, real budget)
- **Within a turn nothing is rebuilt**: of 70k `make_slot` calls, 262 rebuild a slot already built this round
  (0.4%, a fight asked again after `see_again`/`see_stuns`/`see_kills` made a new Safety), and 152-220 of those give
  the same fighter. A per-turn fighter cache keyed on Safety's generation has nothing to take.
- **No fight's sides repeat within a turn**: hashing both sides and the flags at `trade()`, 24-25 of 16.6k-20.6k
  sims (0.1%, 0.1-0.2% of sim fuel) repeat a sim of the same round. Each candidate sim (guard, stand, chase) is a
  different roster or arrival.
- Across turns: 40-53% of builds give the slot's previous fighter (mostly allies and idle enemies whose cooldowns
  are ready), but a build is ~270 and an exact key reads the same ~20 belief fields plus `next_turn_round`, so
  at best ~0.3k a fight-heavy turn. Trade inputs repeat a sim among the last 64 for 6.7-13% of sim fuel, the
  cross-turn fight memo already found dead (~6-10%).
- walk_allies_in: 20.3k calls, 1.05 allies walked a call; 20% of calls (16% of its fuel) have an unseen enemy in
  the fight, which leaves every ally's walk at 0 (no change).

### Dropped (measured)
- **walk_allies_in reading each enemy's acts-from tile once, returning at once with no enemy or an unseen one**
  (`replays/fuel/fc7/sides/walk-allies-hoist.diff`, `variants/fc7-sides-a`): exact (an unseen enemy sets the walk
  to 0 for every ally; strike() is a memo). 100M identical on all six sets against `m8-*` (342/342) but level:
  total def -0.01%, wide +0.00%, pool +0.01%, big +0.01%, heavy -0.02%, td +0.01%; over 100k def 578 -> 581, wide
  2,664 -> 2,664, pool 7,292 -> 7,305, big 1,934 -> 1,938, heavy 4,876 -> 4,856, td 2,230 -> 2,245; turns dearer
  outnumber cheaper 2-6x (codegen). Reverted; no real-budget bench or A/B (no gain to read).
- **Not built, by the counts above**: a per-turn Fighter cache under `Safety::generation()` (0.4% rebuilds), a
  cross-Safety or cross-turn trade memo keyed on the sides (0.1% within a turn; the cross-turn one is the known
  dead memo), a cross-turn fighter reuse (key ~ build), fill copying only mutable fields (the sim reads every
  Fighter field, and splitting them changes the sim's code, which is the sim area's).

### Open (small, exact)
- `fighting_allies` ~190 a call (3.6 a fight-heavy turn): its per-round list is short; why a call costs this is
  unexplained (the function is ~40 instructions plus ~15 an ally).
- The sim's own cost (act 4k, simulate 2.5k a fight-heavy turn) is the lever around the sides; fewer act calls
  (the sim area's open item).

## merge 10

Batch 10, the last: the strike2 worker's `fc7-strike2` (7d6af36d, c988ef71; notes 2c008088, 0125b9be, on merge 9) and
the camps worker's `fc7-camps` (d49efddb, c68064ba, 747d1691; notes c58fad21, on merge 8), plus notes only from
`fc7-late` (371bba16) and `fc7-sides` (b69b0f57), cherry-picked onto merge 9 (6f7bccaf). The camps commits apply
cleanly over merge 9's Reach and sim changes (`find_wakers` in plan.cc, `threats_near` in self_abilities.cc, farm.cc:
none of merge 9's code). NOTES conflicts (appended sections) resolved by keeping both. Frozen as `variants/fc7-m10`.
Nothing dropped.

Review (all exact):
- 7d6af36d: read() writes `h` at every foe it keeps (`h[foes++]` on the walk-only and the full path) and every camp
  member (`h[n++]`), and `n = foes` before the camps; `unit_cell[t]` for every t < n after read_camps. The walk-only
  path returns before unit_cell is written, but `opened()` (its only reader) is called only from grow(), which a
  walk-only search never enters (`settle(root)` only); `read()` returning false ends the search. Every reader of `h`
  indexes t < n or a link / hor index < foes; `saved = h` copies the unread tail only to restore it.
- c988ef71: `window::corner/gather/cut/inside` are Pathing's (merge 8's), with `window::r == grid_r` asserted, so the
  window is the grid's 7x7. `inside()` masks columns and rows off the map, so padding bits past an odd width or height
  and chunks off the edge (gather skips chunks out of range; negative chunk indices use the arithmetic shift) never
  count: the same bits as and-ing with the drawn, clipped square. `from_window` moves bit 8r+c to 7r+c. The three
  pass boards or-ed word by word equal the or_into result read through the box. `across` is a static set once a game
  from the map's chunk count, never from fuel. On small maps read_geometry still draws the box before every
  read_grid (terrain_grid's argument), and the late read_grid at plan.cc's cover test runs after it.
- d49efddb: `dist` is Chebyshev (util.h), and a member's `consider` rejects d > mb.reach; mb.reach <= the group's
  `reach` (the members' max, world.cc), and no member is nearer a champion than the members' bounding box, so a
  champion beyond `reach` of the box was always rejected. The list keeps allies (index order, a < 8, not self) then
  enemies, with the same filters; Cassi and Issac are two beliefs, as before. 32 entries > 2 x 6 champions.
- c68064ba: threats_near takes a const World; `world.slot` is a pure read of ranks and team sizes, positions don't
  change within the call, so each champion's position and `first` are the same for every member. Listing them for
  champions out of reach adds no throw (slot can't throw).
- 747d1691: `affordable` returns true for the farm group and for strength-0 groups, so moving it last changes no
  answer. `min_camp_damage`'s caches give the same answer computed fresh: the `stands` table is static per map; the
  Slots cache hits only on the same group version and all of strength, reflect, range and survivable; the sorted
  members are kept across versions only when `order_holds` shows every comparison of clear_fire's sort unchanged and
  the same living set (so std::sort's permutation and the fire passes are the same), else rebuilt. A skipped fill only
  costs a later caller a recompute. ally_engaged, kited and taken (now before it) only read.

Identity (100M) against `base-*-100M.json`: def 16/16, wide 52/52, pool 128/128, big 32/32, heavy 50/50, td 63/64
(merge 9's `gen-ladder-73102000067` a); against `m9-*`: 342/342. Camps-hot (`camps-hotset.txt`, 96 games): m10 = m9
96/96; m9 against the base 95/96, `mut-one-gem-77021217053` b (m8 = base 96/96, so merge 9 brought it). Debug copies
of m8 and m9 with a `GCOST` print at the `cheap_guard` test (both replaying byte-identically to their bench games)
read `step_guard_costliest()` 15,348 (m8, two-search path) and 14,906 (m9, single) in round 126, the first decision
that differs; the trace's first other difference is in round 139. Kept: base fuel dependence, as in merges 8 and 9.

| set | total vs base | mean base -> m10 (m9) | p99 base -> m10 (m9) | over 100k base / m9 / m10 | round 1 mean base -> m10 |
|---|---|---|---|---|---|
| def | -2.43% | 51,433 -> 50,197 (50,227) | 97,736 -> 95,041 (95,105) | 704 / 566 / 563 | 229,550 -> 213,189 |
| wide | -2.43% | 50,497 -> 49,279 (49,309) | 103,147 -> 100,375 (100,494) | 3,086 / 2,614 / 2,603 | 220,749 -> 205,411 |
| pool | -2.40% | 53,464 -> 52,196 (52,231) | 107,853 -> 102,815 (102,916) | 9,367 / 7,093 / 7,048 | 231,778 -> 215,755 |
| big | -2.38% | 61,397 -> 59,949 (59,964) | 104,092 -> 99,364 (99,506) | 2,523 / 1,908 / 1,897 | 267,537 -> 245,883 |
| heavy | -2.43% | 52,013 -> 50,763 (50,803) | 119,186 -> 116,324 (116,367) | 5,556 / 4,808 / 4,789 | 251,544 -> 231,079 |
| td | -2.07% | 53,524 -> 52,413 (52,450) | 100,172 -> 96,828 (96,896) | 2,744 / 2,174 / 2,164 | 234,695 -> 217,359 |
| hot | -3.13%* | 58,077 -> 56,286 (56,337) | 126,892 -> 121,597 (121,934) | | 241,690 -> 222,187 |

(*hot: 95 identical games against the base; -0.09% against m9.) Over 100k in the six sets 23,980 (base) -> 19,163
(m9) -> 19,064. Against m9: -0.03% (big) to -0.08% (heavy) total. Real budget (indicative), OOF pool / big / heavy /
td: base 770 / 248 / 707 / 209, m9 567 / 191 / 399 / 186, m10 502 / 185 / 405 / 151 (1,934 -> 1,343 -> 1,243).

A/B `m10` (`fc7-m`, 10,240 games, own drafts, real budget) against the base: **50.5% (49.6-51.5)**. OOF 48,710 /
71,315 (**-31.7%**; m9 -32.0%: level), in 6,283 / 7,215 games, by rounds: 1: 3,315 / 6,272 (-47%), 2-10: 2,891 /
6,383 (-55%), 11-60: 6,931 / 9,163 (-24%), 61-300: 11,406 / 16,136 (-29%), 300+: 24,167 / 33,361 (-28%).
Champion-game runs of 50+ OOF 532 / 290 (m9 103 / 904: a dozen champion-games either way). Fuel a turn mean 50,022 /
51,068, p50 47,250 / 48,750, p90 86,350 / 86,550, p99 91,450 / 92,950, at or over 100k 0.21% / 0.26%. Shortcuts
1.946M / 2.255M: farm-partial-evaluation 952k / 1,059k, step-guard-entry 528k / 588k, prey-cut-short 132k / 159k,
turn-order 98.7k / 134k, step-guard-look 72.6k / 75.5k, out-of-fuel 48.7k / 71.3k. Cumulative OOF against the base by
merge: m1 -2.6%, m2 -3.8%, m3 -9.9%, m4 -11.0%, m5 -19.6%, m6 -21.2%, m7 -27.1%, m8 -27.9%, m9 -32.0%, m10 -31.7%
(the suite's ref reads 69,970-71,830 across runs; win rate 49.9-50.9% every merge).

Open leads (batch 10 added to merge 9's list, deduplicated):
- `Pathing::route`'s `cheap_guard` switch reads the step guard's measured cost and its two searches can differ
  (dash vs step): any change to the guard's cost can change play at 100M (two games of the 438 bench games so far).
  Making the switch independent of measured fuel changes play and needs an A/B.
- Step guard: its resolve on strike searches over 40k (19.8k mean there) is the one big strike-search lever left
  (must keep the base's resolve points and `step_guard_costliest`); the first union sim (10.8k on heavy resolves);
  GuardFoes' ~400 build.
- Camp danger: `threats_near` + `escape_landings` (7.2k + 9k a call, 1.6k a heavy turn on hot maps): `danger()` is
  every landing x every awake member near; hazards outer, tiles inner keeps the float sums; the Hazard's `blow{}`
  zeroing per camp member. `camp_settled`'s per-member `health_round` writes (~260 a turn on hot maps); update_camp's
  `camp_awake` read for a member awake last round in reach of our end tile; `Safety::refresh`'s camp_stunned loop.
  `struggling`'s ally-range rebuild (12k a call on tail turns) is real work.
- Fight sides: walk_allies_in + make_slot / make_fighter + fill (~6.7k a heavy turn) build each fight's sides afresh
  (no repeats within a turn: 0.4% rebuilds, 0.1% repeated sims); `fighting_allies` ~190 a call unexplained. Inside
  the sim the lever left is fewer act calls.
- Reach: a cross-round memo for an unmoved enemy (19% of misses repeat; at most ~45 a turn); at()'s ~100 prologue.
- Strike search: the blocked rebuild on big maps (a lazy join only gated on map size); `viewers`' ward lookup once
  per round; `Unit{}` per foe; the late-cover ~400; `clear_fire`'s sort (fewer comparisons change tie order).
- Prey/altar: `returns_go_round` where compute_to runs to exhaustion; `kite_plan` 1.7-2.4k on 17-23% of fires-set
  heavy turns; `team_pressed` ~1.2k a call; Monolith `consider` and `siege_ready`; prey's `fight_key` Reach rebuilds.
- Bytes: farm's `centre_steps` reset (codegen risk); grow's Node copies; `__cxa_allocate_exception` on heavy turns.
- Merge 6's list otherwise (round 1's `build_static` / `init_beliefs` / `champion_enemy`, round-1 and rounds 2-10 OOF
  stacks, `rebuild_altar_access`' uncapped floods, prey's loop, the update's `read_priorities` / `update_champion` /
  `ally_next_rank`, `raw_output` per champion, the stale tail); fuel gates not worth building.
- Late rounds: no streaks; the late OOF class is the fight turn (stand + strike search + sim).

## final (2026-11-06)

Final 20,480-game A/B of `variants/fc7-m10` (main after merge 10) against `variants/astraeus-5166d1c` on the
reserved `fc7-f` suite: **50.5% (95% CI 49.8-51.2)**; out-of-fuel turns **92,090 vs 137,120 (-32.8%)**, by round 1
-49%, 2-10 -52%, 11-60 -25%, 61-300 -30%, 300+ -30%; fuel a turn mean 49,935 vs 50,998, p99 91,350 vs 92,850; at or
over 100k 0.21% vs 0.25%; shortcuts 3.82M vs 4.46M. Files `replays/fuel/fc7/ab/final.*`; EXPERIMENTS "Fuel campaign
7, final". The campaign's commits on main are squashed into one; shas in these notes name commits on the workers'
`fc7-*` branches or main's pre-squash history.
