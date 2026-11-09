# G1a: retreat route reasoning (notes, 2026-11-08)

Copy: `bots/variants/cl2-ret` (from `variants/oc-cl2-base`). Reference for every A/B: `variants/oc-cl2-base`,
`--no-test-draft`, suite `maps/suites/merged/cl2-dev`.

## What the base does (fight.cc)

- `retreat()`: sure kill, step-to-kill, melee hit, then `dash_away` (only when our tile is in danger and a landing
  has less), then `flee_camps` or `retreat_step(home = to_ally_spawn())`.
- `retreat_step`: no danger within 8: field step home. Outside avoid(): path home around avoid(). Else rank the 8
  steps by the one-turn damage tally (Safety bound, sight-aware Reach for visible enemies), stun-free, steps home,
  bush, gap. Steps farther from home only if untouched, and only when no homeward/lateral step is clear; HomeWalk
  (the whole walk onto spawn survives, at most 6 steps) first when no step is clear.
- So every choice is one ply; nothing models where the pursuer will be next turn, its cooldowns, or sight beyond
  this turn.

## Prior evidence (EXPERIMENTS)

- Haven-seeking (retreat toward a nearer healthy ally) changed deaths on neither side (2026-11-02), and "retreat toward
  a nearer healthy ally from the first retreat turn" was 49.5%. Option (b) has negative evidence: not built first.
- V3 "retreat race" (stay if the walk home falls) lost 3.4 points: worst-case pursuit calls survivable walks doomed.
  Option (c) only with a realistic pursuer, and not first.
- Ranged retreat-step variants (standing reach) were level.

## Design v1: a 3-turn route comparison (rplan in fight.cc)

Fires inside `retreat_step` only on the ranked-steps path (danger within 8, no avoid-free path home), when a visible
pursuer is within 9, no option's HomeWalk survives, and fuel > 50k (any later shortfall falls back to the base order).

- Candidates: the same steps as the base; with no clear step also the touched steps away from home (the base drops
  them). With a clear step, only the clear steps (never trade a hit now for a guess about later).
- Score of a first step p = its exact one-turn tally (as the base ranks it, bush margin included) + discounted
  (0.75/turn) damage at our turns 2..3 from a rollout + a death penalty (earlier = worse) + 2% of max health per
  step left home at the horizon. Ties (rounded to 1 hp) keep the base order.
