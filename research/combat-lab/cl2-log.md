# Combat lab round 2: coordinator log (2026-11-08)

Plan: [PLAN2.md](PLAN2.md). Base `variants/oc-cl2-base` (= bots/ocean at 0dd304df9). Suites `cl2-dev`, `cl2-held`,
`cl2-var` (maps/SUITES.md).

## Baseline numbers (base mirror, 1,000 kept replays of cl2-belief-v1, either side ~ the base)
- fight_metrics: 5.8 champion kills a game a side; 0.26 deaths to camps.
- Flee episodes (`scratchpad ana/flee.py`): a champion below 50% health steps homeward with an enemy within 5 (one per
  15 rounds a champion). ~12 a game a side. Within 20 rounds: killed by a champion 27%, home 38%, neither 35%.
  That is 3.2 kills a game a side, **more than half of all kills**. Pursued (nearest enemy within 4 on 2 of the next
  3 rounds): 33% caught, 34% home. By steps home at the start: within 6, 18% caught; 7-15, 26%; 16+, 29%.
  Chase and escape are where most kills are decided.

## Results
| Arm | What | cl2-dev win % (20,480) | Notes |
|---|---|---|---|
| cl2-belief | an unseen enemy whose possible tiles reach its spawn reads at full health (world.cc heal_if_home) | 50.2 (49.5-50.8) | level; kills 5.81 vs 5.72, deaths 5.98 vs 6.07 a game; kept as a correctness fix to stack |
| cl2-ret v1 | G1a: 3-turn rollout route comparison in retreat_step (g1a-notes.md) | 50.1 (49.4-50.8) | level; OOF +6%; ~2 changed steps a game. Rollout well calibrated: all routes fall → dead within 4 rounds 66% melee / 58% ranged, chosen step lives → 2-3% |
| cl2-ret v2 | v1 + doomed_commit (fight when every route falls and a kill lands within 3 turns) | 49.4 (48.7-50.1) | paired deaths +1.27 a game; the widened kill window likely fights for kills that don't land. Untested: strict window (this turn or next: 10 kills / 4 deaths in 13 debug fires) |
| cl2-chase v1 | G1b: lead pursuit to the first reachable tile of the fleer's route home (g1b-notes.md) | 48.7 (48.0-49.3) | lost; OOF +9% (no gate); melee catches 29.5 vs 31.9 |
| cl2-chase v2 | lead = Chebyshev centre of the fleer's next options when all are in reach; fuel-gated | 49.6 (48.9-50.2) | level; OOF +3%; ranged catches +1.8, melee −0.9 (neither significant). Escapes are decided by the pursuer leaving (44% of gap-opening escapes follow its want_home; 19% of pursuers' retreats with a hurt enemy near are at >90% health) |
| cl2-team* | G3a (g3a-notes.md): leave bit in the priority payload; honest rosters (drop a leaving ally), cover (prey a pursuer of a leaving mate), chase bit (count chasing allies from 7) | team 49.3, -h 49.6, -c 49.9, team2 49.8, team2c 50.5 | all level. Stand desertions rare (0.12 deaths a game). Common gap: a free ally within 5 of a fleer's pursuer does nothing in 2.1 flights a game (caught 24.7%) vs hits it in 3.0 (18.3%). Cover blocked by chase_trade calling it lost (41 of 53 asks a game). Honest rosters cut OOF ~10% |
| cl2-peel v1-v3 | G3b (g3b-notes.md): a healthy helper preys on the pursuer of a doomed mate (v1); + mate's main threat and a turn-order bid (v2); + stun worth for a stun that saves a mate (v3) | 49.9 / 49.8 / 49.8 | level. Fired ~1.5 episodes a game; helper hit the pursuer 45%, mate still died 27%. 30% of caught fleers die within 2 rounds, before help arrives. Stratified engaged-vs-not upper bound: 3.6 points of catch rate, ≤0.08 lives a side-game |
| cl2-seat v1 | seat-notes.md: engaged flee/chase pairs take "ahead" of the enemy next round where the gap equals its next-turn real reach; 464 elsewhere | **50.7 (50.0-51.4)** | best so far, level; OOF +2.4%. Doubles at gaps 3-5 shift catches by +9.4 ±3.3 points, but doubles alternate by default, so seating only shifts the phase. Pin prediction wrong ~half the time |
| cl2-seat v1, held | confirmation on cl2-held (40,960 games) | **50.8 (50.3-51.3)** | confirmed; OOF +2.2% |
| cl2-seat v2 / v3 | v2: no pin prediction (bug: recall-feint channel check turned it off); v3: + burst rule, wider firing | 50.3 (partial) / 50.1 (49.4-50.7) | v3's pursuer seats remove our own pursuit doubles |
| cl2-cf-a / -ab | campfire-notes.md: (a) chase steps and chase_trade price camp fire on us; (b) fleers lure the pursuer into awake strong camps | 50.1 (49.4-50.8) / 49.9 (49.2-50.6) | level; (b) OOF +6.3%. Pursuers rarely chase into fire (0.32 entries a game); 96% of pursuers hit were already in the camp's reach (farming their own camp) |
| cl2-cf-r2 | (a) + camp fire on enemy fighters inside the fight sims (new_fight, chase_trade, stand_trade) | 50.4 (49.8-51.1) | level-positive despite OOF +11% (231,665 vs 207,932); a fuel-cheaper version may show more |
| **cl2-stack1** | belief + seat v1 + team2c's chase bit (patches compose cleanly) | **51.2 (50.5-51.8)** | first CI above 50; OOF +5% (215,928 vs 205,629). Roughly additive (+0.7 +0.5) |
| cl2-stack2 | stack1 + cf-r2 (camp fire on us in chases, on enemies in the fight sims) | 51.2 (50.5-51.9) | same as stack1; OOF +15.5% (239,625 vs 207,368). cf-r2 adds nothing on top; dropped |
| cl2-pre r1 | precontact-notes.md: timed stun deny of big enemy tributes + don't lock-deny a carrier whose next strike kills us | 50.3 (49.6-51.0) | level; deniers dead −0.16 a game but those tributes land +9 points (a coin-flip trade). Pre-contact factor table: nothing controllable beyond big-tribute denies reaches 0.1 bodies a game |
| cl2-pre r2 | r1 + lock-and-leap (dash away after a deny's lock) | 50.2 (49.5-50.9) | level; OOF 207335 vs 207799 |
| cl2-seat4 r1 | on stack1: seats only against enemies whose next rank is final (exact) | 50.2 (49.5-50.8) | dip: paired vs stack1 −1.01 ±0.82. "ahead" right 99%, but v1's predicted fires against unacted enemies were real gains (our fleers caught 30.1 vs 28.6) |
| cl2-seat4r2 | on stack1: v4 pair model (prices this boundary and the next, both ways; v1's prediction kept) | 51.3 (50.6-51.9) | level with stack1 (paired +0.10 ±0.70); OOF same. Picks v1's gaps for melee/dash pursuers; its extras decide little |
| cl2-seat4r2, held | r2 on cl2-held (40,960) | 50.9 (50.4-51.4) | level with stack1 (paired +0.13 ±0.49) |
| cl2-seat5 | stack1 with v1's distance pin dropped: in their rounds an unacted enemy's last read rank is trusted | 51.7 (51.1-52.4) | paired vs stack1 +0.59 ±0.78; OOF +5.2% |
| **cl2-seat5, held** | cl2-held (40,960) | **51.4 (50.9-51.9)** | paired vs stack1 **+0.64 ±0.55** (significant); OOF +5.1%. Confirms the drop of the distance pin over stack1 = ocean 475 |
| cl2-g2 | G2: guarded / lethal end tiles re-judged after the plan's own kills and stuns; retreat re-asks want_home after its own kill (g2-notes.md) | v1 49.8 (49.2-50.5), v2 49.9 (49.3-50.6) | level: fires ~0.1 decisions a game (re-judged plan chosen 0.02 a game); search danger was already post-action. Dropped as a lever |
| cal (no arm) | fight-model calibration from natural play: stand/chase verdict margins (log2 health to flip) logged in 1,966 debug mirror games, joined with outcomes (cal-notes.md) | no A/B | calibrated: P(ours first \| a death) crosses 50% at m=0 for stands; regression discontinuity at m=0 flat (stand bodies −0.006 ±0.007, games −0.008 ±0.010; chase bodies +0.010 ±0.009, games −0.017 ±0.018); no subgroup gains games; healthy (≥90%) stayers lose at the boundary. Level arms were level because their opportunities sit where fighting and declining are worth the same |

## Lab v2 (done, 2026-11-08 ~19:30)
`fastrunner forkgame` (stateful forks of real games, every champion live; triggers near/close/branch/death/kill/every),
forced actions (`LabAct`: walk, dash, attack, cast, end; holds), legal-action enumeration, outcome parts at marks,
`tools/combatlab/fork_sweep.py` (regret against ocean's own choice). Identity: unforced arms match pass 1 in 254/254
forks; 74 arms/s a core. Details: lab2-notes.md, RUNNER.md "Forks of real games". Open: noise floor (placebo arm,
perturbations), a second opponent, mixed-op sequences, logging Front::admit/guard/cap discards.

## Analyst (lab v2, ~10.7k forks, mirror and vs astraeus; all 4 runs partial) — analyst-findings.md
- Noise floor (KD bodies a fork): replicate noise 0.10 at mark 10, 0.48 at 30; cross-fit regret 0.15 / 0.37. Ocean's
  local (one-decider) regret is at most ~0.05-0.08 bodies a fork at mark 10, nothing at 30.
- Confirmed right (forcing the decider alone): retreat with an enemy within 8 (a stand loses 0.08-0.32), keeping a
  chase, every one-turn action class in retreats (0 of 43 beat ocean, 36 lose), the dash rules.
- Open leads: declined chases vs astraeus (+0.06 at mark 10 on one map half only); doomed retreats (selection-biased,
  8 unbiased forks).
- Its limits: forced only the decider (allies kept their policy), one op held, no target arms, no rare-state triggers.
  Conclusion: single-champion decisions are not where the gap is; the next lab work is group and multi-turn arms.

## Read-only idea analysis (2026-11-08)
A logic review of past attempts and the base code, with no runs. Verdict: ≥55% more likely comes from fight selection and
team / turn-order timing than per-step combat (big wins were min_bank, pair packing, 464's contact seating).
Ranked:
1. Contact seating for engaged flee/chase pairs at gaps 3-5. The base `contact_priority` (turn_order.cc:171) uses a fixed
   reach of 3/2 with no dash, reset or spell reach (checked).
2. Camp fire priced in chase and new-fight sims; fleers lure pursuers into awake camps. Today only the fleer prices
   camp fire.
3. Retreat to a receiver who commits (the haven / c4 changes moved only the fleer).
4. One more trade before leaving when the rollout says the escape still holds.
5. Cassi/Issac kill worth two lives (one `life_value` today; bags already doubled; checked).
6. A bag-scaled bar for starting fights away from home.
7. Body-blocking at chokes.
8. Escape-aware chip value.
Flagged: walk_allies_in's unseen-enemy walk 0 (documented as intended), HomeWalk ignores pursuit, fixc_commit only
clears leave, team_pressed needs the target in the ally's current range.
