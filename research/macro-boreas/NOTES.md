# macro-boreas: macro refactor of charybdis (BOREAS, 2026-11-11)

Reference: `bots/variants/charybdis-ref` (= charybdis at 81fc6f968). Every A/B: `tools/ab.py CAND variants/charybdis-ref
--no-test-draft --fuel 200000`, release builds, fast runner, own drafts. Dev suite `maps/macro-dev` (5,120 fresh
ladder-v2 maps, 10,240 games); holdout `maps/macro-holdout` (1,280 maps) + `--suites ladder,gen,fresh`. Analysis suite
`maps/macro-extra/s-84000` (256 maps, seed 84000), `s64` its first 64.

## Summary

Result: the 60% target was **not** reached. The committed `bots/charybdis` (452fe1574) is charybdis plus one
mechanical fix to how our Prism reads an enemy Prism's threat: **50.7% of 18,688** games against charybdis-ref at 2x
fuel (dev 50.8% of 10,240; confirm + holdout 50.5% of 4,608; fresh s-84001..4 50.6% of 2,048; ladder/gen/gen-s1
50.1% of 1,280; varied 50.6% of 512). At the real budget: 50.5% of 2,048 (OOF +5.6%).

What the evidence says decides charybdis-vs-charybdis games: with a Prism on both sides (80%), the side whose Prism
dies first loses 89%, and 78% of Prism deaths happen in the 9% of rounds spent within 8 of the enemy Prism; fights go
to the side with more bodies present and the bigger Prism Focus. Ten macro-level levers aimed at that (cohesion
around the Prism, team pricing of Prism-collected gems, a wider Prism collection window, shared enemy-Prism sightings,
pair-kill pricing, Prism shop timing, unseen-Prism Focus growth) were level (49.8-50.9%) or lost (cohesion 37%, extra
Prism shop trips 46%). The one change kept is a modelling fix found by tracing deaths: `lethal()` missed the turn an
enemy Prism's stun hands back, so our Prism walked, banked and retreated onto tiles where stun + ground spell killed it.

Lessons: (1) charybdis is at a robust local optimum for re-pricing and information changes — each moved its target
metric little or not at all (the Prism's share of capture gems stayed ~48-51%, its max health didn't move, sightings
fit the comms bytes in 23% of games); (2) restricting where champions farm costs far more than the fights it wins;
(3) the decisive Prism duel is near-symmetric in the mirror (first casts 185 vs 189), so gains there come only from
modelling the duel better than the opponent, and the remaining gaps (bush reveals, stop-ender walks, untracked
Prisms) are each a few deaths per hundred games; (4) SPRT screens at H1 = 52% reject true +1 changes, so they are
only good for killing losers.

## Evidence (256 mirror games, charybdis vs charybdis-ref on s-84000, 2x fuel)

- Mean 922 rounds; 18 of 256 reach r2000. Winner kills 8.1 / dies 2.8 a game; loser kills 2.5 / dies 8.2 (loses 305
  gems at death a game, 222 of them on its Prism). Captures 60 vs 54 a game.
- Time (macro_stats): moving 50% of champion-rounds (with and without a bag), hitting camps 17-18%, holds 5%, recall 5-6%.
- Decisive fights (champion-damage clusters with unequal kills; 1,838 in 256 games, 7.2 a game). Win % of the side with
  more champions within 8 of the fight centre at its start: +1 61%, +2 65%, +3 77%, +4 82% (mirror side bias: team A
  wins 45% at 0). Prism Focus ratio of the two sides' Prisms in the fight: <0.67x 15%, 0.67-0.9 29%, 0.9-1.1 53%,
  1.1-1.5 56%, >1.5x 86%. 416 of 612 two-Prism fights are lopsided (<0.67 or >1.5).
- The first decisive fight's winner wins the game 67% (156/234); first fights fall mostly before r300.
- Deaths: the Prism is the killer in 58% of kills. Losers' deaths mostly with an ally within 3 (team fights), not isolated.
- Prism Focus by outcome (Prism-both games, 207): r100 217 (W) vs 204 (L); r200 376 vs 325; r300 559 vs 433. The Prism
  carries 55-58% of its team's collected gems at r100-300.
