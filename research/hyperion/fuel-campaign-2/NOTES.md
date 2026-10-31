# Fuel campaign 2 (2026-10-31): notes

Findings, dropped attempts with numbers and open leads, by area. Workers append a `## <area>` section on their
branch; the merge agent keeps them on fuel-orch.

## Campaign summary (merge agent, after round 5; final bot `astraeus-orch2-m5`, CHANGES 247-251)

- **Out-of-fuel turns, A/B against fb0** (1164 games, real budget, own drafts; CAND / REF): m1 4268 / 4385 (-2.7%),
  m2 3508 / 4326 (-18.9%), m3 3232 / 4398 (-26.5%), m4 3105 / 4465 (-30.5%), m5 3084 / 4499 (-31.5%; -29.6% against
  fb0's mirror 4382). Win rates 50.3, 51.5, 49.9, 50.9, 50.8%. The -50% target was not reached. m5 by round against
  fb0: 1 336/401, 2-10 236/408, 11-60 265/664, 61-300 537/966, 300+ 1710/2060: rounds 2-300 are roughly halved or
  better, round 1 and 300+ much less.
- **100M, fb0 -> m5, all byte-identical** (wide 52/52, OOF set 48/48, many-group 24/24):

  | set | mean | p90 | p99 | max | over 100k | round 1 mean / max |
  |---|---|---|---|---|---|---|
  | wide | 47800 -> 46795 | 85764 -> 85567 | 98887 -> 94968 | 296169 -> 296560 | 2308 -> 1803 | 196204 / 279479 -> 194867 / 274351 |
  | OOF set | 52116 -> 50339 | 87253 -> 86617 | 122855 -> 116721 | 443323 -> 442212 | 9235 -> 6865 | 231954 / 414176 -> 227114 / 370937 |
  | many-group | 56622 -> 53729 | 87837 -> 86854 | 120015 -> 110736 | 443323 -> 442212 | 3894 -> 2405 | 226451 / 311260 -> 217943 / 310649 |

  Total fuel -2.10% / -3.40% / -5.10%.
- **Real-budget shortcuts, fb0 -> m5.** A/B, per bot (same games): 155690 -> 126555. farm-partial-evaluation 60179 ->
  53516, step-guard-entry 37088 -> 29501, comms-stale-vision 13391 -> 10228, prey-cut-short 10080 -> 8599,
  turn-order 8742 -> 6859, crow-flies-farm 4405 -> 1984, farm-no-route 2716 -> 1811, ward-no-bushes-fuel 2186 -> 0,
  farm-kept-target 1382 -> 472, static-descend 1582 -> 1368, step-guard-look 5649 -> 5502, ward-no-bushes-clusters
  2889 -> 2984. Benches: wide 11190 -> 9279, OOF set 31668 -> 25557.
- **Gates:** removed fight-cut and ward-no-bushes-fuel; fixed crow-flies-farm and farm-kept-target (round 4).
  Removing comms-stale-vision and farm-no-route (round 4), turn-order and static-descend (gates worker) raised OOF
  turns, so they stay.
- **What's left:** 300+ is over half of m5's OOF turns (1710). farm-partial-evaluation and step-guard-entry are 66%
  of firings. Fight turns pay ~22k before the step guard (world 12k, want_home ~10k: NOTES "Fight turns' fixed
  cost"), and no exact cut of that size was found there. Round 1 is still ~227k mean on the OOF set at 100M
  (build_static, static_camps) and 336 A/B OOF turns.
- **Best open leads:** (1) bound turn-order's offers (`offer_escape`'s `threats_at`, `offer_kills`), then retry the
  plain-priority fallback; (2) the strike search's lazy pricing guard (~19-48M of 95M on the fight set, if its inputs
  are frozen at the search) and the walk-only search (~0.2% on fight maps); (3) farm's banking turns, unbounded over
  60-80 groups (farm-partial-evaluation; TODO 1); (4) rounds 2-3's centre fields (`approach_walk`'s
  `make_field_cap`, ~25k; NOTES "Rounds 1-10") and round 1's build_static / `crossings`, which must be cheap before
  farm-no-route and comms-stale-vision can go (both raised rounds 1-10); (5) the two-turn loops behind the remaining
  50+ runs (gen-mega-groups-600108204, mut-the-pack-600101820; TODO's first section).

## Baseline census (orchestrator; fb0, real budget, OOF set 48 games vs fb0; MAIN/replays/fuel/orch2/cen-census.txt)

- 1046 OOF-first, 498 OOF-late, 34707 heavy finished turns. OOF-first by round: 300+ 41%, 61-300 32%, 11-60 20%, 2-10 7%.
- **Quiet turns dominate now**: 56% of OOF-first have no visible enemy, 62% none within 6 (the first campaign had fight
  turns at 51-60%). Decide-level scope where fuel ran out: farm 49%, carry_bag 12%, strike_search 7%, act_end 7%,
  decide_main 5%, retreat 5%. Innermost: farm.post 26%, farm.loop 18%, farm 10%.
- Component means where present (OOF-first): goal 51k (63% of turns), farm 49k (59%), farm.loop 45k (54%), farm.post
  17k (37%), carry_bag 60k (15%), strike_search 50k (30%), want_home 18k (29%; camp_trapped 8.7k, stand 13k),
  retreat 38k (6%), world 12.7k (100%; camps 5.3k, champion_enemy 4k, track 3.4k on 21%), turn_order 13k (2%).
- Signatures of OOF turns: farm 25%, world+farm 14%, strike_search 9%, want_home+strike_search 9%, carry_bag 7%.
- Types: Heart of Ruin 26% of OOF-first (its OOF turns: strike_search 32.6k, want_home 10.6k), Vendetta 13%,
  Prism 11%. Prism/Willow/Cassi/Varg OOF turns are farm-heavy (farm 43-49k mean).
- Map classes: mega-groups 18% of OOF-first (30% of OOF-late), arena 12%, the-pack 9%, topo-duel 8%.
- OOF-late turns 14% are round 1 (build_static 78k, static_camps 53k, init_beliefs 17.6k).
- SRCH on OOF turns: 40k mean (read 14k, grow 18k, price 13.7k), priced 3 tiles, 13 nodes, 3 foes.

## Farm turns, many-group maps, rounds 1-10 (worker; branch fuel-farm-early, 93c8ae0a, 67d547c2, fb838e05)

Profile first (100M, debug copies timing with raw `fuel()` laps, 12 games vs fb0 on mega-groups-600108204,
dense-camps-600105500, cluster-carpets-600108800, mut-the-pack-600201800, 01elk-arena, topo-duel-600207209):
- A later non-banking farm call: prologue 6.1k (spread: prices 1.2k, farm_recall 0.9k, attack_in_range 0.8k, ...),
  loop 17-22k, post 8.1-8.5k. Loop by where a group left it: **claimed groups (an ally's claim) 2.3 a call at 4.7k
  each = 10.9k, half the loop**; later-turn rated heads 14 x 410 = 5.7k; full bodies 2.3 x 1.7k; the rest small.
  Heavy loops (>30k, ~50 groups): claimed 14.8k, full bodies 11.7k, rated heads 8.4k, value prunes 6.7k.
- The claimed branch (mega-groups): reaching it 1.1-2k (the help check's `struggling()` runs `min_camp_damage` for
  the ally, ~1.6k), `crew_work` 3.4-6.2k (`work_arrival` passes over every member twice per claiming ally),
  `min_camp_damage(S + crew)` 2.7-3.5k on the half that pass the value test. Nobody had bounded it.
- Banking calls (19% of calls, 39k each): 23-27 value prunes x 460 and 7 full bodies x 1.2k. The head's ~400 is
  ~10 pieces of 30-150. No useful lower bound on the trip home: `HomeTrip::rounds` can be 0 (the heal's value), so
  neither a pre-facts bound nor the stop bites for banking. Not pursued.
- `min_camp_damage`'s sorted build on mega-groups' big groups: 14-16k (std::sort of ~60-100 members ~10k, fire
  sums ~3-4k), ~30M fuel a mega game. 20% of builds repeat a (champion, group, version, range) in the same turn.
- Post-loop: route searches are 1-2k mean (kept-route rejections by search fuel: goals differ 42%, we are past its
  labels 22%, new wall below our steps 16%, freed shortcut 11%, >4 changed tiles but otherwise valid 6%);
  `farm_attack_tiles` 7.6k on the heaviest posts (first member builds).

Plan: exact bounds and early exits inside the claimed branch, then the big groups' clear_fire.

Commits (all byte-identical at 100M: wide 52/52, OOF set 48/48, many-group set 24/24 = mega-groups-600108200/04/08/09,
dense-camps-600105500/02, cluster-carpets-600108800/01, mut-the-pack-600201800 and -600101820, atoll-600101912,
continent-600102803, both sides vs fb0):
- 93c8ae0a: claimed groups bounded before `crew_work`: value <= rate(worth x S/(S + crew output), trip) (part <= our
  share with the crew's work all still to do, rounds >= 0), 1.0001 slack. Total -0.94% wide / -0.49% OOF / -0.97% mg.
- 67d547c2: `work_arrival` stops at the first member in reach (its only read, `earliest`, is then 0) and skips the
  spawn pass unless the walk's delay exceeds the recall's (the way by spawn costs at least that). -0.21/-0.25/-0.38%.
- fb838e05: `clear_fire` sums striker strengths by kind with popcounts (whole strengths, total < 2^24: every order
  sums exactly). +0.03/-0.08/-0.10%, over 100k -0.4/-2.1/-3.3%.
- Together vs fb0: total -1.11% wide / -0.82% OOF / -1.44% mg; p99 -0.3/-1.4/-2.5%; over 100k -1.9/-6.2/-8.0%;
  round 1 level. Heavy turns are cheaper on average in every bucket (100-150k: -986 OOF set, -431 wide).
- Real budget (vs `*-real.json`; mg vs a fb0 run): wide OOF 605 -> 523, farm-partial-evaluation 3450 -> 3116;
  OOF set 1547 -> 1524 (without mega-groups-600108204: 1348 -> 1220, fpe 10883 -> 9845); mg 676 -> 750 (without it
  477 -> 446). **mega-groups-600108204 at the real budget is chaotic**: fb0 199 OOF (131 + 68), a fuel-neutral fb0
  perturbation (4-slot sort cache) 497, our variants 267-423. Judge it by the A/B, not by these 2 games.

Dropped (exact, measured): kept-route change limit 4 -> 12 (`kept_steps`): +0.10/+0.21/+0.16% (mg/wide/OOF); a 4-slot
sorted cache in `min_camp_damage` (catches the 20% repeats): -0.04% mg, +0.02% wide, over 100k +0.4% wide.

Open minor items:
- The sort in `clear_fire` (~10k a big-group build on mega-groups) is only exact as std::sort on the same input:
  tied identical strikers' order changes later fires (reach is not symmetric). No shortcut found.
- Claimed branch: `hits > spare_health` holds without `min_camp_damage` when spare_health < 0 (hits >= 0); rare.
- `struggling()`'s ally `min_camp_damage` (~1.6k a claimed visit on mega-groups); no cheap exact bound found.
- Banking heads (~10k a banking call): needs a trip-home lower bound that the heal value doesn't zero.
- `kept_steps` misses on "goals differ" are 42% of route search fuel (attack tiles change as members die).

## Fight turns (worker: fuel2-fight)

Profile (fb0, OOF set at the real budget, census with extra scopes: Reach build/at, the fight sim `trade`,
`awake_members`/`find_members`, the step guard and its cover, the strike search's read/grow/price, exit walk):

- Fight OOF turns (strike search, want_home, retreat, chase or strike_after >= 10k): 638 of 1420 OOF turns. Two kinds:
  - **Camp-heavy maps** (mega-groups, topo-duel, the-pack, rivers, open-field): want_home's `camp_trapped` 12-16k
    (find_members 10-11k, `exit_hits` 13k when it runs), retreat 36k when it runs. find_members is one call a turn at
    ~6k (mega-groups: 25 members, 1.8 near champions) to ~13k (the-pack: 40 members, 4 near).
  - **Champion fights** (arena, atoll, 01elk-arena, gem-drought, monolith-only): search grow 21-33k (HoR 24k at 17
    nodes, ~1.4k a node; settle ~470 a call, landing groups 2.3k), read 13-15k (cover 5.5k), price 12-17k, stand
    11-18k (trade sim 8k), lethal 7k, Reach at 5k (14 calls) and builds 3.5k (3.3).
- **The step guard is cheap on OOF turns only because its entry gate skips it** (g.guard 0.65k a fight OOF turn,
  step-guard-entry 4460 firings in 48 games). At 100M (no gate fires; 6822 placings with exposed tiles on the wide
  set, 14493 on the OOF set) it costs p50 8.2k, p90 20.5k, p99 51k, max 139k; 0-1 new fights in 94% / 87% of
  placings, 2+ in 6% / 13%, 4+ in 0.8% / 2.9%. One-fight placings reach 66k. prey: one fight in 92% / 85% of calls,
  p50 11k, p90 21.5k, max 92k; 3+ fights 1.3% / 2.7%.
- Self fuel over all OOF turns (top fight items): grow 5.3%, find_members 5.2% (as big as grow, bigger than the
  fight sim's 1.9%), price 2.0%, trade 1.9%, read 1.7%, lethal 1.6%, cover 1.3%, Reach at 1.3%, stand 1.3%,
  exit_hits 1.1%, Reach builds 1.0%. Heavy finished turns: find_members 3.9%, trade 3.6%.

Plan: exact cuts where several walks or consumers repeat the same work (the exit walk on retreat turns), then
find_members; the gate removals need the guarded work bounded far below what the counts above allow (see below).

Kept (b2372f52): find_members' reach cut as vector minima. A member's reach and tie are plain minima over the near
champions (one with d - 1 >= reach lowers neither, as reach only falls and reach >= tie - 1), so for groups of 8+
with 3+ near champions (whose turn order the box filter has already read) the loop runs branch-free on flat arrays,
which clang vectorises. 100M identical (wide 52/52, OOF 48/48); OOF set -0.30%, over 100k 9235 -> 8832 (the-pack
-2.8%, mega-groups -0.4%, topo-duel +0.14%); wide +0.01%. Real budget: OOF set OOF 1547 -> 1514, wide 605 -> 587.

Measured cost of find_members (100M, release-like stamps): mega-groups ~5.9k a call (25 members, 1.8 near), the-pack
~13k (40 members, 4 near); per member ~82 plus ~40 a near champion; test(visible) ~40 a counted member,
camp_stunned ~25, the stir check ~850 a call, near setup ~400. Note: work inside debug_block is not charged, and
per-member stamps distort the loop (they read ~3x the real cost).

Dropped (all exact, 100M identical):
- find_members variants: flat minima for every group with turn order read eagerly (wide +0.15%, OOF -0.15%: the
  eager slot() reads cost more on small groups); flat with the original branch (OOF -0.06%); flat minima with
  vectorisation disabled (OOF +0.19%, the-pack +1.3%: the vectors are the gain); vector minima for all big groups
  (OOF -0.23%, topo-duel +0.39%, rivers +0.27%: +150-280 a call with 1-2 near); the stir check branch-free (on top:
  OOF +0.08%, mega -0.6% but the-pack +1.0%), or branch-free by 16 (+0.016%).
- exit_hits keeping each tile's step down for the field and members version (a retreat walks the same way out up to
  ~10 times: camp_trapped twice, flee_camps a neighbour each): OOF set +0.000% (over 100k 9235 -> 9217), wide
  +0.012%. Repeated walks are rarer than the census suggested.

Gate removals, real budget, OOF set against base-oof-real (1547 OOF):
- step-guard-entry/-sim/-look removed: OOF 2920 (+89%), fight-cut 2 -> 720, turn-order 2231 -> 2726.
- prey-cut-short removed: OOF 1916 (+24%), fight-cut 2 -> 215.
- Why (100M traces above): a placing with 4+ fights is 0.8-2.9% of placings but 60-110k; a one-fight placing reaches
  66k; prey with 3+ fights 1.3-2.7% of calls at 37-80k. A count limit that almost never binds (4 guard fights,
  3 prey fights) still allows 60-90k on the fuel-short turns the gates now skip. The sims (7k median, 15k p90 a
  `trade`) have to get several times cheaper first, or the limit has to be a deterministic work budget (plies x
  fighters) set near the p90 with the lethal fallback; both need an A/B.

Open leads (fight side):
- find_members: cross-turn reuse per group (members never move; reach cut changes only with near champions, health,
  sleep) would save most of its ~6-13k a turn on camp-heavy maps; needs a version key per group. Small groups with
  3+ champions could take the vector loop if their turn order were read cheaply.
- HoR / Vendetta grow on OOF turns: 17 nodes at ~1.4k (settle ~470 a call, landing groups ~2.3k a search).
- g.cover's own ~2.5-5.5k (GuardFoes, the window's open tests) repeats inside step_guard when it is resolved
  (est. 1-2k on ~30% of fight turns).

## Merge round 1 (merge agent; fuel-farm-early + fuel2-fight, CHANGES 247)

All four code changes reviewed exact and merged; none dropped. Bot frozen as `astraeus-orch2-m1`; JSONs in
`MAIN/replays/fuel/orch2/m1-{wide,oof}-{100M,real}.json`.
- 100M wide: 52/52 identical, total -1.10%, mean 47800 -> 47270, p99 98887 -> 98371, over 100k 2308 -> 2255;
  turns cheaper 101184, dearer 89780.
- 100M OOF set: 48/48 identical, total -1.12%, mean 52116 -> 51533, p99 122855 -> 120931, max 443323 -> 443349,
  over 100k 9235 -> 8244, round 1 mean 231954 -> 231777; turns cheaper 79853, dearer 95417.
- Real budget: OOF wide 605 -> 594 (27/52 replays identical), OOF set 1547 -> 1503 (8/48). OOF-set shortcuts:
  farm-partial-evaluation 11478 -> 10854, step-guard-entry 7353 -> 7015, comms-stale-vision 3130 -> 2963,
  prey-cut-short 2092 -> 1955. On the wide set, step-guard-entry 2694 -> 3152 and prey-cut-short 1155 -> 1505 rose:
  the games diverged and the sample is small.
- A/B against fb0, real budget, own drafts: 50.3% of 1164 (47.5-53.2). OOF 4268 against 4385 (-2.7%); the mirror
  was 4382. By round, CAND/REF: 1 407/401, 2-10 393/408, 11-60 632/649, 61-300 822/901, 300+ 2014/2026. Runs of
  50+ OOF turns in a champion-game: 99 against 173.

## OOF forensics: what ran after the last fuel check (worker: fuel2-oof)

Method: a census `--trace` (instrument.py; census.h records every `fuel()` read and `fuel_ok()` check with its call
site and what it needed, and every scope entry, in a ring; a turn that ran out prints them as a `CTR` line).
`tools/fuel/census/trace.py DIR` groups run-outs by the last passed check and lists the stretches after it;
`trace_scope.py DIR LABEL` gives a scope's cost per map up to the next event. Extra trace scopes on min_camp_damage,
stand_reach's build, clear_fire's sort, fastest_clear, home_trip, bankable_bag, camp_cast, farm_attack_tiles,
Pathing::attack_tiles, drafted_attack_tiles, dash_towards, walk_on, bank_gems, step_safely, step_towards (both),
make_field. Run on m1 (fuel-orch db16c270), OOF set, real budget vs fb0: 833 OOF-first turns traced.

Where OOF-first turns ran out (innermost scope), m1:
- **stand_reach's first build 14%** (+ clear_fire's sort 3.4%, the rest of min_camp_damage 2%): camps.cc's
  StandReach table is built once per group and range class (melee/ranged) per instance, O(members^2) at ~50-65 fuel
  a pair: measured at 100M (debug print, raw fuel) 71k for a 32-member group (topo-duel), 84k for 36 (mega-groups),
  122k for 48 (the-pack). It runs inside one farm-loop body (room()'s margin is ~12k) or a banking loop
  (carry_bag), or in `struggling()` for an ally's range: no check can cover it, and above ~100k it spans a run of
  OOF turns. 0.9-2.7M fuel a game per team on those maps. **Lead for the camp worker** (their code): build it
  branch-free on flat arrays (members' at-tiles x strikers' pos/reach, <= 32 strikers: vectorises like
  find_members' reach cut), or per member incrementally; then it could also be warmed in the turn-end queue.
- **drafted attack tiles decoded on the hot turn 11%** (Pathing::attack_tiles 5%, drafted_attack_tiles 4%,
  farm_attack_tiles 2%): warm_up skips groups whose attack tiles the draft carries, so farm's first walk to a group
  decoded every member (~1-2k each, up to ~24k for a plan block's first) after farm.post's one search check. Fixed
  (fa01b000).
- **camps_reach_spawn 6.4%** (decide_main): a once-per-instance static read the first time we are hurt on spawn,
  four board calls per member: >300k on fog-field, topo-odd-spawn, dungeon, leaky-diagonals (thousands of members),
  so a run of 3+ OOF turns. Fixed (4fd1037b).
- farm.post's other tails (walk_on 5.6%, camp_cast 4.1%, dash_towards 1%, route/step_goals 3%) and the turn's end
  (act_end 5.8%, turn_order 3.4%, publish_order 1.8%, strike_after 1.8%): mostly turns that reached them with
  < 2-5k because something earlier overran (the classes above, the strike search). farm.post reserves one search +
  end_reserve after its check (farm.cc:1235/1284), then runs: farm_attack_tiles, cast_at_camp_on_approach
  (camp_cast 3.8k mean where present, p99 8k, max 27k on 36-member groups: an sdk_camp read per member plus
  best_ground), dash_towards (its own search, 7.4k mean where present), step_towards (p99 22k, max 45k: up to 3
  route tries, a bare and a guarded search each with a deferred guard), the adjacent-tiles search when the first
  fails, then walk_on. After decide, the turn needs p50 3.3k, p90 7k, p99 13k (send 1.6k, turn_order 1.3k, act_end
  0.9k mean): end_reserve's 10k covers ~p97 of it alone, nothing of farm.post's post-walk casts.
- strike_search 9% / retreat / chase / farm-on-fight-maps 8% (fight turns that reach farm with <5k): the fight
  worker's (plan.cc:1733-1739 stretches, 7-11k between the search's own reads).
- The turn-end queue's warm_centres on dungeon (2%): run-outs right after `nearest_groups` inside it, before its
  first check: `centre_cap()` decodes drafted steps (fixed_steps) that warm_drafted_steps, a step earlier, skipped for
  fuel. Lead (model): warm_centres should not run while warm_drafted_steps is incomplete (needs an accessor).
- turn_order.cc:447 checks end_reserve (10k) then can spend 14k (16 run-outs). Lead (model).

carry_bag (heavy turns >= 30k, 6612 turns, 60k census mean): the banking farm loop 27k (self 19k), carry_bag's own
6.5k (farm's prologue, can_tribute_safely, closing), home_trip 5.2k (1.2 calls), bank_gems 4.7k (step_safely
3.6k), bankable_bag 3k (3.1 calls; altar_access rebuilds on a camp change), closing 1.4k (2.3 calls). It is
bounded by room() like the other farm loop; of 104 traced carry_bag run-outs, 44 ran out in stand_reach's build and
75 had farm.cc's loop check as the last passed one. No separate unbounded piece found.

Commits (both byte-identical at 100M: wide 52/52, OOF set 48/48, vs m1's JSONs):
- 4fd1037b `camps_reach_spawn` by Chebyshev distances to the spawn tiles behind a box filter. Checked against the
  old board test in a debug copy: 495 first reads on the wide and OOF sets at the real budget, all agree (21 true:
  00swirl, 01yellow-brick-road). 100M: total -0.03% wide / -0.05% OOF, OOF-set p99 120931 -> 120455, over 100k
  8244 -> 8160. Real budget, OOF set: OOF 1503 -> 1454.
- fa01b000 the turn-end queue decodes farmed groups' drafted attack tiles (after warm-up, before the tables around
  us), nearest our farm choice first, one member a check at floor + 25k. 100M (both commits): total +0.11% wide /
  +0.13% OOF (the queue spends more, by design; turns dearer 230k are queue turns), p99 98371 -> 98314 /
  120931 -> 120202, over 100k 2255 -> 2239 / 8244 -> 8092, round-1 mean 196473 -> 195372 / 231777 -> 231322.
  Real budget (both): OOF set OOF 1503 -> 1240 (-17.5%), farm-partial-evaluation 10854 -> 10424, comms-stale-vision
  2963 -> 2727, turn-order 2207 -> 1876, prey-cut-short 1955 -> 1858, farm-no-route 782 -> 717, step-guard-entry
  7015 -> 7161; wide OOF 594 -> 548 (-7.7%), prey-cut-short 1505 -> 1215, step-guard-entry 3152 -> 3036.
  Re-traced on the OOF set: OOF-first 833 -> 706; drafted_attack_tiles innermost 33 -> 7, Pathing::attack_tiles
  42 -> 25 (the rest: mega-groups' union of 36 members' tiles redone on each kill, reached with ~3k left).

Dropped: the drafted warm for the nearest 8 groups only before the tables around us, the rest after them (c4):
OOF set OOF 1331, wide 550 against 1240 / 548 for warming all first.

Open leads (others' code): stand_reach's build (above, the largest class left: 120 of 706 OOF-first turns after
these commits, 17%); camp_cast for big groups (an sdk_camp read per member, 3.8k mean, up to 27k, after
farm.post's last check); warm_centres decoding drafted steps unguarded (dungeon); turn_order.cc:447's 10k check
before up to 14k.

## Camp state reuse across turns (worker; branch fuel2-camps)

Profile (100M, debug copy with raw `fuel()` laps in `debug_block`, 32 games vs fb0: the 12-map many-group set
of round 1 plus topo-duel-600207209, mut-the-pack-600201800, arena-600202608; stdout caps cut some games near
round 1000). Per turn on all turns / on turns whose world + decide exceeds 80k:
- find_members 4.5k / 9.9k (the-pack-600201800 11.2k / 17.7k, topo-duel 6.8k / 11.3k, mega-groups-600108204
  5.7k / 9.1k); one call a turn. **Its member loop is 80-90% of it**: 4.0k for 26 iterated members on mega-groups,
  8.7k for 37 on the-pack (~150-230 a member iterated; the visible/stun test is only ~30-37 of that), the rest
  is setup 240-350, the box filter 430-700, the stir check 380-980. Members within 10 of us: 58% / 87%, so a
  lazy by-area list would not help. An exact cross-turn key per group (version, wakefulness, stirred, near
  others' tiles and turn order) repeats for 52% of members on all turns but only 22% on heavy ones.
- min_camp_damage 1.1k / 5.3k (mega-groups-600108200 heavy turns 41.8k at 7.9 sorted builds a turn); sorted builds
  are 87-92% of it. **18-20% of build fuel (47% on mega-groups-600108200's heavy turns) rebuilds a (group, range,
  version) built on an earlier call**: the single sorted slot is overwritten by the next group asked.
- update_camps 4.2k / 6.2k, of which non-settled groups' reads 2.5k / 4.3k (per visible member a health and a
  wake read; health can fall by unseen enemies' hits, so it is not skippable exactly).
- exit_hits 0.1k / 0.36k, struggling() 0.2k / 0.9k (mega-groups-600108204 heavy 8.6k).

Plan: (1) find_members' big groups (8+ members): a per-map table of member tiles and reaches (members never
move), a per-version live-striker mask (health changes only with `version`), and the reach and tie minima as
SIMD over members (4 a vector) rather than per member over near champions; output in the same order. (2) a
sorted build kept per (group, range) for its version, in its own storage so no copy is paid.

Commits (all 100M byte-identical on wide 52/52, OOF set 48/48 and the many-group set 24/24 above; deltas vs m1):
- 22f51a44 find_members' big groups by member lanes (static per-group tiles/reaches, live-striker mask per version,
  SIMD reach/tie minima over members): total -0.09% wide / -0.83% OOF / -1.81% mg, over 100k 2255->2229 /
  8244->7886 / 3172->2836. The member loop on the-pack 8.7k -> 5.5k a call (SIMD 1.4k, emit ~100 a member of
  which the visible+stun test ~35, the rest bookkeeping).
- bc7ad2bb min_camp_damage's sorted build kept per (group, melee/ranged) for its version in one static zeroed pool
  (a first try with a vector per group cost round 1 +0.9% in allocation): on top -0.18% / -0.19% / -0.30%, p99
  -0.9% / -0.7% / -1.3%.
- 47908b1c stand_reach's n^2 table four strikers a vector (the coordinator's lead from round-2 forensics: 71-122k
  first builds, 14% of OOF-first turns): mg turns over 150k 344->285, over 200k 130->98, their mean -20.7k; OOF-set
  round 1 p99 -5.5%, max -8.7%. Real budget (vs m1-*-real): OOF set OOF 1503 -> 1185 (-21%), wide 594 -> 472.
- ebf1f6f2 warm_centres warms the drafted steps under its floor before centre_cap() reads them (queue only; the
  unchecked decode did not fire in the OOF-set games: real-budget counts unchanged).
- Together: wide -0.27% (p99 98371->97380, over 100k 2255->2116), OOF set -1.09% (p99 120931->119178, over 100k
  8244->7630, round 1 231777->228564, max 412917->375795), mg -2.24% (p99 117437->113331, over 100k 3172->2653).

Dropped: the full-health sort kept for good per (group, range) (a respawned or never-hit group re-sorts as before
whatever its version; version 0 skips the health scan): mg -0.11%, over 100k -0.7%, round 1 +0.1%, turns over
150k +75 mean. 19% of builds are full-health non-first, but small ones.

Open:
- clear_fire's sort (warm builds of damaged big groups: ~20k a heavy turn on mega-groups-600108204). An exact
  route: the damage and rounds are invariant under reordering inside a comparator tie block when every s>0 block
  has one (strength, health), the stand-reach relation is symmetric inside it and the sums stay integers below
  2^24; then the previous version's order, updated and insertion-sorted, would do. Needs a measurement of how
  often the conditions hold.
- find_members' remaining loop is emit cost (~100 a counted member); the stun read (~35) is needed per member.
- update_camps 4-6k a turn: awake groups in view read health and wake per visible member; unseen enemies can hit,
  so no exact skip found.
- set_turn_order (turn_order.cc:447) checks end_reserve (10k) and then can spend ~14k in bid().

## Merge round 2 (merge agent; fuel2-oof + fuel2-camps, CHANGES 248)

All six code changes reviewed exact and merged; none dropped. Checked: every write to a camp member's health bumps
`CampBelief::version` (update_camp's member read, `restore`; the other version bumps are state changes), so the
lanes' live mask and the sorted pool key on everything they read; the awake mask matches `member_asleep` (members
past 64 count awake unless the group is asleep); padded lanes are never emitted (live bits stop at n; stand_reach's
padding has reach -1); ranges passed to `min_camp_damage` are attack ranges (>= 1), so range 0 safely marks an
unbuilt slot; the non-reflect path never writes the kept sort; static tables are per instance and rebuilt by
version (the lanes' first build forces a mismatch). Queue order after the merge: prepare_next_turn,
warm_drafted_steps, map warm_up, warm_centres (now warming enemy and drafted steps first), pathing warm_up, bush
clusters, then the drafted attack tiles, then the ring around us.

Bot frozen as `astraeus-orch2-m2`; JSONs in `MAIN/replays/fuel/orch2/m2-{wide,oof,mg}-100M.json`,
`m2-{wide,oof}-real.json`, and the fb0 many-group baseline `base-mg-100M.json` (the 12 maps of round 1's set, vs fb0).
- 100M wide: 52/52 identical to fb0. Against fb0 / m1: total -1.27% / -0.16%, mean 47800 / 47270 -> 47193, p99
  98887 / 98371 -> 97280, max 296169 / 296199 -> 296109, over 100k 2308 / 2255 -> 2102, round 1 max 279479 / 281466
  -> 275911. Turns cheaper 37267, dearer 208260 against m1 (the queue's new warm work fills spare fuel).
- 100M OOF set: 48/48 identical. Against fb0 / m1: total -2.06% / -0.96%, mean 52116 / 51533 -> 51041, p99 122855 /
  120931 -> 118572, max 443323 / 443349 -> 443251, over 100k 9235 / 8244 -> 7464, round 1 mean 231954 / 231777 ->
  228190, round 1 p99 395336 / 392361 -> 369261, round 1 max 414176 / 412917 -> 375808.
- 100M many-group set: 24/24 identical to fb0. Total -4.25%, mean 56622 -> 54211, p99 120015 -> 112766, over 100k
  3894 -> 2592, round 1 mean 226451 -> 219451.
- Real budget: OOF wide 605 / 594 -> 468 (26/52 replays identical to m1), OOF set 1547 / 1503 -> 1175 (8/48).
  OOF-set shortcuts against m1: farm-partial-evaluation 10854 -> 10496, comms-stale-vision 2963 -> 2747, turn-order
  2207 -> 1981, static-descend 395 -> 247, step-guard-entry 7015 -> 7407 (the games
  diverged; small sample). Wide against m1: farm-partial-evaluation 3232 -> 3070, step-guard-entry 3152 -> 2740, prey-cut-short
  1505 -> 1091. mega-groups-600108204 stays chaotic: 199 / 240 -> 259.
- A/B against fb0, real budget, own drafts: 51.5% of 1164 (48.6-54.3; ladder 50.0, gen 52.5, gen-s1 50.8). OOF
  3508 against 4326 (-18.9%; the mirror was 4382, round 1's CAND 4268). By round, CAND/REF: 1 356/401, 2-10
  317/409, 11-60 333/647, 61-300 608/915, 300+ 1894/1954. Champion-game runs: <10 2503/3139, 10-49 951/1130, 50+
  54/57. Campaign target (-50%) not yet reached: -19.9% against the mirror.

## Late game, rounds 300+ (worker: fuel2-late)

Profile (m2 = fuel-orch cb645309, census `--trace --fine` at the real budget, own drafts vs fb0, 32 games on the 16
maps heaviest in late first-in-streak OOF in the round-2 A/B: mega-groups-600108204, the-pack-600101820,
huge-shared-600205200, arena-600202612/08/01, atoll-600101912, gem-drought-600105820, cross-600103300,
dash-lattice-600107612/600207628, topo-duel-600207209, continent-600202800, labyrinth-600203805, 01elk-arena,
01starfish; print floor raised so the 1 MiB stdout cap never cuts late rounds). 800 OOF turns; OOF-first 394 after
round 300, 185 before.
- In the A/B batches, late first-in-streak OOF is 1592 in 351 of 1154 games, spread evenly over rounds 300-1000 and
  thinning after; batch_oof's "queue" phase is only 134 of them (the late-finish label), the rest decide.
- **What differs after round 300 is how often we fight, not what a fight costs.** 71% of late OOF-first turns ran a
  strike search of 10k+ (mean 53k; 81% had an enemy in sight), against 53% in rounds 61-300 and 69% in 11-60. Per search the cost is
  the same in every bucket (SRCH: 16k mean, p90 30.5k, 3 nodes, 2 foes in 11-60, 61-300 and 300+); there are just
  far more searches (66.7k of 82.6k searches in these games came after round 300). No per-turn work that grows with
  game history showed up (world 12k in every bucket; upkeep_tiles, beliefs, tracks are flat).
- 73% of late OOF-first turns passed **no fuel check at all** before running out: the strike search reads fuel only
  in debug marks, so a turn reaches it with ~50-67k, the search spends 45-60k (read ~14k, grow 15-34k), and the goal
  (chase, siege_kite, farm's prologue: pick_up, recall_line, bankable_bag, attack_camp_target, its Safety) is entered
  with 1-9k and runs out before the farm loop's first check. Fight worker's lead: the search has no fuel bound.
- The other 29% (115 turns, no search): farm-heavy maps (the-pack 40, mega-groups 28, topo-duel 27, 01elk-arena 11).
  min_camp_damage on 93 of them (19.7k mean), **clear_fire's sort on 88 (12k mean)**, struggling on 54 (16k), the
  farm loop 28k. Typical trace (mega-groups r473): the loop's check passes with 42k (needed 22k), one claimed-group
  body then runs struggling's min_camp_damage for the ally's range (sort 13.6k), crew_work 6.6k and our
  min_camp_damage (sort again): 28.5k in one body; farm.post's search check fails, farm_attack_tiles'
  Pathing::attack_tiles then spends 5-7k and camp_cast ~2k after it, and the turn ends in step_onto_cleared.
  Late camps are damaged by every champion every round, so each turn bumps the versions and re-sorts big groups.
- Last passed check, late OOF-first: none 72.6%, farm.cc:906 (loop) 13.2% (margin 9k), farm.cc:1235 6.6%, 1284 2.5%,
  guard.cc:467 2.5%; turn_order.cc:447 once.

Plan: (1) clear_fire's sort exact and incremental: on a version change start from the slot's previous order and
insertion-sort; accept the result only where it provably gives the same damage and rounds as std::sort (cross
products exact, so the comparator is a strict weak order; inside every tie block of striking members equal
strength and health and a symmetric stand-reach relation; integer sums below 2^24; reflect calls take std::sort's
own order), else std::sort as now. (2) farm.post's attack-tile union after kills. (3) the post-search goal.

Second census (farm's prologue split into scopes): 'farm' self as innermost (106 of 581 OOF-first) was the recall-out
test (`safety.threatened`, `recall_outruns`, `farm_recall`: 4.3k mean, 46 run-outs) and the loop's setup after it
(home trip, prices, memo contexts, 2.7k mean, 39 run-outs), on turns that entered farm with ~7k. Fuel left on
entering, late OOF-first: strike_search p50 65.6k, post_search 12k, goal 11k, siege_kite 9k, farm 7.3k. After a
search `evaluated` is 0: the loop weighs nothing and the turn walks on to last turn's choice, so that setup is unread.

Commit (100M byte-identical: wide 52/52, OOF set 48/48, many-group 24/24, vs m2):
- 1e31a3cc farm: after a strike search, return before the recall-out test and the loop's setup (walk on as the
  post-loop code did with k = 0). Total -0.11% wide / -0.38% OOF / -0.17% mg; p99 97280->96905 / 118572->117855 /
  112766->112403; over 100k 2102->2032 / 7464->7284 / 2592->2550; turns cheaper 142k / 123k / 47k, dearer 3.8k /
  4.6k / 1.4k. Real budget: OOF set OOF 1175 -> 1041 (-11%; step-guard-entry 7407->7405, comms-stale-vision
  2747->2599, turn-order 1981->1877, prey-cut-short 1968->1989, farm-partial-evaluation 10496->10348), wide 468 -> 448
  (prey-cut-short 1091->1348, step-guard-entry 2740->2933: diverged games, small sample). Census on the 16 late maps:
  OOF turns 800 -> 768, late OOF-first 394 -> 400 (chaotic sample; 'farm' innermost 75 -> 5).
  **The memo contexts must still advance on those turns**: returning before FarmContext / gold / FarmClearing
  updated changed choices on 00swirl-a (r187) and the-pack-600201800-a. A context that goes A -> B -> A then keeps
  facts computed under the first A; the original recomputed them. So some kept facts read inputs their keys miss
  (not traced which: the clearing facts' `soften`/spells inputs or the gold facts are candidates). Lead (farm): find
  the unkeyed input; it is a staleness in the original too.

- 80689194 farm_attack_tiles skips `prepare_attack_tiles` when the group's attack tiles are drafted (every
  prepare_member then returns true at once; asking cost ~130 a member, ~5k for a 36-member group on each kill that
  misses the kept union). On top of 1e31a3cc: total -0.13% wide / -0.13% OOF / -0.22% mg, round 1 mean -0.2 /
  -0.4 / -0.7%. Both commits against m2: total -0.24% / -0.51% / -0.39%, p99 97280->96742 / 118572->117458 /
  112766->111640, over 100k 2102->2011 / 7464->7186 / 2592->2489. Real budget (both): OOF set OOF 1175 -> 979
  (-16.7%; turn-order 1981->1723, comms-stale-vision 2747->2561, step-guard-entry 7407->7424, farm-partial-evaluation
  10496->10959), wide 468 -> 473 (noise: half the 52 replays diverge).

Dropped (measured):
- clear_fire's incremental re-sort (plan 1), exact by construction and checked in a debug copy (the resorted order's
  damage and rounds against std::sort's for 6 strengths on every accepted resort: 0 mismatches in 12 games). It lost:
  mg set +0.26% total (+0.12% over a control with the same code layout and no resort), p99 +1.8%. For n > 30 on
  mega-groups-600108204: std::sort ~9.9k, fire passes ~3k each, the insertion re-sort ~2k but the tie-block check
  3-7k pairwise (asymmetric ties and >24 significant bits of health fail 50-98% of big tries on one side), and a
  failed try pays both. With a transposed one-way matrix (32x32 bit transpose) and the one-Strength case freed from
  the bits test it was still +0.26%. Big-group sorts are only ~100-500 a champion-game; the rest of the build is the
  fire passes. Moving the sorted pool out of line (noinline, farm_turn is flattened) alone cost round 1 +1.3%.
- farm_attack_tiles' union warmed at the turn end (prepare_next_turn) for the members expected to live next turn
  (belief less visible members our kills left dead, read by sdk_camp): exact (52/52, 48/48, 24/24) but mean +0.5% /
  +0.8% (queue work every turn), over 100k -0.3% / -0.6%, real OOF set 1175 -> 1162. Kills between our turns by
  allies or enemies miss the guess.

Open leads:
- Fight worker: the strike search has no fuel bound (73% of late OOF-first passed no check; it leaves p50 12k).
  Everything after it in decide (chase, siege_kite ~1.7k median, farm prologue, walk_on, act_end, turn order, comms)
  needs more than that.
- set_turn_order at 100M on fight maps (12 games, 69.6k turns): >= 2k on 42% of turns, p50 3.2k, p90 5.6k, p99
  10.9k; >= 8k on 1.3%: may_escape 2.5k, plain_priority 2.5k, offer_kills 1.9k, refresh 1.0k, offer_heal 0.9k,
  offer_escape 0.9k. Spread over Safety (camp_damage/awake_members, strike_of, damage_ceiling, tie_hit): the 10k
  check at turn_order.cc:447 covers ~p99; the run-outs there (18 of 400 late OOF-first in the second census) pass it
  with 10.1-12.7k. No exact cut inside turn_order.cc found; it needs Safety's pieces cheaper.
- farm.post after a failed search check (farm.cc:1235) still runs farm_attack_tiles (after 80689194 the union
  alone, ~7k for 36 members after a kill: a slot lookup and a board OR a member; a union kept per block of 8 members
  would redo one block and OR the blocks) and dash_towards (its own search, up to 6k; combat's): p.attack_tiles 22,
  farm_attack_tiles 10 and walk_on 36 of 400 late OOF-first. Pathing::prepare_attack_tiles/prepare_member_tiles could
  take the same drafted shortcut for siege.cc's callers (pathing.cc, not changed here).

## Fight gates: step guard and prey (worker; branch fuel2-fightgates)

Profile (m2 = fuel-orch cb645309, 100M, OOF set 48 games vs fb0; debug copy with per-placing, per-prey-call and
per-sim lines in `debug_block`, replays identical to m2):
- Guard placings with exposed tiles: 15.7k (stage: U1 won 8761 at 8.5k p50; full loop 5403 at 20k p50, p99 101k,
  max 183k). Over all of them p50 10k, p90 30k, p99 75k. **Sims are only ~36% of it** (5.1k mean); the rest: setup
  and bound pass 3.5k, U1's own 1.8k, **exact looks 7.4k mean, p99 34k, max 60k** (~1.2k a tile x foe, Reach builds
  on first touch), the final loop's lethal/keys 2.8k. Sims a placing: 1 at p50, 5 at p99, 11 max.
- Sims (65k): fuel ~ 340 an act + 37 a fighter-act + 640 an early-end check (residual p50 330); one sim max 25k.
  **Cross-turn repeats of the exact sim inputs** (sides hashed field by field): 4.5% the previous round, 6% within 5
  rounds, 0.1% the same turn: a cross-turn fight memo (FUEL-AUDIT 1.4) would save under ~4% of sim fuel. Not pursued.
- A work unit of 9 x acts + fighter-acts + 32 x looks costs ~64 fuel (p10-p90 52-82). Per placing p50 96, p90 457,
  p99 1335, max 3573; per turn p99 1708. A budget binding on 1% of placings still allows ~75k; on 5%, ~50-65k.
- Prey (19k calls): one candidate 79% (12k p50; sim only 3k of it), two 16% (22k), three 4.4% (32k), 4+ 0.6%
  (49-90k). Non-sim 10.9k mean: each candidate's fight_key/late/chase_trade setup ~8k.
- Heavy turns at 100M (OOF set): 100-150k (6410): guard 10k, prey 6.7k, search 15.8k (incl. its guard); 150k+
  (735): guard 36k, prey 11k, search 47k.

Plan: (1) step guard: the three gates go; a per-turn work budget (the sims' acts and fighter-acts from a counter in
`simulate`, plus the looks) set near the per-turn p95-p99, with the fail-closed fallback (tiles not yet settled are
guarded; memoised fights stay free). (2) prey: the gate goes; a per-call candidate budget, with last turn's prey
tried before stopping. Each measured at the real budget (wide, OOF set, arena set) and at 100M (binding rate,
diverging replays).

Results: nothing kept; every variant below is real-budget (`--fuel 0`), against m2's `m2-*-real.json` and an m2
arena run (arena set: the 9 `maps/gen-s1/gen-arena-*`, `mut-arena-600201824`, 01elk-arena, adgato-gemcombat5; 24
games vs fb0). "Won" is games won of the set (OOF set and arena vs fb0, wide vs hecate). m2: OOF set 1175 OOF / 25
of 48 won, wide 468 / 50 of 52, arena 392 / 13 of 24.
- **Budget replacing the three guard gates** (counter `fight_work` in `simulate`: 9 an act + its fighters + 17 an
  early-end check; looks 32; per-turn budget; past it unsettled tiles guarded; memoised fights free; diff kept as
  scratchpad `fightgates/budget-attempt.diff`): budget 1000 (binds ~2.5% of placings at 100M): OOF set 2711 (+131%),
  fight-cut 1 -> 734, 23 won; wide 1428 (3.1x), 48 won. Budget 600 (~6%): OOF set 2835. **The budget's size hardly
  matters**: what runs out is the guard's floor cost on the turns the entry gate skips, not its tail.
- Why (probe at the real budget, m2): the entry gate fires on 7358 of 18258 entries (40%). Fuel left when it fires:
  p10 20k, p50 40k, p90 55k; its floor (`fight_cost_estimate` + 20k) is 42k p50 and `costliest` only 8.6k p50, so
  the gate is not sticky history here: it keeps ~40k for the rest of the turn. Placings that pass have 59k left
  (p10 48k): fight turns spend 40-60k before the guard. A placing whose U1 is won (the commonest kind) costs 8.5k at
  100M (ctor 0.56k, gate 0.33k, expose_here 0.2k, bound loop 2.1k, fight_enemies_any 0.46k, U1 4.9k of which fill
  and setup 1.2k and the sim 3.4k): that floor, on turns already 40-60k deep, is what runs out.
- The turn's fight work so far does not predict the gate: at work > 100 units precision 0.52, recall 0.51; > 300,
  0.89 / 0.15. Fired entries see 3.3 foes against 1.9.
- **Fail-closed fallbacks under the existing gates** (FUEL-AUDIT 1.1; 100M unchanged as no gate fires there):
  - cover (every tile more exposed than ours by bound): OOF set 994 (-15%), 20 won; wide 526 (+12%), 48 won; arena
    322 (-18%), **5 of 24 won**; step-guard-entry 7407 -> 9396, prey-cut-short 1968 -> 2607 (wide 1091 -> 2367).
    Too timid: it loses fights the gate-open bot wins.
  - `safety.lethal(q)` per tile: arena 772 OOF (2x), 13 won; OOF set 1909, 24 won (lethal builds threats/Reach on
    fuel-short turns).
  - bound-lethal (GuardFoes::bound's champion damage x taken >= health + shield; no host queries): arena 472
    (+20%), 13 won; OOF set 1323 (+13%), 26 won; step-guard-sim 74 -> 1214. Level on wins, more OOF: a non-null
    guard also makes the later routes search around it.
  So at today's fight-turn cost the fail-open gate is the cheapest and plays at least as well; FUEL-AUDIT 1.1's
  cover fallback should not be shipped as is.
- Prey: not changed. Its gate fires before the first candidate in 1489 of 1986 cuts (fuel left p50 32k); a
  candidate costs ~12k (fight_key 4.2k with Reach builds 1.5k and at() 1k; chase_trade 5.8k, the sim 3.5k), so a
  budget that keeps one candidate adds ~12k on those turns, which the guard budget shows runs out.

Open leads:
- The gates can go only once a fight turn is ~10k cheaper before the guard (search read/grow, want_home's stand and
  lethal, world update), or the guard's U1-won path (8.5k) is far cheaper; a sims-only budget cannot do it.
- Sims: 32% end at the first early-end check (~480 each); early-end checks are ~25% of sim fuel (~640 each,
  2.3 a sim); acts 74%. Cross-turn repeats 6% (no memo).
- Guard bound loop 2.1k a placing (exposed-tile emission); `step_guard_cover` repeats ctor + expose + loop when the
  guard is resolved after a route's cover (~1k, est. <0.1%).

## Merge round 3 (merge agent; fuel2-late + fuel2-fightgates, CHANGES 249)

Both code changes (1e31a3cc, 80689194) reviewed exact and merged; fuel2-fightgates is NOTES only. Checked, for the
post-search early return: at k = 0 the old post-loop code returned false when banking, checked staleness, set claim
-1 / crew false and then, best < 0 with k = 0, claim = farm_group, crew = crew_of_choice and walk_on(farm_group). The
return does the same, with crew read from unchanged memory (nothing between the old and new reads writes it), and
walk_on's captures (previous, zone, cross) are set above it. Nothing skipped writes memory. The skipped calls fill
only exact caches: to_any_altar (also built by bankable_bag, banks_bag and warm_up), Safety's memos,
nearest_groups, worth_gems. `note_shortcut`, `recall_farm` and the loop's `static led` are not reached at k = 0.
`costliest_field`/`max_field_layers` move only through fields the skipped code builds, and they are read by fuel
gates and one static, `farm_dash_kind`'s. That static is fixed at the first non-opening call: if that call is a
post-search one, it is now fixed at the next call. Hoisting it above the return doesn't help, because the old order
could build to_any_altar (via farm_recall -> closing) before it. The kind only picks which source gives the same
steps, so it was left. For 80689194, `prepare_member` returns true at once for drafted groups before any side
effect.

Bot frozen as `astraeus-orch2-m3`; JSONs in `MAIN/replays/fuel/orch2/m3-{wide,oof,mg}-100M.json`,
`m3-{wide,oof}-real.json`; A/B log `ab-m3.log`, `ab-m3-oof.txt`.
- 100M wide: 52/52 identical to fb0. Against fb0 / m2: total -1.50% / -0.24%, mean 47800 / 47193 -> 47082, p99 98887
  / 97280 -> 96742, max 296169 / 296109 -> 296109, over 100k 2308 / 2102 -> 2011, round 1 max 279479 / 275911 ->
  274367. Turns cheaper 142035, dearer 5330 against m2.
- 100M OOF set: 48/48 identical. Against fb0 / m2: total -2.56% / -0.51%, mean 52116 / 51041 -> 50782, p99 122855 /
  118572 -> 117458, max 443323 / 443251 -> 441622, over 100k 9235 / 7464 -> 7186, round 1 mean 231954 / 228190 ->
  227136, round 1 max 414176 / 375808 -> 370476. Cheaper 124238, dearer 6334 against m2.
- 100M many-group set: 24/24 identical. Against fb0 / m2: total -4.63% / -0.39%, mean 56622 / 54211 -> 53999, p99
  120015 / 112766 -> 111640, over 100k 3894 / 2592 -> 2489, round 1 mean 226451 / 219451 -> 217920.
- Real budget: OOF wide 605 / 468 -> 473 (20/52 replays identical to m2), OOF set 1547 / 1175 -> 979 (0/48).
  OOF-set shortcuts against m2: farm-partial-evaluation 10496 -> 10959, comms-stale-vision 2747 -> 2561, turn-order
  1981 -> 1723, step-guard-entry 7407 -> 7424, step-guard-look 769 -> 889. Wide: step-guard-entry 2740 -> 3045,
  prey-cut-short 1091 -> 1388, farm-partial-evaluation 3070 -> 2970 (diverged games, small sample).
- A/B against fb0, real budget, own drafts: 49.9% of 1164 (47.0-52.8; ladder 45.7 of 140, gen 50.6, gen-s1 50.4).
  OOF 3232 against 4398 (-26.5%; the mirror was 4382, round 2's CAND 3508). By round, CAND/REF: 1 333/401, 2-10
  304/409, 11-60 272/655, 61-300 537/898, 300+ 1786/2035. Champion-game runs: <10 2125/3125, 10-49 764/1205, 50+
  343/68.
- The 50+ runs: 280 of CAND's 343 turns are one champion in one game, gen-topo-shortcut-600106907 order 12 (359 OOF
  on team A; m2 had 3 there, fb0's mirror 4). It reproduces with `bench.py --fuel 0` (358). Champion 2 is in the bank
  branch (`D .. B`) every turn from round ~180 to 836, alternating (6,3) and (7,3) and running out in `decide` every
  other turn: TODO's first section, item 2 (carry flips between bank and chain at a boundary). There are no enemies
  in sight, so no strike search runs and neither change fires on those turns: the real budget diverged the game into
  the loop. A census-instrumented copy diverges again (2 OOF), so the census can't trace it. Without that game CAND
  has 2873. Campaign target (-50%) not yet reached: -26.2% against the mirror.

## Strike search (worker; branch fuel2-search)

Profile (m3 = fuel-orch bf6db460, 100M, debug copies with raw `fuel()` laps through read, grow and price, replays
identical to m3; fight set = the 10 `maps/gen-s1/*arena*`, 01elk-arena, adgato-gemcombat5, gen-atoll-600101912,
gen-gem-drought-600105820, gen-monolith-only-600101500, own drafts vs fb0, 30 games):
- 42.2k searches, 778M = 9.4% of the set's fuel; mean 18.4k, p90 34k. Read 7.7k: guard cover 3.3k, foe loop 2.3k
  (preamble with the Search ctor 0.8k, fill 0.47k, viewers 0.65k), `read_grid(blocked)` 0.87k. Grow 2.8k (settle
  0.96k). Price 6.9k: resolve_guard 2.6k, loop 1.7k, blow 0.7k, tile setup 0.7k, strikers 0.4k, goal_field 0.4k.
  Searches of 30k+ (14%): cover 7.5k + resolve 16.2k (half of them), grow 7k, loop 4k, blow 2.6k.
- 33% of searches offered the start tile alone and did nothing (9.6k mean, 17% of search fuel). Most have a foe within
  `strike_possible`'s bound (ability_range + 1 for everyone) but beyond what the champion can strike this turn
  (Marcella 56%, HoR 32%, Issac, Vesper unable to walk, Ryth, Tavi).

Commit 923b7fc1 (100M byte-identical: wide 52/52, OOF set 48/48, fight set 30/30, vs m3; the wide set is on test
drafts, so HoR, Ren, Stellar and Ryth in most games): `strike_free` shows, by read()'s own distance tests, that no
strike from any end tile reaches a foe (basic attack: range + walk + ready dash + Varg's splash; unit casts: reach + 1
unless they exclude walking; ground casts: reach, and no unseen tracked enemy; HoR's landing: walk + dash + radius),
that no leaf without a strike exists (a ranged walk alone, a heal, a reset alone beside a kept shield, Vendetta's
camp kill), and so the search would choose the start tile with nothing done, or with the shield cast when it would
absorb anything there; it does that without read, grow and price, setting `searched` as the search would and leaving
pathing's guard state as read_geometry and the act loop do. `debug_strike_free` runs the whole search beside it:
0 misses in 26.4k shortcuts (fight + OOF sets). How it differs from what was dropped: W7 "can't skip (sets
`searched`)" (the result is reproduced, not skipped); CHANGES 222's idle skip stops at strike_possible's coarse
bound and returns `searched` false, this proves the search's answer; Phase 2 B's cost moved onto fight turns (here
the remaining searches pay a distance pre-pass, p50 82; ready slots are shared with read()).
- Wide: total -0.48%, mean 47082 -> 46856, p99 96742 -> 95137, max 296109 -> 296849, over 100k 2011 -> 1832, round 1
  unchanged; cheaper 9557 turns (60.2M), dearer 9862 (4.6M: p50 315, p90 1012, max 7382; mostly the 80-100k queue
  turns and caches the skipped reads no longer warm: viewer rows, terrain grids, Reach builds).
- OOF set: total -0.68%, mean 50782 -> 50436, p99 117458 -> 116832, max 441622 -> 441999, over 100k 7186 -> 6932;
  cheaper 15.5k turns (104M), dearer 30k (9.0M: p50 82, p90 700).
- Fight set: total -1.19%, mean 44588 -> 44054, p99 110801 -> 108866, over 100k 3049 -> 2806.
- Real budget (OOF): OOF set 979 -> 949, fight set 443 -> 417, wide on test drafts 473 -> 550, wide on own drafts
  (`--set wide` without `--test-draft`, both bots run now) 317 -> 296; summed 2212 -> 2212. Shortcuts fall where the
  search's fuel went to gated work: step-guard-entry 7424 -> 5786 (OOF set), 3045 -> 2655 (wide), 7057 -> 5571
  (fight); prey-cut-short 2012 -> 1551, 1388 -> 1109, 1822 -> 1373. The wide (test drafts) rise is spread over 20
  diverged games (00corners-b 5 -> 26, 00contest-b 25 -> 41, gen-chambers-102206117-a 122 -> 147, 01hooks-a 9 -> 2);
  three variants of the commit read 522 / 555 / 550 there, but they play alike. Not traced; the A/B decides.
- Debug builds no longer print a SRCH line for the searches shortcut (tools summarising SRCH lines count fewer).

Measured, not changed:
- The guard inside price (gprof copy: a line at every Pathing::guard() ask and resolution). On the fight set the
  search resolves the deferred guard in its pricing loop (the top tile may be guarded) on 4252 searches, 95M (1.1% of
  the set's fuel), and the guard is asked again later in the same turn in only 566 of them; upfront (`sure < 2`) 698,
  12M; in read_geometry for Willow's coverless guard 5002, 52M. In 3268 of the 4252 the chosen tile is outside the
  cover, and in 1100 (19M) no cover tile was priced to the end nor guarded: pricing first and resolving only for a
  tile not cut would skip those (with the query cap counted over unresolved tiles). Not exact as it stands: the guard
  left deferred is then worked out by the turn's later route from the world after our hits, not from the search's.
  It needs the guard's inputs frozen at the search, or a proof that nothing it reads changed.
- After the commit, by why the search still runs (fight + OOF sets, 57k searches, 1.31G): a foe within strike reach
  (HoR, Marcella, Vendetta: 13.3k, 415M, mean 31k: read 9.1k, grow 7.0k, price 14.3k); ranged with its walk leaf and
  a foe in reach (Vesper, Tavi, Willow: 23.8k, 540M); ranged with its walk leaf and **no** foe in reach (11.3k, 186M,
  mean 16.5k: read 8.4k, grow 2.5k, price 5.3k); Willow's heal (3.3k, 80M, read 17k: her coverless guard and
  read_mates).

Open leads:
- Walk-only search: when strike_free fails only on the ranged walk leaf, the leaves are the walk alone, the start
  tile and a lone reset; grow could settle those three and read skip the foe fill, viewers, spells and landings
  (est. ~4k a search, 11.3k searches: ~0.2% on fight maps). Needs the Front offer order kept and the HoR health factor
  (`hors`, `h`) still read.
- Lazy pricing guard (above): ~19-48M of 95M on the fight set if made exact.
- Willow's guard (no cover) is resolved in read_geometry on every search that moves (~10k each).

## Small fuel shortcuts (worker; branch fuel2-gates)

Each gate measured alone at the real budget (`--fuel 0`) on the wide set (52 games vs hecate, test drafts) and the
OOF set (48 games vs fb0), against m3's `m3-*-real.json` (OOF play turns wide 473, OOF set 979; won 50/52, 29/48).
Every variant's 100M replays are byte-identical to m3 on both sets. Per-game OOF swings of +-40-70 in both directions
are common once a game diverges, so a few percent on either set is noise.

| Change | Kind | OOF wide | OOF set | won (wide, OOF) | Verdict |
|---|---|---|---|---|---|
| comms-stale-vision: always observe after moving | remove | 412 (-13%) | 921 (-6%) | 51, 28 | kept |
| turn-order: gate removed | remove | 642 (+36%) | 1288 (+32%) | 51, 25 | dropped |
| turn-order: fall back to plain priority, not the kept rank | fix | 639 (+35%) | 1084 (+11%) | 50, 23 | dropped |
| farm-no-route: always search (capped) | remove | 481 (+2%) | 978 (0%) | 51, 28 | kept |
| crow-flies-farm: skipped approach descends cached `from_centre(g)` | fix | 475 (0%) | 1026 (+5%) | 50, 27 | kept (borderline) |
| farm-kept-target: skipped approach keeps the choice (centre field, else last approach, no claim/crew rewrite) | fix (+crow) | 505 (+7%) | 998 (+2%) | 49, 30 | kept (borderline) |
| ward-no-bushes-fuel: first check dropped | remove | 468 (-1%) | 962 (-2%) | 50, 27 | kept |
| static-descend: always run the capped search | remove | 389 (-18%) | 1090 (+11%) | 50, 28 | dropped |
| fight-cut: simulate never cut | remove | 461 (-3%) | 966 (-1%) | 50, 28 | kept |

Combined (real budget, against m3):
- comms + fight-cut + ward + farm-no-route + crow: wide 417 (-12%), OOF set 934 (-5%); won 51, 30.
- the same + farm-kept-target (branch tip): wide 417 (-12%), OOF set 923 (-6%); won 51, 30. crow-flies-farm 237 ->
  59 / 531 -> 96; farm-kept-target 35 -> 1 / 87 -> 0; comms-stale-vision, farm-no-route, ward-no-bushes-fuel and
  fight-cut 0. farm-partial-evaluation 2970 -> 2758 / 10959 -> 9904; step-guard-entry 3045 -> 2775 / 7424 -> 7209.
  ward-no-bushes-clusters rises (95 -> 110 / 167 -> 229): the turns the first check used to stop now reach it.
- the same + static-descend: wide 403 (-15%), OOF set 1156 (+18%). static-descend raises the OOF set alone and
  together, so it stays.

Why turn-order stays: falling back to `plain_priority` still pays `read_strike` and `danger` on a fuel-short turn, and
the removal pays the bids too (FUEL-GATES: `offer_escape`'s `threats_at` 9-14.5k, `offer_kills`, `offer_heal`). Both
lost wins on the OOF set. Bound the offers first; then retry the plain-priority fallback.

Left without a change: siege-route-fuel (wide ~30, OOF set ~2-6), siege-no-tiles and spell-clear-no-tiles (single
digits): each needs FUEL-AUDIT 9's fixed cap with a static-field fallback or 7's approximate attack tiles, which are
designs rather than gate deletions; at these counts they cannot move OOF turns.

## Fight turns' fixed cost before the step guard (worker; branch worktree-agent-a75a3c6b8ed7a9cf4, NOTES only)

Profile (m3 = fuel-orch bf6db460; scripts and diffs in scratchpad `world/`):
- **Gate snapshot** (debug copy printing the census state at each step-guard-entry check; real budget, OOF set, 48
  games vs fb0): 2871 fired entries had spent 62.3k mean (p10 45k, p50 62k, p90 80k; fuel left p50 38k against 50k
  needed); 3075 passing entries had spent 42.6k. A fired entry's 62k: world 12.0k; want_home ~15k, mostly asked inside
  continue_recall (the "channels" scope, 76% of entries, 11.2k with recall_to_bank etc.) plus 4.0k outside it (s.stand
  6.5k, s.lethal 4.0k whose damage_ceiling is the turn's first strikes 1.7k and Reach builds 2.1k, outmatched 1.6k,
  camp_trapped 1.2k); then the strike search 8.8k closed + 22k open in 29%, chase 6.4k and the goal. Fired prey checks
  (581) had spent 64k, 24k of it in the search.
- **World::update at 100M** (uncharged laps in debug_block, OOF set, 44k turns with enemies in view): 10.9k = camps
  3.1k (groups in view and not settled 2.1k at 1.8 a turn, ~1.2k each; settled checks 0.63k at 3.9), allies 1.7k
  (items 0.56k, cooldowns+shield 0.23k, info 0.17k, stats 0.16k, channel 0.12k), rank_turns 1.5k on 99% of these turns
  (passes 0/1 ~700, 2/3 ~360, ~5 champions a team; priorities change every fight round, so stale every turn), unseen
  enemies 1.4k (track 1.15k at 2.85), visible enemies 1.4k (items 0.42k, fix+stats 0.35k), priorities 0.77k, altars
  and scores 0.54k. Turns with no enemy in view: 8.3k. Everything is per-entity reads at 30-180 each: no single piece
  is skippable at scale.
- **want_home at 100M** (34k turns that reach stand): 9.9k = stand 3.9k (its own trade 5.0k on 26%, fill 2.6k on 26%
  (the turn's first fighters, reused later), memoised fight_of 5.6k on 11%), lethal 2.5k (ceiling 2.36k: strike_foe 1.1k,
  Reach 0.5k: first touches the search and guard reuse), camp_trapped 1.6k (find_members 1.5k on 82%, reused),
  outmatched 0.9k. What only want_home pays is stand's own trade (~1.3k a turn on average); the rest is shared work it
  touches first, so moving or memoising it does not lower the pre-guard total.
- **retreat_step** runs on 17.4k turns at 100M (6%, mostly arena/atoll/dash-lattice), 12.5k each: the option loop
  11.1k on 65% (damage_bound 1.5k a neighbour at 5.4 a call; the unseen any_within is only ~0.2k of it on these small
  maps, the rest visible Reach::at and the camp sum), avoid 2.4k, the avoid step 1.4k. flee_camps 5.5k (damage_bound
  2.9k, exit_hits 1.1k).
- **camp_damage's member loop**: 422 a turn over all turns (0.8% of fuel), 340 a call at 10.9 members (~31 a member);
  1.2-2.4k a turn on the-pack, topo-duel, mega-groups, rivers; p99 5.4k a turn. tie_hit 230 a turn.
- set_turn_order: no exact cut in its Safety queries. Its gate is a fixed threshold (end_reserve) checked before any
  of its work, so a cheaper turn order does not change how often it fires; removing it needs a bounded fallback and an A/B.

Conclusion: the ~10k pre-guard cut the gate removals need is not in this area as exact cuts. Pre-guard fight turns are
world 12k + want_home ~10k + shared first-touch builds; the pieces only one consumer pays are World::update's
per-entity reads and stand's own trade (~1.3k).

Dropped (all 100M byte-identical on wide 52/52, OOF set 48/48 and, for the second, the many-group set 24/24; vs m3):
- Emblem reads skipped when the champion cannot have shopped since our last read (exact by the rules: shopping needs its
  own spawn, death, or Tavi; between our turns it has at most two turns of a teleport landing within 3 plus 3 king steps,
  so with the last read's tile and its tile now both more than 6 from its spawn's bounding box it never stood there).
  Wide -0.05%, OOF +0.05% (dearer 128k / cheaper 131k turns), round 1 +0.2%. The skip applies to only ~25-50% of reads
  (arena maps are mostly within 6 of a spawn) and an items read is ~80-100 in release. Diff: scratchpad `world/emblem-skip.diff`.
- camp_damage over SIMD lanes of awake_members (in_square mask four members at a time, hits summed in member order,
  so the floats are identical): +0.33% wide / +0.33% OOF / +0.44% mg, dearer on ~97% of turns. Building the lanes only
  from a Safety's third query (+0.35%) and moving the lane path out of line (mg +0.46%) changed nothing, so the cost is
  a codegen effect of the change elsewhere in the unity build, not the lanes' work. Diff: scratchpad `world/camp-lanes.diff`.

Open minor items (not tried):
- Each unseen foe's any_within in each_threat, for queries within 1 of our tile (retreat_step, flee_camps,
  quote_escape_walk, mend_step): within(possible, here, reach - 1) non-empty settles all 9 as near, within(.., reach + 1)
  empty settles all as far. Est. ~0.5-1k a retreat turn on 100x100 maps, ~0.1% overall.
- update_camp: a member read dead (health 0) in a group alive and in view last round stays dead (camps never
  regenerate, and a respawn takes 40+ rounds), so its camp_health read can go (keep the visible test for health_round).
  ~40 a dead visible member a turn.
- read_priorities: `priority` this round equals last round's `next_priority` for a champion that had acted when we read
  it last round: one host call (~36) each. ~0.2k a fight turn.

## Merge round 4 (merge agent; fuel2-search + fuel2-gates + the world/want_home profile, CHANGES 250)

Reviewed:
- 923b7fc1: the shortcut runs only when the search would offer the start tile alone (1) or with the shield (3).
  When the search ran, it priced that one tile (`sure` is 1 because `maybe_guarded` excludes our tile, so there is
  no upfront resolve), chose it exact, so `searched` was true, and in case 3 cast the shield, with `failed` (and
  `strike_enemy`) only when the cast was refused. The act loop's `held_guard` / `set_guard(nullptr)` / `restore_guard`
  nets to `route_cover_round_ = 0` with the guard state as held, which `restore_guard(held_guard())` reproduces.
  read_geometry's only state change, working out a guard deferred without a cover, is repeated. The rest of
  read/grow/price writes only per-search tables (`plan_tables`, keyed by per-Search masks) and exact caches (viewer
  rows, Safety memos, `search_box`). `ready` is shared with read(), so its slot reads are the same.
- Gates: every `trade()`/`simulate()` call site was updated for the dropped `fuel_floor` (no shifted positional
  bool). The commits add no fuel read. 844ba6fc/e922dede change only the `approach_skipped()` branch, which needs
  fuel short. `from_centre` is a cache lookup.

100M (final bot): wide 52/52, OOF set 48/48 and many-group 24/24 identical to fb0. Against m3: total -0.48 / -0.69 /
-0.33%, over 100k 2011 -> 1828, 7186 -> 6923, 2489 -> 2439; turns cheaper 34.5k, dearer 9.9k (wide). The full
merge (with the two dropped removals; `m4full-*`) was identical too.

Real budget, full merge (`astraeus-orch2-m4full`): OOF wide 473 -> 584 (143 of the rise is gen-chambers-102206117,
both sides), OOF set 979 -> 849. A/B against fb0 51.4% (48.5-54.2), OOF 3293 / 4365; **against m3 50.7% (47.8-53.6),
OOF 3381 / 2895 (+17%)**: round 1 450/333, 2-10 519/308. Bisect, each against m3 (1164 games; `ab-m4*-vs-m3.log`):

| variant | win | OOF CAND / REF | round 1 | 2-10 |
|---|---|---|---|---|
| search only (923b7fc1) | 50.1% (47.2-53.0) | 2895 / 2904 | 334 / 333 | 305 / 309 |
| gates only (e922dede) | 51.5% (48.6-54.3) | 3441 / 2756 | 449 / 333 | 521 / 306 |
| full merge without comms-stale-vision removal | 49.8% (47.0-52.7) | 3164 / 2919 | 385 / 333 | 401 / 308 |
| full merge without farm-no-route removal | 51.0% (48.2-53.9) | 3180 / 2870 | 403 / 333 | 404 / 308 |
| full merge without both (final) | 50.2% (47.3-53.0) | 3015 / 2967 | 337 / 333 | 313 / 309 |

So ff74eb1b and aaff6f4f were reverted (e6ddf2f6, 8c6a8666). m3's REF count ranged 2756-2967 across these runs
(diverged games), so the final's +48 is noise. Rounds 1-10 are heavy turns where an extra observe (~1-2k) or a
route search no longer skipped for fuel tips the turn over. The small benches missed it: their 52/48 games have few
round 2-10 OOF turns and swing by +-40-70 a game.

Final bot frozen as `astraeus-orch2-m4` (MAIN and worktree); JSONs `MAIN/replays/fuel/orch2/m4-{wide,oof,mg}-100M.json`,
`m4-{wide,oof}-real.json`; A/B logs `ab-m4.log` (vs fb0, batches `*-ab-orch2-m4-final-*`), `ab-m4-oof.txt`,
`ab-m4-shortcuts.txt`, `ab-m4nn-vs-m3.log` (final vs m3).
- Real budget: OOF wide 605 / 473 -> 434 (fb0 / m3 -> m4; won 50/52), OOF set 1547 / 979 -> 1021 (won 29/48).
  OOF-set shortcuts against m3: step-guard-entry 7424 -> 6172, prey-cut-short 2012 -> 1658, crow-flies-farm 531 ->
  168, farm-kept-target 87 -> 33, ward-no-bushes-fuel 374 -> 0, farm-partial-evaluation 10959 -> 10803.
- A/B against fb0: 50.9% of 1164 (48.1-53.8; ladder 50.7, gen 52.0, gen-s1 50.0). OOF 3105 against 4465 (-30.5%).
  By round, CAND/REF: 1 337/401, 2-10 310/409, 11-60 254/660, 61-300 539/926, 300+ 1665/2069. Champion-game runs: <10
  2191/3217, 10-49 836/1104, 50+ 78/144 (m4's one: mut-the-pack-600101820, champion 1, 78 turns). Shortcuts per bot
  127960 against 155972.
- A/B against m3 (the final's code, run as `astraeus-orch2-m4nn`): 50.2% (47.3-53.0), OOF 3015 against 2967; shortcuts
  127799 against 139389 (step-guard-entry 29116 / 35018, prey-cut-short 8200 / 9781, crow-flies-farm 2104 / 3690,
  farm-kept-target 485 / 1082, ward-no-bushes-fuel 0 / 1589).

## Turn order's offers (worker; branch worktree-agent-aa46d1597dd64c94a)

Profile (m4, 100M, fight set = the 10 `maps/gen-s1/*arena*`, 01elk-arena, adgato-gemcombat5, gen-atoll-600101912,
gen-gem-drought-600105820, gen-monolith-only-600101500, own drafts vs fb0, 30 games; a debug copy timing each offer
and, inclusively, find_members, Reach builds and compute_strike inside set_turn_order; the 1 MiB stdout cap keeps
~128k of 186k turns, mostly the earlier rounds; scripts in scratchpad `turnorder/`):
- Per call: mean 1.9k, p50 1.7k, p90 4.0k, p99 7.1k, p99.9 11.4k, max 21.3k. Calls of 10k+: 0.2%.
- **No Safety query here recomputes a dearer answer the turn already has.** find_members runs in 4.7% of calls
  (mean 28 a call, 0.8k on 10k+ calls), Reach builds in 0.2% (1.2k on 10k+ calls), compute_strike misses ~20 a call:
  the turn's Safety already holds the members, the strikes and most Reaches. The cost is our own loops over the few
  champions (~2-3 fuel an instruction): offer_kills 0.35k mean (2.7-3.0k on 8k+ calls: side_damage's rank and strike
  per ally per enemy 1.3k, can_act_before 0.5k, enemy ranks 0.3k), may_escape 0.35k (2-2.8k: the seen loop's
  strike_of, turns_before_ours and slots), plain_priority 0.5k (danger's per-enemy strikes 0.9k; tie_hit 70),
  offer_escape 0.07k (3k on 10k+ calls: threats_at with its Reach builds), offer_heal 0.06k (1.2-1.4k), live
  enemies and read_strike 0.2-0.5k.
- Commit 4ff80ffc: a champion farther than `Strike::max_reach` adds 0 to every sum here (`Strike::at` and `hits`
  stop at its reach, which compute_strike and threat_strike clamp to max_reach), so danger, side_damage, offer_heal
  and may_escape's seen loop skip it before its strike, ranks and turn rounds. 100M byte-identical vs m4: wide
  52/52, OOF set 48/48, fight set 30/30. Total -0.07% / -0.15% / -0.22%; mean 46853->46821 / 50433->50357 /
  44049->43953; p99 95108->94998 / 116816->116707 / 108826->108735; max 296755->296577 / 441788->442203 /
  441788->442203; over 100k 1828->1811 / 6923->6870 / 2805->2785; round 1 unchanged. Turns cheaper 32.6k / 67.9k /
  59.9k (10.3M / 25.7M / 22.0M), dearer 23.1k / 40.8k / 40.9k (2.4M / 4.8M / 4.3M; p50 21-29, p90 ~200, p99
  2.2-2.8k, max 8.6k / 24k / 24k: the turn-end queue filling the fuel saved; turns 80k+ at m4 net -0.9M / -2.9M /
  -1.3M). set_turn_order on the fight set: mean 1908 -> 1820, p50 1737 -> 1645, p99 7133 -> 6926, p99.9 11423 ->
  11288, max 21312 -> 20535 (plain_priority 521 -> 441). Real budget vs `m4-*-real.json`: wide 434 -> 452 OOF
  (diverged games, noise), turn-order 662 -> 673; OOF set 1021 -> 1020, turn-order 1774 -> 1772.
- **Gate removal not retried**: the worst case is not bounded under 10k (p99.9 11.3k, max 20.5k at 100M), and the
  gate checks a fixed reserve before any of this work, so a cheaper turn order barely changes its firings. The
  round-4 removal (+36% / +32% OOF) stands until the tail goes.

Open leads (each exact, each small):
- side_damage: test an ally's strike at the tile before its rank (ally_next_rank loops over the allies, per ally per
  enemy), and stop summing once the kill is shown (every term >= 0): ~0.3-0.8k on heavy offer_kills calls, ~0.02%.
- offer_escape's tail is threats_at's Reach builds for visible enemies in reach (1.5k on 10k+ calls), Reaches later
  queries would build anyway: only a cheaper Reach helps.
- The walk-only strike search (Strike search's open lead) was not attempted this round.

## Rounds 1-10 (worker; branch worktree-agent-afeecac8fce7a194b, 46b1e45d, 7f2d2424)

Profile: the m4 A/B's rounds 2-10 OOF turns are not on many-group maps but on maze-like ones (topo-tree, topo-backdoor,
topo-split, topo-odd-spawn, topo-shortcut, 00ambush, 01yellow-brick-road, 01big-world, dash-lattice, archipelago,
islands), 104 of 310 first-in-streak in round 2, 55 in round 3. Census `--trace` on m4 (22 such maps, 44 games vs fb0,
real budget; scratchpad `early/cen`): 206 traced rounds 2-10 run-outs, 60% of them before any fuel check. Their work:
spawn floods made cold because round 1's overrun skipped the queue (`foot` 64 calls x 19.8k, `dash_foot` 28 x 23.9k,
`landing_dash_foot` 17 x 22.2k, `hops` 43 x 14.7k), centre fields (`approach_walk/field/make_field_cap` 46 x 25k, rounds
2-3), `track -> champion_enemy` 4.7k, `recall_line -> wh.outmatched` 7.5k. A 100M debug log of build order (228
instances): foot was made after the spawn field in 162 (its flood is the field's visited board), dash floods always
before the dasher's spawn field (rounds 11+). Stacks: foot under farm/group_hops (make_group_hops(0) on the second
turn, which reads no hop) and under channels (bank.cc's `test(foot(), here)`).

Commits (100M byte-identical to m4: wide 52/52, OOF set 48/48, many-group 24/24):
- 46b1e45d foot() is the spawn field's flood: made together (the field's `visited`), so neither waits for the other.
  Boards byte-equal (padding included) on 599 builds. Total -0.04 / -0.02 / -0.02%.
- 7f2d2424 the first turns' foot tests without map-wide floods: make_group_hops(0) returns at once;
  `Pathing::on_foot(p)` proves p on foot by a radius-8 flood meeting the spawn, else tests foot (checked 146/146);
  dash floods grow from foot (a field rooted on foot over the dash walls, a subset of blocked_for_us; byte-equal 9/9);
  the queue makes a dasher's foot after the map warm-up. A first version without the cached pointer and queue warm
  cost +41 a turn (p50), +0.04% total.
- Together vs m4 (100M): total -0.05 / -0.03 / -0.03%; rounds 2-3 mean 98394 -> 96717 / 109790 -> 108334 / 103764 ->
  102268, p99 211115 -> 194372 / 245692 -> 232248 / 196525 -> 187683; round 1 level.
- Real budget, OOF play turns by round (1 / 2-10 / 11-60 / 61-300 / 300+), m4 -> both: wide 3/16/42/83/308 ->
  3/10/40/70/331 (total 452 -> 454; 300+ is gen-chambers-102206117, chaotic); OOF set 63/74/86/255/655 ->
  63/53/101/246/655 (1133 -> 1118); the 22-map early set 111/206/48/135/146 -> 108/134/66/120/137 (646 -> 565).
  Rounds 2-10 -29% to -38%; later buckets move with diverged games.

Open (not done):
- Centre fields on rounds 2-3 (`approach_walk` building `make_field_cap`, ~25k): round 1's queue never reaches
  warm_centres on these maps. The draft could send the first farm target's centre-field cap, or the queue could warm
  the farm choice's centre before the map warm-up's group hops (order change, exact).
- Round 1 itself is unchanged (~108 of the early set's OOF turns): build_static (static_camps) and init_beliefs.
- `crossings` (find_crossings, dashers only) is ~21k on round 1 on these maps; its per-member set_tile loop for
  non-striking members could be a board op (drop the cluster tiles).

## Merge round 5 (merge agent; turn order's offers + rounds 1-10, CHANGES 251)

Reviewed:
- 4ff80ffc: `Strike::damage` has max_reach + 1 entries and every reach is clamped to max_reach (compute_strike's
  `add`, which covers dash landings, Varg's splash through `basic_reach`, ground and unit casts; threat_strike's
  widening), so `at(d)` is 0 and `hits(d)` false beyond it. offer_heal's next-turn basic blow needs d <= basic reach
  + 1 and the heal itself is outside the loop; danger's camp damage is outside it. `outgoing` and `incoming` start
  at 0 and only get max / + 0 from a skipped term. may_escape's `n` counts only hits. The skipped `strike()`,
  `next_strike()` and `strike_of()` calls only fill memos keyed on everything they read.
- 46b1e45d / 7f2d2424: the field's goals are `ally_spawn` minus walls, so its `visited` is the flood from the
  spawn, the same as foot's flood from `ally_spawn_tiles[0]` (a connected rectangle). dash_walls and
  landing_dash_walls are blocked_for_us minus crossable tiles plus some of them back, and crossable is cut to holes
  and altars, so foot holds no dash wall and a field rooted on it gives the dash flood of the spawn tile's
  component. on_foot floods over `static_walls()`, the walls of the same dash kind as `foot()`, from our own tile
  (never a wall); meeting the spawn proves p on foot by symmetry of the king-step flood, and every other case falls
  back to `test(foot(), p)`. make_group_hops(0) built only boards that their accessors build lazily. The queue step
  reads fuel only to choose whether to precompute. Nothing dropped.

100M (`astraeus-orch2-m5`): wide 52/52, OOF set 48/48 and many-group 24/24 identical to fb0. Against m4: total
-0.12 / -0.19 / -0.16%, over 100k 1828 -> 1803, 6923 -> 6865, 2439 -> 2405; p99 95108 -> 94968, 116816 -> 116721,
110915 -> 110736; turns cheaper 182.3k, dearer 63.1k (wide).
- Real budget: OOF wide 605 / 434 -> 462 (fb0 / m4 -> m5; +20 on gen-chambers-102106111, both sides, diverged late
  games; 00ambush and 01hooks the rest), OOF set 1547 / 1021 -> 1019. Shortcuts (out-of-fuel included) wide 11190 /
  9197 -> 9279, OOF set 31668 / 26282 -> 25557.
- A/B against fb0: 50.8% of 1164 (47.9-53.6; ladder 50.7, gen 50.4, gen-s1 51.2). OOF 3084 against 4499 (-31.5%).
  By round, CAND/REF: 1 336/401, 2-10 236/408, 11-60 265/664, 61-300 537/966, 300+ 1710/2060. Rounds 2-10 fell
  310 -> 236 from m4's A/B, as the rounds 1-10 worker measured; 300+ rose 1665 -> 1710 (diverged games). Champion-game
  runs: <10 2144/3227, 10-49 862/1128, 50+ 78/144. Shortcuts per bot 126555 against 155690 (farm-partial-evaluation
  53516 / 60179, step-guard-entry 29501 / 37088, comms-stale-vision 10228 / 13391, prey-cut-short 8599 / 10080,
  turn-order 6859 / 8742, crow-flies-farm 1984 / 4405, farm-no-route 1811 / 2716).

Final bot frozen as `astraeus-orch2-m5` (MAIN and worktree); JSONs `MAIN/replays/fuel/orch2/m5-{wide,oof,mg}-100M.json`,
`m5-{wide,oof}-real.json`; A/B `ab-m5.log` (batches `*-ab-orch2-m5-*`), `ab-m5-oof.txt`, `ab-m5-shortcuts.txt`.

## quill: run-out forensics (worker; branch worktree-agent-a079390925ba6ceb1)

quill (main 3c492dbe, `astraeus-q0`) against the pre-quill bot (309b1dc3, `astraeus-pre-q`) and f33d8e6.

**Where quill's extra run-outs are.** The 20,480-game real-budget A/B against f33d8e6 (`MAIN/replays/batch-20261031-145444-ab-qmain-vs-f33d8e6-*`, OOF lines per bot): 118,617 / 84,711. By round, quill / f33d8e6: 1 22,502 / 8,299, 2-10 13,818 / 7,489, 11-60 16,262 / 14,106, 61-300 23,401 / 20,674, 300+ 42,634 / 34,143. Round 1 is 42% of the excess and spread thin (+1.4 a map over 4,330 maps); the rest sits on topology maps (topo-shortcut +2,776, topo-backdoor +1,481, topo-necks +1,287, topo-odd-spawn +1,243, close-spawns +992, dungeon +948, far-spawns +892), in a few long runs (games with 200+ OOF turns: 13 against 4). quill runs out less on mega-groups (-1,198) and cluster-carpets (-842). The orchestrator's OOF set (fb0's heaviest maps) is level (q0 1069, pre-q 1114), so a **quill set** was built: the 24 fresh-98xx maps with the largest quill excess in that A/B (list in the session scratchpad `quill-oof/qset.txt`; close-spawns-987904808, topo-odd-spawn-987907106, topo-shortcut-989706930, far-spawns-988604903, topo-backdoor-987806707, dungeon-989402413, topo-necks x3, topo-island x2, topo-shortcut x3, mega-groups-988408208/986608207, archipelago-989202003, topo-tree-986106400, mut-hooks-989701801, dash-lattice x2, topo-backdoor-988806741, big-groups-988106103, mut-tangle-988101816). Real budget vs fb0, own drafts, 48 games: q0 7507 OOF turns, pre-q 1418 (the A/B's own games: deterministic).

**100M profile** (debug fuel probes, 12 games: mega-groups-600108204, the-pack-600201800, 01yellow-brick-road, dungeon-600102424, 00monolith, 01boss-battle): `plan_crew` is 1.095G of ~4.4G total (25%), 293k calls, 1.36 pricings a call. Inside: `share_damage` 503M (1.26k a pricing), the available-ally loop (`crew_available`) 212M, `crew_tank` 178M, the claimer loop 80M, `min_camp_damage` 76M (cached; its own pass is 174 a call, clear_fire's sort 543). `crew_tank` feeds only `CrewPlan::tank`, which only the CREW traces read. stand_reach's builds: 2996, 6.5M, up to 28.9k (48 members x 32 strikers).

**Census with --trace, quill set** (1637 traced run-outs; pre-q's census on the same maps: 1099), last passed check:
- farm loop's `room()` (farm.cc:986) 646 (pre-q's farm.cc:931: 239). Left 35.6k, needed 27.2k, margin 8.4k; one body then spends more than the margin. The costliest stretches are plan_crew's pricings (`min_camp_damage -> min_camp_damage`, 903 x 4.6k: crew_tank + share_damage + the next ally), stand_reach's first build (11.8k each), clear_fire's sort (9.9k). On the OOF set the class is 349 of 947 with 26k a turn after the check (min_camp_damage + stand_reach + sort 19k).
- farm.post's walk check (farm.cc:1517) 429 (pre-q's farm.cc:1326: 124), and static descend (pathing.cc:940) 166 (202): one search reserved, then two run. In farm.post, `step_towards(attack tiles)` fails (~10k: a route that fails floods the goals' region to the cap) and `step_towards(adjacent)` runs on the same check (~10k), then walk_on. Concentrated on topology maps (topo-island, topo-tree, far-spawns, tangle: crews in necks). pathing.cc:955's wider retry is the same shape.
- none 290 (450): strike search and retreat, as in round 2.
- Round 1 (OOF set census, 106 traced): 50 after the loop check (stand_reach's build 12.4k and pricings 8k a turn on the bodies after it), 28 in world init before any check (static_camps 76k: unchanged).

**Plan:** make the loop body's crew pricing cheap without touching what plan_crew evaluates (the claimed-group bound and plan reuse are the farm worker's): crew_tank only where it is read, share_damage without repeated own-record reads and member walks, stand_reach's build in byte lanes. Leave the double search (a reserve change would be a gate) as an open item.

Commits (each exact; the three together benched: 100M byte-identical wide 52/52, OOF set 48/48, many-group 24/24, quill set 48/48, all against q0's JSONs; crews and Monolith operations form on the wide set's 00monolith, 01boss-battle, gen-monolith-heavy and on the quill set):
- ae9af312 stand_reach's build compares 16 strikers a vector (i8x16: coordinates below 100, differences within a byte). Biggest build 28.9k -> 16.6k; all builds 6.50M -> 4.62M.
- ba5589cc plan_crew computes the tank inside debug_block (traces only; free in debug builds, absent in release). crew_tank 178M -> 1.6M.
- 649519bf share_damage reads our record once (it read my_health/my_max_health/my_position six times a call, a host call each) and keeps steps_to per group and body by tile (pure in both). share_damage 503M -> 375M; plan_crew 1.095G -> 0.79G.

| set (100M) | total | mean | p99 | max | over 100k | round 1 mean |
|---|---|---|---|---|---|---|
| wide | -3.07% | 57465 -> 55712 | 131782 -> 119890 | 336643 -> 336643 | 9673 -> 6817 | 283866 -> 263601 |
| OOF set | -4.62% | 63821 -> 60891 | 318037 -> 265900 | 883281 -> 732571 | 26618 -> 24599 | 424727 -> 383778 |
| many-group | -4.47% | 67668 -> 64666 | 267582 -> 223349 | 528173 -> 443359 | 10496 -> 8900 | 402222 -> 364924 |
| quill set | -5.97% | 74205 -> 69787 | 261306 -> 215794 | 627278 -> 550441 | 50648 -> 40870 | 374664 -> 341507 |

Dearer turns: 15.7k / 6.9k / 4.4k / 9.8k (p50 ~1k, p99 ~20k); all but 3 / 12 / 0 / 3 of those over 5k end below 90k: the turn-end queue filling the fuel freed.

Real budget, OOF turns q0 -> new: wide 616 -> 510, OOF set 1069 -> 955, quill set 7507 -> 2642 (pre-q 1418). Shortcuts, wide: farm-partial-evaluation 23353 -> 17238, comms-stale-vision 2837 -> 2131, step-guard-entry 2534 -> 2462, turn-order 1831 -> 1483, farm-no-route 941 -> 597, prey-cut-short 1027 -> 805, static-descend 216 -> 290. OOF set: farm-partial-evaluation 31434 -> 26912, comms-stale-vision 5335 -> 4309, turn-order 4386 -> 3344, farm-no-route 2412 -> 1663, step-guard-entry 5806 -> 6261. Quill set: farm-partial-evaluation 94960 -> 75125, turn-order 27193 -> 14915, static-descend 13506 -> 4990, comms-stale-vision 9633 -> 7315, farm-no-route 6606 -> 3407.

Census after the three commits (quill set, debug-instrumented copy; its games diverge from the plain bench's, 1687 OOF turns against q0-cen's 1462, so only the shape counts): 1827 traced; the loop check 646 -> 388; double search now leads: farm.cc:1517 564, pathing.cc:940 542, concentrated in runs on single games (topo-odd-spawn-987907106 312, dungeon-989402413-a 71, topo-island-987006603-a 60, far-spawns-988604903 89).

Open items:
- **Double search after one check** (farm.post's attack-tile then adjacent `step_towards` at farm.cc:1517; static descend's capped then 6x-wider search at pathing.cc:937/955). A failed route floods the goals' region to its cap (~10k), and a champion stuck behind a neck repeats both every turn: two-turn OOF runs on topology maps. No exact cut found: the second goal set is not implied by the first's failure, and make_way can move us after a failed route. Reserving two searches would be a gate. Lead: why the first search fails on those maps (crew members holding necks, `failed_` reused only within a turn).
- plan_crew is still ~0.79G of ~4.1G on the 12 profile games: share_damage 375M (~940 a pricing, mostly the ally loop and our own add), the available-ally loop 212M, the claimer loop 80M, the wrapper of min_camp_damage 76M. The number of pricings (each strong group every farm turn, prunes bypassed) is the farm worker's; reusing plans across turns would remove most of it.
- crew_available: evaluate the centre tests before `dist(a.pos, my_position())` (a host call) — same result; untested, likely < 1% of plan_crew.
