# Fuel campaign 5 (2026-11-03): notes

Findings, dropped attempts with numbers and open leads, by area. Workers append a `## <area>` section on their
branch; the merge agent keeps them on fuel5-orch. Baseline and method: BRIEF.md.

## Campaign summary

Three rounds, 13 fuel-only commits (CHANGES 308-320), all byte-identical at 100M on the 8 sets (234 replays). The
final bot is `astraeus-fc5-m3`. Real budget, own drafts, fast runner, fresh-11000..11019, 10,240 games each, against
fc5b in the same run:

| bot | win % (CI) | OOF cand / ref | r1 / 2-10 / 11-60 / 61-300 / 300+ | runs <10 / 10-49 / 50+ | fuel mean / p90 / p99 | >= 100k | shortcuts (no OOF) |
|---|---|---|---|---|---|---|---|
| fc5b mirror | 50 | 58,518 | | | 49,924 / 86,150 / 92,450 | 0.22% | ~3.05M |
| m1 (308-310) | 50.1 (49.1-51.0) | 60,117 / 60,007 (+0.2%) | 4,020 / 6,228 / 9,191 / 13,472 / 27,206 | 37,685 / 18,516 / 3,916 | 49,179 / 86,050 / 92,250 | 0.23% | 2.60M (-14.8%) |
| m2 (+311-313) | 50.7 (49.8-51.7) | 57,920 / 59,731 (-3.0%) | 4,178 / 6,268 / 9,030 / 13,113 / 25,331 | 37,358 / 17,678 / 2,884 | 49,229 / 86,050 / 92,250 | 0.22% | 2.60M (-14.5%) |
| **m3 (+314-320)** | **50.4 (49.4-51.4)** | **50,627 / 58,754 (-13.8%)** | 4,132 / 5,872 / 7,205 / 11,100 / 22,318 | 33,406 / 15,301 / 1,920 | 49,139 / 86,050 / 91,850 | 0.21% | 2.56M (-15.7%) |
| m3, fresh-520xx (unused) | 50.2 (49.2-51.2) | 51,067 / 57,039 (-10.5%) | 3,596 / 5,536 / 7,006 / 10,256 / 24,673 | 32,164 / 16,237 / 2,666 | 48,947 / 86,050 / 91,850 | 0.21% | 2.53M (-15.1%) |

- **The target** was -30% (<= 40,960). The campaign reached -13.8% (-10.5% on unused suites). The OOF drop came
  from exact early exits that skip one heavy piece of work on turns just over budget: 320's takeover field build
  (-7.1%) and 314's retreat pricing (-5.1%). Round 1's farm-loop floors cut shortcuts by a fifth, but not OOF.
- 100M against fc5b: totals -0.6% to -3.2% on seven sets (fs +0.22%, 308's codegen). Turns over 100k fell on seven
  sets (fs 22,467 -> 22,546). p99 fell on six sets (mg +0.3%, fs +0.2%), round-1 p90 -0.8% to -7.1% on five.
- Every merge was level on wins (no CI below 49).

**Best open leads** (from every section below, roughly by expected OOF):
1. **Fields built for candidates a later pure test rejects** (econexit). 320 was the campaign's biggest single cut
   from ~0.1% of total fuel, because a ~15k build lands on one turn. Audit every `cached()` / `to_group` /
   `to_altar` build for tests that could come first: mend_step's `to_group(farm_group)` is one.
2. **Bounded fight work with a deterministic fallback** (fight, fight2, budget, exit): the strike search's 24-node
   DFS and priced tiles (~45-49k when it runs on 300+ near turns), and want_home's `stand` (~8-12k). The units are
   at their floor and reserves can't reach 85% of near OOF turns, so only less work helps. It must keep the cap's DFS
   leaf set or be argued as a FUEL-GATES rule-2 limit.
3. **The bound-ordered farm loop** (farm): per-group cross-turn value parts, one vectorised bound pass, best-first
   with an exact stop. Halving the loop finishes 76% of cut loops. a3's order-independence code is a start.
4. **step_field's static-then-wide pair as one search** (post, path): needs one field in one place, plus the
   static failure emulated for make_way / label_through.
5. **Runaway games** (round 1's rivers-1100302130, and m3's runs of 50+ on fresh-520xx, +907): find their stacks
   with the fuel-exact replay harness. Each is hundreds of OOF from one repeated failing search.
6. Minor: label_through's memo store cost where nothing repeats (~280 a walk; oof/mg p99 +0.7-1.0%);
   sole_escape_threat / offer_channel walk-and-stop like other_hits; the step-guard cover written as the search's
   Grid (~0.5k a search); `prices()`'s key (gems_share moves every tribute); round 1's +2-4% OOF since 313.

## Baseline mirror A/B (orchestrator)

`astraeus-fc5b` (= fc4's m4) against a copy of itself, real budget, own drafts, fast runner,
`maps/fresh-11000..11019` (10,240 games, 1m55s; batches `fuel5/replays/batch-*-ab-fc5-mirror-*`). Per bot:
- **OOF 58,518** in 6,290 games. Campaign target (-30%): **<= 40,960**.
- Fuel a play turn: mean 49,924, p50 48,350, p90 86,150, p99 92,450, at/over 100k 0.22%.
- Shortcuts 3.11M with out-of-fuel: farm-partial-evaluation 2,060,111, step-guard-entry 436,619, turn-order
  117,074, prey-cut-short 105,306, step-guard-look 81,564, crow-flies-farm 65,413, comms-stale-vision 53,505,
  ward-no-bushes-clusters 51,243, farm-no-route 48,724, static-descend 18,232, farm-kept-target 7,051,
  step-guard-sim 6,016, siege-route-fuel 2,038, farm-no-attack-tiles 993, spell-clear-no-tiles 609, siege-no-tiles 244.

## Fight-side tail (worker; branch fc5-fight)

No bot change: the round ran out of time after the census. Tooling: 5cf3b071 (census patterns follow the current
bot; a stdout budget per instance keeps long games' late turns), 60860bae (scopes for `Reach::build`,
`awake_members`, `strike_foe` and the strike search's parts `ss.*`; 160 labels). Scratch `/tmp/fc5/fight/`
(`an.py`, `an2.py`, `an3.py`, `srch.py`, `oofb.py`).

**Census of the current bot** (`instrument.py --fine --trace` copy of fc5b vs fc5b, real budget, fast runner,
fresh-11000..11003, 2,048 games; `cen3-ab4`). The census copy ran out 12,759 times against the reference's 11,669
in the same games (+9%, instrumentation). OOF-first turns 9,329, by round 2-10 / 11-60 / 61-300 / 300+: 988 / 1,477
/ 2,148 / 4,716. Of the 4,716 in rounds 300+, 3,146 (67%) had an enemy within 6.

Rounds 300+, OOF-first, enemy within 6 (3,146 turns; fuel per turn over all of them, and per turn that ran it):
- **strike_search: 81% of turns, 49.2k when it runs** (self 25.6k over all turns). On heavy turns that finished
  (300+, near) it is 20.3k when it runs. SRCH phases on these turns: read 15.0k, grow 16.0k, price 13.9k (mean
  45.4k, p90 61.4k, max 81.7k); 12 nodes, 19 offers, 7 end tiles, 3 priced. The strike search has no fuel gate:
  it runs whatever is left, and 761 of these turns ran out inside it.
- By type (turns, strike_search when run, read / grow / price): Heart of Ruin 1,469 (37% of all 300+ OOF-first),
  49.7k, 15.4k / **22.9k** / 11.7k with 15.8 nodes (the dash-landing groups); Vesper 425, 41.7k, 12.3k / 7.8k /
  **22.6k** (12 end tiles, 5.2 priced); Vendetta 316, 40.4k, 15.6k / 17.8k / 12.7k; Issac 248, 33.3k.
- want_home: 41% of turns, 23.9k when run: `Safety::stand` 13.5k a call (self 8.8k, the unmemoised trade with
  walkers or camps), `lethal` 7.2k (damage_ceiling 6.5k, Reach builds), outmatched 2.0k, camp_trapped 3.3k.
  channels (a tribute or recall under way, which asks want_home) 58%, 24.4k when run.
- **turn_order is not the tail here**: it ran on 2% of these turns (its gate cuts it), 12.5k when run. The
  non-quiet offer_kills / escape pair matter for the gate's firings, not for these OOF turns.
- Step guard: g.cover (`step_guard_cover`, read_geometry's deferred-guard cover) 78% of turns, 5.5k when run;
  g.step_guard 37%, 2.8k. Reach builds 3.6k a turn (2.9 calls), strike_foe 2.0k (4.8 calls).
- Where they ran out (first scope under decide_main): goal 955 (farm, siege_kite, chase after the search),
  strike_search 761, act_end 396 (place_lock 152, ward_bushes 90), carry_bag 279, retreat 252, turn_order 155,
  strike_after 140.
- Rounds 300+ OOF-first with **no enemy visible** (1,125): farm 46.6k (loop 24.1k, post 25.1k), carry_bag 18.9k
  (26%): the farm side, not the fight side.

**step_guard_cover laps** (a copy with raw `fuel()` laps, real budget, 256 games fresh-11000; 20,736 calls over
1.5k): GuardFoes ctor 469 median, expose_here 286, the 24-cell loop (with clear_board, set_tile, the open test)
1.7k median, 3.1k p90; total p90 ~4.0k. Writing the cover straight as the search's 5x5 Grid (no clear_board,
set_tile or read_grid) would save ~0.6-0.8k a strike search: below the brief's bar, not done. `route()` caches the
cover per round but read_geometry recomputes it; sharing it needs a key covering here, radius and Safety's
invalidations.

**Leads, by size.**
- The strike search's grow phase for dashers with landing hits (Heart of Ruin 22.9k at ~1.4k a node, Vendetta
  17.8k): the search is capped at 24 nodes, which binds on 10%+ of these turns (nodes p90 24). A best-first expansion with an
  upper bound per child (its hits so far plus every remaining foe's health at most) that stops once no open child
  can beat the best leaf would cut nodes without changing the result if ties are broken as now.
- The price phase for ranged kiters (Vesper 22.6k, 5.2 tiles priced): tiles are priced best bound first, but each
  priced tile runs Reach blows and camp sums; a cheaper per-tile danger ceiling (Strike by distance, already in
  GuardFoes) before the exact Reach would end pricing sooner.
- want_home's `stand` (8.8k self, unmemoised): with walkers or camps the trade has no memo; a memo keyed on (key,
  walking arrivals, camp) would share it with the strike search's pricing of the start tile when they agree.
- None of these is a gate: they make OOF turns cheaper directly, as the strike search is unbounded by fuel.

### Fight-side round 2 (worker; branch fc5-fight)

**Strike search laps** (raw `fuel()` laps per part, real budget, fast runner, 256 games each of fresh-11000/11001
vs fc5b; searches over 30k in rounds 300+, ~2.7-4.9k searches): read 12.4k (geometry 7.0-7.9k, which holds the
cover and on Ren, whose Reach builds land there first, 23.8k; the enemy loop 1.9-2.1k; members 0.3-0.5k), grow
8.4-10.5k (settle/offer 3.3-3.9k, hit_unit 0.7-0.9k, group_landings 0.5-0.7k, HoR 2.1k; ~4k node overhead), price
(blow 3.2-3.6k with Reach builds, resolve_guard, threats_at 0.16k, lethal 0.25k, setup 2.8k). Vesper: price 22.5k,
of it resolve_guard 9.1k and blow 4.7k. Searches over 45k (962 of 56.5k, HoR 378, Vesper 282): geometry 8.8k,
enemy loop 2.3k, settle 5.8k, grow rest ~6k, blow 5.3k, resolve_guard 5.2k, price rest ~4.8k. No single part
dominates. One search a turn (14,444 turns with one, 287 with two).
- **The step guard when the search resolves it** (16% of searches, 6,688 of 42,358): 7.6k mean, 6.8k median.
  GuardFoes and expose_here 0.9k, the first pass over the window 1.3k (both repeat the cover's), first union
  1.4k, exact exposures 0.9k, last loop (lethal, fights) 3.1k.

**Kept: f1351fc6, the strike search's step guard reuses its cover's first pass.** While the search runs
(`GuardInputsHeld`, from before `read()` to the plan's first action), step_guard_cover keeps its GuardFoes (foes,
Reach pointers, exposure here) and the tiles past `no_worse_at` with their nears. A step_guard asked from the
same tile and radius in that window skips the constructor, expose_here and the window pass and runs the same
per-tile body over the kept tiles in the same order. Exact: nothing the guard reads (world beliefs, Safety's
seen enemies, Strikes, Reaches, the open map) changes between the search's read and its first action, and the
fuel gate between the constructor and expose_here only reads fuel (100M: never binds).
- 100M: identical replays on all 8 sets (wide 52, oof 48, mg 24, q 48, big 32, fs 24, fight 30, tgt 16). Total
  fuel -0.02 / -0.05 / +0.00 / -0.01 / -0.00 / -0.00 / -0.09 / -0.01%. fight p99 116,891 -> 115,963 (-0.8%), max
  380,991 -> 375,285 (-1.5%); wide max -2.7%, tgt max -2.1%. Many turns a few fuel dearer (codegen), fewer turns
  cheaper by ~2k. It fires on any champion with a deferred cover (not Willow): wide (test drafts: HoR, Ren,
  Stellar, Ryth, Vendetta) and fight.
- A/B vs fc5b (10,240 games, real budget, fresh-11000..11019): 49.8% (5097-5143), CI 48.8-50.7. OOF CAND 59,268
  vs REF 58,954 (+0.5%, within the ~600-800 run noise). By round 1 / 2-10 / 11-60 / 61-300 / 300+: 4,062 / 6,589
  / 9,170 / 12,920 / 26,527 vs 4,035 / 6,560 / 9,228 / 13,000 / 26,131. Shortcuts -0.4% (3,094,364 vs
  3,107,793): step-guard-entry -1.9%, step-guard-look -4.1%, step-guard-sim -16%. Level on OOF: the saving
  (~2.2k on a sixth of searches) is too small to show.

**Dropped:**
- **The search's board reads in place** (`window::bits`, moved to a header, for `read_grid` and the dash pass's
  camps | enemies | enemy spawn instead of or_into + and_into + positions_into): identical replays, but total
  fuel +0.17% on fight and +0.09% on oof, -0.04% on big and -0.03% on fs. The host calls cost chunks + 13, less
  than the in-place read on small maps. Choosing by map size would save ~1k a search on 100x100 only, where
  searches are rare.
- **Lead 1, a best-first grow with a bound per child:** not exact. The 24-node cap binds on 10%+ of OOF fight
  turns, and the leaves kept are those of the first 24 nodes in DFS order. Any pruning or reordering changes
  which nodes fall inside the cap. A bound would also have to beat each end tile's best leaf per removed-enemy set
  (Front), because pricing subtracts danger per set, not just the global best.
- **Lead 2, a distance-only ceiling before the exact Reach blow:** the price loop already orders each tile's
  blows by Strike share and stops once the tile can't win. Strike::at is an upper bound on each blow, but cutting
  a tile sooner needs a lower bound on its danger, so the ceiling doesn't let any query be skipped. Most of the
  blow cost is Reach builds, which later consumers would pay instead.
- **Lead 3, a memo for want_home's `stand`:** it runs exactly once a turn (6,313 of 6,327 turns with it in rounds
  300+ near enemies; 12.6k incl, 9.0k self), and the strike search never calls it, so a same-turn memo saves
  nothing. A memo across turns would need the walkers' arrivals, camps and both sides' cooldowns to repeat.
- **Sharing the cover between route() and the search:** the cover runs once a turn (1.0 calls), so there is no
  repeat to share.

**Open minor items:** the cover written as the search's Grid (no clear_board, set_tile or read_grid; ~0.4-0.7k
a search); the window pass done with masks for bounds and the open map (~0.45k a cover or first pass);
`Unit{}` reset and per-foe host reads in the read loop (~0.6k a foe).