- Gold: spent at once (20-30 unspent); ~80 earned by r100, ~190 by r200 per champion. Not a lever early.
- Solo vs idle (256 maps one side): 1000 tributed at r688; walking 53% of champion-rounds; 8.3 completed recalls per
  champion a game, 5.5 of them at >= 80% hp (recall-to-farm transits: most kept recalls follow a farm turn, RFKEEP);
  recall + walk-out ~31% of champion time; captures 40.5% of a supply bound (own side 62%, mid 42%, enemy 18%).

## Experiments
- First Prism death (Prism-both games, 207): 143 games have one; the other side wins 89% (127/143); the killer is the
  enemy Prism 71%. Prism-on-Prism engagements: victim had seen the attacker in the 2 rounds before in 77%; when only an
  ally had (12%) or nobody (11%) the victim died 31-32% vs 13%.
- In decisive fights each side has ~2 alive champions more than 8 away; the loser's extra absentees are dead ones
  (1.0 vs 0.3 a fight): fight numbers follow deaths (snowball) more than dispersion.
- Gem captures: Prism takes part in 51% (by gems); allies alone 46%, ~24% of the total within 15 tiles of the Prism.

### b-sq: Prism-anchored squad zone (allies farm only groups within 10 of the Prism, slack 4, fallback unzoned)
SPRT on macro-dev (seed 11): **36.9% of 371, H0**. Allies did close in (mean distance to Prism 10.6 vs 13.1; within 8:
55% vs 48% of champion-rounds) but lost far more farm than fights gained. Confirms the priors: cohesion by restricting
farm choice loses heavily. Dropped.

