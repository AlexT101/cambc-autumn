# Fuel campaign 3 (2026-11-01): notes

Findings, dropped attempts with numbers and open leads, by area. Workers append a `## <area>` section on their
branch; the merge agent keeps them on fuel3-orch. Baseline and method: BRIEF.md.

## Campaign summary

Four merge rounds, every kept change byte-identical at 100M (CHANGES 265-268). The final bot is `astraeus-fc3-m4`
(main after round 4). Target was -50% OOF against fc3b; **reached -30.6%** (mirror 54,610 -> 37,908 per bot), and
-28.4% on 10 unused suites (fresh-11100..11109: 18,475 against fc3b's 25,796 in the same games, 50.6% win). Win
rate stayed level throughout (50.5-50.8% against fc3b).

A/B OOF per bot (fresh-11000..11019, own drafts, real budget, 10,240 games each):

| bot | OOF | round 1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ |
|---|---|---|---|---|---|---|---|
| mirror (fc3b) | 54610 | 10456 | 5944 | 7734 | 9919 | 20557 | 36880 / 13116 / 4614 |
| m1 (farm) | 43359 | 5668 | 3849 | 6886 | 9034 | 17922 | 28681 / 12323 / 2355 |
| m2f (scale, loops) | 40457 | 5223 | 4157 | 6500 | 7945 | 16632 | 28412 / 10511 / 1534 |
| m3 (audit) | 38820 | 5301 | 4013 | 6108 | 7717 | 15681 | 27003 / 9987 / 1830 |
| m4 (camps, sim) | 37908 | 5316 | 4047 | 6267 | 7533 | 14745 | 27302 / 8940 / 1666 |

Round 1 halved (round 1's farm bounds); 300+ fell 28%, runs of 50+ 64%. Most of the cut came in round 1 (-20.6%).

100M totals, fc3b -> m4 (fs from m1, where it began; all replays identical in every round): wide -4.70% (mean
54,055 -> 51,541, p99 116,496 -> 107,327, over 100k 5,694 -> 3,697, round 1 255,471 -> 215,904), oof -7.03% (p99
193,140 -> 151,596, over 100k 20,818 -> 13,888, round 1 333,174 -> 235,014), mg -6.71% (175,378 -> 142,446; 9,415 ->
6,530; 329,263 -> 223,151), q -10.95% (227,093 -> 164,361; 43,157 -> 26,302; 319,115 -> 258,204), big -5.69%
(131,958 -> 119,553; 6,866 -> 4,156; 294,034 -> 235,971), fs -18.83% from m1 (mean 111,957 -> 90,780).

Shortcut firings per bot in the A/B, fc3b -> m4: farm-partial-evaluation 2,601,718 -> 1,766,494, step-guard-entry
295,700 -> 275,834, comms-stale-vision 280,121 -> 182,349, turn-order 224,421 -> 141,268, farm-no-route 107,731 ->
57,462, prey-cut-short 81,505 -> 77,458, ward-no-bushes-clusters 76,605 -> 56,280, crow-flies-farm 69,455 -> 66,038.
No gate was removed (the same 17 tags and 23 `fuel()` reads as fc3b). Fuel a real-budget play turn: mean 50,010 ->
48,022, p90 86,250 -> 85,950 (the gates cap heavy turns either way).

**Dropped:** fc3-routes (afea1852, round 1: lower-bound fields; exact in decisions but +1,044 OOF in the A/B,
mostly long loops); fc3-fight's lazy guard (0a4c638b, round 3: not exact once the query cap binds after an owed
guard; -0.05%). The workers' measured drops are in their sections.

**Best open leads for a future campaign** (from every section):
- **Topology runaways** are now the top games every round (gen-topo-necks-1101807004-a 547, topo-shortcut, -duel,
  -backdoor, -gatehouse): banking / make_way deadlocks in dead-end corridors ("What drives the q set's ... OOF runs"),
  walk_on's unguarded 6x search after descend fails, queue-phase loops. A behaviour fix (who backs off), then a cheap
  lower bound to prove a search fails.
- **Round 1** (5.3k, unchanged since round 2): world init ~75-90k (static_camps ~45-55k on 180-member maps, crossings
  and the draft plan 16-25k, init_beliefs 15-18k), the farm opening ~140k, plan decode on unindexed plans.
- **Fight turns**: one cover cache keyed on a Safety generation (~5M on the fight set), settle skips, the early-end
  checks in one pass, a one-fighter play_quiet and early-end check; want_home and the step guard need fewer sims.
- **Camp maps**: clear_fire's re-sort after deaths in 24+ member groups (12.9k on 78% of the remaining camp-heavy OOF
  turns), stand_reach's first build (12.7k, could be warmed in the queue), find_members 5.9k and crew_work 8k on most
  camp-heavy OOF turns, camp_cast's per-member reads.
- **Tracking in rounds 2-10** (6.9k a turn): share the dasher lineage's walk-only growth; skip prunes provably beyond
  view.
- **Gates**: farm-partial-evaluation (1.77M firings) needs banking's group loop bounded; comms-stale-vision and
  farm-no-route lost before only on rounds 1-10, which this campaign made cheaper: worth retrying one at a time.

## Baseline mirror A/B (orchestrator)

`astraeus-fc3b` against itself, real budget, own drafts, `maps/fresh-11000..11019` (10,240 games, 4m19s;
`MAIN/replays/batch-20261101-060516-ab-fc3-mirror-fresh-110*`). **54,610 OOF turns per bot** (target <= 27.3k).
- By round: 1 10,456 (19%: about one a game), 2-10 5,944, 11-60 7,734, 61-300 9,919, 300+ 20,557.
- Champion-game run sizes: <10 36,880, 10-49 13,116, >=50 4,614. Phases: decide ~60%, queue (late finish) ~38%.
- Long single-game runs dominate some suites: gen-wild-1101406239 1,188, gen-fortress-1101902231 997,
  gen-topo-gatehouse-1101507306 776, mut-elk-arena-1101201809 254, gen-topo-island-1101706600 290,
  gen-serpentine-1101604500 265; gen-fuel-stress-* 130-300 each; mega-groups 50-240.

## Farm evaluation (worker; branch fc3-farm)

Target: the farm-partial-evaluation gate (`room()` in farm.cc's loop). Result: not removable yet; exact cuts below.

**Profile** (100M, debug copies with raw `fuel()` laps by group class and phase; q set unless named). Before:
the first turn's call was prologue 24k + loop 152k + post 30k; of the loop, strong groups reaching `plan_crew` 102k
(6.9 a call at 14.9k: clear 3.8k, plan 5.7k, crew bound 1.2k, facts, steps). Later non-banking calls: loop 42k,
of it planS 13k (2.4 groups), crew bound 7.4k, claimed 6.7k; banking calls 51k. Round 1 at 100M: world ~95k
(build_static 46k, static_camps 24k, init_beliefs 12k), decide 229k, farm ~206k of it.

**Why the gate fired so much.** The prunes' bounds for strong groups (quill, 731863dd) priced a crew as our whole
part at the whole team's speed. A crew of output O pays our part S/O and clears no quicker than F S/O (F our
fastest), so the value is at most rate(w S/O, T + F S/O). That falls with O in the plain ratio, and the rated form
peaks at O = S F / sqrt(T (h + T)) (h the rate's horizon): `crew_rate`. With it most strong groups are pruned
before their clear; across 74k plan_crew calls none beat the bound (measured in a debug copy).

**Commits** (each byte-identical at 100M on wide 52/52, oof 48/48, mg 24/24, q 48/48, big 32/32):
- 0e057315 strong-group bounds by `crew_rate` (pre-facts rated bound, the opening's unweighed bound, beaten_near,
  the value prune; a winning capture keeps part 1 at the team's speed; the crewable branch's bound over
  O in [S + claimers, all]).
- 478c0454 the claimed (joined) group bound: the share is rate(w S r / H, trip + r) in its rounds r <= H / (S +
  others): it peaks at r = sqrt(trip (h + trip)); 247's bound took the whole share at no clear time.
- 2d38adbe `camp_in_reach`'s board as `square_dilate(camp_tiles, range)` (~14 whole-board ops) instead of a
  `draw_chebyshev` per member (~7k on the first turn of a 70-group map). Fires in every first farm call.
- 8470d2fc `recall_line` on the first turn: when no enemy's possible tiles are within Strike::max_reach +
  threat_radius, credible_enemy_may_hit_within cannot hold, and its foes (~1.5k each) are not built. In an
  out-of-line function so later turns' codegen stays (inline it cost +40-67 fuel a later turn).

100M against the baseline, after 8470d2fc (total over identical games):

| set | identical | total | mean | p90 | p99 | max | over 100k | round 1 mean / max |
|---|---|---|---|---|---|---|---|---|
| wide | 52/52 | -2.96% | 54055 -> 52488 | 86904 -> 86590 | 116496 -> 108634 | 320361 -> 320365 | 5694 -> 3989 | 255471 -> 217075 / 531617 -> 412563 |
| oof | 48/48 | -4.51% | 56519 -> 54041 | 90348 -> 88075 | 193140 -> 155539 | 594115 -> 674773 | 20818 -> 16036 | 333174 -> 237728 / 887490 -> 458495 |
| mg | 24/24 | -3.92% | 61719 -> 59397 | 95340 -> 90501 | 175378 -> 146351 | 401771 -> 368253 | 9415 -> 7318 | 329263 -> 226254 / 625380 -> 322727 |
| q | 48/48 | -8.25% | 69654 -> 63931 | 113316 -> 101047 | 227093 -> 166134 | 517013 -> 444056 | 43157 -> 30046 | 319115 -> 260616 / 722721 -> 611103 |
| big | 32/32 | -3.76% | 60334 -> 58113 | 88007 -> 87363 | 131958 -> 120620 | 290573 -> 338440 | 6866 -> 4463 | 294034 -> 237726 / 451383 -> 387834 |

Round 1 by commit, mean (q / oof / mg / big / wide): base 319 / 333 / 329 / 294 / 255k; 0e057315 266 / 243 / 233 /
244 / 221k; 478c0454 same; 2d38adbe 265 / 241 / 230 / 242 / 220k; 8470d2fc 261 / 238 / 226 / 238 / 217k.

Dearer turns: a few tens a set by 30-100k, in early-mid rounds (r16-70) on mega-groups, the-pack, dungeon,
topo-duel. The bounds skip strong groups' clears (min_camp_damage's sorted build) in the calls that no longer
need them; the next call that weighs the group (often a banking call) builds it. gen-dungeon-600102424 r35-36 went
590k -> 675k (oof set max); big set's max 291k -> 338k is gem-flood r24. Both far over any budget already.

**Real budget** (indicative: 24-52 games, runs of lost turns dominate). After 0e057315: OOF wide 595 -> 617, oof 894
-> 798, mg 386 -> 335, q 2678 -> 2480, big 151 -> 133; fpe 14657 -> 11439, 20466 -> 18291, 7888 -> 6874, 70312
-> 57403, 20116 -> 17356; farm-no-route -30 to -45%. After 478c0454, OOF rose on q (4097) and mg (694): the rise
is in four games that entered two-turn loops (gen-dungeon-989402413-b 6 -> 786: exactly 50 run-outs every 100
rounds from r200, each after a static-descend shortcut, i.e. the double route search; topo-shortcut-989706930-a 16
-> 536; mut-the-pack-600201800-b, 600101820-b), while others fell.
Final (8470d2fc) against base-*-real: OOF wide 595 -> 1273, oof 894 -> 860, mg 386 -> 348, q 2678 -> 3747, big 151 ->
127; without games of 150+ run-outs on either side wide 442 -> 448, q 1021 -> 791 (others unchanged); round-1 turns
at the 200k cap 43 -> 21, 104 -> 72, 49 -> 36, 85 -> 63, 41 -> 34; fpe 14657 -> 12298, 20466 -> 17262, 7888 ->
6280, 70312 -> 53213, 20116 -> 16056; farm-no-route 508 -> 590, 1262 -> 877, 556 -> 338, 3373 -> 1858, 766 -> 443;
turn-order down on four sets. Wide's rise is one game, 01boss-battle-b (6 -> 636; 682 -> 2000 rounds), in the
banking two-turn loop the quill notes describe; q's are gen-topo-island-986606600-b (2 -> 684) and
gen-topo-shortcut-989706930-a (19 -> 536), the same loop shape. The 10k A/B should judge.