## Farm loop (worker; branch fc5-farm)

Target: farm-partial-evaluation (fpe), the `room()` cut of `farm_turn`'s group loop. The worker was restarted once;
the first run's measurements are recovered here (scripts `/tmp/fc5/farm/mkmeas*.py`, `an1-4.py`).

**The prize** (a debug copy that plays at 100M but marks where the real budget would cut, then lets the loop finish;
~100k virtual cut turns in each of three runs): on a cut turn the loop has spent 32.5k median and needs 11.7k
median more to finish (p75 24k, p90 43k); it is cut at k/n 0.48 median (p25 0.23, p75 0.72). The finished loop's
choice differs from the cut one on **13-17% of cut turns** (banking 16-17%, not banking 11-17%; every cut at k = 0,
~3% of cuts). Where the best value rises after the cut (non-banking, ~25% of those turns) the cut best is 0.60 of the
final median. How much cheaper the loop must be to finish: x0.80 finishes 35% of cuts, x0.67 55%, **x0.50 76%**,
x0.33 88%. Fuel of cut-turn loops by how a group ended: crewable with plan_crew 37% (3.3k each), the steps prune 21%
(~0.9k each), alone fully valued 14% (1.7k), pre-facts prunes 9% (~0.26k), claimed 8% (6.6k), alive kited 6%. The
crew bound `most` of the crew groups that reached plan_crew was below the loop's final best for 41% of them not
banking and 72% banking: those evaluations happen only because the final best was not known yet.