### b-hub: allies price gems their Prism can collect at the Prism's carried price
`keep_bonus` extended to non-Prism allies (carried_bonus on the Prism ally's belief) when the Prism's ETA to the group
is within carry_reach of our clear's end. SPRT macro-dev (seed 12): **48.3% of 2,025, H0**. Debug: ~46 hub picks a
Prism game, the bonus ~2.3 gems a gem early; the Prism took 37% of hub-picked groups (18% of other ally gem picks), but
only ~5% were handed over by leave_for_prism: allies paid for a collection that mostly didn't happen. Same outcome as
macro4's M4-a3 on charybdis's base. Dropped.

- Decision mix in real games (128 debug mirror games): farm 60%, none/dead 8.5%, bank 5.9%, retreat 4.7%, Willow 4.7%,
  hold 3.8%, altar guard 3.2%, tribute 2.5%, recall kept 2.0%, capture recall 1.6%, chase 1.4%.
- Decisive fights by location: on team A's half A wins 40%, on B's half 57%, mid 44% (n 503/464/871): the invader wins
  ~57-60% (it chose the fight; the defender was caught farming).
- At the first Prism-on-Prism kill: killer Focus 844 vs victim 718 (mean), max hp 2,368 vs 1,854 (gold bought hp),
  both mostly near full health (victim 0.83, killer 0.79): bursts (2.5 x Focus) are about the target's health.
- Captures by side (r2000, per game): winner own 764 / mid 156 / enemy 127; loser 695 / 92 / 65.

### b-intel: allies post the enemy Prism's last sighting (shared bytes); only our Prism folds it into its beliefs
SPRT macro-dev (seed 13): **50.3% of 941, H0 (vs 52)**. Level; not a lever on its own.
  The record fit in only 26 of 112 two-Prism smoke games (claims + bag + camp fill 58-63 bits on 5-6 body teams);
  where it fit: ~176 posts and ~62 applied sightings a game, 6.7 a game with the enemy Prism within 8 of ours. So the
  test mostly measured nothing; its effect where it fits is unknown (at most a fraction of a point overall).

### b-col: the Prism as the team's gem collector (priced collection window)
Allies leave a cleared gem group to the Prism while its ETA is within W(g) = capture_time + b x cycle(g) (b = the
Prism's carried bonus a gem, capped at the respawn); the Prism's 'L' picks reach the same window. SPRT macro-dev
(seed 14): **49.9% of 2,797, H0 (vs 52)**. Level.

## Replay study: why the first Prism dies (26 cases, debug mirror; scratchpad study/)
Taxonomy: lone farm walk into an enemy 7; walked onto an enemy-held altar / to stop a game-ender / own long tribute 5;
team fight lost with the Prism focused 6; near-even duel lost on first cast or max health 5; camp 3. 13 of 23 entered
danger from a farm turn ('F'); 20 of 26 died retreating after the first hit. The victim never had more max health
than the killing Prism; 17 of 20 before r400 were at base 700, several carrying 285-780 gold. Hazard per 1,000
Prism-rounds: base 4.8; outnumbered within 6: 128; enemy Prism within 8 whose stun alone kills us: 93 (30 if it
can't); our max health below the enemy Prism's: 6.95 vs 1.71 above. Only 8 of 59 victims had not seen the killer in
their last 3 rounds. The killing Prism was standing still (hold, tribute, after a kill) in 6 of 15 Prism kills.
- Prism unspent gold: mean 129 over r50-600 (others 21); r400 187, r600 275; 43% of Prism deaths carry 60+ gold.
  Its shard plan is mostly Health emblems, so this is missing max health.

### b-pair: an enemy Cassi/Issac kill is worth two lives (offense only)
`pair_life` (2 x life_value while the partner lives) in kill_distance/hit_worth, the strike search, prey cost and the
turn order's kill offers; audit fixed a double-counted pair kill in ground casts. Pair bodies took 32% of our strikes.
Cassi & Issac are drafted in 96% of mirror games and are 47% of the loser's body-deaths.
SPRT macro-dev (seed 15): **49.8% of 2,215, H0**. Level.

Lesson so far: re-pricing (hub, collector window, pair life) and information (intel) are all level; cohesion loses.
The study points at two mechanical Prism-survival gaps instead: unspent gold (missing max health) and walking into
the enemy Prism's one-shot range. Halving our Prism's first-death hazard would be worth roughly the whole target.
  b-col's implementer later found why: a distant ally's clear is not in the Prism's beliefs (comms carries captures and
  respawns, not clears), so the Prism cannot pick most left groups; teammates' gold prices also differ ~6x, so the
  window isn't shared. Prism share of capture gems 0.485 vs 0.479 in the same games: the mechanism never engaged.

### b-shop v1: the outgunned Prism shops (trip when max health < enemy Prism burst 2.5 x Focus)
SPRT macro-dev (seed 16): 49.8% of 1,091, H0. Smoke extraction showed the mechanism barely fired (Prism unspent gold
127 vs 144, max health at r200 equal). Revised (v2) to widen the trigger and find the blocking gate.
- b-lethal v1 (pre-audit, burst over-counted): SPRT 49.9% of 581, H0. Re-run on the audited version below.
- b-shop v2 (outgunned = max health not above max(enemy Prism burst, its max health); trip at 60+ gold whenever
  the purchase adds health or Focus): unspent gold 117 vs 142, max health unchanged (r200 901 vs 894, r400 1686 vs
  1689): the shard plan buys Focus/Power first, and tributing turns never reach the shop test. Hoarded gold mostly
  sits on a Prism already ahead. Full dev run below.
- b-shop v2 full dev run, stopped at **45.7% of 4,080**: the extra Prism shop trips cost more farm and position than
  the slightly earlier shards gave. Dropped (the hoarded gold was a symptom of the shard plan and of tributing, not
  of trip timing).
- A constant tune (SPSA on 45 strategic constants vs charybdis-ref, fresh pool s-84001..4) was started and stopped:
  on the shared box (load ~130) it ran at 3 games/s, too slow to move 45 constants in the time left.
- Prism hazard (study script, 125k Prism-rounds of the mirror): 78% of Prism deaths-within-10 happen in the 9% of
  rounds within 8 of the enemy Prism (39/1,000; 0.58 with no enemy within 8). So the duel's first cast is the game:
  the remaining work targets how our Prism concedes it (b-lethal: the stun's handed-back turn; b-lethal2: stale
  unseen Focus; b-duel: a diagnosis of first casts conceded).

### b-lethal2: unseen enemy Prism Focus grows at our Prism's gem income; capture-state evidence places it
Inert: 0 of 73 guard-refused tiles depended on it in 128 debug games (tracked-but-unseen Prisms are at most ~3
rounds stale; untracked ones rarely show capture evidence within cast range). Run stopped; not kept.

### b-lethal (audited): our Prism's steps refuse tiles where a known enemy Prism's first-strike burst kills it
Diagnosis (5 traced deaths): `Safety::lethal()` counted only each enemy's own turns before ours (stun + a basic), not
the turn the stun hands back (stun + ground spell + basics = 2.5 x Focus); and the work guard (farm, bank, shop,
siege, contest walks) refused only tiles where a fight sim lost, not tiles that are merely lethal. Fix: `stun_burst`
/ `burst_lethal` for a known enemy Prism whose stun is ready on its first turn before ours and that starts it within
cast range; `lethal()` includes it for our Prism; `work_guard`/`work_cover` add burst-lethal tiles; a Prism standing
on one with its walk left retreats. Fires rarely (28 guard turns, 4 retreats in 128 games).
Full dev run: **50.8% of 10,240 (CI 49.8-51.8)**, OOF 470 vs 450.

### b-duel: diagnosis of Prism-on-Prism first casts (128 debug games, b-lethal vs ref) and a retreat fix
First casts are even (ours 185 vs theirs 189; stun-first 126 vs 130): our Prism does not systematically concede
them. Of 35 Prism deaths within 10 rounds of an enemy-first stun: ~17 ended a turn on a tile our own Safety already
flagged lethal (retreat 6-7, stop-ender 5, farm 2, chase/siege/tribute 1 each), ~6 were bush/fog reveals, ~6 double
turns from distance 5-6. Fix: `retreat_step` counts the stun burst and ranks burst-lethal steps last (Prism only);
fires ~0.5 turns a game. Follow-up (b-duel2): a retreating Prism that casts its ground spell is pinned on the lethal
tile (18 of 26 unmoved lethal retreat ends; 6 died within 3 rounds).
- b-lethal holdout (macro-holdout + ladder,gen,fresh): **50.2% of 3,840 (CI 48.7-51.8)**: holdout 50.6% of 2,560,
  ladder 48.4% of 256, gen 50.4% of 512, gen-s1 49.0% of 512. OOF 180 vs 180.
- b-duel (b-lethal + burst-aware retreat steps) dev: **50.8% of 10,240 (CI 49.9-51.8)**, OOF 469 vs 451 — nearly
  the same games as b-lethal (5,205 vs 5,201 wins).
- b-lethalall (b-lethal's burst guard for every champion, not only the Prism) dev: **50.8% of 10,240 (CI 49.8-51.7)**,
  OOF 855 vs 458 (the burst test on every champion's guard nearly doubles out-of-fuel turns even at 2x fuel).
- b-duel on fresh confirm maps (ladder-v2 seeds 84005-84008, 1,024 maps) + macro-holdout: **50.5% of 4,608
  (CI 49.1-52.0)**: confirm 50.4% of 2,048, holdout 50.6% of 2,560; OOF 212 vs 212.
- b-combo (b-duel + b-pair + b-intel, merged) dev: **50.9% of 10,240 (CI 50.0-51.9)**, OOF 517 vs 428: the same as
  b-duel within noise; pair and intel add nothing measurable.
- b-duel2 (b-duel + a retreating Prism walks off a burst-lethal tile instead of pinning itself with a cast + the
  double-turn walk-in in stun_burst) dev (v2 code): **50.7% of 10,240 (CI 49.8-51.7)**, OOF 463 vs 454. No gain over
  b-duel. (Its retreat rule walked instead of casting 70 times in 128 debug games; 157 times every step was lethal.)
- b-duel on the standard suites (ladder, gen, gen-s1): **50.1% of 1,280** (49.6 / 51.2 / 49.2). On a `--mix varied`
  stress suite (seed 84009, 256 maps): 50.6% of 512. At the real budget (1x fuel) on the confirm maps: 50.5% of
  2,048, OOF 11,159 vs 10,564 (+5.6%: `stun_burst` inside `lethal()` costs fuel; fuel work would recover it).

## Final (committed): bots/charybdis = b-duel with its traces removed (`b-final`; release replays byte-identical)
Pooled b-duel: dev 50.8% of 10,240; confirm + holdout 50.5% of 4,608; ladder/gen/gen-s1 50.1% of 1,280; varied
50.6% of 512 — 50.7% of 16,640 (about +0.7, CI roughly +-0.8). The 60% target was not reached.

### b-outnum (on the final): our Prism retreats when visible enemies that can reach it within pursuit_steps outnumber it and its allies within pack_ally_radius
Fires ~1.6 times a game (199 in 128 debug games; 90 of 155 consecutive fires recur within 3 rounds: oscillation).
In those 128 debug games our Prism died 102 times vs the reference Prism's 141, yet the dev run is **50.6% of 10,240
(CI 49.6-51.6)**, OOF 783 vs 512: fewer Prism deaths bought with lost farm/fight time, again level. v2 adds a work-step
mask against the oscillation (below).
  On 400 of its dev games (extracted): our Prism died first in 106 two-Prism games vs the reference's 126 (-16%),
  yet the games went 205-195. The 89% "first Prism death" relation is not causal at the margin: a death avoided by
  retreating costs position and tempo that the mirror converts into the same result.
- b-outnum2 (b-outnum + an outnumbered-tile mask on the Prism's work steps; halves true ping-pong, 26 -> 13): dev
  **50.4% of 10,240 (CI 49.5-51.4)**, OOF 760 vs 500. Level. Not kept.

## Open leads
- The duel is decided by modelling it better than the opponent, not by caution: the remaining measured gaps are
  bush/fog reveals of an enemy Prism (~6 of 35 traced deaths), stop-ender walks onto lethal tiles (70 turn ends in
  128 games, 5 deaths), and untracked enemy Prisms (last seen 76-243 rounds before, Focus believed 300/90 vs real
  510/749); placing an untracked, non-capturing Prism needs a belief the bot doesn't have.
- The carry is information-bound, not price-bound: a distant ally's clear never reaches the Prism's beliefs (comms
  carries captures and respawns, not clears), and teammates' gold prices differ ~6x. A comms record of "left for the
  Prism" groups would let 'L' picks work beyond sight, though b-col's numbers bound its value at ~16 gems a game.
- Comms are full on 5-6 body teams (58-63 of 64 bits): any new shared record (sightings, clears) first needs the
  layout compacted (claims are also in the priority payload; the ally record is unused without a healer).
- Fuel: the stun-burst test in `lethal()` costs +5.6% out-of-fuel turns at the real budget; make it cheaper before
  shipping at 1x (an early distance check before the unseen-Prism work).
- The "first Prism death loses 89%" statistic is correlational: b-outnum cut our first Prism deaths 16% at no win-rate
  gain. Future work should target decisions whose counterfactual value is measured, not this outcome proxy.

### b-hub2 (on the final): b-hub with its audit's fixes
No bonus on already-cleared groups or with an enemy in sight; the arrival bound is the real hand-off condition
(capture_time + the Prism's remaining busy time, or its claim within carry_reach); prism_eta only after the prunes,
no bonus short of fuel. Dev: **50.6% of 10,240 (CI 49.6-51.6)**, OOF 628 vs 493. Level.

Patches: `patches/<variant>.diff` are against the pre-session charybdis (= charybdis-ref); `*-on-final.diff` are
against the committed final.

### b-left (on the final): a comms record of the gem group an ally just left for the Prism; the Prism marks it cleared
Fits the free bits in 36 of 128 smoke games (28%); ~0.5 posts a game, and only 7 groups in 128 games were new to the
Prism (5 then captured by it). Dev: **50.8% of 10,240 (CI 49.8-51.7)**, OOF 467 vs 450 — the same games as the final
(5,197 vs 5,205 wins). Inert: the Prism already knows most left groups, and the bits rarely fit. Not kept; confirms
the comms layout must be compacted before any new shared record can matter.