**Gate removal** (a copy with `room()` true and the two in-loop field breaks gone, on 478c0454): real-budget OOF
wide 3264, oof 7718, mg 3039, q 15296, big 2491 (4-18x). Not removable. Census (q, real budget, current bot): of
888 first run-outs, the innermost scope is farm.post 30% (the walk after the loop: the reserve the gate keeps is
too small for the searches that follow), act_end 17%, route 10%; farm.loop is 27% of the self fuel on run-out
turns. Round 1 (61 of 244 turns run out; all "late" turns): world 74k (91k on run-outs), farm 68k (prologue ~20k,
loop 32k cut by the gate, post 16k); run-outs in farm.post 23, siege_kite (hops / ally_spawn_field on shared-gem
maps) 18, farm 6, turn_order 5. So the opening cannot evaluate in full on 200k while world init takes ~75-90k.

**Remaining farm cost** (later calls, q, after these commits): loop ~32k a non-banking call: plan_crew'd strong
groups 8k (1.6 x 5k: plan 2.4k, crew bound 1k, clear/facts/steps), pre-facts prunes 9.5k (~18 groups at ~470:
segments room 10, loop head 51, early skips 68, prune conditions 112, worth/fastest 58, rated_below 175), claimed
groups 7.6k (op: crew_work + plan_crew each), steps 4.4k. Prologue 6k (prices 2.4k, recall/home trip 2.1k), post
13k (route search). The first turn: prologue 24.5k (recall_line 8.4k before 8470d2fc, attack_in_range 7.2k before
2d38adbe, prices 8k, the lead decode and order ~7k), loop 86k (3.3 strong groups to plan_crew at 13.6k: with every
ally available on the first turn plan_crew prices up to 5 crews), post 30k (attack tiles 6.7k, route).

Dropped (exact, measured at 100M, identical replays):
- Trips lower bound for the crew bound (our trips with every available ally in the pool at the least damage,
  via share_damage, read only when one trip would rule the plan out): total -7.51 -> -7.45% q, -4.06 -> -3.93%
  oof, every set slightly dearer: it rarely prunes (crew values are mostly well under the bound for other reasons).
- A "dense" stop: the tail's most worth per health point bounds every full-health non-winning group's value at
  sup over F' of rate(d F', T + F') (alone, partner and crews are all in that family). The tail's densest group (gem
  clusters) makes it loose: pre-facts prunes 12.65 -> 12.29 a call; totals -8.26 -> -7.54% q, -2.96 -> -2.40% wide.
- recall_line's pre-check inline (8470d2fc's first form): round 1 the same, but +40-67 fuel on every later turn.

Open items:
- Two-turn loops after static-descend (route search, not farm) dominate the small real-budget benches' OOF.
- World init on the first turn (~75-90k at the real budget) leaves the opening ~110k; the farm opening is ~140k.
- plan_crew repeats the crew bound's claimer and crew_available loops (~0.5k a plan call): pass the list in.
- Pre-facts prunes ~470 a group: mostly fixed per-iteration work; a leaner path might save ~100 a group (~2k a call).
- The opening's plan_crew with every ally available (5.1k a strong group): a crew bound over the discrete outputs
  the plan can reach (prefix sums of available allies by distance) instead of the continuous range.
- Banking calls weigh ~28 groups each. A banking pre-facts prune (trip >= steps - bank_now, the altar cycle >= its
  walk out + capture, both at crew_rate, under max(best, from_altar)) is exact but mixed: q -8.25 -> -8.33% (p99
  166k -> 158k, over 100k -399), oof -4.65%, mg -4.03%, but wide -2.96 -> -2.62% and big -3.76 -> -3.63%: most
  banking groups fail it, so its ~100-150 a group is mostly waste. Dropped; a cheaper first test might keep it.

## Route search and pathing (worker; branch fc3-routes; its code dropped in merge round 1)

