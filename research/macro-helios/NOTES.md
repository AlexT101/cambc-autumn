# HELIOS: macro refactor of charybdis (2026-11-11, 19:00-23:00 UTC)

Worktree /home/ubuntu/wt/macro-o6, branch macro-o6-20261111. Reference `bots/variants/charybdis-ref` (= charybdis at
the start). Every A/B: `tools/ab.py CAND variants/charybdis-ref --no-test-draft --fuel 200000`, fast runner, release
builds unless noted. Dev suite `maps/macro-dev` (5,120 ladder-v2 maps, 10,240 games); holdout `maps/macro-holdout`
plus `ladder,gen,fresh`. Study suite `maps/macro-extra/s-88001` (256 maps, seed 88001).

## Study: charybdis mirror, 512 debug games on s-88001 (turn_budget.py, winner vs loser)

- 97% of games end on 1000 gems; median length 748.
- Losers die 6.8 + 0.3 a game against 2.6 + 0.3; dead 12.1% of champion-rounds against 5.2%. Gems lost at death to
  champions 254 against 69 a game, 72.8% of the loser's in 100+ bags (0.5 such deaths a game), Prism 175 gems a game.
- Kills: winners 6.8 a game, losers 2.6; more kills wins 83.5%, fewer gems lost at death 85.1%, more captured 80.1%,
  more mid captures 82.3%.
- Supply is not binding: own groups are asleep (up, unworked) 54% of gem-weighted group-rounds, mid 71.5%,
  enemy-side 54%. The economy is labour-bound (as macro2/3 found on ocean).
- Time (W/L, % of champion-rounds): camp 18.4/16.6, hold 5.0/4.5, walking ~45 (bag->altar 15.4/14.1,
  empty->camp 17.6/16.9, bag->camp 6.7/6.3, empty-other 6.0/7.4), retreat branch R 4.7/6.1, idle-off 5.4/4.1.
- Deaths with 3+ allies and 3+ enemies within 8: losers 16.6 per 10 games, winners 6.9: team fights decide.
- Mean carried gold 47 (median 17): gold does not sit unspent.