**Kept: cc2637d6, a crew share's value floors the own-group prunes.** Once a share is set, an own group whose value
stays below `shared_value` changes no pick: the share wins unless the best beats it, so the loop's prunes test own
groups against max(best_value, shared_value) (`bar_lt` for `<` tests, `bar_le` = nextafter below for `<=` tests, so a
group equal to the share is not pruned). shared_value only rises (a new share needs value >= it), and a later share
is rejected only by `value <= best_value`, which a lower best never tightens. Off where best_value is read past the
pick: banking (its pick reads best_value against from_altar_value), any kited group on the map (`risky` replaces a
missing best) and a takeover in reach (the post-loop takeover's work rate is best_value; the test is the takeover
loop's own `steps_to < capture_time && allies_on > 0`). Byte-identical at 100M on all 8 sets.

**Kept: 20f0f925, once a help call is set, skip groups that cannot be a nearer help.** The help call overrides the
best and the share; only a farm Monolith best that we claim keeps it off, so on maps with no farm Monolith
(`farm_monolith` false for every group, a static per game) a group `may_help` rules out (Chebyshev distance past
help_steps or help_radius, not alive, no strength, banking) changes no pick. Help candidacy reads no best: the prunes
before it (pre_upper, the later-turn and first-turn pre-facts prunes, beaten_near, the stop) all exempt `may_help`
groups. Byte-identical at 100M on all 8 sets.

100M against the baseline JSONs (`farm-b1-*` = both commits; identical replays on every set):

| set | identical | total | mean | p90 | p99 | max | round 1 mean / p90 / max |
|---|---|---|---|---|---|---|---|
| wide | 52/52 | -1.74% | 51919 -> 51015 | 86447 -> 86320 | 107443 -> 105803 | 276792 -> 276792 | 218844 -> 213546 / -4.3% / +0.2% |
| oof | 48/48 | -1.23% | 55476 -> 54796 | 88271 -> 87802 | 151026 -> 148504 | 555669 -> 557833 | 240433 -> 234724 / -4.8% / -9.1% |
| mg | 24/24 | -1.07% | 59725 -> 59087 | 89577 -> 88662 | 149290 -> 148882 | 373058 -> 384593 | 231016 -> 229434 / -0.3% / +1.0% |
| q | 48/48 | -2.08% | 60546 -> 59293 | 90393 -> 88884 | 138656 -> 134649 | 438608 -> 438187 | 262663 -> 249090 / -7.5% / +0.3% |
| big | 32/32 | -2.18% | 60562 -> 59240 | 87500 -> 87292 | 119861 -> 114730 | 327360 -> 328627 | 248914 -> 244459 / -3.3% / -4.0% |
| fs | 24/24 | +0.59% | 94855 -> 95412 | 132691 -> 133687 | 196715 -> 198404 | 611791 -> 618586 | 550887 -> 556439 / +1.2% / +0.9% |
| fight | 30/30 | -0.35% | 48562 -> 48392 | 85980 -> 85954 | 116891 -> 116749 | 380991 -> 380993 | 196135 -> 196537 / -0.0% / +0.4% |
| tgt | 16/16 | -0.43% | 50964 -> 50748 | 86744 -> 86567 | 117584 -> 112914 | 263616 -> 263618 | 230092 -> 222419 / -1.1% / -6.7% |

By commit (total): cc2637d6 wide -1.40, oof -1.09, mg -0.84, q -1.74, big -1.84, fs +0.60, fight -0.27, tgt -0.39;
20f0f925 on top wide -0.35, oof -0.14, mg -0.22, q -0.35, big -0.34, fs -0.01, fight -0.07, tgt -0.05. fs is dearer
(+0.6%, from the first commit: ~220-group maps where the share rarely forms and the flattened codegen shifts); its
real-budget OOF is level. "Dearer" turn counts are high (~2-3x the cheaper ones) but small: codegen.

Real budget benches (small, indicative), OOF / fpe, base -> both commits: wide 1404 / 10083 -> 631 / 7979, oof 2819 /
19003 -> 2689 / 14476, mg 1794 / 9302 -> 1594 / 6384, q 3056 / 47242 -> 2871 / 42910, big 168 / 19023 -> 172 /
14597, fs 1978 / 42260 -> 1977 / 42227, fight 844 / 1543 -> 847 / 1358, tgt 899 / 3409 -> 897 / 3848; all 12,962 /
151,865 -> 11,678 / 133,779.

**A/Bs** against astraeus-fc5b (fresh-11000..11019, 10,240 games, real budget, own drafts, fast runner; candidate /
fc5b side):
- cc2637d6 alone (variants/fc5f-a1): win 50.5% (49.5-51.4); OOF 59,690 / 59,616 (level); fpe 1,703,958 / 2,067,098
  (-17.6%); fuel a turn mean 49,336 / 49,947, p50 47,350 / 48,350, p90 86,150 / 86,150, p99 92,250 / 92,450.
- **both (variants/fc5f-b1 = 20f0f925): win 50.5% (49.5-51.5); OOF 59,359 / 59,441 (level; r1 4,029 / 4,035, 2-10
  6,201 / 6,580, 11-60 9,293 / 9,264, 61-300 13,359 / 12,943, 300+ 26,477 / 26,619; runs <10 / 10-49 / 50+ 37,929 /
  18,927 / 2,503 vs 37,733 / 19,539 / 2,169); fpe 1,655,578 / 2,065,448 (-19.8%); all shortcuts 2.68M / 3.11M
  (-13.8%); fuel a turn mean 49,204 / 49,960 (-1.5%), p50 47,150 / 48,350, p90 86,050 / 86,150, p99 92,250 /
  92,450, at/over 100k 0.22% / 0.22%.** Also down: ward-no-bushes-clusters 40,794 / 51,340, crow-flies-farm 58,630 /
  61,929, farm-no-route 46,654 / 48,709 (cheaper loops leave more for what follows).

**Dropped (measured, all byte-identical at 100M on all 8 sets):**
- The banking floor (from_altar_value floors own groups while banking: under it a group cannot make us farm, and if
  we farm the best beats it), on top of the share floor (variants/fc5f-a2): 100M a little dearer than without
  (wide -1.30% vs -1.40%); A/B 50.1%, OOF 59,399 / 59,421, fpe 1,718,940 / 2,060,502 (-16.6%, vs -17.6% without).
- Seeding the loop with last call's best (by banking or not, before shares and help) and making the result
  order-independent (ties by position in the usual order via `earlier`, `<=` prunes at nextafter below the best,
  `may_help` admitting equal steps) on top of both floors (variants/fc5f-a3; the redesign's step 1 plus a first
  "likely best first" order): 100M dearer than a2 (wide -0.95%, fight -0.06%, tgt +0.03%); A/B 49.6%, OOF 58,896 /
  60,708 (-3.0%, inside the run-to-run noise of the reference side, 59.4-60.7k across these four runs), fpe
  1,733,484 / 2,051,682 (-15.5%, worse than a1's -17.6%). The order-independence code is in that variant's src if
  the bound-ordered loop is built later.

**Open leads:**
- The redesign (per-group cross-turn value parts, one vectorised bound pass, best-first with an exact stop) is still
  the way to finish the loop: halving the loop's cost finishes 76% of cuts. Not started here. The floors above make
  part of it cheaper; a3's ordering code is a start on step 1.
- The prize measurement says the crew bound `most` was below the loop's final best for 72% of banking crew
  evaluations (41% not banking): a cheap estimate of the final best (not last turn's: a3 lost) would prune those.
- Minor: the share floor is off on shared-gems maps (any kited group): an exact form needs to know whether a pruned
  group would have set a best (est. small); `position()` scans the order on ties only.
- **Disk:** the root disk was full (993G, 100%) during this work, ~630G in `MAIN/replays` and ~320G in old
  worktrees' replays (fc4-*, fuel4, agent-*). One A/B (a3, first try) died with ENOSPC; my scripts now delete A/B
  batches after extracting stats (`/tmp/fc5/farm/abx.sh`).

## Merge round 1 (merge agent)

fc5-farm (cc2637d6, 20f0f925, 34ddaa1a) and fc5-fight (f1351fc6, 57d5f7b2; its census tooling was already on
fuel5-orch) merged into fuel5-orch whole (merges 5a637469, e2f50e33). Nothing dropped. Frozen:
`fuel5/bots/variants/astraeus-fc5-m1` (= fuel5-orch's bot). CHANGES 308 (cc2637d6), 309 (20f0f925), 310 (f1351fc6),
all fuel only.

**Review.**
- cc2637d6, the share floor (exact).
  - **Which bars changed.** Every changed prune tests an own group's upper bound against `bar_lt()` (strict `<`) or
    `bar_le()` (`<=` against max(best_value, nextafter(floor, 0))). For a positive float f, `x <= nextafter(f, 0)`
    is `x < f`, so the floor prunes only groups strictly below it. With no share set (floor 0), every bar is the old
    one: `barred()` is `best >= 0`, `bar_lt` and `bar_le` are best_value, and the crew test's `most < 0` can't hold
    (worth > 0 there). Claimed groups are never floor-pruned: every prune is `!claimed`, pre_upper is +inf for
    claims, and the stop keeps `is_claimed`. So shares are weighed as before.
  - **Monotone.** The stop's threshold is still monotone. The floor only rises (a new share needs value >= the old),
    best_value only rises, and max(best_value, floor) >= floor when best appears. So `stop_from`'s binary search
    from the last stop stays valid. `beyond` now reads `tested_value`, which equals the old best_value when the
    floor is 0.
  - **Same pick.** Call a run with the floor F and one without N. A group F prunes, or values lower (the crew bound
    under the floor keeps the alone value, also under it), has value v < floor_t <= the final shared_value S. So
    best_value_F <= best_value_N at every step, and they differ only when N's max is below the floor.
    - Shares: a later share needs value >= shared_value > v. So the share test `value <= best_value` rejects the
      same shares in both runs, and the share's own prune (`most < best_value`) the same claimed groups.
    - Final pick: if N's best value V >= S, the group that sets it was never under the floor, so F evaluates every
      group of value >= V and ends on the same best (ties: `earlier` is by position). If V < S, the share wins in
      both runs (`shared_value > best_value`).
    - help_group is set before every changed prune, which exempt `may_help` groups (pre_upper +inf within
      help_radius, the pre-facts prunes and beaten_near test `!may_help`, and beyond is false within help_radius).
      So help is the same in both runs.
  - **State read after the loop.**
    - best_value against from_altar_value (banks_bag): floor off.
    - risky replaces a missing best: only kited groups set risky, and the floor is off on any map with one. `kited`
      = shared_gems && big_group, static per map, so the per-instance static is safe.
    - The takeover's work_rate = best_value: off when any cleared group has `steps_to < capture_time` and allies on
      it, the takeover loop's own early returns, and it never runs when `memory.banking`. Nothing in the loop changes
      the world or memory.
    - from_altar_value: banking only. mono_seen: traces only. recall_farm reads `steps_data[best]` for the final
      best, which both runs evaluate. Caches (group_facts, centre fields) are keyed and already partly filled
      whenever the old prunes fired.
- 20f0f925, the help skip (exact).
  - **Help always wins.** With no farm Monolith (`any_mono` false, static per map and template instance), the help
    override `!(farm_monolith(best) && claim == best)` always holds. So a set help_group decides best, best_steps,
    claim (crew), spell and the mode. After it: `memory.crew` is true, so the proposal branch is skipped. Help
    groups have no Monolith, so the Monolith start doesn't run, and the end reads only memory. recall_farm reads
    steps_data of the help group, which both runs evaluate. banks_bag can't have a help call (`may_help` and the
    candidacy both need `!banks_bag`).
  - **The same help group.** A group may replace help only with steps < help_steps, or equal and `earlier`, which
    needs n_lead > 0. Since steps >= near (Chebyshev), any group with near > help_steps, or near == help_steps and
    n_lead == 0, can't replace it, and `may_help` is false for exactly those (and for not alive, no strength,
    banking). The final help group passed `may_help` at its turn. So help_group, help_steps and the pick are the
    same.
- f1351fc6, the guard first-pass reuse (exact).
  - **Same body.** The shared path runs step_guard's per-tile body (`exposed_at`) over the cover's tiles and nears,
    in the cover's dy/dx order with the same window, bounds, open-map and `no_worse_at` tests. The rest of
    step_guard uses `g` only through `exposure` (lazy `reaches` fills: pointers into Safety's per-enemy reach pool,
    whose addresses don't move), `no_worse`, `visible_of` and `n`. `expose_here(here)` is the only writer of
    here_mask and here_damage, and the shared case has it from the same tile. Old step_guard ran expose_here after
    the entry fuel gate, which never binds at 100M. 24 kept tiles is enough: the 5x5 window (`Window::cells` are
    32-bit) caps radius at 2, as step_guard's own 24-slot arrays already do.
  - **Inputs fixed.** Nothing GuardFoes reads changes between the cover and resolve_guard:
    - Moves, attacks, casts and hidden-blocker bumps happen only in "Carry it out", after `held.release()`.
    - `Safety::refresh()`/`invalidate()` (which reset Reach builds) run only after acting (fight.cc). There is one
      Safety a turn (bot.cc). Its `seen_enemies` is listed once a turn, and Strikes are fixed for the turn.
    - Beliefs (world.enemies) are fixed for the turn, and the search takes `const World&`.
    - The keys: the cover and the guard come from the same deferred `(guard_here_, guard_radius_)`, and the reuse
      requires an equal here and radius. work_cover/work_guard call the same pair.
  - **Lifetimes.** `GuardInputsHeld` sets `valid = false` on construction, so a second search in the same turn (14,444
    turns with one, 287 with two in the worker's laps) starts empty. Its destructor clears `held` on every exit,
    including a `throw_if_stale` unwind. A turn resumed after running out throws at step_guard's `throw_if_stale`
    before reading the kept pass. A cover that returns early (no enemy seen, `reaching == 0`) leaves `valid` false.
    Outside the search, `held` is false and both functions behave as before.

**100M** (base -> m1, `MAIN/replays/fuel/fc5/m1-*-100M.json`, `bench.py compare`): all 234 replays identical.

| set | identical | total | mean | p90 | p99 | max | over 100k | round 1 mean / p90 / max |
|---|---|---|---|---|---|---|---|---|
| wide | 52/52 | -1.77% | 51919 -> 51003 | 86447 -> 86315 | 107443 -> 105525 | 276792 -> 269399 | 3989 -> 3630 | 218844 -> 213754 / -4.2% / +0.3% |
| oof | 48/48 | -1.28% | 55476 -> 54769 | 88271 -> 87793 | 151026 -> 148154 | 555669 -> 557833 | 16830 -> 14939 | 240433 -> 234934 / -4.7% / -9.1% |
| mg | 24/24 | -1.06% | 59725 -> 59088 | 89577 -> 88647 | 149290 -> 148944 | 373058 -> 384593 | 7734 -> 7323 | 231016 -> 229642 / -0.2% / +1.0% |
| q | 48/48 | -2.09% | 60546 -> 59289 | 90393 -> 88877 | 138656 -> 134531 | 438608 -> 438187 | 18447 -> 16697 | 262663 -> 249298 / -7.5% / +0.4% |
| big | 32/32 | -2.18% | 60562 -> 59239 | 87500 -> 87288 | 119861 -> 114716 | 327360 -> 328627 | 4087 -> 3288 | 248914 -> 244667 / -3.3% / -4.0% |
| fs | 24/24 | +0.59% | 94855 -> 95412 | 132691 -> 133677 | 196715 -> 198404 | 611791 -> 618586 | 22467 -> 23088 | 550887 -> 556647 / +1.2% / +0.9% |
| fight | 30/30 | -0.44% | 48562 -> 48348 | 85980 -> 85932 | 116891 -> 115771 | 380991 -> 375287 | 4796 -> 4595 | 196135 -> 196745 / +0.1% / +0.5% |
| tgt | 16/16 | -0.45% | 50964 -> 50742 | 86744 -> 86560 | 117584 -> 112772 | 263616 -> 258022 | 2438 -> 2079 | 230092 -> 222627 / -1.0% / -6.6% |

The farm commits' numbers plus the guard's (fight max -1.5%, wide max -2.7%). Turns over 100k fall on every set but
fs, whose +0.6% is 308's codegen on ~220-group maps.

**Real budget benches** (base -> m1; small, indicative): OOF / farm-partial-evaluation wide 1404 / 10083 -> 528 / 8161,
oof 2819 / 19003 -> 3744 / 13775, mg 1794 / 9302 -> 2629 / 5789, q 3056 / 47242 -> 3108 / 43531, big 168 / 19023 ->
180 / 14536, fs 1978 / 42260 -> 2059 / 42509, fight 844 / 1543 -> 848 / 1106, tgt 899 / 3409 -> 1030 / 3566; all
12,962 / 151,865 -> 14,126 / 132,973. oof and mg swing by hundreds from diverged games (farm-b1 alone read 2,689
and 1,594 there). The A/B below judges.

**A/B m1 vs fc5b** (fresh-11000..11019, own drafts, real budget, fast runner, 10,240 games; log
`MAIN/replays/fuel/fc5/ab-fc5-m1-vs-fc5b.log`, stats `/tmp/fc5/merge1/ab-fc5-m1-vs-fc5b.stats`, batches deleted):

| bot | win | OOF | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p50 / p90 / p99 | >= 100k | shortcuts (no OOF) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **m1** | **50.1 (49.1-51.0)** | **60,117** | 4,020 | 6,228 | 9,191 | 13,472 | 27,206 | 37,685 / 18,516 / 3,916 | 49,179 / 47,150 / 86,050 / 92,250 | 0.23% | 2,596,495 |
| fc5b (ref) | | 60,007 | 4,035 | 6,566 | 9,226 | 13,107 | 27,073 | 37,943 / 19,244 / 2,820 | 49,921 / 48,350 / 86,150 / 92,450 | 0.23% | 3,046,961 |

- OOF is level (+0.2%; without shared-gems maps 57,338 / 57,122, +0.4%). Rounds 2-10 -5.1%, 61-300
  +2.8%, 300+ +0.5%. Shortcuts -14.8%.
  - farm-partial-evaluation 1,652,284 / 2,064,553 (-20.0%), ward-no-bushes-clusters 40,930 / 51,357 (-20.3%),
    step-guard-sim 5,139 / 5,741 (-10.5%), crow-flies-farm 56,405 / 61,699 (-8.6%), step-guard-look 74,231 / 77,730
    (-4.5%), farm-no-route 46,446 / 48,981, comms-stale-vision 51,219 / 53,371, step-guard-entry 425,933 / 435,436
    (-2.2%), turn-order 114,228 / 116,359, prey-cut-short 100,249 / 102,099, static-descend 18,006 / 18,578.
  - Fuel a play turn: mean -1.5%, p50 -2.5%.
- **Runs of 50+ rose 2,820 -> 3,916, two thirds of it one game.** In gen-rivers-1100302130 (fresh-11003, order 21),
  m1 ran out 711 times against 0. From round 579 one champion (handle 8, banking, decision B) runs out on every turn
  it plays, which shows as `OOF <r> queue` on alternate rounds: the CHANGES 304 runaway signature, where every
  decide runs out. It is deterministic: `bench.py run variants/astraeus-fc5-m1 --opp variants/astraeus-fc5b --maps
  maps/fresh-11003/gen-rivers-1100302130.map26a --fuel 0` gives 710 for m1, 710 for 308 alone, 710 for 308+309,
  and 0 for fc5b and 310 alone. 308 changes nothing while banking (the floor is off), so 308 only diverges the game
  into a state whose turn overruns. A census copy diverges again (0 OOF), so the stack wasn't found; the fuel-exact
  replay harness would find it. Runner-up: gen-dash-lattice-1100007606 (order 12), m1 348, reproducing at 432 for
  m1, 287 for fc5b, 335 for 308+309 and 157 for 310: the noise of a long fight game. The worker's b1 A/B had runs of
  50+ 2,503 / 2,169.
- Step 5 (dropping a commit) was not needed: win 50.1% with the CI over 50, and OOF within 110 of the reference.

**Left after round 1.** OOF 60k against the campaign target of 40,960. farm-partial-evaluation fell by a fifth,
but OOF didn't move. The rounds 300+ tail (27k, 45%) is still the fight side's strike search
(no gate) and want_home. Open, in order:
- the bound-ordered farm loop (redesign; a3's ordering code);
- the strike search's grow for dashers, exact only if the 24-node cap's DFS set is kept;
- the rivers-1100302130 runaway (a banking champion's every decide overruns from round 579: find the stack with the
  replay harness).

## Fight unit costs (worker; branch fc5-fight2)

Two exact cuts, both on Heart of Ruin's landing classes: 25b15808 (group_landings joins a class's hit cells to
their group as one mask, not cell by cell) and a95ac05f (`find_classes` partitions `land_hits` once a search by
each foe's landing square and each local camp group's member squares, replacing the per-cell `land_touch` /
`land_foes` memos). Both byte-identical at 100M on all 8 sets and on a forced Heart of Ruin firing set (below).
Scratch `/tmp/fc5/fight2/` (`f2lap` lap copy instrumentation: `patch_lap*.py`; aggregators `agg*.py`;
`turndiff.py` per-turn fuel diffs; `b100.sh` 100M benches; `hor.sh` the firing set).

**Lap measurements** (an m1 copy with `debug_block` laps, real budget, fresh-11000..11004 vs m1, 512 games each):
- `Safety::stand`: mean 7.9k a call = scan 0.84k + key 0.85k + fill 2.2k (fighters ~1.56k, walk_allies ~0.6k) +
  simulate 4.0k. A real simulation runs ~6.5 loop iterations; an act costs ~240 (quiet), ~440 (plain), ~490 (full);
  hurt ~550 a stand. play_quiet rarely applies (each side's first act has quiet_until 0).
- Strike searches over 40k. Heart of Ruin: read 14.4k (geometry 7.1k, most of it the step guard's cover; rest
  2.2k; foes 2.3k), grow 21.5k (settle 7.8k, of it offer 5.6k and place 3.9k; landing 7.3k, of it groups 3.4k and
  classes 2.2k; attack 3.5k; walk 1.3k), price 12.1k (blows 4.5k, ordering 2.1k, resolve_guard 1.9k). Vesper:
  price 26.6k (resolve_guard 8.0k, blows 7.6k over 7.2 queries, ordering 4.8k, setup 1.6k), grow 7.4k, read
  10.2k. Vendetta: grow 19.7k (attack 6.0k, settle 8.3k). Laps inflate grow's sub-parts.
- Overrun at 100M on the fight set: a fight turn that runs out at 100k is a median 13.6k over it; ~23% are under 5k.
  An exact cut needs ~5k a fight turn to rescue a fifth of them.

**Exact cuts found and their size.** c1 saved fight 84.5k over 404 changed turns (median 73). c2 (with c1) saved
on 100M wide max -1.4%, tgt max -0.9% / p99 -0.2%, fight total -0.01%; per turn against c1 fight 204 turns saved
over 1k, 24 over 3k; wide 411 / 67; tgt 150 / 49.

**Firing set:** copies of m1 and c2 drafting Heart of Ruin first (`map_model_draft = false`, heart_of_ruin first in
every table; `variants/hor-*`), fight + oof maps vs fc4b at 100M: 62/62 replays identical; total -0.01%, p99 -0.1%;
32.7k turns changed, 709 saved over 1k, 127 over 3k (p1 -2.1k; the rest -9, codegen).

**A/B** (`ab.sh fc5f2-c2 variants/f2-c2 variants/astraeus-fc5-m1`, 10,240 games): c2 50.1% (49.1-51.1). OOF 56,103
vs 57,961 (-3.2%); by round 2-10 / 11-60 / 61-300 / 300+: 6,243 / 8,782 / 12,783 / **24,277** vs 6,239 / 8,900 /
13,072 / **25,732** (-5.7% in 300+). Shortcuts 2,639,858 vs 2,645,026 (-0.2%). The m1-vs-fc5b mirror read 60,117 /
60,007, so the -3.2% is beyond that run's spread, but it is ~1.9k turns of the ~17k the campaign's 40,960 target needs:
far short.

**Dropped.**
- n-sized `UnitHealths` copies in grow (`memcpy` of `n` floats in place of the 56-byte array copy): **dearer**,
  fight +2.1M over 24.6k turns (median +74). A fixed 56-byte copy compiles to inline loads and stores; a
  variable-length `memcpy` becomes `memory.copy`, charged per byte plus the call. Copies under ~64 bytes are not
  the per-byte cost they look like.
- Re-checking simulate's early-exit bounds every half turn: ~180 a stand at best.
- Lazy Fronts (price only the tiles asked): heavy Heart of Ruin searches price most tiles anyway.
- Simulator micro-optimisation: 20-30% of ~4k a stand at best, 0.91 stands a near turn: ~1k.
- price's tile order by one sort: the bound only changes on the tile just taken, so one sort is exact, but with
  ~7 end tiles and ~3-5 priced the rescans cost ~0.2-0.5k.
- `Reach::build` (1.35k, 2.66 a turn): already reuses its sets by origin, occupancy and kind, and its ways by
  recipe; what is left is window dilations.

**Conclusion.** Each unit is already near its cost floor; the exact slack measured is a few hundred fuel a heavy
turn per primitive, an order below the ~5k a fight turn the tail needs. The fight tail is the amount of work
(nodes, stands, priced tiles), not its unit price: cutting it needs the inexact routes (TODO Fuel item 2,
bounded search sizes) rather than cheaper units.

## Economy-side OOF (worker; branch fc5-post)

Two fuel-only commits on fc5-post (from fuel5-orch e2aefaa4): 9fe383a6 (label_through) and e321cb9f (spare failed
searches). Both leave all 8 sets' replays identical at 100M against m1.

**Where m1's OOF is (A/B m1 vs fc5b, 10,240 games, by the overrunning decide's D branch).** F 24,136, no D line
17,200, R 8,460, B 5,426, G 1,978, C 1,958. A 256-game fuel trace (fastrunner `FASTRUNNER_TRACE_SITES=1`) spreads
OOF turns' fuel thinly (farm_turn 6.8%, Search::grow 6.8%, plan_strikes 6.5%, route_around 6.3%). In the last 25k
of those turns route_around (17.8%) leads. Two runaway champion-games held 36% of the sample's OOF. Champion-game
runs of 50+ OOF turns are ~4k of the ~58k; the rest is runs under 50, which no single lead here reaches.

**Runaways are route searches repeated every turn.**
- gen-rivers-1100302130 (m1 710 OOF): a banker in a standoff runs make_way 4 times a turn (step_safely with and
  without avoid, each at the static then the wide cap). Each calls label_through twice, ~5.5k each, walking a crowd
  of 4-8 allies with a host test and a field read per tile, finding no label.
- gen-topo-shortcut-1101506904 (a1/a2 as side b: 1,516): a 16k attack-tile search and a 20k wide search fail every
  turn. failed_ holds one failed search, so two alternating ones never reuse.
- gen-dash-lattice-1100007606: a farm walk's static then wide search every turn plus a chase.

**9fe383a6, label_through (exact).** route_around's `visited` output (moved into a member, `route_labelled_`,
swapped with the field wherever the field is) equals the field's labelled tiles: checked on 21,476 searches with a
debug variant. A line of allies holds at most as many allies as the board has (a among them), each beside one
before it, so every tile the walk reads is within min(8, count) of a. When the line reaches 4, one draw and
intersect with route_labelled_ checks for any labelled tile that near; none means unreachable, which the full walk
would return. a's neighbours, already read by the nearest-label check, are not read again (they hold no label). The
walk breaks once `best <= d + 1` (depths are listed in order and labels are >= 0).
- Per call, measured by bracketing label_through with traced host calls: rivers side b 5.2k -> 2.05k (22.7k calls);
  topo-backdoor-987806707 side a 3.39k -> 3.89k (34k calls, its lines are as long but labels are near: the board
  ops cost ~180 each on that map).
- Dropped versions: a2 (row masks from positions_into, BFS on masks) and a3/a4/a5 (box on a local ally count before
  the walk). In-WASM bit work costs about what host reads do, so masks only paid for their exits; the local count
  costs 4 whole-board ops, and a separate level-0 loop cost more than the reads it skipped (lambda not inlined).
  Threshold 5 instead of 4 is neutral on topo-backdoor but leaves rivers at 3.7k a call. Threshold 6, or a box only
  at a full line, misses rivers.
- 100M totals vs m1: wide -0.01%, oof -0.01%, mg -0.04%, q +0.10%, big 0.00%, fs 0.00%, fight -0.01%, tgt 0.00%.

**e321cb9f, spare failed searches (exact).** Before a fresh search, a valid failed_ (whose labels route_field_ holds;
keep_round and the success path already invalidate it before moving the field) swaps into the least recently used
of three spares: field, labelled board, goals, walls, origin, cap, layers. A search matching a spare under
failed_'s own rule (same origin, goals, walls; cap no higher or the spare ran dry) swaps it back and proceeds as the
failed_ path does (`layers = min(f.layers, cap)`, labels past the cap filtered by route_label_cap_). A field computed
from the same walls, goals, origin and a cap at least as high labels the same tiles up to the cap, so reads match a
fresh search; route_labelled_ may then hold tiles past the cap, which only makes label_through's box test pass more.
The within_failed path still only looks at failed_. Single games: topo-shortcut-1101506904 b 1,516 -> 329; a 254 ->
216; dash-lattice a 304 -> 154. 100M totals vs m1: wide +0.07%, oof +0.08%, mg +0.08%, q -0.11%, big +0.10%, fs
+0.05%, fight +0.09%, tgt +0.05% (three spares' lookups and swaps on every fresh failed search).

**Real-budget A/Bs against m1 (10,240 games each, own drafts, fast runner).** Frozen copies: `variants/post-a9`
(= 9fe383a6), `variants/post-b9` (= e321cb9f).

| Cand | Suites | Win | OOF cand / m1 | Runs >= 50 cand / m1 |
|---|---|---|---|---|
| a9 | fresh-11000..11019 | 49.9% | 56,876 / 56,429 (+0.8%) | 2,200 / 1,747 |
| a9 | fresh-10100..10119 | 50.2% | 51,303 / 52,244 (-1.8%) | 483 / 1,374 |
| b9 | fresh-11000..11019 | 49.7% | 57,669 / 58,940 (-2.2%) | 2,395 / 4,318 |
| b9 | fresh-10100..10119 | 50.2% | 52,114 / 52,582 (-0.9%) | 481 / 1,250 |

By round bucket (b9, fresh-110xx, cand / m1): 1: 4,178 / 4,019; 2-10: 6,289 / 6,228; 11-60: 8,897 / 9,007; 61-300:
13,259 / 13,054; 300+: 25,046 / 26,632. m1's own OOF moves by ~2.5k between runs of the same suites against
different candidates (runaways are chaotic: one game's path decides whether a standoff starts), so these are level
to slightly down, not clearly down. Runaways move from game to game: b9's top in its first A/B was a new standoff on
topo-shortcut-1100306900 (336 OOF as side a; a9 33 and m1 21 in the same pairing), two fresh failing searches a turn
that match no spare. What the commits remove is the runaways' per-turn cost; the bulk (runs under 50, ~51k) is
spread over farm, fight and round-start work, which neither touches.

Open, in order:
- wide-first in step_field: compute the static stage at the wide cap and derive the static answer (label cap,
  layers = min); a farm walk's static-then-wide pair (~6-8k + ~14-16k a turn on dash-lattice) becomes one search.
  Caveats: walking_round_ and round_fails see the cap.
- a memo for make_way's repeated label_through calls within a turn (same a, field and allies): rivers calls it 8
  times a turn.
- spares' common-case overhead (+0.05-0.1% at 100M): skip the lookup when no spare has our origin.

## Fight-turn budget (worker; branch fc5-budget)

Question: on turns with an enemy near, do the existing fuel checks leave reserves that miss work running after
them, as the farm loop's did in campaign 4 (e95d13b0)? **Answer: almost never.** On 85% of near-enemy out-of-fuel
turns, no fuel check passes between the start of `act()` and the point where fuel runs out. So no reserve can change
those turns. The two reserve changes tried for the other 15% were level or worse. No bot change kept: f64df912 is
reverted by 12aa16d9. Scratch: `/tmp/fc5/budget/` (`py/an*.py` census tables, `py/lap*.py` lap tables; the census
games are in `cen/`).

**Census.** `bud-cen` is m1 with `instrument.py --fine --trace`, played against m1 at real budget on
fresh-11000..11003 (2,048 games). OOF-first turns: 8,642. Of those, 4,614 had an enemy within 6 ("near"), 2,776 of
them in rounds 300+. For each turn, the last fuel check *passed* after `act()` began (CTR trace):
- **Near (4,614):**
  - **No check passed: 3,530** (another 122 traces were capped and 390 had no trace).
  - A check passed (568, 12%): static-descend 133, turn-order 109, step-guard-sim 81, prey 73, farm-no-route
    (post-loop) 64 + 20, farm loop `room()` 42, approach 27, step-guard-look 10, other 9.
  - On the turns where no check passed, the gates that ran had *failed* (fired): step-guard-entry 1,341, prey 479,
    approach 181, static-descend 154, turn-order 114. They already stop their work, so their reserves are moot.
- **Far (no enemy within 6, rounds 2+, 4,028):** the opposite. Loop `room()` 1,318, post-loop route 1,093 + 372,
  static-descend 306, and only 400 (10%) with no check passed. That is the farm side's reserve problem, not the
  fight side's.
- **Near, rounds 300+:** ran out in strike_search 725, goal/farm 509, act_end 347, retreat 243, carry_bag 221,
  siege_kite 176, turn_order 121, strike_after 117. On goal/farm turns the goal starts with 10.2k median left and
  `farm` with 4.3k. On act_end turns act_end starts with 0.6k. The ungated work before them (world 12.5k,
  want_home ~21k when it runs, strike search ~47k) had already spent the turn, and there is no gate before the
  strike search to give it a reserve.

**Laps** (m1 copies with `debug_block` laps, real budget, fresh-11004/11005 against m1, 1,024 games each).

Turn order:
- Near enemy: 3.4k p50, 6.2k p90, 10.5k p99, 14.4k p99.9. From its start to the turn-end queue: 8.4k p90,
  12.1k p99.
- Seen enemy, none within 6: 7.9k p99 to the queue. No enemy seen: 8.3k p99.
- Of 6,687 near calls entered with 10-14k left, 166 did not reach the queue.

From decide's end to the queue:
- Near: 7.0k p50, 11.3k p95, 15.4k p99. Far: 4.5k, 8.4k, 11.7k.
- 1,336 near decides that ended under 40k missed the queue. 1,075 of them had under 5k left when decide ended:
  decide itself used the turn.

`Pathing::step_field`'s gated `step_route`, actual cost minus estimate:
- Near, dash not ready: -1.5k p50, +3.9k p90, +17.3k p99.
- Far, dash ready: +6.6k median, +9.5k p90. This is the travel plan that static-descend's reserve doesn't count.

**Tried (10,240-game A/Bs, real budget, fresh-11000..11019 unless named; reruns of a pair are identical).**

| change | vs | win | OOF CAND / REF | 300+ | shortcuts | turn-order |
|---|---|---|---|---|---|---|
| to12: turn order's reserve 12k with an enemy within 6 (f64df912) | m1 | 49.8 | 57,013 / 57,702 (-1.2%) | 25,090 / 25,812 | +1.1% | 141,399 / 113,561 |
| to12, unused fresh-51300..51319 | m1 | 50.2 | 59,789 / 59,768 (+0.0%) | 28,818 / 28,844 | +1.3% | 151,540 / 119,707 |
| to14 (14k) | m1 | 50.3 | 57,565 / 58,362 (-1.4%) | 25,753 / 26,114 | +2.6% | 178,063 / 113,002 |
| v3: to12 + a 14k near end_reserve (search with an enemy within 6) at static-descend, prey, farm-no-route, loop floor | m1 | 50.1 | 56,501 / 57,088 (-1.0%) | 24,465 / 25,028 | +3.5% | |
| v3 | to12 | 50.1 | 56,828 / 56,139 (**+1.2%**) | 24,717 / 24,199 | +3.0% (prey +28%, static-descend +35%) | |

- to12 was identical at 100M on all 8 sets (fuel too). Over 20,480 games it reads -0.6% at +25% turn-order firings;
  comms-stale-vision fell 7%. Reverted: it isn't clearly down.
- v3 is worse than to12 alone. A gate that fires earlier on a near turn falls back to work that also costs: prey's
  cut keeps the chase, and static-descend's fallback (`descend_with`) plans the dash too. The ungated work after it
  is unchanged.
- **Not tried, for that reason:** static-descend counting the travel plan when the dash is ready (+6.6k median
  over the estimate). When gated it falls back to `descend_with`, whose dash plan travels anyway, so the reserve
  skips nothing.

**Why reserve accounting can't recover the fight tail.**
- A reserve changes play only on turns where its check passes and the turn still runs out. That is at most 12% of
  near OOF-first turns, about 2.8k OOF-first turns in 10k games, spread over nine sites (largest 2.9%).
- The near tail's 85% runs out on work with no check after it: want_home, the strike search, retreat, strike_after
  and act_end, behind gates that already fired.
- Cutting it takes cheaper or bounded fight work (the strike search's node and pricing counts, `Safety::stand`), or
  a gate before the strike search, which the no-new-gates rule forbids.
- fc5-fight2's conclusion still stands: the units are near their floor, so the work done has to shrink.

**Open:** the near tail needs bounded work, not reserves.
- The strike search's 24-node DFS and its priced tiles: a limit that rarely binds, with a deterministic fallback
  (FUEL-GATES rule 2), measured against the 81%-of-turns, ~49k searches.
- want_home's `stand` (~21k when it runs on these turns).
- Turn order's near tail: `offer_escape`'s `threats_at`, `plain_priority`.

## Merge round 2 (merge agent)

fc5-fight2 (25b15808, a95ac05f; notes c5858beb, a084782e), fc5-post (9fe383a6, e321cb9f; notes 3c8ee3b7) and
fc5-budget (notes 5451174b; its f64df912 and revert 12aa16d9 cancel) merged into fuel5-orch whole (merges
0754f84b, 1ce09d8d, 082b5a89). Nothing dropped. Frozen: `fuel5/bots/variants/astraeus-fc5-m2` (= fuel5-orch's bot).
CHANGES 311 (25b15808 + a95ac05f), 312 (9fe383a6), 313 (e321cb9f), all fuel only.

**Review.**
- a95ac05f (with 25b15808), landing classes by partition (exact).
  - **The same classes.** The old classes were the equivalence classes of hit cells under the key (`land_foes(c)`,
    `land_touch(c)`). `land_foes(c)` is the foes with `dist(tile(c), u[t].pos) <= land_radius`, which is the grid
    cells of `square(u[t].pos, land_radius)`. `land_touch(c)` is `touch_near(tile(c), land_radius)` (or `touch1`,
    equal to `touch_near(p, 1)` inside the 9x9 window and falling back to it outside): the local groups with a member
    within land_radius, which is the union of the members' squares. `find_classes` starts from one class (all of
    `land_hits`) and splits every class by each foe's square, then each group's union of squares, setting the bit
    on the inside part. Two cells end in one class iff they agree on every split set, iff their keys are equal, and
    each class's masks are its key. So the partition is the old classes over `land_hits`, computed at once instead
    of on first need. Class numbers differ, but nothing reads them in order: `land_at` reads the masks of a cell's
    class, and `group_landings` creates groups in the order of each class's lowest hit cell, as the old cell-order
    pass did. Each group's mask is the union of its classes' hit cells, as before. The inputs (foe and member
    positions, `land_radius`, `land_hits`) are fixed once `read()` returns, as the old per-Search memos assumed.
  - **class_foes_all covering unhit classes.** It is now the union over all classes, a superset of the old
    cumulative union, which already included every class of the current hits. If the old `merge` was false, every
    foe of the hit classes is alive. Then `class_foes[j] & alive = class_foes[j]`, and distinct classes have distinct
    (foes, touch), so a merge joins no two classes: the groups and their order are the same with `merge` true. If
    the old `merge` was true, the new one is too.
- 9fe383a6, label_through's box (exact).
  - **route_labelled_ is the field's labelled set.** It is `compute_to_with_expansion_count`'s `visited` output
    ("the tiles the search reached"), and it moves with `route_field_` at every swap: the success path's swap with
    `kept.field`, `keep_round`'s with `round_labels_.field`, and the spares' (`swap_spare`). The fresh search writes
    both. The constructor fills `route_labelled_` and the kept and round boards with every tile, matching a field
    never written (which reads 0 everywhere). An unwritten spare enters `route_labelled_` only by the eviction swap,
    which the fresh search then overwrites. The worker checked visited against the field's labels on 21,476 searches.
    A reused search with a higher cap labels a superset, which only lets the box test pass more.
  - **The reach bound.** Every line entry is an ally (pushed only on `test(allies, p)`), distinct, each beside an
    earlier one, so entry index n-1 is at depth at most n-1 and within that many steps of a. n <= min(8, ally
    count). Tiles read are neighbours of entries, so within min(8, count) of a (Chebyshev). `draw_square`
    (`DrawChebyshev`) covers exactly that. So with no labelled tile in the box, no read finds a label, and the old
    walk returns unreachable. If an earlier iteration had already found a label, that tile is in the box, so the
    test can't return early wrongly.
  - **The 4-ally threshold** only decides when the box is tested, not what is returned: below 4 entries the old
    walk runs unchanged.
  - **The other two cuts.** `i == 0` skips a's own non-ally neighbours, which the first loop read and found
    unlabelled (else it returned). The `best <= d + 1` break is exact because entries are listed by depth
    (breadth first) and labels are >= 0, so any later entry gives l + 1 + d' >= best.
- e321cb9f, three spare failed searches (exact).
  - **Matching.** A spare matches under failed_'s own rule (layers >= 0, same origin, cap no higher or the spare
    ran dry, equal goals and walls), without the `within_failed` widening. `walls` is rebuilt every call from
    blocked/occupancy, crossings, avoid (or the danger region) and the guard. The search's only other inputs are
    the goals and the origin tile (me). So the field and visited are a pure function of the key, and the spare's
    labels up to the cap are what a fresh search would label. A move, bump, occupancy or wall change within the turn,
    or a new round, either changes the key (no match) or leaves the result the same. No invalidation is needed, as
    for failed_, which was never invalidated either. A hit swaps the spare into failed_, `route_field_` and
    `route_labelled_` (failed_'s old contents go to the spare) and takes failed_'s reuse path. layers = min(s.layers,
    cap), so `route_exhausted_` matches a fresh search: s.layers < cap iff the search runs dry below cap.
  - **Later state.** failed_ then holds the spare's cap and layers, which may be higher than a fresh search's. That
    is the old failed_ reuse's state too. Every reader of f.cap (the next match, `keep_round`'s cap and dry for
    `round_fails`) reads only labels below the current cap.
  - **Eviction.** Only a valid failed_ (layers >= 0, so `route_field_` holds its labels) is evicted. `keep_round`
    and the success path set layers to -1 before the field leaves.
  - **Against campaign 4's dropped B** (also 3 slots; uncommitted): this one is LRU, carries the labelled board
    label_through's box needs, and is judged with 9fe383a6. On its own B was level, and so is this one (worker
    A/Bs: b9 -2.2% and -0.9% OOF against a9's +0.8% and -1.8%). It is kept for the runaways it removes
    (topo-shortcut-1101506904 b 1,516 -> 329) and judged on the merged A/B.
- fc5-budget: f64df912 and its revert 12aa16d9 cancel, so the merged source has no change from it (`git diff
  e2aefaa4` on bots/ touches only plan.cc and pathing.{cc,h}).

**100M** (base -> m2, `MAIN/replays/fuel/fc5/m2-*-100M.json`, `bench.py compare`): all 234 replays identical against
fc5b and against m1.

| set | identical | total | mean | p90 | p99 | max | over 100k | round 1 mean / p90 / max | total vs m1 |
|---|---|---|---|---|---|---|---|---|---|
| wide | 52/52 | -1.71% | 51919 -> 51033 | 86447 -> 86320 | 107443 -> 105536 | 276792 -> 265632 | 3989 -> 3635 | 218844 -> 214327 / -3.8% / +0.5% | +0.06% |
| oof | 48/48 | -1.20% | 55476 -> 54809 | 88271 -> 87841 | 151026 -> 148123 | 555669 -> 557900 | 16830 -> 14979 | 240433 -> 235415 / -4.3% / -8.9% | +0.07% |
| mg | 24/24 | -0.99% | 59725 -> 59134 | 89577 -> 88689 | 149290 -> 148234 | 373058 -> 384645 | 7734 -> 7358 | 231016 -> 230316 / +0.3% / +1.4% | +0.08% |
| q | 48/48 | -2.20% | 60546 -> 59220 | 90393 -> 88768 | 138656 -> 134348 | 438608 -> 437866 | 18447 -> 16681 | 262663 -> 249895 / -7.0% / +0.7% | -0.12% |
| big | 32/32 | -2.08% | 60562 -> 59299 | 87500 -> 87303 | 119861 -> 114926 | 327360 -> 328679 | 4087 -> 3309 | 248914 -> 246158 / -2.7% / -3.5% | +0.10% |
| fs | 24/24 | +0.64% | 94855 -> 95452 | 132691 -> 133748 | 196715 -> 198448 | 611791 -> 618391 | 22467 -> 23125 | 550887 -> 558348 / +1.5% / +1.2% | +0.05% |
| fight | 30/30 | -0.36% | 48562 -> 48386 | 85980 -> 85946 | 116891 -> 115798 | 380991 -> 375269 | 4796 -> 4586 | 196135 -> 196741 / +0.4% / +1.2% | +0.08% |
| tgt | 16/16 | -0.41% | 50964 -> 50762 | 86744 -> 86565 | 117584 -> 112610 | 263616 -> 255615 | 2438 -> 2074 | 230092 -> 223217 / -0.7% / -6.3% | +0.04% |

Against m1 the totals rise 0.04-0.10% on every set but q (-0.12%), from 313's spare lookups and swaps on every fresh
failed search. Round-1 means rise 0.2-0.6% on seven sets (fight level). 311 and 312 save on heavy turns only (against m1: wide max
-1.4%, tgt max -0.9%).

**Real budget benches** (m1 -> m2; small, indicative): OOF wide 528 -> 570, oof 3,744 -> 1,543, mg 2,629 -> 531, q
3,108 -> 2,214, big 180 -> 164, fs 2,059 -> 2,127, fight 848 -> 792, tgt 1,030 -> 954; all 14,126 -> 8,895. The
oof and mg drops are runaway games, which swing by thousands once games diverge.

**A/B m2 vs fc5b** (fresh-11000..11019, own drafts, real budget, fast runner, 10,240 games; log
`MAIN/replays/fuel/fc5/ab-fc5-m2-vs-fc5b.log`, stats `/tmp/fc5/merge2/ab-fc5-m2-vs-fc5b.stats`, batches deleted):

| bot | win | OOF | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p50 / p90 / p99 | >= 100k | shortcuts (no OOF) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **m2** | **50.7 (49.8-51.7)** | **57,920** | 4,178 | 6,268 | 9,030 | 13,113 | 25,331 | 37,358 / 17,678 / 2,884 | 49,229 / 47,250 / 86,050 / 92,250 | 0.22% | 2,595,508 |
| fc5b (ref) | | 59,731 | 4,035 | 6,564 | 9,277 | 13,134 | 26,721 | 37,965 / 18,900 / 2,866 | 49,918 / 48,350 / 86,150 / 92,450 | 0.23% | 3,037,303 |

- OOF -3.0% (without shared-gems maps 55,133 / 56,737, -2.8%). m1 had read +0.2%. Rounds 300+ -5.2%, 2-10 -4.5%, 11-60 -2.7%, 61-300 level. Round 1 +3.5% (+143). The worker's 312+313 A/B
  read the same (+159), and fc4's dropped spare cache read +~350 there. So it is likely 313's lookups: the
  100M round-1 means are +0.2-0.6% against m1.
- Runs of 50+ level (2,884 / 2,866; m1 read 3,916 / 2,820). The 10-49 bucket fell 6.5%.
- Shortcuts -14.5%. Against fc5b: farm-partial-evaluation 1,653,290 / 2,059,860, step-guard-entry 422,047 /
  434,240, turn-order 112,475 / 115,712, prey-cut-short 98,835 / 101,485, step-guard-look 74,521 / 76,735,
  crow-flies-farm 61,244 / 59,612, comms-stale-vision 51,529 / 53,215, farm-no-route 47,041 / 48,906,
  ward-no-bushes-clusters 40,978 / 51,347, static-descend 16,951 / 18,981, step-guard-sim 4,703 / 5,734,
  siege-route-fuel 2,559 / 2,230.
- Step 5 (dropping a commit) was not needed: all three reviews hold, the win CI (49.8-51.7) doesn't fall
  below 50, and OOF is down, not up.

**Left after round 2.** OOF 57.9k against the campaign target of 40,960 (-30%). The rounds 300+ tail is still 44%.
Both fight-side workers conclude that the fight units are near their floor, and that reserves can't reach 85% of
near-enemy OOF turns. Open, in order:
- bounded fight work with a deterministic fallback (FUEL-GATES rule 2): the strike search's 24-node DFS and priced
  tiles, and want_home's `stand` (~21k when it runs);
- the bound-ordered farm loop (round 1's lead);
- step_field's static-then-wide pair as one wide search (fc5-post);
- 313's common-case cost: skip the spare lookup when no spare has our origin (+0.05-0.1% at 100M, and round 1's
  +143 OOF);
- a per-turn memo for make_way's repeated label_through calls.

## Unread work on near turns (worker; branch fc5-near)

One exact cut kept (b07ae236, retreat's untouched tests stop at the first blow: OOF -5.1% in the A/B, below);
every other candidate traced was read on the paths that follow it, or too small to judge. Data: the budget worker's census (`/tmp/fc5/budget/cen`, `--fine --trace`, 2,048
games, m1 opponent), rounds 300+ with an enemy within 6: 3,375 turns, 2,776 of them out of fuel. Scripts
`/tmp/fc5/near/`: `sc.py` (scope incl / self / calls a turn), `kept.py` (want_home followed by later work or not),
`gaps.py` / `gapsr.py` (fuel between consecutive trace entries, all OOF turns / from `retreat` on).

**want_home is read on every path.** `decide` reads `leave` for Willow's branch, local_support, the heal/shield
block, mend, retreat and (when false) the strike search: there is no branch that decides the turn before it.
On the 60% of near turns that run a channel first, `continue_recall` asks it (we start a recall every turn end) and
the recall is then cancelled and `decide` reuses the cached answer; the channel ended the turn on 0.3% of near
turns where want_home ran (31 of 9,778 in all rounds). Within it, `low || outmatched || camp_trapped` already
short-circuits, and `lethal` is read twice after (`stand`'s `falls` / `unseen` and the result). A same-turn second
evaluation is rare (decide's own `want_home` scope ran on 69 near channel turns, after a ward or shop reset).
- Rule-based bound for `stand`: `simulate` already opens with the exact prefilters (`their_cap.short_of`,
  `our_bounds` + `overwhelmed`); the rest is a played-out fight, 7.6k self a call, ~0.85 calls a near turn.
- `lethal`: 6.3k a near turn, of it damage_ceiling 5.6k (self 2.2k; the rest Reach builds that `stand`'s
  `approach` / `blow` would build next anyway: Reach is pooled by Safety per enemy). `worst_damage` past it is only
  ~0.7k a turn: the ceiling is below health on most calls. Building threats straight away is not exact (`built_`
  switches `threats_at` and `lethal` to other code paths).

**World update (11.7k a near turn)**: champion_enemy 3.3k (6.2 calls), camps 3.2k, rank_turns 2.25k (93% of
turns), champion 1.7k. All read: this round's ranks feed every `slot()` (next_turn_round in each Reach build);
next round's ranks are copied, not sorted, when priorities are stable.

**Strike search**: the cover runs once a search (0.73 calls a near turn vs 0.78 searches); `route()`'s cover cache
and the deferred guards (`guard_steps`, `guard_work`'s `work_cover`) add no second cover on the same tile.
Reach builds and Strikes are shared with want_home through Safety. The search's `lethal` is at grid-edge tiles,
not at `here`. Fight / fight2 cover what is left (fronts, pricing, cap order).

**Kept: b07ae236, `Safety::touched`: retreat's untouched tests stop at the first blow.** Tracing which scope
each `Safety::bound` sits under (`bnd.py`), on near OOF turns in rounds 300+ 2.4k a turn of bound is under `retreat`
(1,876 calls over 3,071 turns, 3.9k a call incl: a blow, i.e. Reach::at with its sight windows, per enemy per tile);
on the 397 that retreat, 16.8k a turn. Two of retreat's callers read only whether the tile is touched:
`quote_escape_walk` (`untouched(bound(p))`: doubled <= 0, no hit, no stun) and retreat_step's longer steps (kept
only when `damage > 0 || hits` is false). `touched(p, scale)` answers `camp > 0 || some blow hits or has
damage*scale > 0`, walking the threats in each_threat's order and stopping at the first that settles it.
Exact: every term bound sums (camp damage, blow damage times a positive scale, doubled by 1 or 2) is at least 0, so
a sum is > 0 exactly when some term is (float addition of non-negatives is monotone); a stun implies a hit. A
longer step that is untouched has bound() all zero, so its option is `Bound{}`. Skipped work is blow() calls
(Reach::at, Reach builds, `x.asked` memos) and the `threat` count_within calls nobody read; Reach and its memos are
caches of the turn's state, and the 100M benches show no decision moved.
- 100M: identical replays on all 8 sets (wide 52, oof 48, mg 24, q 48, big 32, fs 24, fight 30, tgt 16). Total fuel
  -0.07 / -0.14 / -0.05 / -0.03 / -0.01 / -0.01 / **-0.23** / -0.06%; fight p99 115,771 -> 115,474. It fires in all
  sets (retreats), so no extra firing set.
- A/B vs m1 (`ab.sh fc5near-t1 variants/near-t1 variants/astraeus-fc5-m1`, 10,240 games, real budget): 49.8%
  (5102-5138), CI 48.9-50.8. **OOF CAND 54,809 vs REF 57,749 (-5.1%)**; rounds 2-10 / 11-60 / 61-300 / 300+:
  6,221 / 8,551 / 12,162 / **23,857** vs 6,242 / 9,018 / 12,945 / **25,526** (-6.5% in 300+). Shortcuts 2,634,217
  vs 2,643,480 (-0.4%; turn-order -2.4%). Larger than the fuel totals suggest: retreat turns are the heaviest near
  turns (42k for `retreat` alone), so a few k there is what pulls them under 100k.
- Confirmed on fresh-10000..10019 (10,238 games, no A/B of this campaign used it): 50.1% (49.1-51.0); OOF 56,684
  vs 59,434 (-4.6%); rounds 2-10 / 11-60 / 61-300 / 300+: 5,964 / 8,647 / 12,368 / 25,819 vs 5,969 / 9,066 /
  12,905 / 27,608 (-6.5% in 300+). Shortcuts level (2,715,687 vs 2,714,443).

**Kept: dash_retreat_casts' quote tile also asks `touched`** (same argument, scale 1; `untouched()` removed).
100M: identical on all 8 sets; against b07ae236, 398 turns cheaper and 10 dearer over the 8 sets, totals -0.00%.
Too small for an A/B of its own; it rides on b07ae236's.

**Leads.** retreat_step's homeward/sideways options still need every bound in full (they sort by damage), as do
`mend_step`, `exposure_at` (Willow) and `flee_camps`' damage_bound. want_home's Willow test reads only `bound(here).threat`:
an early stop at the first visible hitter would be exact (Willow only). `avoid` as a pre-filter for retreat_step is
not exact: an unseen threat's area is a walls field of capped radius, while each_threat tests Chebyshev reach
(`any_within`).

Dropped as too small (< ~1k on the turns they fire): retreat's second `camp_trapped` / `mono_trapped` after
want_home's (needs a key on shield and Safety's epoch: heal_ally / shield_if_needed run between); laziness for
search_strikes' intent inputs (retaining_gems, farm_step_value: cheap); `pull` in retreat_step (~100 a tile).

## Early exits (worker; branch fc5-exit)

Three exact cuts kept, each byte-identical at 100M on all 8 sets against `exit-base` (m2 + fc5-near, benches
`exitbase-*`). Together: **OOF -0.6% / -0.7%** on two 10k suites (rounds 300+ -0.3% / -1.3%), win 50.1% / 50.2%:
real but small. Scratch `/tmp/fc5/exit/` (`cmp.sh` 100M compare, `kids.py` a scope's children from the census
trace, `seq.py` a scope's event sequence; census `cen/`: exit-r2 `--fine --trace` vs exit-r2, fresh-11000..11003).

**Kept.**
- 3d9ba0ef, retreat_step's homeward and sideways steps (fc5-near's open lead). `Safety::tally` sums bound()'s
  damage / hits / stuns in each_threat's order and stops after the first term that makes damage > 0; `finish`
  resumes from the enemies left. Steps that may rank first (homeward walks, and complete steps with no damage
  and no stun) are tried first in the full sort order; the rest are finished and sorted only if all of those
  fail. Exact: every term is >= 0 (float addition of non-negatives is monotone), so a stopped tally has damage
  > 0 and ranks after every lead step; the sort is stable, so the two halves concatenated are the full order;
  a refused move changes no Safety input (Safety reads World, not Pathing). It also drops bound()'s unread
  `doubled` and `threat` (count_within per unseen hitter). A first version (a class test, then bound() in full)
  repeated the walk when every step was touched: ~3k dearer on 10% of changed turns; the resumable tally fixed
  that. 100M fight -0.11%, oof -0.06%; ~3.8k turns saved over 1k on each of fight and oof.
  A/B vs exit-base (fresh-11000..11019): 50.1%, OOF 54,070 vs 54,107 (level); fresh-10000..10019: 50.2%, OOF
  54,485 vs 54,760 (-0.5%).
- 9bc487bc, Willow's want_home test (`bound(here).threat`): `Safety::threat_at` walks bound's order and returns
  once the threat holds (it never turns false). Willow only (188 of ~4.3k near OOF turns in the census): 100M
  ~400 turns saved over 1k on fight and oof, median -500 on changed turns. A/B (with 3d9ba0ef): OOF 54,043 vs
  54,135.
- 4f5c745e, `only_threat` (retreat's sure kill, step_to_kill per adjacent tile and **per dash landing**, up to
  24): it built every threat's blow at p via threats_at, the victim's included, to ask whether another enemy
  hits. `Safety::other_hits` walks threats_at's entries in its order and 16-entry cap, never works out the
  victim's blow and returns at the first other hit (unseen bisection factored out as `unseen_blow`, shared).
  Seen in the census as nine camp_damage + threats_at pairs at ~4k each in one retreat turn. Fires rarely at
  100M (tens of turns, most over 3k). A/B (all three): **50.1%, OOF 53,758 vs 54,074 (-0.6%)**; rounds 2-10 /
  11-60 / 61-300 / 300+: 6,247 / 8,392 / 11,817 / 23,125 vs 6,265 / 8,506 / 11,921 / 23,205. Confirmed on
  fresh-10000..10019: 50.2%, **OOF 54,477 vs 54,870 (-0.7%)**, 300+ 23,971 vs 24,277 (-1.3%). Shortcuts level.

**Dropped.**
- `damage_bound_until` for damage_bound's threshold consumers (recovered_for_work's `health <=`, shield_at's
  `min(shield, turns * bound)` cap in the strike search's pricing, strike_free's `> 0` via tally): identical,
  but only a few dozen turns over 1k on any set; the rest codegen (+65 median).
- retreat_step best-first (`extend(t, limit)`: a step's tally carried on, least partial first, only while <= the
  least complete damage; lead = least-damage steps): identical, OOF -0.4% vs 3d9ba0ef+'s -0.6% (level), and
  many turns ~250-750 dearer at 100M (p99 +3.2k) for ~1.2k saved over 1k on fight. Once all steps are touched
  the first-ranked one needs every term anyway, and the rest stop after one term already.

- flee_camps' argmin (a direction whose own-tile damage_bound, summed until it passes the best so far,
  already exceeds it skips the rest and its exit_hits walk; exact: non-negative terms, strict >, ties need
  equality): identical at 100M, ~200 turns saved over 1k on fight and oof, median +100 on changed turns
  (codegen). A/B vs 4f5c745e: OOF 53,651 vs 53,771 (-0.2%) on fresh-11000..11019, 54,439 vs 54,360 (+0.1%) on
  fresh-10000..10019: level.

**Census of exit-r2 (rounds 300+, an enemy within 6, 3,276 turns, 2,656 out of fuel).** By type: Heart of Ruin
1,843 of 4,255 near OOF-first turns, Vesper 597, Issac 415, Vendetta 368, Marcella 305, Willow 188. strike_search
44.5k when it runs (79%), s.stand 12.5k (83%), lethal 6.5k (92%; damage_ceiling self 2.1k a call), channels 21k
(62%), retreat 34.8k (8.9%). The census tracer's per-scope cost between sibling events includes the parent's
uninstrumented work: `s.awake_members` looks like 1.9k a call there, but its own cost is ~450.

**Not exact / not taken.** `lethal`'s ceiling compared with health needs every term when it is below (most
calls); a Strike-based upper bound first is not exact (blow() allows Reach 0.01 over Strike, the REACH-BOUND
check), and its Reach::at results at `here` are read again by stand. The strike search's Front::admit already
rejects cheaply; offers can't be skipped before `got` is set.

**Open leads.**
- sole_escape_threat and offer_channel read threats_at in full and return at the first settling entry: the same
  walk-and-stop as other_hits (once a turn at `here`, small).
- The remaining near-turn cost is read work (fc5-near, fc5-fight2): the HoR strike search's grow and `stand`.

## Pathing follow-ups (worker; branch fc5-path)

Two fuel-only commits from fuel5-orch dab1970e: 7de069e4 (313's common-case cost) and 2d660e57 (label_through
memo). Both leave all 234 replays of the 8 sets identical at 100M against m2. Frozen: `variants/path-d` (= 7de069e4),
`variants/path-m` (= 2d660e57's code).

**Where 313 cost.** Reverting 313 on m2 (`path-r`) makes 92-97% of all turns cheaper: wide -0.08%, oof -0.09%, mg
-0.12%, big -0.10%, fs -0.05%, fight -0.09%, tgt -0.05% (q +0.21%: the spares pay there). So the cost was not the
failed searches' lookups but the inlined lookup loop in flattened route_around, paid on every fresh search
(~30-50 fuel), plus 12 allocations on the first turn (~400 of round 1). Tried: lazy allocation alone (+0.01-0.02%
against m2: round 1 only); out of line alone (+0.02-0.03%: the call costs more than the loop); out of line plus
one kept origin, dropping spares from any other (-0.03..+0.01%, but oof/mg p99 +0.1%, as oscillating standoffs lose
their spares).

**7de069e4 (kept).** take_spare/spare_failed out of line, called only when `me` equals one of the three spares'
origins, mirrored inline in `spare_me_` (set in swap_spare: the spare's me if valid, else {-1,-1}); spares made on
first use. Exact: a spare can match only from its own origin (its key includes me), so skipping the lookup elsewhere
changes nothing; the LRU order is the same (an empty slot first). 100M totals vs m2: wide -0.03%, oof -0.02%, mg
-0.01%, q -0.02%, big -0.03%, fs -0.02%, fight -0.03%, tgt -0.02%; round 1 means -0.1% on every set; p99 within
±0.1%. A/B vs m2 (fresh-110xx, 10,240): 50.1% (49.2-51.1), OOF 56,568 / 55,792 (+1.4%): round 1 4,145 / 4,176,
2-10 6,302 / 6,299, 11-60 8,920 / 8,785, 61-300 12,796 / 12,674, 300+ 24,405 / 23,858; runs >= 50 1,643 / 1,258
(the difference is runaways); shortcuts 2,679,394 / 2,679,284. Level.

**label_through repeats (measured with a debug copy at 100M, oof+q+mg sets as side b, 60 games).** 98k calls,
260M fuel (~0.8% of those games' fuel), 15% of it in calls repeating one earlier in the turn with the same field,
cap, a, me, allies, avoid and guard (by content). Concentrated: topo-odd-spawn-986807107 19.6M, topo-necks-987007003
8.4M, topo-backdoor-987806707 4.8M, atoll-600101912 4.5M. On odd-spawn's heaviest turns make_way's 12 calls a turn
are 4 tiles x {avoid, no avoid} x {static cap 23, wide 103} at ~3k each: different searches (equal labels, but
different fields and caps), so no exact key joins them. The rivers-1100302130 runaway doesn't reproduce at 100M.

**2d660e57 (kept).** A 4-entry ring memo around the line walk (only after a's neighbours hold no label, i.e. the
costly part): key route_gen_ (bumped at the four places route_field_ changes: the fresh compute, the success swap
with kept, swap_spare, keep_round), route_label_cap_, a, me, avoid/guard null-ness, and allies, avoid and guard by
boards_equal. Exact: the walk reads only route_label (route_field_ and the cap), allies, avoid (incl. test(avoid,
me)), guard(), a and me; route_labelled_ only feeds the box test, which never changes the result. A pending guard
(guard_fn_ set) bypasses the memo, as the walk would work it out; with none pending guard() returns guard_ unchanged.
100M vs m2: wide -0.02%, oof +0.04%, mg +0.11%, q -0.83% (odd-spawn-986807107 a -57M, backdoor-987806707 a -32M),
big -0.02%, fs -0.02%, fight -0.01%, tgt -0.01%. Cost: stores copy up to 3 boards (~280 a walk on
mut-the-pack-600201800, no repeats there: +7.2M on side a, oof/mg p99 148.1k -> 149.3k / 148.2k -> 149.8k). Variant
storing only walks that listed 4+ allies (`path-m2`): q -0.37%, mut-the-pack +3.8M, p99 +0.4-0.5%. A/Bs vs m2
(10,240 each): store-always 50.6% (49.6-51.5), OOF 56,098 / 56,515 (-0.7%; 300+ 23,992 / 24,501, round 1 4,128 /
4,177, runs >= 50 1,232 / 1,363); long-only 50.2%, OOF 55,990 / 56,009. Both level; store-always kept for its q
savings and runaway turns.

Open:
- step_field's static-then-wide pair as one search (not built). The static search's result is reproducible from a
  wide one only when it succeeds within the static cap (BFS stops at our layer, so the field is the same). When it
  doesn't, the static failure must still be emulated for make_way/label_through (labels capped, failed_ with the
  static cap and layers = cap, route_exhausted_ false), and the wide search later wants the same field as a kept
  route: holding it in both route_field_ and kept costs a field copy (~2 bytes a tile, 20k on 100x100). Also the
  static stage is guarded (deferred guard, know_failure) while the wide pre-check is unguarded, and walking_round_ /
  round_fails / travel's dash plan read the cap. Needs a design that keeps one field in one place.
- label_through's store cost on maps with no repeats (~280 a walk): store allies only and key avoid/guard by
  pointer plus a per-turn version, if one can be proven to bump on every write to those boards (est. 0.05% on
  oof/mg).
- the remaining static/wide x avoid/no-avoid repeats: unreachable under the static cap is implied by unreachable
  under a higher cap over the same labels; joining them needs a field identity that survives the static->wide
  re-search (est. up to ~2/3 of odd-spawn's make_way fuel).

## Economy early exits (worker; branch fc5-econexit)

One exact change kept: 4130f1fe (the takeover pass's walk-independent tests before its walk field), **OOF -7.1% and
-6.6%** in two 10k A/Bs against m2. Scratch `/tmp/fc5/econexit/` (`sc.py`: census scopes on no-enemy OOF turns;
`stk.py`: the scope stacks where those turns ran out; `lapsum.py`: `LAP` lines; `b100.sh`: 100M on the 8 sets).

**Where no-enemy OOF turns spend** (budget worker's census `/tmp/fc5/budget/cen`, 4,028 OOF turns with no enemy near,
incl a turn): farm 52.9k (loop 28.7k, post 21.3k), carry_bag 13.3k (18% of turns), update 10.7k, make_field 7.8k
(0.5 calls, ~15k a build), min_camp_damage 5.9k, siege/kite 4.5k self, clear_fire 4.3k. act_end is only 0.66k: its
OOF stacks (place_lock 199, ward_bushes 252) are where an already-spent turn ran out, not where it was spent.

**Kept: 4130f1fe, farm's takeover pass asks its walk-independent tests first (exact).** After the loop, for each
cleared group near us with an ally on it, farm read `pathing.to_group(g).at(here)` (a static field, ~15k to build
once per group, used almost nowhere else) and then `takeover_worth`, which returns -1 at once for a champion that is
neither Marcella nor has Vesper Vale's gold bonus, and for a group another holds alone, an enemy stands on, or our
hold would not outvalue. Those tests read no walk: `takes_over(world)` (per turn, hoisted into the pass's guard) and
`may_take_over(world, G)` (per group, before the walk) now run first. All are pure reads (sole_capture_holder,
enemy_on, outvalues_holders, gold_paid), so skipping a group they reject skips only the field build; a field built
later is the same (static walls, same goals) and kept forever (Pathing::cached).
- 100M vs m2: identical replays on all 8 sets; totals wide -0.11, oof -0.12, mg -0.13, q -0.11, big -0.16, fs
  **-0.39**, fight -0.08, tgt -0.13%; p99 big 114,926 -> 113,602, fs 198,448 -> 197,044, q 134,348 -> 133,828.
- A/B vs m2 (`ab.sh fc5econ-t1 variants/econ-t1 variants/astraeus-fc5-m2`, fresh-110xx, 10,240): 50.2% (49.2-51.2).
  **OOF 52,130 vs 56,111 (-7.1%)**; rounds 1 / 2-10 / 11-60 / 61-300 / 300+: 4,175 / 5,960 / **7,378** / 11,668 /
  22,949 vs 4,177 / 6,288 / **8,860** / 12,913 / 23,873. Shortcuts 2,633,939 vs 2,667,560 (farm-no-route 32.5k vs
  46.7k, turn-order 102k vs 111k). p99 a turn 91,850 vs 92,150.
- Confirmed on fresh-100xx (10,238): 50.2% (49.2-51.1); OOF 53,027 vs 56,745 (-6.6%); 11-60 7,819 vs 9,194 (-15%),
  61-300 11,400 vs 12,363, 300+ 24,131 vs 25,181.
- Why so large for -0.1% total: a build is ~15k on one turn, once per (champion, group), on the early-mid turns when
  allies first hold captures, which is where 11-60 OOF sits.

**Kept: 8b8df913, the takeover pass prices the holders before the walk field (exact).** takeover_worth's holder
loop, gain test and payout timer read no walk either: `takeover_gain` runs them first, and a timer below 2 or below
`steps_to + 1` rejects as `timer < walk + 1` would (a walk to the group's tiles is never shorter than the Chebyshev
distance to them: CampGroup::tiles() is the members' positions). `takeover_worth(gain, timer, walk, ...)` adds the
walk. It fires only for Marcella / Vesper Vale-bonus champions past may_take_over.
- 100M vs m2: identical on all 8 sets; totals as 4130f1fe's within 0.01%.
- A/B vs econ-t1 (= 4130f1fe; `ab.sh fc5econ-t2 variants/econ-t2 variants/econ-t1`, fresh-110xx, 10,240): 50.0%,
  OOF 52,088 vs 52,128: level, as expected from how rarely it fires.
- Side effect of both: fewer field builds leave `max_field_layers()` / `costliest_field()` (fuel estimates only)
  lower on some turns; at 100M nothing reads them for a decision.

**Measured, not changed.**
- siege() (laps, oof set, real budget, all turns): mean 3.1k, p90 6.8k, p99 16k; of it siege_candidate 2.4k, mostly
  altars_sealed 1.7k, which is altar_access's rebuild (p90 2k, p99 8.9k; on live-camp flips) plus access_fire
  (0.23k). Both are memos shared with bankable_bag, read whole; fire_on_open already stops at a zero tile.
- camp_cast 0.24k a no-enemy OOF turn: a per-slot bound (a cast's value is at most the sum of its targets' worths,
  exact in float for non-negative terms summed in the same order) could skip the second slot's skip board, but the
  whole scope is too small.
- ward_bushes 0.38k: a cluster-size bound before its count_within calls would need a stored size; too small.

**Open leads.**
- Other static fields built for a candidate a later pure test rejects: mend_step builds `to_group(farm_group)` before
  checking that any neighbour is a free spawn tile (likely rare off spawn).
- prices(): its key includes gems_share, which moves every tribute, and re-runs best_emblem; best_emblem reads items
  the key leaves out, so splitting the key is not exact as it stands.

## Merge round 3 (merge agent)

fc5-exit (with fc5-near: b07ae236, 02cface6, 3d9ba0ef, 9bc487bc, 4f5c745e; notes 4da176e9, 783b282e, 8ab8ab34,
9237a0bd, bedeabd9, d7a108fe), fc5-path (7de069e4, 2d660e57; notes e8b957ed) and fc5-econexit up to 92f0241f
(4130f1fe, 8b8df913; notes 789a586f, 92f0241f) merged into fuel5-orch whole (merges 963d4aec, e85ea6be, c0b827a9;
NOTES conflicts only, both sides kept). Nothing dropped. fuel5-orch already held the tool-speed merge (859a5bc6: fast
runner PGO bot builds, heap mallopt, libdeflate level 1, stats only for .camstat, slot polling, a build lock, oof.py
bytes.find; tooling only, no bot change). The runner in the primary checkout has not been rebuilt with it; the
orchestrator does that. Frozen: `fuel5/bots/variants/astraeus-fc5-m3` (= fuel5-orch's bot), and `astraeus-fc5-m3x`
(m3 without 2d660e57). CHANGES 314 (b07ae236 + 02cface6), 315 (3d9ba0ef), 316 (9bc487bc), 317 (4f5c745e), 318
(7de069e4), 319 (2d660e57), 320 (4130f1fe + 8b8df913), all fuel only.

**Review.**
- b07ae236 + 02cface6, `Safety::touched` (exact).
  - `any_threat_at` is each_threat's loop with an early return: the same enemies in the same order, the same skips
    (gone, reach < 0, unseen with weight 0), the same `asked`/`near` memo, the same blow (visible: `blow`, unseen:
    `s.blow(0)` if near).
  - The old test was `damage > 0 || hits` (retreat_step's longer steps) or `doubled <= 0 && !hits && !stuns`
    (quote_escape_walk, dash_retreat_casts). Every term is >= 0: camp damage, and blow damage times a positive
    scale, doubled by 1 or 2. A float sum of non-negatives is > 0 iff some term is, and doubled > 0 iff damage > 0.
    stuns needs hits. So both tests are "some term has damage > 0 or hits", which touched answers at the first such
    term.
  - Skipped work: blow() (Reach builds, pooled per enemy and keyed on the turn's state) and the `asked` memo
    (any_within, a pure function of p). These are caches only. The `threat` count_within calls were never read.
- 3d9ba0ef, retreat_step's tally (exact).
  - **The sum.** `tally` starts from camp damage, the same first term as bound, and stops only once damage > 0.
    `finish` resumes from `left` (the enemy bits not yet visited), so a finished tally adds the same terms in the
    same order, the same floats as bound's `damage`. hits and stuns are ORs over the same terms.
  - **reached.** reached (`damage > 0 || hits`) is exact before finishing: a tally that stopped has damage > 0, and
    one that didn't is complete.
  - **Longer steps.** Untouched longer steps get `Tally{}`, which equals bound's all-zero result.
  - **The split.** Lead = home options (priced in full) plus complete options with damage 0 and no stun. Rest = the
    other non-home options: either damage > 0 (a stopped tally's partial > 0, so the full damage is > 0) or damage 0
    with a stun. Every lead option ranks before every rest option under `by`: home first, then damage, then
    `b.stuns`. The sort is stable and the partition keeps relative order, so sorted(lead) followed by sorted(rest)
    is the full stable sort. Rest is priced in full before its sort.
  - **Pricing after refused moves.** Rest is priced after lead's refused `try_move`s. A refusal changes only
    Pathing (`bumped_`, invalidate). Safety and Reach read World (const here) and its allies, never Pathing or host
    vision, so the prices are the same.
- 9bc487bc, `Safety::threat_at` (exact). It equals bound's `threat`: a visible hitter sets it. An unseen near
  hitter multiplies `safe` by `1 - chance * hit_given_reach` with the same count_within, and sets it once
  `1 - safe >= recall_risk`. bound stops updating once threat is true, so returning there is the same. Non-hitting
  and far blows don't touch `safe`, in both versions.
- 4f5c745e, `only_threat` by `other_hits` (exact). Built: threats() in order, the first 16 (`n++ == kept` breaks
  where threats_at's `n < 16` stops filling). Not built: the same loop as threats_at, counting each entry it would
  list (gone or full: skip; reach < 0: skip; visible, or unseen with weight > 0: one entry). Only the hit test of
  non-victim entries is read. The unseen bisection is moved verbatim into `unseen_blow`. camp_damage > 0 still
  returns false first.
- 7de069e4, the spare lookup out of line (exact).
  - **spare_me_ mirrors every spare's origin.** spare_me_[i] = s.me if s.layers >= 0, else {-1,-1}, set in
    swap_spare. That is the only place a spare's fields change: take_spare and spare_failed both go through it, and
    nothing else touches spare_routes_.
  - **The skipped lookup.** The old match needed `s.layers >= 0 && s.me == me`, which is exactly `spare_me_[i] ==
    me` (me is in bounds, never {-1,-1}). So skipping the lookup when no spare_me_ matches skips only searches that
    couldn't match.
  - **Eviction.** The old LRU picked the first minimum `used`. Unmade spares had used 0, made ones >= 1, and slots
    fill in index order. So it took the first empty slot, else the first least-used, as spare_failed does. A fresh
    slot is default-constructed as the old array's was.
- 2d660e57, label_through's memo (exact).
  - **The key covers what the walk reads.**
    - route_label: route_field_ (route_gen_) and route_label_cap_ (keyed).
    - route_labelled_ in the box test: it moves with route_field_, so route_gen_ covers it. The box only returns
      unreachable early, never a different label.
    - allies (content; the box's board_count too), avoid (content, and `test(*avoid, me)`), guard() (content), a,
      me, in_bounds (static).
  - **route_gen_ bumps.** route_gen_ is bumped at all four writes to route_field_ / route_labelled_: the fresh
    compute, the success swap with kept, swap_spare and keep_round. `grep route_field_` finds no other writer, and
    the constructor's fill precedes any memo entry.
  - **The guard.** A pending guard (guard_fn_) bypasses the memo both ways. With none pending, guard() returns
    guard_ unchanged, so a hit skips no side effect. The walk's static `box` is scratch.
- 4130f1fe + 8b8df913, takeover tests before the walk field (exact at 100M).
  - **The same rejections.** Old per group: walk unreachable, then takeover_worth's walk < 1, the gold test,
    sole_capture_holder, enemy_on, outvalues_holders, timer < walk + 1, no holder, gain <= 0. New: the gold test
    (`takes_over`, a per-turn read of our facts and gold_paid, constant over the pass), may_take_over, then
    takeover_gain (timer < 2, holder, gain), timer < steps_to + 1, walk unreachable, then walk < 1 || timer < walk
    + 1. All are conjunctive rejections and pure reads of World. Nothing in the pass writes World: to_group fills
    only Pathing's field cache.
  - **The added tests reject nothing new.** `timer < 2` is implied by walk >= 1 and timer >= walk + 1.
    `timer < steps_to + 1` is implied too: to_group's goals are G.tiles(), the members' positions (rules: camp
    tiles are spawn positions), and a king-step walk is never shorter than the Chebyshev distance (steps_to is the
    Chebyshev minimum over members). The accepted set and the worth are the same.
  - **Skipped builds.** A skipped `cached()` field is built later from the same static walls and goals and kept
    forever.
  - **Fuel estimates.** Fewer builds can leave `max_field_layers()` / `costliest_field()` lower. These feed fuel
    reserves (bot.cc's altar-walk flood, main.cc's first-turn reserves, pathing.cc's centre and route estimates,
    world.cc). At 100M no reserve binds, so the replays are identical. At the real budget a lower estimate can pass
    a reserve that would have failed: a real-budget play change in fuel-gated code only, as any change to which
    fields get built already makes.

**100M** (`MAIN/replays/fuel/fc5/m3-*-100M.json`, `bench.py compare`): all 234 replays identical against fc5b and
against m2.

| set | identical | total vs fc5b | mean | p90 | p99 | max | over 100k (fc5b / m2 / m3) | round 1 mean / p90 / max | total vs m2 | p99 vs m2 |
|---|---|---|---|---|---|---|---|---|---|---|
| wide | 52/52 | -1.92% | 51919 -> 50922 | 86447 -> 86289 | 107443 -> 105191 | 276792 -> 265607 | 3989 / 3635 / 3542 | 218844 -> 214164 / -3.9% / +0.4% | -0.22% | -0.3% |
| oof | 48/48 | -1.49% | 55476 -> 54651 | 88271 -> 87828 | 151026 -> 149209 | 555669 -> 557875 | 16830 / 14979 / 14797 | 240433 -> 235266 / -4.4% / -9.0% | -0.29% | +0.7% |
| mg | 24/24 | -1.07% | 59725 -> 59086 | 89577 -> 89007 | 149290 -> 149797 | 373058 -> 384635 | 7734 / 7358 / 7368 | 231016 -> 230149 / +0.1% / +1.3% | -0.08% | +1.1% |
| q | 48/48 | -3.18% | 60546 -> 58626 | 90393 -> 88680 | 138656 -> 133769 | 438608 -> 437900 | 18447 / 16681 / 15714 | 262663 -> 249411 / -7.1% / +0.6% | -1.00% | -0.4% |
| big | 32/32 | -2.28% | 60562 -> 59181 | 87500 -> 87280 | 119861 -> 113459 | 327360 -> 328669 | 4087 / 3309 / 3146 | 248914 -> 245801 / -2.8% / -3.6% | -0.20% | -1.3% |
| fs | 24/24 | +0.22% | 94855 -> 95057 | 132691 -> 133030 | 196715 -> 197052 | 611791 -> 617285 | 22467 / 23125 / 22546 | 550887 -> 557907 / +1.4% / +1.2% | -0.41% | -0.7% |
| fight | 30/30 | -0.79% | 48562 -> 48176 | 85980 -> 85840 | 116891 -> 115398 | 380991 -> 375269 | 4796 / 4586 / 4415 | 196135 -> 196556 / +0.2% / +1.1% | -0.43% | -0.3% |
| tgt | 16/16 | -0.63% | 50964 -> 50646 | 86744 -> 86522 | 117584 -> 112533 | 263616 -> 255615 | 2438 / 2074 / 2026 | 230092 -> 222966 / -0.8% / -6.4% | -0.23% | -0.1% |

The oof and mg p99 rises against m2 are 2d660e57's store cost (m3x, without it: oof p99 148,133, mg 148,267, over
100k 14,727 and 7,301; q's over 100k 16,493 against m3's 15,714). Turns over 100k fell on six sets against m2 (mg
+10, fs -579). fs is still +0.22% on fc5b (308's codegen), down from +0.64%.

**Real budget benches** (m2 -> m3; small, indicative): OOF wide 570 -> 860, oof 1,543 -> 1,526, mg 531 -> 690, q
2,214 -> 2,838, big 164 -> 98, fs 2,127 -> 1,797, fight 792 -> 707, tgt 954 -> 767; all 8,895 -> 9,283. These swing by
hundreds from diverged games; the A/Bs judge.

**A/Bs against fc5b** (own drafts, real budget, fast runner, 10,240 games each; logs
`MAIN/replays/fuel/fc5/ab-fc5-m3-vs-fc5b.log`, `ab-fc5-m3-conf.log`, `ab-fc5-m3x-vs-fc5b.log`; stats
`/tmp/fc5/merge3/*.stats`; batches deleted):

| bot | suites | win | OOF | r1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ | fuel mean / p50 / p90 / p99 | >= 100k | shortcuts (no OOF) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **m3** | fresh-110xx | **50.4 (49.4-51.4)** | **50,627** | 4,132 | 5,872 | 7,205 | 11,100 | 22,318 | 33,406 / 15,301 / 1,920 | 49,139 / 47,150 / 86,050 / 91,850 | 0.21% | 2,562,487 |
| fc5b (ref) | | | 58,754 | 4,035 | 6,575 | 9,426 | 12,822 | 25,896 | 37,701 / 19,017 / 2,036 | 49,907 / 48,350 / 86,150 / 92,450 | 0.22% | 3,038,456 |
| **m3** | fresh-520xx (new) | **50.2 (49.2-51.2)** | **51,067** | 3,596 | 5,536 | 7,006 | 10,256 | 24,673 | 32,164 / 16,237 / 2,666 | 48,947 / 46,950 / 86,050 / 91,850 | 0.21% | 2,531,706 |
| fc5b (ref) | | | 57,039 | 3,541 | 6,049 | 8,963 | 12,407 | 26,079 | 36,304 / 18,977 / 1,759 | 49,651 / 48,150 / 86,150 / 92,350 | 0.22% | 2,980,683 |
| m3x (no 319) | fresh-110xx | 50.5 (49.5-51.4) | 50,874 | 4,136 | 5,951 | 7,196 | 10,997 | 22,594 | 33,358 / 15,911 / 1,605 | 49,135 / 47,150 / 86,050 / 91,850 | 0.21% | 2,572,802 |
| fc5b (ref) | | | 59,181 | 4,035 | 6,581 | 9,436 | 12,806 | 26,323 | 37,837 / 19,447 / 1,897 | 49,920 / 48,350 / 86,150 / 92,450 | 0.22% | 3,044,145 |

- OOF -13.8% on fresh-110xx (without shared-gems 48,663 / 56,495, -13.9%) and -10.5% on the unused fresh-520xx
  (48,869 / 54,631). Every bucket from round 2 falls: 11-60 -23.6% / -21.8% (320), 61-300 -13.4% / -17.3%, 300+
  -13.8% / -5.4%. Round 1 +2.4% / +1.6%.
- Shortcuts -15.7% / -15.1%. fresh-110xx, m3 / fc5b: farm-partial-evaluation 1,655,573 / 2,055,215, step-guard-entry
  420,003 / 437,357, prey-cut-short 103,238 / 103,348, turn-order 99,219 / 114,539, step-guard-look 74,111 / 77,363,
  crow-flies-farm 58,782 / 61,518, comms-stale-vision 44,463 / 53,474, ward-no-bushes-clusters 40,757 / 51,324,
  farm-no-route 32,706 / 48,950, static-descend 17,570 / 18,401, step-guard-sim 4,956 / 5,818. fresh-520xx:
  farm-no-route 30,997 / 45,780, crow-flies-farm 42,068 / 51,021, prey-cut-short 114,577 / 116,862,
  static-descend 18,287 / 15,759 (+16%).
- Runs of 50+ are level on fresh-110xx and +907 on fresh-520xx: runaway games, which move between suites. Not
  traced (the replay harness would find their stacks).
- **2d660e57 kept**, a judgement call. Its A/B effect is level: m3 and m3x read -13.8% and -14.0% against their
  references, which differ by 427. At 100M it costs oof and mg p99 +0.7% / +1.0% (+137 turns over 100k between
  them), and saves q 779 turns over 100k (-0.83% total). Net over-100k across oof, mg, q, big and fs: -640. The
  worker's long-only variant was no better.
- Step 5 (dropping a commit) was not needed: every review holds, both win CIs include 50 with the lower end above
  49, and OOF is down in both A/Bs.