**Why routes fail on the q set.** A debug copy logged every failed fresh search in `route_around` with the distance
from us to its goals over the terrain alone, over terrain + live camps, and over all walls but allies (q set, 100M,
48 games): 150k failed searches, ~870M fuel (4.3% of the set's total). By what cut the goals off:
- terrain (goals off our walking region: farm targets reached only by dash or crystal, dashers' static fields that
  cross holes): fp1 (farm.post's attack-tile search) 31.5k, cheap (2.3k mean); static descend 5.3k at 6k;
- live camps (a camp holding a neck): fp1/fp2 25k at 4.1k; topo-odd-spawn-986807107 has a champion standing at
  (10,15) all game, 4 steps from its goals by terrain, cut off by camps, both searches every turn;
- the cap: the live walk is more than the cap (best_steps + 16, or the static field's steps + 16, then x6) even
  before units: static descend 8.3k at 9.2k, its 6x retry 2.4k at **21k**. topo-backdoor-987806707: the field says
  14 steps, the walk round the camp in the backdoor is 146, so both searches (~30k) fail every turn all game.
  far-spawns: farm's attack-tile and adjacent searches fail by 0-10 steps over their cap on every turn of the walk;
- allies in necks (topo-necks, dungeon, close-spawns) 14k at 5-9.5k; enemies / the pack zone 25k at 6-14k.
Half of all failures repeat the previous round's (same goals, same tile).

**Kept (afea1852): route bounds from fields over the terrain and live camps.** Every route's walls hold
`blocked_for_us` and `live_camps()`, so a field over those alone (W) bounds its steps from below. For the goals of
a failed search that cost more than `cut_worth` (chunks x (20 + layers) >= 4000), the turn-end queue makes such a
field as deep as its fuel pays for (`warm_route_bounds`, right after `prepare_next_turn`); `route_around` reads it
before a fresh search (only when a slot exists and the search could be costly). Exact because: a walk through camps
dead since the field was made first enters one, d, from a labelled tile (or from d if a goal), so it is at least
that label + 1 + dist(d, us) (up to 8 dead camps, else no bound); respawns only add walls. Past cap + 10 the search
fails and labels none of the tiles make_way reads (only past an ally beside us, within 9 steps: label_through's
line), so it is skipped; with no ally beside us (occupancy board) past the cap suffices. `route_exhausted_` is
set only when the bound is unreachable (a wider search could not succeed either); a finite bound leaves it false,
which only lets static descend's 6x retry run (it fails too, and make_way stays inert). A slot that bounds nothing
for 20 rounds is dropped (each slot costs every costly search a board comparison).
- 100M, byte-identical on all five sets (wide 52/52, oof 48/48, mg 24/24, q 48/48, big 32/32). Total +0.04 / +0.07 /
  +0.05 / **-0.30** / +0.15%; mean 54055->54074, 56519->56559, 61719->61750, 69654->69441, 60334->60426; p99
  116496->116527, 193140->193024, 175378->175446, 227093->227288, 131958->132050; over 100k 5694->5706,
  20818->20836, 9415->9420, **43157->42741**, 6866->6874; round 1 +0.0% everywhere (+120). Most turns pay +6-10
  (the queue's check and codegen), costly searches ~40 more.
- Real budget (bench, indicative): OOF wide 641->623, oof 1054->1002, mg 467->404, q 2833->2657, big 209->199;
  static-descend q 4972->4627, big 213->150; siege-route-fuel q 400->391; comms-stale-vision q 7203->6297;
  turn-order q 11199->9581; farm-no-route q 3373->3592.
- A/B against the baseline, real budget, own drafts, 16 new suites (`mapgen suite --seed 7731-7746`, 8192 games;
  CAND / REF): OOF 45408 / 45163; without games where a bot ran out 100+ times 37062 / 37264. A 300-map topology
  suite (12 presets x 25, seeds 881001-881025: 600 games): 2760 / 2642, one map's side-A loop is +491 (both bots
  loop there, by side). **Noise floor**: a copy of the baseline that only spends ~20 more fuel a turn gave 46461 /
  45644 (36623 / 36905 without runaways) and 2661 / 2662: the change is level within noise on OOF.

**Dropped (measured):**
- An eager test of the goals against our terrain region (foot() or regions flooded in the queue) before every
  search: cut the q set's terrain failures but cost every search two board ops (+46-100 a heavy turn on the other
  sets, +0.06-0.16%). The kept fields cover repeated terrain cuts.
- Fields made on the hot turn once the goals failed on two earlier turns (as deep as the cap + 11): q -0.86 to -1.4%
  at 100M, but the 8192-game A/B without runaways rose 37198 -> 37700 (+1.3%; rounds 11-60 +2.7%).
- Failed searches kept per goal set (two records, each with its labels) and reused while the walls changed only off
  the tiles they reached and their neighbours (exact, 100M identical): the topo-island loop below 572 -> 145 OOF on
  its own, but +0.3-0.7% fuel on oof/mg/big and A/B 38826 / 37362 without runaways, 2834 / 2582 on the topology suite.
- static-descend gate removed (on the bounded searches): q OOF 2536 -> 3990, mg 411 -> 558, big 226 -> 275. The
  capped search it guards still fails and is followed by the 6x one; kept.
- farm-no-route and comms-stale-vision removals not retried: the searches farm.post runs after its check are still
  two (fp1, then fp2 on the same check) and fail on the loops below; comms is World::observe, not a route.

**What drives the q set's and the topology maps' OOF runs (leads, not route search):**
- **Stuck champions.** topo-island-881015 (`mapgen gen topo-island --seed 881015`), side A: champions 0, 1 and 3
  carry 15/49/8 gems in the bank branch from round ~140 to the end (1,700 rounds) at (91,27), (92,27), (91,28): a
  1-wide dead-end corridor north of the 2-thick wall that cuts the home island off. Champion 0's farm.post searches
  (attack tiles, then adjacent) fail every turn because the other two stand in the corridor (13.4k each), then the
  turn runs out: 364-619 OOF a game depending on divergence. Champion 2 meanwhile holds 141 gems at (97,0). Both bots
  do it. A make_way / banking deadlock to fix in behaviour; worth a probe of who should back off.
- **Kite on shared-gem maps** (gen-wild-1101406239, the mirror A/B's worst game, 1,008 OOF here): `kite()` rebuilds
  its stations from every member of a big group each turn (~30k: draw_square, member_attack_tiles, groups_near and 9
  station squares per member) and then `cast_at_camp` -> `camp_cast` (an sdk_camp read per member plus best_ground,
  ~40-46k), with no fuel check between: a champion standing at its station runs out every other turn. The stations
  depend only on the group's live members, nearby groups' live members and our facts: exact to cache by camps
  version.
- **Queue-phase loops**: gen-topo-shortcut-773406900 side A (both bots, 450-1,235 OOF): champion 1 in the bank branch
  runs out in the queue every other turn ("OOF r queue"); not reproduced under the census (chaotic).
- Round 1 world init (round-1 OOF are the farm worker's): static_camps costs ~45-55k on 180-member maps
  (topo-shortcut-987206909: 182 members, 86 groups: `groups.resize` 6.2k, ~100 a member, ~250 a group's epilogue);
  crossings + the draft plan read ~16-25k; init_beliefs ~15-18k. Every champion pays it; the draft bot (10M fuel,
  1 KiB) cannot carry the layout.

Open minor items: fp2 (adjacent tiles) could be skipped after fp1 failed when every member is alive and on no bush
(its goals are then a subset of fp1's) and fp1's make_way found no ally within the cap (~5-13k a stuck turn, rare
elsewhere); `step_towards_funded`'s cap from the fuel left spends everything to end_reserve when a siege route fails.

## Merge round 1 (merge agent)

fc3-farm (0e057315, 478c0454, 2d38adbe, 8470d2fc) merged into fuel3-orch; fc3-routes (afea1852) dropped.

**Review.** 0e057315: rate(w / k, B + F / k) = w h / (k B (h + B) + F (h + B) + B F + F^2 / k): the denominator is
convex in k with its minimum at F / sqrt(B (h + B)), so clamping that k to [lo, hi] gives the maximum. B always
holds capture_rounds (>= 1), so rate's max(rounds, 1) clamp never binds. The partner bound it drops is the k = (S +
P) / S member of the family (the partner is a living ally, so P is in the team's output). The plain ratio w S / (O T +
F S) falls with O. Crew outputs in [S + claimers, all] and clears >= F S / O are the assumptions 262's bounds already
made. The crew_rival_factor (0.8) only lowers the value. 478c0454: r / ((t + r)(h + t + r)) peaks at r^2 = t (h + t);
for t + r < 1 the clamped rate rises in r, so the argmax is max(r*, 1 - t), capped at health / (S + others); the
actual r = health_left / output is no larger, under the same claimer set the old bound assumed. 2d38adbe: camp_tiles
is set for every member (world.cc), and square_dilate gives Chebyshev r like draw_chebyshev; padding is never read.
8470d2fc: list_enemies takes alive visible or tracked enemies; strike reach is clamped to max_reach (compute_strike,
widened); visible enemies at e.pos are already handled by `line`'s first loop, so the new check covers only tp_dest
(acts_from). The skipped foe builds are lazy caches that a later reader rebuilds from the same beliefs.
afea1852 (routes): the skip is exact in decisions. label_through reads tiles at most 9 steps from us through ally
tiles, and those tiles are walkable in the cut field's walls (died camps within 10 are refused), so their labels are
>= bound - 9 > cap. It is not exact in state, though. In the dry or enclosed cases a finite bound leaves
route_exhausted_ false and pocket_at_ unset, so static descend's 6x retry runs as an extra failing search, which
costs fuel only. Moot: dropped on the A/B.

**100M** (all identical; same numbers as the worker's):

| set | identical | total | mean | p90 | p99 | max | over 100k | round 1 mean / max |
|---|---|---|---|---|---|---|---|---|
| wide | 52/52 | -2.96% | 54055 -> 52488 | 86904 -> 86590 | 116496 -> 108634 | 320361 -> 320365 | 5694 -> 3989 | 255471 -> 217075 / 531617 -> 412563 |
| oof | 48/48 | -4.51% | 56519 -> 54041 | 90348 -> 88075 | 193140 -> 155539 | 594115 -> 674773 | 20818 -> 16036 | 333174 -> 237728 / 887490 -> 458495 |
| mg | 24/24 | -3.92% | 61719 -> 59397 | 95340 -> 90501 | 175378 -> 146351 | 401771 -> 368253 | 9415 -> 7318 | 329263 -> 226254 / 625380 -> 322727 |
| q | 48/48 | -8.25% | 69654 -> 63931 | 113316 -> 101047 | 227093 -> 166134 | 517013 -> 444056 | 43157 -> 30046 | 319115 -> 260616 / 722721 -> 611103 |
| big | 32/32 | -3.76% | 60334 -> 58113 | 88007 -> 87363 | 131958 -> 120620 | 290573 -> 338440 | 6866 -> 4463 | 294034 -> 237726 / 451383 -> 387834 |

**Real budget** (base -> m1; JSONs `MAIN/replays/fuel/fc3/m1-*-real.json`):

| set | OOF | OOF, games < 150 | round-1 turns at 200k | farm-partial-evaluation | runaways (150+) |
|---|---|---|---|---|---|
| wide | 595 -> 1273 | 595 -> 448 | 43 -> 21 | 14657 -> 12298 | 01boss-battle-b 636, gen-chambers-102206117-a 189 |
| oof | 894 -> 860 | same | 104 -> 72 | 20466 -> 17262 | none |
| mg | 386 -> 348 | same | 49 -> 36 | 7888 -> 6280 | none |
| q | 2678 -> 3747 | 1042 -> 791 | 85 -> 63 | 70312 -> 53213 | topo-island-986606600-b 684, topo-shortcut-989706930-a 536 (new); backdoor, mega-groups, far-spawns (both) |
| big | 151 -> 127 | same | 41 -> 34 | 20116 -> 16056 | none |

**A/B** (fresh-11000..11019, own drafts, real budget, 10,240 games each; `MAIN/replays/ab/fc3-m1{,r}/`):

| | win % (95% CI) | OOF cand / ref | round 1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ |
|---|---|---|---|---|---|---|---|---|
| mirror (fc3b) | 50 | 54610 | 10456 | 5944 | 7734 | 9919 | 20557 | 36880 / 13116 / 4614 |
| m1 (farm) | 50.5 (49.6-51.5) | 43359 / 55116 | 5668 | 3849 | 6886 | 9034 | 17922 | 28681 / 12323 / 2355 |
| m1r (+ routes) | 50.6 (49.6-51.5) | 44403 / 55238 | 5700 | 3869 | 6941 | 9160 | 18733 | 28679 / 12761 / 2963 |

m1 is -20.6% against the mirror (target -50%): round 1 halves (one run-out every ~2 games now), runs of 50+ halve,
and 300+ falls 13%. Routes on top: +1,044 OOF, mostly 300+ and runs of 50+ (long loops). Dropped.

**For round 2.** Round 1 is still 5.7k OOF, the biggest single bucket after 300+ (world init ~75-90k at the real
budget; farm opening ~140k). 300+ (17.9k) and 61-300 (9.0k) are now 62% of OOF: the long two-turn loops (banking
deadlocks in dead-end corridors, kite station rebuilds on shared-gem maps, queue-phase loops), which routes' NOTES
trace, are the lead. The small benches' wide and q OOF are dominated by a few runaway games: judge on the A/B.

## Map-size and camp-count scaling (worker; branch fc3-scale, round 2)

Baseline `astraeus-fc3-m1`. Sets: the five standard ones, plus **fs** (`fsset.txt` here, 12 gen-fuel-stress maps from
suites outside fresh-11000..11019, 24 games, own drafts against m1) and, for real-budget OOF only, **fs2**
(`fs2set.txt`, 40 more, 80 games). Own-draft sets were run against `variants/astraeus-fc3-m1` (the merge's m1
JSONs used fc3b as opponent; the 100M numbers agree).

**Profile of a fuel-stress turn** (100x100, ~224 groups, ~454 members; m1, 100M): mean 112k, half the turns over
100k. The farm loop is ~95k of a non-banking call: ~170 groups a call end in the later-turn pre-facts prune at
~350 fuel each (the bound's arithmetic and conditions, not the loop's bookkeeping: the same code in a separate
scalar pass still cost ~290 a group, and a gather of its inputs alone ~120). Banking calls (farm_turn<false,true>)
have no pre-facts prune and weighed ~135 groups at ~1k each (~148k a call). The rest of a turn: world update ~10k
(camps 5k), the claimed path ~5.5k a claimed group, full evaluations 3-5k a group. Round 1 at 100M is ~560k:
build_static 238k (static_camps 140k; the plan's steps decode 54k, as these maps' plans have no fixed-width index;
crossings 28k for dashers), init_beliefs 40k, update 17k, decide 262-334k.

**Commits** (each byte-identical at 100M on wide 52/52, oof 48/48, mg 24/24, q 48/48, big 32/32, fs 24/24):
- 3c054fd2 world init: static_camps' member loop keeps a group's sums in v128 lanes (~150 -> ~100 fuel a member),
  CampGroup's fields the build writes lose their initialisers, CampBelief is made with its health slices.
  Round 1 -2 to -4k on the standard sets, -23k on fs.
- df97d3aa farm: an upper bound on each group's pre-facts prune bound, from per-map tables in f32x4 lanes (~15 fuel
  a group): worth at most the unweighted gems and gold (weights <= max_exposure; negative prices as 0), trip at
  least the Chebyshev distance (or the recall from as close), clear and crew only lengthen the trip or shrink our
  part; every float op of rated_below is monotone and a 2e-4 slack covers the worth's other summation order. A
  group under best_value is skipped where the prune would `continue`. Excluded: wins, strikers within
  help_radius, claims, our last choice, held crews; off for Ren, crystal hops, no strength; on the first turn only
  with 128+ groups (below that the opening pass cost more than it saved: q round 1 +2.4k). Catches ~98% of the
  prune's groups on fs.
- 6169356f farm: stop_from's table built from per-map prospected gems/gold and spawn distances, not zero-filled.
- 0cc0a1a9 farm, banking calls: the same pass prices each group's value bound (trip >= Chebyshev less bank_now)
  and its altar-cycle bound (walk out >= nearest altar's distance less the tribute range, or recall + Chebyshev
  from spawn); a group under min(best, from_altar_value) with its cycle under from_altar_value changes neither,
  so nothing later groups compare with moves. Kited groups (the risky pick), claims, our claim and last choice
  are never skipped. Altar distances are computed on the first banking call.

**100M after 0cc0a1a9** (against m1): total wide -0.55%, oof -0.96%, mg -1.03%, q -1.78%, big -1.31%, **fs -18.4%**
(mean 111957 -> 91271, p90 167472 -> 126408, p99 238893 -> 189031); round 1 mean wide 217075 -> 215536, oof
237728 -> 234252, mg 226254 -> 222593, q 260616 -> 257575, big 237726 -> 235403, fs 560539 -> 516395. Many turns
are a few tens of fuel dearer (the pass on calls where it skips little, codegen); maxima +1-3.5% (single heavy
turns: oof 674773 -> 698117, big 338440 -> 348454).

**Real budget** (m1 -> after; OOF / round-1 turns at the 200k cap): wide 1273 -> 566 / 21 -> 18, oof 1872 -> 838 /
72 -> 71, mg 1310 -> 351 / 36 -> 26, q 3654 -> 2140 / 63 -> 60, big 131 -> 111 / 34 -> 30, fs 2365 -> 1691 / 134 ->
134, **fs2 (80 games) 6317 -> 4449** (farm-partial-evaluation 162k -> 112k). The m1 baselines' wide/oof/mg/q include
runaway games (mut-the-pack 982, 01boss-battle 636, ...) the candidate did not repeat: the small sets' OOF is
indicative. After df97d3aa alone fs2 was 3995 (noise between runs is several hundred).

**Dropped (measured):**
- The exact pre-facts bound priced for every group before the loop, scalar (same expressions): +6 to +8% on fs:
  ~290 a group, as dear as the in-loop prune, and paid for every group. Gathered inputs + f32x4 math: about
  level: the gather alone ~120 a group (11 loads from three AoS structs).
- The per-map tables in one buffer vs separate vectors: no change.

**What remains:**
- fs OOF stays mostly in farm evaluations that outrun the loop's reserve (single groups' first facts and clears
  of 30k+: census --trace stretches after `room()`), in the claimed path (~5.5k a claimed group) and the queue:
  the farm gate's own work, not map scaling.
- Round 1 on fs cannot fit 200k (world ~270k + decide); every fs round-1 turn still runs out. On typical maps
  world init is ~70k at the real budget (q): static_camps ~21k (a member ~100, a group ~200 of plain code),
  update ~15k (enemies' track and update_champion ~1k each), init_beliefs ~11k (beliefs ~100 a group,
  ChampionBelief construction ~750 each), plan decode 6-13k, crossings 6-16k (dashers), static_boards 6k.
  No piece left is over ~20k on a typical map; each further cut is a few k.

**Open minor items:**
- Plan steps decode on unindexed plans (fs 54k on round 1, ~240 a group): the altar codes could be skipped and
  decoded on first read (~20 a group; drafted_.end still needs the walk past them).
- static_camps' per-group epilogue (~200: flags, centre with two divisions): perhaps ~50 a group with lanes.
- pre_prune_upper's per-map tables cost ~22k on their first call on fs (~100 a group); ~5k could go.
- decode_enemy_steps' full decode (~150 a group) on the first later home_ground of an unindexed plan.

## Runaway loops (worker; branch fc3-loops)

Target: single games where one champion runs out every turn or every other turn for hundreds of rounds. Baseline
m1 (`astraeus-fc3-m1`); its 10k A/B against fc3b (`batch-20261101-0757*-ab-fc3-m1-*`).

**What the runaways are.** Consecutive streaks (OOF turns at most 3 rounds apart) of 15+ in that A/B: m1 1,449 turns
(gen-wild-1101406239's kite 902, farm 501), fc3b 2,809 (banking 1,480, mostly fortress-1101902231's 953). The other
"runaway" games are frequent, not consecutive, run-outs. bench.py against `variants/astraeus-fc3b` reproduces the A/B
games exactly (m1 vs m1 does not: different opponent).

**Tracing without divergence.** Phase labels set inside `debug_block` (a `QP(name)` macro that writes `fuel_phase()`
only while `round_number()` is still the turn's, so `OOF r <label>` names the step that ran out rather than the last
phase the resumed turn reached) left 27/28 real-budget games byte-identical to m1's; FuelMeters and the census
diverge. With them: every OOF in the streak games was in `decide` (the usual `OOF r queue` label is the resumed
turn's), and in the 1,471 run-outs of champion-games with 40+ OOF: farm.post's second search (fp2) 568, walk_on's
`step_towards(Field)` (its capped search, then the unguarded 6x one) 217, elsewhere in decide 304, after farm 141.
A copy with the labels plus `printf`s of fuel inside `debug_block` still diverged on gatehouse maps.

**Kept, 4c1d7355: kite's stations and productive step.** gen-wild-1101406239 (shared gems, 23-member group): a
ground caster at its station paid stations 30k (5 whole-board ops and ~11 squares a live member), the camp cast
~10k, and on 7 turns in 8 (spell on cooldown) `kite_productive_action` ~70k (targets 10k, ~9k of damage() per
endpoint over all 22 members) to conclude "stay": 132k a turn at 100M, a run-out every other turn. Now (exact):
- the station boards (threat, near, basic, attackers) are kept while the group, our ranges and station kind, and
  which members live (ours, and those of the other groups the loop consulted, which are the same while ours are)
  stay; the prepare loop is skipped then too (prepared tiles are never dropped). `basic &= goals` now writes a
  separate board so the kept one stays whole. A first version keyed every member's neighbour groups (+20k on round 1
  of gen-wild-1101506214); recording the groups the loop reads costs ~1.3k on a miss.
- kite_productive_action prices only members within reach + 1 of us (the endpoints are within 1); whether any live
  harmful member exists still decides the early exit.
gen-wild-1101406239 real budget 1,188 -> 21 OOF (100M play -25%); gen-wild-1101506214 11 -> 8.

**Kept, 2affa588: fp2 reuses fp1's failure.** farm.post searches the attack tiles (fp1), then the group's adjacent
tiles (fp2), after a fuel check that reserves one search. A champion stuck behind allies (gatehouse's 1-wide spawn
strip, a 1-wide corridor head-on, topo-island's dead end) fails both every turn and runs out in fp2 every other
turn (m1 vs fc3b gatehouse-1101507306-b c10: 151 of 155 run-outs in fp2, at (59,65) for 250 rounds). `route_around`
already reused the latest failed search for equal goals, walls, tile and cap; `step_towards_within` (fp2 only) also
accepts goals within its goals: a search from fewer goals labels no tile lower, so it fails too. Exactness:
make_way / labelled_ally_beside read the labels only for allies beside us; when every such ally off the goals has
no label under the failed search's labels, it has none under ours (labels only rise), so they decide the same
(else the search runs). route_exhausted_ and pocket_at_ may differ but are read only after the next search
(pocket_at_ is an exact shortcut); failed_ and route_field_ stay consistent. The flag is set by an RAII guard
(a StaleTurn throw must clear it) and the subset test is out of line: inlined, the flag stores and the redo after a
non-inert borrow cost +0.07% at 100M (+3.7k on standoff turns that redid route()'s walls).

**100M** (m1 -> 2affa588; oof/mg/q/big against `--opp variants/astraeus-fc3-m1`, my own m1 runs; wide against
MAIN's m1-wide-100M): all identical, wide 52/52 +0.02%, oof 48/48 +0.00%, mg 24/24 +0.01%, q 48/48 -0.19% (p90
101047 -> 100343, max 444056 -> 435845), big 32/32 +0.03%; round 1 +0.0-0.1%. The +0.01-0.03% is ~20 fuel on
non-firing turns (the out-of-line call). Runaway set (16 maps, m1 vs m1): 32/32 identical, -1.21%, p90 -2.0%.

**Real budget** (OOF; m1 / kite only / both):

| set | m1 | 4c1d7355 | 2affa588 | notes |
|---|---|---|---|---|
| wide | 1273 | 1273 | 1273 | 01boss-battle-b 636 (banking loop) unchanged |
| oof | 1872 | 1778 | 1773 | mut-the-pack-600201800-a 982 in all |
| mg | 1310 | 1313 | 1303 | same |
| q | 3654 | 3654 | **2270** | topo-island-986606600-b 674 and topo-shortcut-989706930-a 536 gone |
| big | 131 | 131 | 119 | |
| runaway maps, m1 vs m1 | 3138 | 1968 | 2697 | new: topo-shortcut-1100006923-a 162 -> 459, gatehouse-1101507306-b 431, the-pack-1101701851-a 219 |
| streak maps vs fc3b | 1319 | 1319 | 2318 | new: gatehouse-1101507306-a 1328 (c4, farm group 30, r661-1942) |

The fp2 commit is exact at 100M but its real-budget effect is mixed: the loops it targets end (q -38%), and new
ones appear in chaotic games (gatehouse maps both times; a labelled copy diverges there, 117-234 OOF, so the new
loop could not be traced). The m1 game's fp2 loop and the new c4 loop are on the same gatehouse spawn strip. Judge
it alone in the A/B; 4c1d7355 is safe on its own.

**Remaining runaways, explained (not fixed):**
- Head-on in a 1-wide corridor (topo-shortcut-1101306909-b, m1 vs fc3b, c5/c7 at (4,70)/(4,71), r910-1135): both
  dashers, both live searches fail at their caps because the walk round is far longer than the dash field says, so
  make_way's labels never reach the adjacent ally and neither backs off. Every turn c5 runs fp1 9k, fp2 11k,
  walk_on's capped search, then the unguarded 6x search (no fuel check), where it runs out. Behavioural (who backs
  off when no label reaches the ally); TODO's held gap-deadlock fix is the nearby work.
- Gatehouse spawn strips: allies queue on the 1-wide spawn row; whichever champion is behind fails its searches
  every turn. Same behavioural root.
- walk_on's `step_towards(Field)`: after the capped search fails and descend fails, a 6x-cap search runs with no
  fuel check (`wide` when the failure is deferred, else the guarded one); 217 run-outs above. A cheap exact
  "fails" proof needs a lower bound on the walk (routes' terrain fields, dropped on its A/B).
- Farm loop + post at ~95-100k on stuck turns: the loop runs to its reserve (one search), the post then runs 2-4.
- fc3b's banking loops (fortress 953, necks, backdoor, dash-lattice) do not appear in m1's games of those maps.

Dropped: keying kite's neighbour groups on every member (+20k round 1); re-running `route()` after a non-inert borrow
(+3.7k a turn in standoffs); `[[gnu::noinline]]` on the wrapper alone (no codegen change).

Open minor items: walk_on's 6x search has no fuel check and runs after descend fails (a fixed-cost bound, not a gate,
would need a cheap lower bound); camp_cast reads every member with an sdk_camp call (~6.8k for 14 visible members on
wild) where only those within the spells' reach can be hit (members out of reach still decide `sole_finish`, so an
exact cut must count them).

## Merge round 2 (merge agent)

fc3-scale (3c054fd2, df97d3aa, 6169356f, 0cc0a1a9) and fc3-loops (4c1d7355, 2affa588) merged into fuel3-orch; all
kept. Frozen: `astraeus-fc3-m2` (m1 + scale + kite, without 2affa588) and `astraeus-fc3-m2f` (+ 2affa588, = the
merged bot). JSONs `MAIN/replays/fuel/fc3/{m2,m2f}-*.json`, m1 on fs/fs2 `m1-fs*-*.json` (all against fc3b).

**Review.**
- 3c054fd2: lanes 0/1 of `sums` add health and strength in member order from 0, as the scalar sums did; `most`'s
  lane 2 is the int max of reach from 0; `at`'s lanes 2/3 sum x and y (int32 is ample; mean by int division as the
  long one for non-negative sums); `extra`'s monolith lane sums 0/1, read only as != 0. The 16-byte stat store spills
  4 bytes into the next member's first word, which that member's own record store overwrites later (the spare covers
  the last). Every CampGroup field losing its initialiser (gold, gems, cluster_*, respawn, strength, health, reach,
  has_monolith, map_) is written in the build loop for every group made; `groups.resize(lookup)` only shrinks, and
  nothing else constructs a CampGroup. CampBelief's new constructor keeps the default member initialisers.
- df97d3aa: against the later-turn prune (`rated_below(worth, soonest, fastest, crew)`) and the opening's
  `unweighed_beaten`: worth is at most max(0, gems + max(0, per_gold) gold + max(0, tribute) gems) (same sum order;
  the kept facts' weighted worth has weight <= 1 and the 1.0002 slack covers rounding); soonest >= near, and the
  recall form >= max(channel, channel + hurt + spawn_near - value) (FarmRecall::rounds with arrive at least that);
  fastest >= 0 and the crew form's k >= 1 only lower rated; the partner term is a conjunct. rated() is monotone op by
  op. Excluded as inf: wins (gems >= short_by), strikers within help_radius (covers may_help whatever help_steps is),
  claims, farm_group, claim/mono when not prunable; gate requires !banks_bag, !hop_any, reflect <= 0, tight (later)
  or rated (opening). The skipped prune's only side effect is the fastest-clear memo (keyed by version and strength).
- 6169356f: every `Most` entry is written before `most` is read; the per-group reach table matches the inline
  expressions.
- 0cc0a1a9 (banking): a skipped group's value is rate(worth * part <= worth, trip + ...) with trip >= max(0, steps -
  bank_now) (bank >= 0; steps >= Chebyshev, dashers' fields count a crossing as a king step), so < best_value and no
  tie; its from_altar candidate has walk_out = min(centre_to_altar, recall + spawn_steps) >= min(nearest altar
  Chebyshev - submit_gems_range (tribute_tiles is that square), recall + spawn_near). Help, takeover and shared/risky
  paths are off in banking or excluded (claims; kited = shared_gems && big_group, the same predicate). In a pocket
  without hops steps from here is unreachable anyway.
- 4c1d7355: the station boards read static data (positions, reach, member_attack_tiles = viewers & open_for_us,
  never dropped), the ranges and station kind (keyed), our live set (all members when respawning) and the noted
  neighbour groups' state/health > 0 (keyed; they are the same groups while our live set is). On a hit the prepare
  loop would return true for every member (all prepared at the miss), so ground/unit stations stand; a miss whose
  preparation failed is not kept. `basic_goals` leaves `basic` whole; nothing else writes threat/near. In
  kite_productive_action, members beyond max(attack range, the slot's damage range) + 1 never pass any endpoint's
  range test, and dropping them keeps the order of the rest (argmax ties unchanged); `any` reproduces the empty test.
- 2affa588: fp2's goals within fp1's, same tile, walls and cap: fewer roots label no tile lower, so fp2 fails too.
  make_way reads labels only for allies beside us off the goals (allies on goals open without labels); within_failed
  requires all of them unlabelled under fp1's labels (no guard skip, so more conservative), hence under fp2's, and
  make_way returns false either way. route_exhausted_ may differ but nothing reads it before the next search
  (step_towards(Field)'s read follows its own search); pocket_at_ may be set where it was not, and its use is the
  exact `enclosed` proof. failed_ keeps fp1's goals: a later equal-goal reuse is the pre-existing exact one.

**100M** (m2f against m1; m2 the same within 0.02%, all replays identical for both):

| set | identical | total | mean | p90 | p99 | max | round 1 mean |
|---|---|---|---|---|---|---|---|
| wide | 52/52 | -0.53% | 52488 -> 52211 | 86590 -> 86557 | 108634 -> 108686 | 320365 -> 320369 | 217075 -> 215538 |
| oof | 48/48 | -0.95% | 54041 -> 53527 | 88075 -> 87664 | 155539 -> 153092 | 674773 -> 698121 | 237728 -> 234302 |
| mg | 24/24 | -1.02% | 59397 -> 58793 | 90501 -> 89270 | 146351 -> 144986 | 368253 -> 373899 | 226254 -> 222671 |
| q | 48/48 | -1.98% | 63931 -> 62664 | 101047 -> 98300 | 166134 -> 165199 | 444056 -> 440628 | 260616 -> 257737 |
| big | 32/32 | -1.28% | 58113 -> 57371 | 87363 -> 87267 | 120620 -> 120369 | 338440 -> 348454 | 237726 -> 235402 |
| fs | 24/24 | -18.38% | 111957 -> 91290 | 167472 -> 126463 | 238893 -> 189080 | 729061 -> 739867 | 560539 -> 516396 |

m2 -> m2f at 100M: q -0.20% (max 448839 -> 440628), others +0.01-0.03%.

**Real budget** (m1 -> m2 -> m2f; OOF / round-1 turns at 200k / farm-partial-evaluation):

| set | OOF | OOF, games < 150 | r1 at cap | fpe | runaways (150+), m2f |
|---|---|---|---|---|---|
| wide | 1273 -> 566 -> 567 | 448 -> 566 -> 567 | 21 -> 18 -> 18 | 12298 -> 10989 -> 11171 | none |
| oof | 860 -> 675 -> 665 | same | 72 -> 72 -> 72 | 17262 -> 14647 -> 14698 | none |
| mg | 348 -> 234 -> 233 | same | 36 -> 26 -> 26 | 6280 -> 5836 -> 5834 | none |
| q | 3747 -> 2429 -> 1840 | 791 -> 810 -> 795 | 63 -> 60 -> 60 | 53213 -> 50806 -> 56022 | mega-groups-986608207 a/b 258/204, backdoor-987806707-a 203, far-spawns-988604903-b 203 |
| big | 127 -> 112 -> 105 | same | 34 -> 30 -> 30 | 16056 -> 16272 -> 16384 | none |
| fs | 2367 -> 1671 -> 1673 | 2186 -> 1671 -> 1673 | 134 (all) | 48906 -> 36142 -> 36164 | none |
| fs2 (80) | 6314 -> 4561 -> 4522 | 5778 -> 4561 -> 4522 | 441 (all) | 162952 -> 110545 -> 110004 | none |

**A/B** (fresh-11000..11019, own drafts, real budget, 10,240 games each, against fc3b; `MAIN/replays/ab/fc3-m2{,f}/`):

| | win % (95% CI) | OOF cand / ref | round 1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ |
|---|---|---|---|---|---|---|---|---|
| mirror (fc3b) | 50 | 54610 | 10456 | 5944 | 7734 | 9919 | 20557 | 36880 / 13116 / 4614 |
| m1 | 50.5 (49.6-51.5) | 43359 / 55116 | 5668 | 3849 | 6886 | 9034 | 17922 | 28681 / 12323 / 2355 |
| m2 | 50.4 (49.5-51.4) | 41943 / 57280 | 5228 | 4186 | 6591 | 8240 | 17698 | 28453 / 11022 / 2468 |
| m2f | 50.5 (49.5-51.4) | 40457 / 56707 | 5223 | 4157 | 6500 | 7945 | 16632 | 28412 / 10511 / 1534 |

m2f is -25.9% against the mirror, -6.7% against m1 (target -50%). The reference side (the same bot) read 57,280 and
56,707 in the two runs: noise of ~600-800 a run. **2affa588 kept**: -1,486 against m2, mostly runs of 50+ (-934) and
300+ (-1,066), win rate level; its q bench -589. gen-wild-1101406239 (1,188 OOF in m1's A/B) is out of the top games
in both (kite). Shortcuts in the A/B (m1 -> m2f; fc3b ~2.60M fpe): farm-partial-evaluation 1,948,706 -> 1,821,949,
step-guard-entry 295,456 -> 290,824, comms-stale-vision 197,703 -> 192,548, turn-order 153,252 -> 149,465,
farm-no-route 63,252 -> 59,361.

**For round 3.** Biggest buckets: 300+ 16.6k (41%), 61-300 7.9k, 11-60 6.5k, round 1 5.2k (unchanged by this round
outside fs: every fs round-1 turn is over 200k). m2f's top games: gen-topo-shortcut-1101306903-a 290,
gen-topo-backdoor-1100306703-b 279, mut-the-pack-1101701851-b 186, gen-topo-shortcut-1100206938-b 181,
gen-topo-odd-spawn-1101707100-b 154, gen-topo-duel-1100007207-b 152, gen-mega-groups-1101108200 a/b 147-148,
gen-fuel-stress-1100108400-b 138: topology loops (head-on corridors, walk_on's unguarded 6x search, backdoor's
146-step walk round a camp) and mega-groups. step-guard-entry (~290k firings) is the second shortcut after fpe.

## Every-turn audit (worker; branch fc3-audit, round 3)

Baseline `astraeus-fc3-m2f`. Read World::update and what it calls, Safety's common queries, turn order, comms,
main.cc's skeleton and the turn-end queue against cambc-rules.yaml, asking whether each read can have changed, is
read, or is repeated. Profiled with raw `fuel()` laps inside `debug_block` (one `PF` line a turn; scripts in
`/tmp/fc3/audit/`), oof set at 100M, turns after round 1.

**Where an every-turn's fixed cost goes** (m2f, oof, per turn, 57.7k mean): decide 35.3k (the act skeleton:
approach 391, ward 341, lock 341 (only while a lock is carried), strike_after 242, heal+shield 190, see_revealed 129,
count_use 100, recall 78), queue 9.2k (spare fuel only), world update ~9k: camps 2.9k (visible-tile step 466,
settled checks 582, update_camp's members 542 in live groups, 249 in cleared or respawning ones, group loop 595), allies 1.77k, enemies read 1.08k,
track 1.05k, rank_turns 0.74k, priorities 0.69k, altars 0.37k, vision 0.28k, scores 0.16k; set_turn_order 1.4k,
observe (turn end) 0.77k, comms receive 0.38k / send 0.30k, play_turn's prologue/epilogue 0.3k each.
Inside a visible champion's read the emblems (~120 each) were the largest piece.

**Kept** (each byte-identical at 100M; totals per commit on oof / mg, cumulative):
- 7c895dad: an ally's kept recall (World::update_champion) from the state and channel time already read, not a
  second record and channel-time read (allies feint a recall every turn end, so nearly every visible ally paid them).
  -0.04% / -0.04% (~20 a turn).
- 36735f95: a champion's emblems are read again only when its max health, Strength or Focus moved since the last
  read (and a Prism's gems, whose Focus follows them); Tavi always. Exact by the rules: items change only by buying
  a shard, which adds that stat's growth (every growth is positive; an emblem forms from bought shards), or by Tavi's
  sales on its spawn; a Health shard raises max health wherever it is bought. Cumulative -1.08% / -1.04% (~560 a turn on oof: allies
  -380, enemies -130). Campaign 2's skip (no shop possible: last and current tile beyond 6 of the spawn) applied to
  25-50% of reads and was level; this key holds on nearly every read after the first.
- 27805f63: Safety::find_members and refresh read a camp member's stun buffs before its tile's visibility (the
  read fails out of sight, as cheaply as the tile test; the test then only confirms a rare stun): one host call
  instead of two a visible member. Cumulative -1.11% / -1.07%.
- ef7d2305: update_camps keeps the camp-tile view as a byte per tile, toggled by the tiles of the xor with last
  update's view, instead of listing every visible camp tile at each change (most moves); camp_settled and update_camp
  read members' tiles from it instead of a host Bitboard_Test each; a group a tile left is looked over once
  afterwards. Cumulative -1.46% / -1.56%; round 1's view step +158 (the first view is listed in full, as before).

Final (all four), 100M against m2f's JSONs, every replay identical:

| set | identical | total | mean | p90 | p99 | max | over 100k | round 1 mean |
|---|---|---|---|---|---|---|---|---|
| wide | 52/52 | -1.11% | 52211 -> 51628 | 86557 -> 86483 | 108686 -> 107550 | 320369 -> 319097 | 4001 -> 3777 | 215538 -> 215791 |
| oof | 48/48 | -1.46% | 53527 -> 52742 | 87664 -> 87515 | 153092 -> 151889 | 698121 -> 697407 | 14508 -> 14089 | 234302 -> 234573 |
| mg | 24/24 | -1.56% | 58793 -> 57873 | 89270 -> 88578 | 144986 -> 143583 | 373899 -> 371993 | 6914 -> 6684 | 222671 -> 223066 |
| q | 48/48 | -0.91% | 62664 -> 62090 | 98300 -> 97703 | 165199 -> 164558 | 440628 -> 439738 | 27081 -> 26403 | 257737 -> 258068 |
| big | 32/32 | -0.65% | 57371 -> 56999 | 87267 -> 87232 | 120369 -> 119824 | 348454 -> 348273 | 4296 -> 4201 | 235402 -> 235783 |
| fs | 24/24 | -0.53% | 91290 -> 90797 | 126463 -> 125523 | 189080 -> 188379 | 739867 -> 740042 | 18830 -> 18438 | 516396 -> 516960 |

Round 1 rises 250-570 (0.1-0.2%): in the oof profile the allies' read +206 (every first emblem read also builds
its key), the view step +158, and play_turn's prologue and the pre-update lap +150-270 with no code change there
(unexplained; codegen or static layout). Profile of the final bot (oof, later turns):
-758 a turn, world update allies 1771 -> 1393, enemies 1082 -> 952, camps 2.9k -> 2.6k.

Real budget (indicative; games diverge): OOF wide 567 -> 517, oof 665 -> 716 (mut-the-pack-600201800 +50,
gem-drought-600105820 +45, the rest mixed), mg 233 -> 237, q 1840 -> 1800, big 105 -> 122; farm-partial-evaluation
11171 -> 10590, 14698 -> 13748, 5834 -> 5157, 56022 -> 49309, 16384 -> 15636; comms-stale-vision down on all five.

**Dropped.**
- A camp member read dead in a live group not read again for 40 rounds (it returns only with its group: capture
  3+ rounds, respawn 40+): exact, but +10 fuel a turn on oof/mg (no measurable saving; camp_health on a dead camp is
  a cheap failing read).
- The first camp-view version: a per-group member mask from a tile-to-member index built in StaticMap::build (+1.7k
  on round 1, ~6 fuel a member), then lazily on a group's first sight (+1.1k on round 1 for the index and per-group
  counts). The byte-per-tile view needs no index: round 1 +158 on the view step, later turns slightly less saved
  than the masks (mg -1.53% vs -1.75% with the masks and the stun order) for a third of the round-1 cost.
- A visible-group count per group (zeroed on first sight) to tell a group left view: dearer on round 1 than looking
  over the left groups' members once.

**Checked and necessary (later audits need not repeat):**
- read_vision, tributing_enemies, update_scores, update_altars: a few host calls each; altars' 365 is mostly guard and
  loop overhead.
- read_priorities: both reads are needed for a champion in sight; only the current priority of one read last round
  after it acted equals last round's next_priority (one host call, ~30-40 a turn: minor).
- rank_turns: runs only for a stale side, and in fights (our bot and the mirror set danger-based priorities) both the
  current and next orders change most rounds.
- update_champion: the record, cooldowns (casts out of sight), channel time (only while channelling), shield (only
  inside a cast's duration), gems (captures, kills). The stun buff read: a side with no stunner picked can never be
  stunned (exact, picks known from round 1), but our draft opens with Prism, so it never fires. Out of view: the
  liveness read could be skipped until 60 rounds after the last alive read for a champion known dead (respawn
  60-61): ~1 read per dead champion-turn, minor.
- update_camps: a settled group's witness awake read is the only damage detector (asleep implies undamaged); an awake
  group's members need health and awake reads every turn (anyone's damage; the 2-phase sleep timer is unseen);
  group_state only for groups in view and not settled. The awake-camp occupancy board (57) does not beat per-member
  reads at these counts.
- observe at turn end: the prune of unseen tracked enemies by the post-move vision changes next turn's growth, so it
  is needed; sharing it within a lineage would save only the board_empty (a copy costs as much as the and).
- set_turn_order (1.4k on oof): live_self/enemies 250, offer_kills+heal 256, plain_priority 385 (danger, tie_hit),
  may_escape 290, offer_escape ~60; strike() is memoised. may_escape's !seen case could return false early when no
  enemy can be within Strike::max_reach (offer_escape then offers nothing), but that skips a refresh() whose camp stun
  reads tie_hit then uses, so it is not exact.
- comms: receive/send are mostly run()/guard overhead and a few host calls.
- Safety::find_members: already lane-vectorised for big groups; the stun read is the per-member host cost (fixed above).

**Open leads.**
- Tracking in rounds 2-10: 6.9k a turn on oof (observe 2.0k) against ~1k later: every enemy is tracked from its spawn,
  lineages split by dasher, and a dasher lineage pays a widen_by_dash field and two dilates a turn. (a) A non-dasher
  lineage fixed at the same moment grows exactly as a dasher lineage's `undashed` (walk-only, same land): copying it
  saves a dilate (~10 board ops) a turn while both exist. (b) A prune or growth whose possible set is provably beyond
  our view (a Chebyshev extent kept through every change to `possible`: fixes, the recall's spawn, teleports, comms
  sightings) is a no-op on `unseen_`. Both need care with undashed_all and the lineage bookkeeping.
- Priorities: the current-priority read for a champion read last round after it acted (~30-40 a turn).

## Fight turns (worker; branch fc3-fight, round 3; its code dropped in merge round 3)

Baseline m2f (`astraeus-fc3-m2f`), opponent fc3b. Sets: the five standard ones and a **fight set** (the 10
`maps/gen-s1/*arena*`, 01elk-arena, adgato-gemcombat5, gen-atoll-600101912, gen-gem-drought-600105820,
gen-monolith-only-600101500; own drafts, 30 games; list in `/tmp/fc3/fight/fightset.txt`). Scripts and diffs in
`/tmp/fc3/fight/scripts/` (prf*.py add `debug_block` laps; *_sum.py tabulate them).

**Where late run-outs go now** (census `--fine --trace`, real budget):
- Fight set: 198 OOF-first (300+ 48%, 61-300 30%); 88% ran a strike search (54k inclusive: read 14k, grow 17.6k,
  price 17.6k); Heart of Ruin 60% of them. Innermost scope: strike_search 28%, farm 18%, act_end 11%, siege_kite 8%,
  turn_order 6%. 84% of traced run-outs passed no fuel check (the search has none).
- A late set (21 maps drawn from m2f's A/B games with 8-30 late first-in-streak run-outs, no topology or
  fuel-stress maps): 776 OOF-first, 54% with no visible enemy; decide-level farm 45%, strike_search 13%, act_end 11%,
  carry_bag 7%. Fight signatures (want_home/channels + search, retreat) are ~32%; the rest is farm's.
- m2f's A/B: 300+ first-in-streak run-outs are spread over 3,432 games (~4 each) beyond the topology runaways.

**Profile at 100M, fight set** (8.5G fuel, 191.6k turns; every table from debug laps, replays identical):
- Strike search 554M (6.5%), 25.9k searches, mean 21.4k. Searches of 30k+ (4.7k, mean 47.5k): the guard worked out
  in pricing 17.5k (on 66%, 26.5k there), the cover or Willow's guard in read_geometry 6.9k, grow 7.7k, pricing's
  loop 3.9k, foe loop 2.9k, blows 2.5k.
- Step guard: 71k resolutions, 283M. In the search: r1 5.9k at 13.2k (Willow's coverless guard ~3.4k of them at
  10.6k), r2 (dash ready) 1.6k at 29.8k; elsewhere r1 2.2k, r2 3.4k mean. Only 83 turns work out two guards. An r2
  placing in the search that reaches the per-tile loop (850) costs 44.7k: exact looks 16k (Reach::at ~1k a tile x
  foe), the final loop's sims and lethal 13.5k, U1 8.1k, bound pass + fight_enemies_any 5.4k; U1 won (740) 12.9k.
- want_home: 154k calls (80% of turns), 861M (10%), mean 5.6k: lethal 1.5k, stand 1.8k, outmatched 0.6k,
  camp_trapped 0.6k, recall_line 0.5k. Heavy calls (>= 20k, 4.8%): stand's sim 12.7k, lethal 6.3k (first touches of
  Reach, threats and members the search reuses), stand's setup 3.1k. continue_recall (66% of turns, 928M) is
  want_home plus ~1.6k (recall_to_bank/shop 0.9k, cancel 0.5k, game_ender 0.2k).
- Shared cores: trade() 309M (3.6%; 68.6k sims at 4.5k; ~19.7k on turns heavy in these), Reach::at misses 133M (591
  each), Reach::build 115M (980 each). Safety rebuilt mid-turn (see_stuns, see_again) on 2% of turns; the rebuilt
  generations' members/threats/Reach/fights cost 1-3M each over the set: not a lever.
- Grow ~1.2k a node for every type: HoR 7.5k at 6.5 nodes (settle 612 a call x4.3, own work 505 a node: child Node
  and health copies, legality; group_landings 1.1k x0.6, land_at 0.35k), Vendetta 7.0k at 6.9.
- read: the Search ctor and prologue ~1.3k, viewers 0.8k, per-foe fields ~0.4k, terrain grid 1.15k.
- Turns over 100k (2,032; census at 100M): search 49.6k where present (86%), chase 27.8k (54%: prey's sims and a
  capped route), farm 21.3k (74%), walk_on 16k (40%), channels 18k (70%), stand 10.5k, lethal 6k, world 11.8k.

So a fight turn is many distinct consumers (want_home's stand, the search's tree and pricing, the guard's looks and
sims, prey, the goal's route), each mostly first-touch work the others reuse; no fight is simulated twice in a turn
(campaign 2: 0.1% same-turn repeats) and no Reach is rebuilt but on the 2% of turns that rebuild Safety.

**Kept, 0a4c638b: the lazy pricing guard.** A tile the deferred guard may cover is priced before the guard is
worked out; only a tile not cut needs it (a cut one is dropped whether guarded or not). Exact because: the loop's
order is the old one up to the first such tile on top (where the old code resolved); best_total only moves on a
tile not cut, which now resolves first, so later tiles price alike; the query cap counts a cut tile's queries only
once the guard shows it unguarded (`waiting`), and when the sum could reach the cap the guard is worked out and the
same tile taken again, so the cap binds where it did; t.total/t.bound of a dropped tile are unread (done, not
exact). A guard the search owed but never needed is left skipped (`Pathing::skip_guard`), as route() leaves one,
so settle_guard works it out before Safety changes (Safety reads frozen beliefs until refresh/see_stuns/see_again);
decide no longer settles a skipped guard that guard_steps replaces at once (nothing reads it in between).
- 100M identical: wide 52/52, oof 48/48, mg 24/24, q 48/48, big 32/32, fight 30/30. Fight set total -0.05%, p99
  106412 -> 105704, over 100k 2496 -> 2439; in-search resolutions 7561 (127M) -> 6708 (108M), settled later
  2070 (4.6M) -> 2255 (11.3M). Other sets: wide -0.01%, oof -0.02%, mg +0.00%, q -0.00%, big +0.01% (p99 wide
  108686 -> 108520); every set's other turns pay ~5 more (codegen).
- Real budget (indicative): OOF wide 567 -> 570, oof 665 -> 629, mg 233 -> 252, q 1840 -> 1836, big 105 -> 105,
  fight 330 -> 269; step-guard-entry 2879 -> 2821, 6225 -> 5230, 2055 -> 1222, 1400 -> 1267, 401 -> 388,
  4709 -> 4775; prey-cut-short about level.
- Why only ~15% of in-search resolutions go: in most a tile the cover holds survives pricing (the tiles nearest
  the enemies price best), and a guard skipped by the search is settled at decide whenever we attacked or cast
  without being re-placed.

**Dropped (measured):**
- Walk-only search (campaign 2's lead): a ranged champion with its walk unspent and no visible foe within
  strike_free's bound (walk included) offers only the start tile's leaf and the walk's (every other node is owed a
  strike), so read could skip the foes' strike fields, spells, members and landings and grow could settle the two
  leaves. 22% of searches on fight and oof sets (5.7k each, mean 15k). Exact (30/30), but -0.06% on top of the lazy
  guard at best: grow -5.2M and read about -6.4M on those searches, while strike_free's longer path cost the other
  12.5k ranged searches ~300 each (+4M) even with distances tested before record reads; a radius-1 cover for these
  searches moved Reach builds later in the turn (net -0.01%). Diff `/tmp/fc3/fight/walk-only-attempt.diff`.
- Willow's coverless guard (10.6k a search, 36M on the fight set) under the lazy scheme with an implicit cover of
  her 8 neighbours: not tried in code. Her guard is needed whenever her search moves, and settled whenever she heals
  or attacks in place without moving, so almost none would be skipped.
- Per-tile step guard for the search: the guard's answer for one tile depends on the unions U1/U2 over all exposed
  tiles (U2 needs every tile's exact look, the 16k) and on the sorted settle order; only the final loop's sims for
  tiles after the asked one could be saved.

**Open items (estimates):**
- Settle skip when nothing can read the old guard (no move, no dash left): try_move tests the guard before it
  checks the walk, and siege.cc:316 reads it at our own tile, so every caller needs an audit; bounded by the 11.3M
  of settles on the fight set.
- trade() at 4.5k a sim is ~20k on heavy fight turns; a 30% faster exact sim (same float order) is the one shared
  cut that would move want_home, the guard and prey at once. The early-end checks (~640 each, 2.3 a sim) loop the
  AoS fighters four times; a single pass gathering their sums would keep each float sum's order.
- Grow's own work ~500 a node is spread thin: skipping `h = saved` after a walk, reset or plain dash child (exact:
  those change no health and every grow returns with h as it found it) saved 15 a search (fight set 30/30
  identical, -0.4M), so the copies are not it; settle's per-tile offers (~50-80 a tile) are the larger part.
- The cover is computed by the search, again inside step_guard (GuardFoes ctor ~1.2k a placing in the search) and
  by route() after restore_guard resets route_cover_round_: one cache keyed by the deferral would save ~1-2k on
  fight turns that route after the search (~5M on the fight set from the step_guard rebuild alone).

## Merge round 3 (merge agent)

fc3-audit (7c895dad, 36735f95, 27805f63, ef7d2305) merged into fuel3-orch, all kept. fc3-fight's code (0a4c638b)
dropped; its NOTES kept above. Frozen: `astraeus-fc3-m3` (m2f + audit, = the merged bot). JSONs
`MAIN/replays/fuel/fc3/m3-*.json` (against fc3b, as m2f's).

**Review.**
- 7c895dad: `channel == recall` is set exactly when the state read contains `recalling` (tested first), which is
  kept_recall's first test; the channel time it read again is the one read above. A failing read gives nullopt and
  false, where kept_recall's `ok()` would have thrown, but the read is of a visible champion and does not fail.
- 36735f95, against the rules. The items read feeds only `engine::emblems()`: home, durability, jungle, tribute,
  capture, prospector and the damage factors (Skirmish, Monster, Collectors' distinct families); no consumable
  count is read from it (teleport crystals and locks are not read from a champion's items anywhere), so buying or
  using a crystal or lock, which moves no stat, changes nothing the cache holds. Items change only by (a) a shard
  bought (economy.shards: it adds that stat's growth; every champion's growths are positive; emblems form only from
  shards, so a new emblem, Power's and Bruiser's extra stats and Greed's 35 included, comes with a stat rise; a Health
  shard raises max health wherever bought, healing only on spawn), or (b) Tavi's sales on spawn (Tavi always read).
  Nothing lowers max health, Strength or Focus otherwise: deaths keep items, no buff touches Strength, Ryth's
  Strength follows max health (a rise either way), Heart of Ruin's passive scales damage, not the stat (a rise only
  re-reads). Prism's Focus is the one stat that falls (gems: a capture, kill or tribute); with its gems in the key,
  Focus at equal gems moves only with Focus shards (3 shards x 8 = 16 gems x 1.5 would otherwise cancel). Float
  adds of growths at these magnitudes never round away. The key is first -1 (a first read always reads), and an
  enemy unseen while shopping is read on its first sighting with changed stats. Exact.
- 27805f63: camp_stunned is a pure read that returns false on failure (no throw); `&&` of two side-effect-free
  tests commutes.
- ef7d2305: `seen` = visible & camp_tiles, so the xor covers every change to the view, whatever its cause (our move,
  our ward, a ward placed this turn, bush clusters, dead camps' tiles: camp_tiles is every member's spawn tile, static).
  camp_tile_seen starts zeroed and the first update lists `seen` whole (as before); `before` is swapped on every
  call, and nothing between the toggles and the swap can throw. A group's bit is set by any tile entering; one a
  tile left is cleared once and re-set after all toggles if any member tile remains (members = the tiles with
  group_at = g, the same table). camp_settled and update_camp, the only new readers, run inside update_camps after
  the toggles, with `visible` unchanged. Tiles<2 x (17x17 + 13x13)> bounds the xor (each view at most one cast).
  Maps without camps take the `first` path every turn with an empty `seen`.
- 0a4c638b, **dropped**: not exact in one path. The old loop resolved the guard when a maybe-guarded tile first came
  on top; the new one does not when that tile is then bound-stopped (camp damage) or cut without a query (a shield
  with no strikers), so `owed` is set but `maybe_guarded` stays. If the 10-query cap then binds, the old code had
  maybe_guarded == 0 and skipped the capped block, so guarded tiles not yet done were priced by the
  "unpriced tiles keep their Strike price" loop and could be chosen; the new code enters the block, resolves the guard
  and marks them done. Arguably the old path is the bug (a capped search may pick a guarded end), but it is a
  behaviour change, the replays did not exercise it, and the gain is -0.05% on the fight set (~0 elsewhere): dropped
  per the brief's default. To redo exactly: on `owed`, resolve in the capped block without marking (or fix the old
  path first as its own change, A/B'd). The worker's other arguments held (query cap equivalence via `waiting`;
  Safety reads frozen beliefs until refresh/see_stuns, so settling later reads the same inputs).

**100M** (m3 against m2f, every replay identical):

| set | identical | total | mean | p90 | p99 | max | round 1 mean |
|---|---|---|---|---|---|---|---|
| wide | 52/52 | -1.11% | 52211 -> 51628 | 86557 -> 86483 | 108686 -> 107550 | 320369 -> 319097 | 215538 -> 215791 |
| oof | 48/48 | -1.46% | 53527 -> 52742 | 87664 -> 87515 | 153092 -> 151889 | 698121 -> 697407 | 234302 -> 234573 |
| mg | 24/24 | -1.56% | 58793 -> 57873 | 89270 -> 88578 | 144986 -> 143583 | 373899 -> 371993 | 222671 -> 223066 |
| q | 48/48 | -0.91% | 62664 -> 62090 | 98300 -> 97703 | 165199 -> 164558 | 440628 -> 439738 | 257737 -> 258068 |
| big | 32/32 | -0.65% | 57371 -> 56999 | 87267 -> 87232 | 120369 -> 119824 | 348454 -> 348273 | 235402 -> 235783 |
| fs | 24/24 | -0.53% | 91290 -> 90797 | 126463 -> 125523 | 189080 -> 188379 | 739867 -> 740042 | 516396 -> 516960 |

**Real budget** (m2f -> m3; indicative, games diverge): OOF wide 567 -> 517, oof 665 -> 716, mg 233 -> 237, q 1840 ->
1800, big 105 -> 122, fs 1673 -> 1627, fs2 (80) 4522 -> 4487; farm-partial-evaluation 11171 -> 10590, 14698 ->
13748, 5834 -> 5157, 56022 -> 49309, 16384 -> 15636, 36164 -> 34665, 110004 -> 107167.

**A/B** (fresh-11000..11019, own drafts, real budget, 10,240 games, against fc3b; `MAIN/replays/ab/fc3-m3/`):

| | win % (95% CI) | OOF cand / ref | round 1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ |
|---|---|---|---|---|---|---|---|---|
| mirror (fc3b) | 50 | 54610 | 10456 | 5944 | 7734 | 9919 | 20557 | 36880 / 13116 / 4614 |
| m2f | 50.5 (49.5-51.4) | 40457 / 56707 | 5223 | 4157 | 6500 | 7945 | 16632 | 28412 / 10511 / 1534 |
| m3 | 50.5 (49.5-51.4) | 38820 / 56943 | 5301 | 4013 | 6108 | 7717 | 15681 | 27003 / 9987 / 1830 |

m3 is -4.0% against m2f, -28.9% against the mirror (target -50%). Round 1 +78 (its first reads build the keys and
list the view whole: +0.1-0.2% at 100M); every later bucket fell. Runs of 50+ rose ~300, nearly all one topology
runaway: gen-topo-shortcut-1100206938-b 557 (181 in m2f's). Shortcuts (m2f -> m3): farm-partial-evaluation
1,821,949 -> 1,774,772, step-guard-entry 290,824 -> 279,515, comms-stale-vision 192,548 -> 185,094, turn-order
149,465 -> 141,646, farm-no-route 59,361 -> 57,903.

**For round 4.** 300+ is 15.7k (40%), 61-300 7.7k, 11-60 6.1k, round 1 5.3k. Top games: gen-topo-shortcut-1100206938-b
557, mut-the-pack-1101101822 a/b 270/185, gen-topo-necks-1101407001-a 216, gen-wild-1100006217-a 197,
gen-topo-duel-1100007207 a/b 182/167, gen-mega-groups-1101108200-a 177, gen-topo-shortcut-1100406900-a 132,
gen-hourglass-1100003411-b 125: still topology loops, the pack and mega-groups. fpe (~1.77M firings) and
step-guard-entry (~280k) remain the top shortcuts; the fight worker's profile above puts late fight run-outs in the
strike search (HoR), want_home and trade() (4.5k a sim).

## Camp-heavy maps (worker; branch fc3-camps, round 4)

Baseline `astraeus-fc3-m3`, opponent fc3b. Target: the camp maps' run-outs in m3's A/B (mega-groups 2,322, the-pack
945, big-groups 844, dense-camps 654, cluster-carpets 365 OOF). **tgt set** (`/tmp/fc3/camps/tgt.txt`, 8 maps, 16
games, own drafts): mut-the-pack-1101101822, -1101701851, -1101201805, -1100601891, gen-mega-groups-1101108200,
-1101808209, -1100808212, -1100708211 (paths under `maps/fresh-110xx/`). bench.py against fc3b reproduces the A/B's
games exactly (checked: replay hashes equal).

**Where the run-outs were.** Census (`--fine --trace --lenient`, plus scopes in camp_trapped, find_members, siege,
altar access; scripts `/tmp/fc3/camps/scripts/morescopes*.py`), real budget, tgt set: of OOF turns' self fuel,
clear_fire's sort 10.4% (present on 76% of OOF turns, 12.8k mean), **access_fire 10.0% (50% of OOF turns, 18.7k
mean, max 46k)**, farm.loop 7%, find_members 6% (90%, 6.2k), crew_work 5.5%, update_camps 5%, min_camp_damage's own
pass 4%. access_fire hid under siege_candidate (altars_sealed) and bankable_bag (altar_usable): it was recomputed
every turn per champion: open tribute tiles x stirring groups near altars x every member.

**Kept** (each byte-identical at 100M on wide 52/52, oof 48/48, mg 24/24, q 48/48, big 32/32, fs 24/24, tgt 16/16):
- 963df310 min_camp_damage keeps the slot's sorted clear order when the same members live and every comparison of
  clear_fire's comparator involving a member whose health moved (at most 8) has the same outcome (3-way, on the
  float products): std::sort's permutation is a function of its comparisons' outcomes and the input order (member
  order), and the fire passes read only the order and the living set. The member being cleared is already the
  strict maximum ratio, so later hits on it keep the order; the first hit out of a full-health tie block and deaths
  re-sort. Verified in a debug copy (fresh sort compared on every accepted kept order): 8.6k checks, 0 mismatches.
  Alone, 100M: wide -0.13%, oof -0.09%, mg -0.15%, q -0.07%, big -0.07%, fs -0.05%, tgt -0.37% (p99 -1.0%, over
  100k 2707 -> 2566); round 1 unchanged.
- f4be94a5 access_fire: the fire reads only the open tribute tiles and, per stirring group near them, the members
  that live and may be awake (health > 0, !maybe_asleep). The key is that list (group, active words) plus the open
  board's content (an access rebuild on any camp's death bumps its version but seldom moves the open tiles: compared
  with boards_equal); live words are re-read only when the group's version moved (every health write bumps it,
  monotone). No active member anywhere: every tile's fire is 0 (widens the stirring-empty shortcut). A miss sums
  each tile's reaching members from per-group, per-tile masks made when first read (i8x16 Chebyshev test, 16
  members a vector, box-culled; group threat() is the union of the members' squares, so the masks replace its test),
  by Strength kind with popcounts when every Strength is whole and the active total is below 2^24 (exact in any
  order), else bit by bit in member order (the original's terms in its order). Verified in a debug copy against the
  original on ~87k calls (tgt, fuel-stress, 01yellow-brick-road, 00corners): 0 mismatches.

**100M, both** (against m3's JSONs): total wide -0.09%, oof -0.13%, mg -0.21%, q -0.05%, big -0.06%, fs +0.00%;
p99 107550 -> 107477, 151889 -> 151714, 143583 -> 143285, 164558 -> 164382, 119824 -> 119586, 188379 -> 188097;
over 100k 3777 -> 3731, 14089 -> 13975, 6684 -> 6591, 26403 -> 26326, 4201 -> 4165, 18438 -> 18449. **tgt set:
-2.82% total, mean 57616 -> 55975, p50 -3.7%, p99 130276 -> 122189 (-6.2%), max 243929 -> 234822, over 100k 2707 ->
2033.** Round 1 +0.0-0.2% (oof +441 mean: 01yellow-brick-road's round 1 +12k a champion, where an awake group near
an altar makes the first call build the tables; those turns are 300-390k already). access_fire's first call per
instance on a map costs ~10-14k more than one old call (tables), once.

**Real budget** (indicative; games diverge): **tgt 1482 -> 796 OOF** (mut-the-pack-1101101822 a/b 269/184 -> 68/54,
mega-groups-1101108200-a 174 -> 105, -1100808212-b 71 -> 20, -1100708211-a 66 -> 23; out-of-fuel shortcuts 1511 ->
824, fpe 4149 -> 2867). Census on the tgt set (diverged copies): OOF turns 963 -> 680; access_fire 18.7k on 484 ->
4.2k on 288 OOF turns. Sets (m3 -> both): wide 517 -> 460, oof 716 -> 746, mg 237 -> 257, q 1800 -> 2477
(gen-topo-backdoor-987806707-b 53 -> 550, the known backdoor loop; without it 1747 -> 1927), big 122 -> 138, fs
1627 -> 1633; round-1 turns at 200k unchanged but big 28 -> 29.

**Dropped (measured, all exact):**
- The sort kept across deaths for fewer than 24 living (libc++'s std::sort there is insertion sort / sort3-5,
  stable: brute-forced its small sorts in Python, `/tmp/fc3/camps/scripts/stable.py`): the kept order, dead dropped,
  is the sort's when each adjacent pair is apart in Strength/health by more than the products' rounding (checked in
  double, margin 2^-20) or exactly tied and ordered by fire then member. tgt +0.08%: small sorts are cheap, so the
  check rarely pays.
- The same for 24+ living requiring no equivalent pairs (then the sorted order is unique whatever the algorithm):
  tgt +0.27%, p99 +2.9%: full-health tie blocks are common, and a failed check pays both.
- access_fire with a per-group slot for every map group (vectors, unique_ptrs made eagerly) or all T tiles' masks
  built at once: first calls of 20-70k (mega-groups 155k -> 227k turns); lazy per tile and only for groups with an
  active member fixed it.
- Member lists per (group, tile) summed in member order: a 48-member group by an altar still ~12.6k a miss; the
  popcount-by-kind sum is ~1k.

**Open items:**
- clear_fire's sort after deaths in 24+ member groups (12.9k mean on 78% of the remaining tgt OOF turns): libc++'s
  introsort is not stable, so only a replica of its partition steps could predict it.
- stand_reach's first build (12.7k on 18% of tgt OOF turns, per instance, static per group and range): could be warmed
  in the turn-end queue for the farm choice's group.
- find_members 5.9k on 84% of tgt OOF turns; crew_work 8k on 71%; update_camps 5.1k.
- access_fire's first call (~10-14k once per instance; round 1 on maps with awake groups by altars).

## Fight core: trade() simulations (worker; branch fc3-sim, round 4)

Baseline m3 (`astraeus-fc3-m3`), opponent fc3b. **Method:** a corpus micro-bench. A debug copy dumps every
trade()/turns_to_kill_idle() input (both Sides, the kits and the flags) inside `debug_block`. The dumps come from 8
fight-set games, and every 4th sim is kept, 4,400 in all. A bench copy of the bot replays them in its first turn at a
1G budget. It prints the fuel of each sim, a hash of every Trade field, and a hash of the fields release reads (lost,
self_falls, falls_known, lost_known; turns_to_kill_* are read only by debug output). Each variant takes about a minute.
Scripts are in `/tmp/fc3/sim/scripts/`: patch_cap.py, gen_corpus.py, patch_bench.py, bench.sh, and the prof*.py laps.

**Profile** (corpus, m3: 19.87M, 4.5k a sim):
- Acts take 57%: 28.7k acts, 6.5 a sim. A plain act costs ~330-350, a non-plain one ~370-380, a quiet-branch act ~50,
  and hurt plus Ren ~75. By the acting side's size: 1 fighter 304, 2 fighters 392, 3+ fighters 520.
- Early-end checks take 16%: 1.74 a sim at ~400 each (their_cap 95, short_of 80, the falls_unknown test 80, the
  prefilter 80; overwhelmed 400, but on only 999 checks).
- play_quiet takes 8-10% (6.9k calls at ~250). The loop and entry take the rest.
- Sides are small: 19% of sims are 1v1, and 61% have a one-fighter side. The wasm is already tight; most of the cost
  is the logic itself.

**Kept, 9b198301** (corpus 19.87M -> 19.17M, -3.5%; every Trade field identical). Floats keep their operations and
order.
- play_quiet: each side's quiet end, the damage on each weakest and the two healths are held in locals. Neither side's
  alive, stunned or quiet_* changes inside play_quiet, and nobody falls there. The `s` path writes u.health back before
  lowered() reads it. play_quiet no longer takes ours/theirs by reference; simulate adds the turn deltas instead
  (play_quiet and play_shielded only ever bump them alongside .turn). Before, those references kept both counters in
  memory. -1.6%.
- `NO_UNROLL` on loops over a side's members. Clang unrolled them by 2 with remainder code; sides have 1-3 members.
  -0.7%.
- act<One>: the act of a one-fighter side gets its own instance, in which the loops fold. attack() is forced inline:
  with two instances it stopped inlining, which alone cost +3.5%. -1.2%.

**100M** (sim1 against m3; fight set: m3 benched here, own drafts against fc3b, 30 games):

| set | identical | total | mean | p99 | max |
|---|---|---|---|---|---|
| wide | 52/52 | -0.08% | 51628 -> 51589 | 107550 -> 107404 | 319097 -> 318675 |
| oof | 48/48 | -0.12% | 52742 -> 52679 | 151889 -> 151722 | 697407 -> 697407 |
| mg | 24/24 | -0.15% | 57873 -> 57788 | 143583 -> 142998 | 371993 -> 371993 |
| q | 48/48 | -0.03% | 62090 -> 62074 | 164558 -> 164548 | 439738 -> 439738 |
| big | 32/32 | -0.04% | 56999 -> 56973 | 119824 -> 119762 | 348273 -> 348273 |
| fight | 30/30 | -0.13% | 43517 -> 43461 | 105248 -> 104848 | 361320 -> 360419 |

Round 1 is unchanged. The fight set saved 10.6M, about 3.4% of its ~309M of sim fuel. Dearer turns are a few percent
of turns, from codegen elsewhere.

**Real budget** (indicative only; games diverge): OOF wide 517 -> 492, oof 716 -> 793, mg 237 -> 358, q 1800 -> 1733,
big 122 -> 131, fight 401 -> 370 (m3 benched here). step-guard-entry: wide 2638 -> 2858, oof 7535 -> 5944, mg 3688 ->
2175, fight 4628 -> 4540.

**Dropped (measured):**
- A tighter overwhelmed(): the fewest of their turns n whose basic attacks could take all of ours, then
  overwhelmed(n, n). It fires on 182 of the 4,400 sims, and a scan of every n reaches only 260. Net +4.8%: the extra
  bound costs more on the checks where it fails. In settle mode the result also depends on the path (a later
  full-horizon overwhelmed() sets lost_known), so it was skipped there.
- A "we must win" bound, the mirror: none of ours can fall within k turns, and our basic attacks less their stuns
  outweigh their health, shields and heals. Every one of its 260 firings matched the played-out outcome, but those
  sims are only 5.0% of sim fuel (2.8% at the first check). In falls_unknown mode a later check's exit makes it
  path-dependent, so only need_falls sims qualify. Not built; the cost of its bound would eat most of the gain.
- act templated on Ren (Back): +1.1% (the same attack() inlining loss, before it was found). Hits packed into a 4-bit
  mask: +1.6%. act forced inline into simulate: +3%.
- Willow's blocked heal keeps next_cast <= turn, so her side gets no quiet stretches. It happens on only 527 heal
  attempts in 28.7k acts: not a lever.
- Guard cover cache: not built. route() recomputes the cover after restore_guard, but keying it exactly needs a
  Safety/World version (see_stuns, see_again), and it is worth ~5M on the fight set.

**Open minor items:**
- A one-fighter specialisation of the early-end check and of play_quiet, by the same template trick: est. ~1% of sim
  fuel.
- The cover cache keyed on a Safety generation counter: ~5M on the fight set.
- The other heavy sim callers (want_home's stand, the step guard's U1/U2) need fewer sims, not cheaper ones: the sim's
  remaining cost is its logic, at ~250-500 an act.

## Merge round 4 (merge agent)

fc3-camps (963df310, f4be94a5, 239e305f) and fc3-sim (9b198301, c1c0ab23) merged into fuel3-orch, all kept.
Frozen: `astraeus-fc3-m4c` (m3 + camps) and `astraeus-fc3-m4` (+ sim, = the merged bot). JSONs
`MAIN/replays/fuel/fc3/m4-*.json`; m3 on the fight and camp-heavy sets `m3-{fight,tgt}-*.json` (lists `fightset.txt`,
`tgtset.txt` there). All against fc3b.

**Review.**
- 963df310: order_holds requires the same living set (count equal, and every kept member alive now) and, for each
  member whose health moved, the same 3-way outcome on the comparator's products (sa * hb against sb * ha, the same
  float products in either argument order) against every other kept member, at its old and new health. Pairs of
  unmoved members compare the same values; ties fall to the pre-sort fire, a function of the living set only, so
  the same. With member-order input, std::sort then makes the same permutation (comparisons of an element with a
  pivot copy of itself tie either way). The stored healths are updated, so the invariant "the order is a sort of the
  current healths" carries over chains of keeps. The stored fires (post-sort pass) depend only on order and living
  set. The only reader is min_camp_damage(left, ...), whose non-reflect path does not write; the reflect path takes a
  copy. More than 8 moved, a death, a respawn read or a range change: rebuilt as before. The spare slot resets its
  range when its group changes, so it never keeps across groups.
- f4be94a5: the old fire read a.open, the stirring groups with `near` (static), and per member health > 0,
  !maybe_asleep (awake == awake, and for i < 64 the asleep bit), in_square (static) and strength (static); its
  `threat()` filter is the union of the members' squares (CampGroup::threat), so dropping it is exact. The key holds,
  per near stirring awake group with a live maybe-awake member, its id and those members' words (awake and asleep
  read every call; liveness re-read on a version change: every camp health write, world.cc's update_camp
  `version += hp != health[i]` and restore's `++version`, bumps it, monotone), plus the open board's content
  (compared when a.version moves; a.open is written only by rebuild_altar_access, which bumps it). A group with no
  such member adds nothing in the old sum either. Sums: the per-kind path needs every active group's Strengths whole,
  positive (0-Strength members add exactly +0) and at most 4 kinds, and the float total below 2^24 (a float total that
  rounds stays >= 2^24), so every partial sum is an exact integer in any order; else members are summed by bit, in
  group then member order, the old order. a.open is within the tribute tiles (rebuild copies `tributes` and only
  drops), so the board-order scan finds each open tile. Masks: coordinates < 100 and reaches fit i8; padding has
  reach -1; chunk c's bits land at 16c + j.
- 9b198301: inside play_quiet nothing writes alive, quiet_alive, stunned, quiet_until, quiet_damage or taken (nobody
  falls: each hit is checked to leave health > 0; lowered() writes only `weak`), so their_end / our_end reproduce the
  per-iteration tests (a side not quiet gets end = its current turn and breaks at its first half-turn, as before);
  on_us / on_them are the same products. u.health is written back before lowered() reads it in the camp path, and
  e/u healths and both turns on every exit (the early return became a break). The turn counters were only bumped
  alongside .turn in play_quiet and play_shielded, so simulate's deltas equal them. act<One>, always_inline attack()
  and NO_UNROLL change no operation.

**100M** (m4 against m3, every replay identical; m4c's own numbers are the worker's):

| set | identical | total | mean | p90 | p99 | max | over 100k | round 1 mean |
|---|---|---|---|---|---|---|---|---|
| wide | 52/52 | -0.17% | 51628 -> 51541 | 86483 -> 86465 | 107550 -> 107327 | 319097 -> 318685 | 3777 -> 3697 | 215791 -> 215904 |
| oof | 48/48 | -0.24% | 52742 -> 52612 | 87515 -> 87484 | 151889 -> 151596 | 697407 -> 695669 | 14089 -> 13888 | 234573 -> 235014 |
| mg | 24/24 | -0.36% | 57873 -> 57664 | 88578 -> 88411 | 143583 -> 142446 | 371993 -> 370259 | 6684 -> 6530 | 223066 -> 223151 |
| q | 48/48 | -0.07% | 62090 -> 62045 | 97703 -> 97614 | 164558 -> 164361 | 439738 -> 439901 | 26403 -> 26302 | 258068 -> 258204 |
| big | 32/32 | -0.10% | 56999 -> 56939 | 87232 -> 87225 | 119824 -> 119553 | 348273 -> 348321 | 4201 -> 4156 | 235783 -> 235971 |
| fs | 24/24 | -0.02% | 90797 -> 90780 | 125523 -> 125381 | 188379 -> 188097 | 740042 -> 738889 | 18438 -> 18436 | 516960 -> 517385 |
| fight | 30/30 | -0.20% | 43517 -> 43429 | 84544 -> 84513 | 105248 -> 104714 | 361320 -> 360419 | 2383 -> 2344 | 195939 -> 195983 |
| camp-heavy (tgt) | 16/16 | -2.93% | 57616 -> 55920 | 88016 -> 87544 | 130276 -> 121976 | 243929 -> 234822 | 2707 -> 2024 | 213659 -> 213752 |

**Real budget** (m3 -> m4; indicative): OOF wide 517 -> 452, oof 716 -> 1031, mg 237 -> 539, q 1800 -> 2530, big 122 ->
151, fs 1627 -> 1653, fs2 (80) 4487 -> 4472, fight 401 -> 385, tgt 1482 -> 694. The rises are single runaways:
mut-the-pack-600201800-a 73 -> 360 (in both oof and mg), gen-topo-backdoor-987806707-b 53 -> 550 (the known backdoor
loop; it did the same in the camps worker's bench), topo-island-986606600-a 19 -> 162; OOF in games under 150 fell
(oof 716 -> 671, mg 237 -> 179, q 1004 -> 855). farm-partial-evaluation 10590 -> 11013, 13748 -> 13730, 5157 -> 5088,
49309 -> 49732, 15636 -> 15924; tgt 4149 -> 3777; step-guard-entry fight 4628 -> 4353, oof 7535 -> 6451.

**A/B** (fresh-11000..11019, own drafts, real budget, 10,240 games, against fc3b; `MAIN/replays/ab/fc3-m4{c,}/`):

| | win % (95% CI) | OOF cand / ref | round 1 | 2-10 | 11-60 | 61-300 | 300+ | runs <10 / 10-49 / 50+ |
|---|---|---|---|---|---|---|---|---|
| mirror (fc3b) | 50 | 54610 | 10456 | 5944 | 7734 | 9919 | 20557 | 36880 / 13116 / 4614 |
| m3 | 50.5 (49.5-51.4) | 38820 / 56943 | 5301 | 4013 | 6108 | 7717 | 15681 | 27003 / 9987 / 1830 |
| m4c (camps) | 50.7 (49.8-51.7) | 37799 / 56233 | 5316 | 4047 | 6265 | 7445 | 14726 | 27051 / 9375 / 1373 |
| m4 (+ sim) | 50.8 (49.8-51.7) | 37908 / 55825 | 5316 | 4047 | 6267 | 7533 | 14745 | 27302 / 8940 / 1666 |

Camps: -1,021 against m3, from 61-300 and 300+ and runs of 50+ (the pack and mega-groups leave the top games; round 1
+15, its first access_fire call). **Sim kept**: +109 against m4c, inside the ~600 run-to-run noise (the fc3b reference
side read 56,233 and 55,825 in the two runs), win rate level; its benches are -0.03-0.2% everywhere. m4's top games:
gen-topo-necks-1101807004-a 547 (a new topology runaway, also m4c's top), gen-wild-1100006217-a 197,
gen-topo-duel-1100007207-b 177, gen-atoll-1100501935-b 170, gen-topo-duel-1100407201 a/b 135/167,
gen-topo-backdoor-1100306703-b 145, gen-topo-gatehouse-1101107313-a 144, gen-hourglass-1100003411 a/b 133/134.
Shortcuts (m3 -> m4): farm-partial-evaluation 1,774,772 -> 1,766,494, step-guard-entry 279,515 -> 275,834,
comms-stale-vision 185,094 -> 182,349, turn-order 141,646 -> 141,268, farm-no-route 57,903 -> 57,462.

**Fuel a play turn in the A/Bs** (every play turn of every game, round 1 included, from the replays' team fuel files;
quantiles to 100 fuel; `/tmp/fc3/merge4/fuelstats.py`): mirror fc3b mean 50,010, p50 47,050, p90 86,250, p99 91,750;
m3 48,084 / 44,650 / 85,950 / 91,050; m4 48,022 / 44,550 / 85,950 / 91,050 (fc3b in the same games 50,004 / 47,050 /
86,250 / 91,750). Real-budget p90 barely moves: heavy turns are cut at ~86-92k by the gates either way, and the
saving shows as fewer gate firings and run-outs.

**Confirmation on unused suites** (`maps/fresh-11100..11109`, made for this, no campaign A/B used them; 5,120 games,
m4 against fc3b, own drafts, real budget; `MAIN/replays/ab/fc3-final-conf/`): **50.6% (49.2-52.0), OOF 18,475
against 25,796 (-28.4%)**. By round 2,595 / 1,801 / 2,802 / 3,674 / 7,603 against 5,014 / 2,702 / 3,437 / 4,801 /
9,842; runs <10 / 10-49 / 50+ 13,324 / 4,498 / 653 against 17,796 / 6,455 / 1,545. Shortcuts fc3b -> m4:
farm-partial-evaluation 1,222,208 -> 828,172, step-guard-entry 163,706 -> 145,114, comms-stale-vision 144,499 ->
91,501, turn-order 115,999 -> 67,163, farm-no-route 51,719 -> 26,905. Fuel a play turn: mean 49,857 -> 47,821, p90
86,250 -> 85,950. The cut holds on new maps at about the size it had on the campaign's suites (cand / ref there
37,908 / 55,825 = -32%).