## Experiments
- The first team holding a winning bag (tributed + one champion's bag >= 1000) wins 91% of games; median 32 rounds
  from then to the end. Lock wars stretch some (139 of 512 team-games hold a winning bag 30+ rounds, nearly all with
  locks placed), but conversion is not where games are decided.
- Prism duels decide bags: of 155 Prism deaths with 60+ gems, 108 were killed by the enemy Prism (median Focus ratio
  killer/victim 1.27 at the first hit). At the killer's first hit the victim's stun was on cooldown in 52% of cases
  (killer's: 15%), against a base rate of 30% of rounds with the enemy Prism within 8: a ~2.5x relative risk. Near
  the enemy Prism (<= 10), ~35% of our Prism's stun casts go to camps (990 of 2812 in 256 games).

### E1 h-oppstand (19:39): opponent-modelled stand
- Idea: ref retreats when the side facing it wins striking first; so a stand we lose only when THEY strike first, but
  win when WE strike first, is one the enemy leaves itself: stay. Relaxes `stand_lost_at`'s `t.lost` clause and the
  matching `step_guard` tiles; bags >= brake_bag, lethal tiles, linked pairs keep the old rule; every enemy in the
  roster must be visible, in our next-turn strike reach, off its spawn, not channelling a teleport or holding a capture.
- Smoke (512 debug): fires 1.6 kept stands + 5.3 unguarded tiles a game out of ~20 tests; OOF 30 vs 13 (unexplained).
- **macro-dev: 49.9% of 10,240 (CI 49.0-50.9), OOF 707 vs 464. Level.** Fires too rarely to matter: only ~20 stand
  tests a game reach the trade at all, against ~110 retreat runs a team (60% of them a single step): most retreats
  come from other triggers (pack zone, recall line, step guard), not the stand trade. Dropped.
- Throughput: a 10,240-game release A/B takes ~2 minutes on the pool.
- Monoliths (69 of 256 study maps, mostly one a side): never captured in 45 of those games; when captured, the first
  capturer wins 18 of 24; median first capture round 581 (game median 741). At ~200 champion damage a round and 20k
  health it is a mid-game crew job; not pursued for lack of time.

### E2 h-reserve (19:55): the Prism keeps its stun for the duel
- Our Prism casts no stun at camps while an enemy Prism with >= half its Focus is visible or tracked within 12
  (stun cooldown 8 + its range 4); one predicate in `camp_cast`. Smoke: ~6.4 withheld casts a game where it fires
  (155 of 512 games); stun-on-cooldown share with the enemy Prism within 8 30.3% -> 27.1%.
- **macro-dev: 50.1% of 10,240 (CI 49.1-51.1), OOF 438 vs 474. Level.** Saves ~3 points of stun-ready rounds; not
  enough to move duels.

### E3 h-pack (19:56): teammates' fights joined on a we-strike-first gate
- Team engagement detection, a relaxed chase gate for team fights (won when we strike first, linked body not falling
  first), focus by allies' damage in reach, melee leftover hit redirected from camp to the joined target.
- Smoke: ~6 join turns a game; camp-hit share near engaged enemies unchanged (6.4 vs 6.5%). The gate passed 5% of
  15k tries: nearly every failure is `self_falls` — the fight model sends each side's whole damage at the other side's
  weakest body, and the joiner often is it. `preyable` filters half the candidates (healthy enemies on their half).
- **macro-dev: 50.2% of 10,240 (CI 49.2-51.2), OOF 538 vs 427. Level.**
- Lesson so far: three rules that fire a few times a game cannot move a mirror; the decisions that matter fire every
  turn (farm choice, step guard, the fight model's verdicts) and are shared by both sides.

### E4 subsystem ablations (20:04)
Ten variants, each with one charybdis subsystem switched off (abl-cook, -fixc, -reveal, -contest, -siege,
-guardaltar, -wakering, -crew (non-Monolith crew operations), -ender, -willowfollow), to find any subsystem that is
worthless or negative against charybdis-ref now that the Prism economy changed the game.
- Results (macro-dev, 10,240 games each, win % of the ablated bot vs ref): **crew 30.2**, willowfollow 47.5,
  ender 47.6, contest 48.4, fixc 49.2, reveal 49.4, cook 49.6, siege 49.6, wakering 50.0, guardaltar 50.1.
- Crews on strong groups are by far the largest subsystem: without non-Monolith crew operations charybdis loses 70%
  of games. That makes crew coordination (who joins whom, from how far, with what information) the lever to push:
  it is exactly the "summon allies to a camp" idea, already working. Crew availability counts only allies *in sight*
  (vision is personal) within `crew_available_radius` 11 of the group.

### E5 coordinate scan (20:13)
40 variants, one constant each scaled down/up (8 crew constants first, then home_power, camp_risk, farm
stickiness, hurt/home retreat ratios, brake_bag, pick_up/help/pack radii, cycle horizon, fight_ally_radius,
life_value). Not to tune knobs blindly: charybdis's Prism economy changed the game since these were fitted on
ocean's ancestors, and the crew result says coordination radii/timings may now sit off their optimum. Anything that
moves gets a mechanism read before it is kept.

### Crew anatomy (study, 512 mirror games; Elk groups ~3,300 health, same game phase)
| crew | health per hitting champion-turn | rounds first hit -> clear | 2nd / 3rd member's first hit | first leaver before clear |
|---|---|---|---|---|
| 1 | ~500 | ~15 | - | - |
| 2 | ~270 | ~23 | +10-16 | 7-9 rounds |
| 3+ | ~180 | ~23 | +5-7 / +10-13 | 9-11 rounds |
Crews are a relay, not a strike: the first arriver wakes and tanks alone, members trickle in, someone leaves for a
heal before the end; a 3-crew is no faster than a solo clear. Monoliths already gather before waking (`mono_engage`).
-> E7 h-gather: generalise the gather to every crew operation. (E6 h-crewinfo: crew availability from comms-told
tiles, porting ocean 507 first as h-told.)
- Scan results (first 31 of 40, 10,240 games each): every variant is within 48.9-50.3%, all CIs overlapping 50
  (crewcap-hi, a no-op since teams have at most 5 bodies, reads exactly 50.0: the noise check). homepow-hi 48.9 and
  crewtrip-hi 49.1 are the only reads near a point below. No constant among radii, timings, risk weights,
  stickiness, horizon, life value is off its optimum: charybdis sits on a flat plateau for local knobs, and the
  gains, if any, are structural.
- Remaining scan variants also flat (49.5-50.4). Closed.

### E6 h-told / h-crewinfo (20:46)
- h-told = ocean CHANGES 507 ported to charybdis (each ally's comms slot carries its tile when its claim is unchanged;
  an unseen claimer counts in its group's crew by its told tile), plus charybdis's `recent_tile` (Prism hand-over)
  reading the slot with the cell's slack. **50.7% of 10,240 (CI 49.8-51.7), OOF 450 vs 457.**
- h-crewinfo = h-told + unseen teammates with a fresh told tile count as available crew (claiming nothing or a
  harmless group): proposals 17.7 vs 15.7 a game, bails 0.71 vs 0.57. **50.5% of 10,240 (CI 49.5-51.4).** The extra
  proposals bring no extra wins; availability is not what limits crews.
- h-told confirmation: maps/macro-conf (2,560 fresh maps, seeds 88002-88011) 50.4% of 5,120; holdout 48.4% of 2,560.
  Pooled with dev ~50.3%: noise level, as on ocean (+0.16).
- Monolith ops: the farm prices them (MONO VALUE lines) at ~50 heal trips around round 200 and ~11 by round 475; a
  late-game job by construction, consistent with first captures at ~r580.

### E7 h-gather (21:09): crews gather before waking a sleeping strong group
- Monolith gather (`mono_engage`) generalised to every crew operation: wait staged out of reach until
  `mono_gather_share` of the plan's output is staged or the planned members' arrival / `mono_max_wait`; the wait is
  priced into the operation's rounds; free hits while waiting.
- Smoke: ~17 engages a game, mean wait 0.9 rounds (most resolve at once); 2nd/3rd member lag down only 1-4 rounds
  (Elk 3+: 4.1/8.8 vs 5.3/10.2; Golem 3+: 4.7/12.2 vs 8.8/17.5), clears 1-4 rounds shorter.
- **macro-dev: 50.1% of 10,240 (CI 49.1-51.1), OOF 478 vs 432. Level.** The relay is mostly not caused by the first
  arriver waking early; members are simply busy elsewhere when the op starts.

### E8 h-oneshot (21:24): turn-order traps and the enemy Prism's position in comms
- Diagnosis of Cassi's deaths to the enemy Prism (512 smoke games): in 187 of 223 seen cases `Safety::lethal` was
  already true where she ended; ~59 were the stop-ender branch walking in by design; only ~19 avoidable that turn.
  The main cause is a trap formed one turn earlier: the guard, `lethal` and the fight sims price only the enemy turns
  before our next turn, and with alternating team order the enemy's turns between two of ours run 2, 0, 2, 0. A turn
  before a 0-window prices nothing, so ending at distance 4 looks safe; the next turn precedes a 2-window (walk +
  cast), and one step cannot get out. 96 retreat deaths had every reachable tile lethal.
- Fix: `Safety::trapped(p)` — p is a trap if every tile our next turn can reach from p is within lethal reach of a
  visible enemy whose burst kills us, over that enemy's turns after our next turn (its real window from the turn
  order); the step guard keeps off trap tiles, retreat ranks them as one more hit. Plus the enemy Prism's tile in the
  comms camp field (posted by any seer), applied only by bodies its burst kills and by our own Prism.
- Smoke: deaths to the enemy Prism -27% (all bodies 960 vs 1,318; Cassi+Issac 344 vs 473; our Prism 172 vs 291).
- **macro-dev: 49.9% of 10,240 (CI 48.9-50.9), OOF 658 vs 461. Level** despite ~27% fewer deaths to the enemy
  Prism in the smoke: keeping off trap tiles costs the farm and fights the deaths saved, the pattern every caution
  change on these bots has shown. Follow-up h-oneshot-pair: the same, for the linked Cassi/Issac pair only (one
  death costs two bodies and both bags there).
- h-told on `ladder,gen,fresh`: 50.1% of 1,280 (ladder 50.8 of 256, gen 49.4 of 512, gen-s1 50.4 of 512).

### E9 h-combo (21:30): crewinfo + gather + reserve + pack merged
- **macro-dev: 49.9% of 10,240 (CI 48.9-50.8), OOF 624 vs 449. Level.** Four level-to-slightly-positive changes do not
  add up; the OOF cost does.
- h-told on maps/macro-conf2 (5,120 fresh maps, seeds 88012-88031): 50.2% of 10,240, OOF 523 vs 520. Pooled over
  all five reads (29,440 games): ~50.25% (CI about 49.7-50.8).

### E10 h-oneshot-pair (21:37)
- h-oneshot restricted to the linked Cassi/Issac pair (trap guard, retreat rank and the shared Prism record), with a
  cheaper memoised trap test (same answers, cross-checked in debug). **macro-dev: 50.2% of 10,240 (CI 49.2-51.2),
  OOF 484 vs 444. Level.**

## Outcome (21:50)

`bots/charybdis` = `bots/variants/h-told`: charybdis + ocean's CHANGES 507 (comms slots carry each teammate's tile
when its claim is unchanged; an unseen claimer counts in its group's crew by its told tile) + charybdis's own Prism
hand-over (`recent_tile`) reading those tiles with the cell's slack. It is the only change with a non-negative read
everywhere and no fuel cost; it is not a significant gain:

| suite | games | win % vs charybdis-ref | CI |
|---|---|---|---|
| maps/macro-dev | 10,240 | 50.7 | 49.8-51.7 |
| maps/macro-conf (seeds 88002-88011) | 5,120 | 50.4 | 49.0-51.7 |
| maps/macro-conf2 (seeds 88012-88031) | 10,240 | 50.2 | 49.2-51.1 |
| maps/macro-holdout | 2,560 | 48.4 | 46.5-50.3 |
| ladder,gen,fresh | 1,280 | 50.1 | 47.3-52.8 |
| pooled | 29,440 | ~50.25 | ~49.7-50.8 |

The 60% target was not reached.

## What this session learned

1. **The mirror is flat to every local change.** 40 one-constant variants (crew radii/timings, risk weights,
   stickiness, horizon, retreat ratios, life value, pick-up/help radii) all read 48.9-50.4% over 10,240 games each.
2. **Crews are the engine.** Turning off non-Monolith crew operations costs 20 points (30.2%); the next most valuable
   subsystems are Willow's follow (2.5), the game-ender stop (2.4) and contesting captures (1.6); guard-altar and
   wake-ring are worth nothing measurable. But making crews better informed (told tiles, unseen availability) or
   synchronised (gather) did not move the result: the relay shape (members joining 5-16 rounds apart) comes from
   members being busy, not from the first arriver's timing or from missing information.
3. **Rules that fire a few times a game cannot move a mirror** (oppstand 1.6 stands a game, pack ~6 joins, reserve
   ~6 withheld casts in a third of games). The fight model's pessimism (each side's whole damage on the other's
   weakest body, `self_falls`) gates every engagement decision on both sides alike.
4. **Fewer deaths is not more wins.** h-oneshot cut deaths to the enemy Prism by ~27% (a real mechanism: the 2,0,2,0
   enemy-turn windows between our turns let a "safe" tile become a trap one turn later) and still read 49.9%: the
   avoidance costs as much farm and fight as the deaths it saves, as every caution change on these bots has.
5. Facts worth keeping: first team to hold a winning bag wins 91%; the enemy Prism makes about half of all kills and
   its stun alone kills Cassi from her health in 91% of those kills; Prism stun on cooldown is a 2.5x relative risk
   factor in fatal duels; 65% of Monolith-map games never capture the Monolith (first capturer wins 75%); supply is
   not binding (own groups up and unworked 54% of the time).

## Open leads
- Tempo from the 2,0,2,0 enemy-turn windows: tested afterwards in the chase gate (E11, fires 0.16 a game, level)
  and as a whole threat-model correction with the trap guard (E12, level, +40% OOF). What is left is the strike
  search itself planning two-turn sequences (strike in a 0-window, leave before the 2-window); not built.
- Crew *assignment* rather than crew information: members join late because they are mid-task; a team-level choice
  of which strong group the free members converge on (claims ordered by when each member frees up) is untested.
- Monolith timing on the 27% of maps that have one: the farm prices it at ~50 heal trips around r200 and ~11 by
  r475, and first captures come at ~r580; an earlier, Prism-held Monolith (200 gems = +300 Focus) is the largest
  single swing left on the table.

### E11 h-tempo (21:52): chase gate with us striking first in a 0-window
- On the final charybdis (h-told): when the chase target and every enemy in its fight get no turn between ours,
  `prey()` re-asks the trade with us striking first (and our walk not delaying our strike). Flips the gate 0.16 times
  a game. **macro-dev: 50.7% of 10,240 (CI 49.7-51.7), OOF 449 vs 471** — the same as h-told alone (50.7): nothing
  added.
- Found on the way: `threat_strike` gives a visible enemy its next-turn strike even when it has no turn before our
  next one, so the step guard, `lethal` and the blows price a 0-window enemy as a threat on every other turn.
  -> E12 h-window: no threat from 0-window enemies, with the trap test guarding the following 2-window.

### E12 h-window / h-window2 (21:58): no threat from enemies that cannot act before our next turn
- `waits_turn`: a visible enemy with no turn before our next one gives no strike (as a stunned one), fights from its
  next turn in the simulator (we act first); h-oneshot's trap test guards the following 2-window. h-window also keeps
  the shared Prism record; h-window2 is the same on the final charybdis without it.
- h-window: **macro-dev 50.1% of 10,240 (CI 49.1-51.1), OOF 629 vs 466; holdout 48.4% of 2,560, OOF 250 vs 118.**
  h-window2: **macro-dev 50.1% of 10,240 (CI 49.1-51.0), OOF 634 vs 435.** Level, with ~40% more out-of-fuel turns
  from the trap test. A more exact threat model, again, moves nothing against a bot that shares the old one.

### E13 h-assign (22:10): team-level crew assignment by free-up time
- On the final charybdis: each teammate's free-up time (0 if unclaimed, its capture's payout if holding, walk + short
  clear on a harmless claim, excluded on another strong op or a bag trip); a plan's expected crew counts teammates
  that free up and walk in within the op's horizon, arriving then; no new strong-group proposal while an ally's op
  still lacks its planned crew.
- First build (frozen at 22:16): **macro-dev 50.7% of 10,240 (CI 49.7-51.7), OOF 499 vs 452** — identical to the
  current bot's 50.7 on the same maps. Level.
- Final build (sorting the expected crew by walk + free-up delay; ASSIGN-WAIT: no new proposal while a nearer ally
  op has under 2 claimers, ~12 turns a game): **macro-dev 50.6% of 10,240 (CI 49.7-51.6), OOF 489 vs 449**, against
  50.7% for the current bot on the same maps. Not better; not committed. Smoke: ASSIGN adds a not-yet-free ally
  ~11k times in 422/512 games but the resulting crew is still 1 extra member in 94% of cases (delays 1-3 rounds):
  the free-up horizon (our own arrival) is too short to pull in teammates who are really mid-task. Untested next
  step: a horizon of our arrival plus the clear, and blocking rival proposals only when the ally's group needs a crew.

### E14 h-assign2 (22:25): horizon = our arrival + the clear; block rivals only when the ally's group needs a crew
- `crew_delay` counts a not-yet-free teammate whose free-up + walk fits our arrival plus the clear (group health over
  our own output); `plan_crew` credits a late joiner's output only for the share of the clear it is there; `short_op`
  blocks a rival proposal only when the ally's claimers would need a trip home alone (alone-trips test).
- Smoke: ASSIGN ~124 pricing lines a game (mean delay 3.9 rounds, 74% with partial credit), ASSIGN-WAIT ~35.
- **macro-dev: 50.4% of 10,240 (CI 49.4-51.3), OOF 518 vs 475** vs 50.7% for the current bot. Not better; not
  committed. Crew assignment, like crew information and crew gathering, leaves the mirror level.