- Rollout: pursuers (visible, up to 4 nearest) each act turns_before_ours times after our first move, then once per
  turn. Each picks its best legal action by the rules: stand and hit (basic needs sight in range, reset = second
  basic, unit spells need sight within 4, ground spells reach 5 without sight; one cast a turn); walk then hit
  (melee walk and attack are independent; ranged only through a reset; exclusive spells not after a walk); dash then
  hit (ranged: dash then basic from the landing; melee: dash, walk, hit; Heart of Ruin's landing damage + stun).
  With nothing to hit it chases: dash when more than range+1 away (as our chase does), else a walk (as built: the
  open step closing most as the crow flies over its walls, our spawn among them; host fields were too dear). Cooldowns from the readable ready rounds (8-round
  slots). A pursuer more than 8 away loses us and stops. A stun on us skips our next move.
- Our moves after the first: a homeward step (lateral if none) fewest pursuers' one-turn Chebyshev reach can hit,
  then steps, then distance. Our dash and our own hits are not modelled.
- Sight: `attack_viewers(q, 4)` (exact bush rule: a bush tile is seen only from its own cluster), memoised per tile.

## Building it (fuel and a bug)

- First traces (debug, maps/gen): the plan fired 4.6 times a game of ~153 ranked retreat turns. Cause: a visible
  enemy that shows a recall channel was left out, and every ocean-like enemy shows one (the turn-end recall feint).
  Fixed: only tribute and teleport channels drop a pursuer. Then 36 plans a game, ~2 changed steps a game.
- Retreat deaths (debug, 1024 games): 4.2 of 4.9 champion deaths a game have an R decision in the victim's last 4
  rounds, and 89% of those passed through retreat_step's ranked path (not the far or around-avoid paths).
- Fuel: the first rollout cost p50 26k / p90 36k (pursuer walks on host fields, then mostly our own loops). With
  Chebyshev walks over the pursuers' walls, a reach bound so an out-of-reach pursuer only chases, and cached sight:
  p50 ~22k / p90 ~34k, gated at 50k left (falls back to the base order below 30k).

## Round 1 (cl2-ret-v1): the route comparison alone

- 20,480 games on cl2-dev: **50.1% (49.4-50.8)**; OOF 217,912 vs 205,664 (+6%).
- fight_metrics on 2,000 kept games: deaths 10.12 vs 10.06 a game, kills 9.64 vs 9.72, gems 700 vs 717.
- Debug gen+gen-s1 (1,024 games): champion deaths 4.94 vs 5.11, retreat deaths 4.27 vs 4.43 (within noise).
- Calibration of the rollout (debug, 1,024 games, plans by the cand): when **every** candidate step's rollout ends
  in our fall, the champion died within 4 rounds 66% (melee, n=2,569 turns) / 58% (ranged, 2,079); when the chosen
  step lives, 2.5% / 1.7% (~43k turns). The model separates doomed from safe retreats well; most changed steps were
  clear-step reorderings (a lateral step over a homeward one) that cost little and gain little.

## Round 2 (cl2-ret-v2): + doomed_commit (option c)

`doomed_commit` (fight.cc, end; called in bot.cc after fixc_commit): in contact (hurt this round or last), more than
one step from home, every walking step's rollout falls, and a visible enemy within 7 dies to our basic hits
(kill_turn) before the soonest of those falls: fight (leave = false) instead of retreating. With the kill within our
next 2 turns it fired 13 times in 512 debug games (10 killed within 4 rounds, 4 died); relaxed to the rollout's
horizon (3 turns) for the A/B.

- 20,480 games on cl2-dev: **49.4% (48.7-50.1)**; OOF 224,802 vs 206,870 (+8.7%).
- fight_metrics on the 1,000 kept games (the first to finish, so short games): deaths 9.07 vs 8.15, kills 7.81 vs
  8.73, gems 711 vs 773. On the 474 games both rounds kept: cand minus ref deaths +0.24 a game (v1) against +1.27
  (v2), win 48.3% against 44.7%. Suggestive of harm in fast, fight-heavy games, but a small biased sample.
- Debug gen (512 games): doomed_commit fired 15 times (11 killed within 4 rounds, 4 died); debug champion deaths
  4.88 vs 4.92. The release rate may be higher (debug traces spend fuel, so fewer turns pass its 50k gate), and the
  relaxed window (a kill up to 2 turns away against a fall the rollout puts at 2-3) is the likeliest cause of the
  drop. Not confirmed: no third round.

## Verdict and what was learned

- Neither round beats the base: v1 level (+6% OOF), v2 level to slightly worse (-0.6, +8.7% OOF). Not for shipping.
- The rollout is a usable predictor (doomed vs safe separates 60% vs 2% death within 4 rounds) but acting on it in
  step choice changes ~2 steps a game and nothing measurable. Retreat deaths are decided before the ranked steps:
  by the time every route is predicted lost the champion is already caught.
- Cost: ~22k fuel a plan (our own loops: ~1 fuel a WASM instruction), firing ~36 times a game; too dear for the
  effect. A version worth trying would run it only where it can matter (no clear step, or a pursuer within its
  one-turn reach + 1), in a few k.
- Next: use the doom signal earlier, at the leave decision (want_home: leave sooner, or do not start a walk the
  rollout already loses), and test doomed_commit with the strict window (a kill this turn or next) alone on v1.
- Tools (session scratchpad, not kept): RPLAN / RPSKIP / RS / DOOMC debug traces in the copy; scripts joining them
  with extract.mjs deaths (retreat deaths by path, rollout calibration).
