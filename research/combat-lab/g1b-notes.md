# G1b: pursuit (chasing) reasoning (notes, 2026-11-08)

Copy: `bots/variants/cl2-chase` (from `variants/oc-cl2-base`). Reference for every A/B: `variants/oc-cl2-base`,
`--no-test-draft`, suite `maps/suites/merged/cl2-dev`. Scripts: scratchpad `g1b/` (pursuit.py: flee episodes with
the nearest pursuer's per-round trace; join.py: episodes against the debug `PT` lines; intercept.py: static
interception gain; dashes2.py: dashes toward hurt enemies and whether they hit).

## Diagnosis (base mirror, cl2-belief-v1's 1,000 games; debug batch of 300 games for the branch traces)

- Pursued flee episodes (flee.py's definition): 33% caught, 34% home. By the pursuer: melee 32% / ranged 35%;
  by enemies within 5 at the start: 1 → 30%, 4+ → 42%; by gap: 1 → 44%, 4 → 27%.
- Distance over the episode: in escapes the gap sits at 4 (45% of episodes at k=2), then grows from k=3: the
  pursuer stops. In caught ones it stays at 1-3.
- **What the pursuer does** in the first 8 rounds of a pursued episode (debug `PT` line: decision + prey's verdict),
  escapes vs catches:
  - retreating itself (`R`, want_home): 22% + 6% of turns in escapes, 7% + 1% in catches.
  - chasing (`C`, prey chose it; mostly through pressed/team_pressed): 18-21% in escapes, 30% in catches.
  - farm/attack branches with the target preyable (`F`): 12% vs 26%.
  - prey said the fight is lost (`l`): 2.7% of escape turns; pack zone (`p`): 0.5%. Neither is the bottleneck.
- `C` turns are mostly at gaps 5-8 (the strike search handles 5-6 and nearer), and the gap holds or grows: at equal
  speed a follower never closes unless the fleer is slowed.
- Static interception (BFS, fleer on a shortest route home, pursuer to any tile of that route in time): at the
  episode start, 15-20% of escapes were interceptable but not yet in reach, 23-27% of catches. A real lever, but
  not a large one.
- Dashes toward a hurt enemy: from 2-3 (melee) or 4-5 (ranged) they hit ~97% / 91%; from farther (melee 5-8, ranged
  6-8) they never hit that turn and rarely the next (~4.6 such dashes a game, both sides). By pure geometry an early
  dash and a held one convert on the same condition (the fleer slowed by the same amount), so it is not a free fix.

## Design v1: lead pursuit (fight.cc `lead_aim`)

- A visible enemy is **fleeing** if it stood farther from its spawn (static steps, `enemy_spawn_steps`) at our
  previous turn's end (`note_sightings`, per enemy index, written at each turn end).
- Its route: up to 10 steps, each one step nearer its spawn, choosing the one farthest from us (its first step
  avoiding tiles a seen champion holds), ending before its spawn's edge.
- Its moves before each of our turns by turn order: `turns_before_ours` = 2 gives 2, 0, 2, ...; 0 gives 0, 2, 0;
  1 gives 1, 1, ...
- Our reach at our turn t+1: t steps + next turn's strike (ranged: range, +1 with a reset; melee: range + 1) + 2 if
  our dash is off cooldown by then.
- Aim: the first route tile we reach in time; else its current tile (follow, as the base).
- Used by `chase_aim` (the strike search's walk gain) and by `chase()`'s goals (attack range around the aim).

Fires (debug, 300 games): aim moved off the target tile ~48 calls a game; fleeing with no intercept ~60.

### v1 result (cl2-chase-v1, 20,480 games): **48.7% (48.0-49.3), lost**

- Out-of-fuel turns 225,244 (15,744 games) vs 206,756 (15,487): +9%. v1 had no fuel gate or memo (up to ~80 field
  reads, ~2k fuel, twice a turn), on the heaviest turns.
- Kept 1,000 games: kills 7.78 vs 7.99 a game, deaths 7.99 vs 7.78 (champion).
- Catch rate when we pursue the base (pursued episodes): 30.3% vs the base's 31.9% pursuing us; melee pursuers 29.5%
  vs 31.9%, ranged 31.9% vs 31.7%. Melee dashers lost most (31.0 vs 33.1).
- Why (reasoning, not separately tested): a single predicted tile is worse in the worst case than the fleer's
  current tile for a melee follower: beside it, every step it takes stays within a walk-and-hit; beside its
  predicted tile, its other options can open a gap of 3. And far leads (up to 10 moves, crediting a dash that
  comes back later) walk us towards its spawn on a guess.

## Design v2: minimax centre, one move-set ahead, fuel-gated

- The fleer's options at our next turn: all tiles its `turns_before_ours` moves home can reach (each move one step
  nearer its spawn, not onto a champion we see; at most 8 tiles kept).
- Aim: the Chebyshev centre of those options (nearest all of them at once: covers whichever it takes and holds the
  middle of its exit), only when every option is within our next-turn reach (1 step + strike, + dash if ready now);
  else its current tile. No lead when it has no move before our next turn.
- Memo per turn (chase_aim and chase share it); skipped below 40k fuel.

### v2 result (cl2-chase-v2, 20,480 games): **49.6% (48.9-50.2), level**

- Out-of-fuel turns 214,066 (15,533 games) vs 207,375 (15,459): +3% (v1 +9%). The 40k gate covers the option
  search, not `fleeing()`'s two field reads before the memo; part may be behaviour (more fights), not cost.
- Kept 1,000 games: kills 9.52 vs 9.68 a game, champion deaths 9.68 vs 9.52.
- Catch rate when we pursue the base: 30.6% vs 30.7% (12.6k pursued episodes a side). Melee pursuers 30.0% vs
  30.9% (−0.9, ~1.3 SE), **ranged 32.0% vs 30.2% (+1.8, ~1.6 SE)**. Not significant either way, but the same sign
  as v1's melee loss.

## What was learned

- Pursuit kills are decided less by the chase's walk than by whether the pursuer keeps pursuing: when the gap
  opens to 6+ in an escape, the pursuer's previous turn was a retreat (want_home) 44% of the time, and 36% of those
  pursuers were above 90% health (a stand lost to the fleer's allies, G3's ground). Prey's own verdicts (lost
  fight 3%, pack zone 0.5%) rarely end a chase.
- At equal speed in the Chebyshev metric, following and leading are nearly the same in open ground; leading only
  gains where the route bends, which static BFS puts at 15-20% of escapes.
- For a melee follower, its target's current tile is the worst-case-optimal aim (beside it, any step stays within
  walk-and-hit). Leading a melee pursuer cost catches in both versions. For a ranged one, the centre of the fleer's
  options can keep it in range after its step, and v2's ranged catch rate was the one that rose.
- Turn order matters for prediction: `turns_before_ours` is 0, 1 or 2, and alternates 2/0 between seats.

## Next steps (not run)

- v3: the v2 lead for ranged pursuers only (melee follows the current tile), with `fleeing()` inside the fuel gate.
- Far chases with no intercept (gap 7-8): 1.6-3.9% end in our kill within 20 rounds; a futility stop there would
  cost little but also free little (~1 such chase start a game).
- The bigger lever is the pursuer leaving (want_home) mid-chase against a fleeing target, which is G3's.
