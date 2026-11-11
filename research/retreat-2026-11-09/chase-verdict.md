# The chase verdict: the escape planner mirrored (ocean, 2026-11-09)

The question: before chasing, can the target get away from our real pursuers? If it can walk home clear of every
hit our visible team could land, the chase is futile, and we drop it. The candidate is `bots/variants/cv-v2`, which
equals this branch's `bots/ocean`; the reference is `variants/oc-esc-merge` (e2c735657, CHANGES 478 + 480).

## Design

**The race, mirrored** (`model/escape.{h,cc}`).
- `Plan::build` is split into two parts:
  - a front end per side: `build` for us running from the enemies, `build_chase` for an enemy running from us;
  - a shared core, `Plan::finish(Pathing&, Race&)`: the terrain rows, the hit layers, the goals and the full pass.
- A `Race` holds what differs by side:
  - which spawn is the runner's (it heals there, and its pursuers may not enter) and which blocks it;
  - the pursuer classes (`Kinds`);
  - the runner's steps home and its turns left;
  - the goal field, and how to read it.
- **The chase race.**
  - The runner is a visible enemy, from its tile. Plan turn 1 is its last turn, already ended; its turns 2..5 are left.
  - Its dash turn is `max(2, ready_round - next + 2)`, where `next` is its next turn's round.
  - Its home is the enemy spawn. The field is our walking field from our spawn (`StaticMap::from_ally_spawn`), exported
    once with 16 entries of padding each side, and read at the symmetry's mirror tile, as `World::enemy_spawn_steps`
    does. Horizontal and rotational maps read the 16 columns backwards and bit-reverse the result; vertical and
    rotational maps read the mirrored row. `goal_rows<FlipX, FlipY>` is templated, so our own read is unchanged code.
- **The pursuers** are this champion, from the turn's start tile with all of this turn's moves, and every visible ally
  with its cooldowns. An ally's next turn always counts as coming before the target's.
  - This over-credits our pursuit, which is the sound direction for a futility call: a clean verdict means not even
    our best pursuit lands a hit.
  - A ranged pursuer's walk, attack reset and shot counts as a burst of basic reach + 1 (Vesper, Tavi, Willow). Our
    own plan keeps that pessimism out (la-fid lost); here it is on the safe side. Our own plan passes `resets = false`.
- **The verdict.** `runner_hits` = whether the target's tile is hit on turn 1 (our first turns: a strike now), plus
  `after_walk` from that tile, capped at `many`.
  - The target *escapes* when that is 0 on the full goal (`horizon - 1` steps nearer its spawn in its four turns),
    or on the slack goal (3 steps short of that).
  - `chase_plan` keeps up to 4 plans a round, keyed by round, target and tile. Nothing a chase plan reads moves
    during our turn.

**The rule** (`combat/fight.cc`, `escapes`): a chase pays through its target. A target that can walk home clear of
every hit our visible team could land is not caught, so the walk after it is futile.
- `prey()` skips such a target: in the pressed shortcut, in the team-pressed shortcut, and in the candidate loop
  before `chase_trade`. The skip also spares that fight sim. The loop re-checks the sim's fuel after the verdict.
- `chase_aim()` takes the nearest engaged prey that does not escape.
- `continue_tribute`'s `prey()` follows, so a tribute is no longer cancelled to chase a target that escapes.
- The race's runner walks on its next turn. A target held in place by a pending stun, a teleport or a tribute it
  keeps is not judged; recalls are judged, since every bot here feints one each turn end.
- With no plan (fuel under `params::escape::min_fuel`, the target on its spawn or cut off, or out of sight) a
  target reads as catchable, as before the change.
- **Precheck:** if any pursuer already strikes the target's tile on its first turn, the target is not clean, and
  no plan is built. That is a melee walk and hit, or a ranged shot from where it stands. The precheck errs only
  towards "catchable", which is the old behaviour.

**What was not built, and why.**
- **Exceptions for captures, bags and strike reach** (the analysis report's suggestion): none were needed.
  - In the shadow run, clean chases of carriers killed 4.4% and of capturers 3.8%, no more than other clean chases
    (4.9%).
  - `contest_capture` runs right after `chase`.
  - A target in strike reach is never clean by construction.
- **A "running home" condition:** clean targets that moved in the round before were killed *more* often (6.0%)
  than ones that stood (4.0%).
- **Chase steps** were left alone: lead pursuit and minimax steering lost before. `want_home`'s stand verdict is
  untouched.
- **Doomed-first target order** (the report's step 2): built later as `variants/cv-doom` (one-hit targets after the
  rest). It changes ~0.9 picks a team-game, too few to screen (EXPERIMENTS "Doomed-first chase order").

**Known limits.**
- Turn order is modelled as strict alternation. Counterpart pairs flip with round parity, so a pursuer can get two
  turns before the runner moves and none before its next. Our own escape plan has the same simplification. The
  shadow's empirical kill rates already include its effect.
- Ward sight into bushes, allies out of our sight, and the rule that the runner's dash may not cross our visible
  champions are not modelled.

## Identity of our own escape plan

`tools/fuel/bench.py run BOT --opp variants/oc-cl2-seat5m --set wide --test-draft --jobs 86` at 100M, then
`bench.py compare`. BOT is oc-esc-merge with only the final `escape.{h,cc}` swapped in (`variants/cv-refactor`).
- **Identical replays 52/52.** Total fuel 13,329.3M → 13,330.3M (+0.01%, ~70 a build).
- The first cut was +0.03%. Templating the goal loop and inlining the class adds brought it to +0.01%.
- The same check passed at each step.

The mirrored goal read was checked directly too. A temporary debug pass compared every window goal bit against
`World::enemy_spawn_steps`. It found 0 mismatched tiles in 1,389 chase builds, over one ladder map of each symmetry
(00ambush rotational, 00anvil horizontal, 00collision vertical). A chase build costs ~8-11k, like our own.

## Shadow runs

Debug builds that compute and log the verdict without acting (`CV` lines, inside `debug_block`, fuel paused). Each
is 1,280 games: the default suites (`ladder`, `gen`, `gen-s1`), both sides, against oc-esc-merge. Tools:
`tools/cv_shadow.py` (one row per CV line, joined with the replays).
- "Kill" is the target killed by our team within 10 rounds.
- Episodes are runs of chase (P) turns on one target, with gaps of 2 rounds or less; their kill window runs to the
  episode's end + 3.

**Shadow 1** (`cv-shadow`, the first verdict):

| chase turns (P) | share | kill within 10 | chaser died |
|---|---:|---:|---:|
| clean | 40.9% (86.5 a team-game) | **4.9%** | 1.1% |
| one hit | 9.5% | 9.4% | 1.6% |
| doomed (2+) | 43.4% | **22.7%** | 2.3% |
| no plan | 6.2% | 23.6% | 2.0% |

- **At equal distance it still separates.** By gap (distance − attack range) 3 / 4 / 5: clean 6.3 / 4.6 / 3.5%,
  doomed 22.0 / 19.4 / 16.9%.
- **By target health:** under 25% health, clean 13.7% against doomed 62%; 75% and over, 3.2% against 10.0%.
- **Episodes by their first turn:** clean 3.7% kill, one hit 6.4%, doomed 15.1%. Episodes clean on every turn:
  1.9% (24.9k episodes, 50 turns a team-game).
- **The strike search's aims (A lines):** clean 7.1%, doomed 27.7%.
- That met the gate (clean far below doomed), so the rule was built.

**Shadow 2** (`cv-shadow2`, the verdict after the audit's fixes, below), judged turns only (no stun, teleport or tribute):

| chase turns (P) | share | kill within 10 |
|---|---:|---:|
| clean | 40.6% | **4.9%** |
| one hit | 11.3% | 9.1% |
| doomed | 41.9% | **22.2%** |

- The full goal now carries the verdict: 99.9k clean turns on the full goal, 4.3k on the slack goal only.
- Every health band separates as before.

## The audit

A read-only auditor reviewed the first candidate. It confirmed these as correct:
- the mirrored index arithmetic for all three symmetries, and the padding;
- the cooldown and dash formulas;
- the spawn roles;
- the cache;
- the shared statics (nothing leaks into our own plan).

It found five problems, fixed in cv-v2:
1. A stunned target was credited with its lost turn's walk. Now it is not judged.
2. A target channelling a teleport was credited with walking. Now it is not judged.
3. The full goal asked for `horizon` steps in the runner's `horizon - 1` turns. Walkers could never reach it, and
   the verdict fell back on the slack goal alone. Now it asks for `horizon - 1`.
4. Ranged walk-reset-shoot was missing from our pursuit. Added for the chase only.
5. A tribute the target keeps: it is not judged, since escaping costs it the tribute.

Left as a known limit: turn-order flips (above).

## A/Bs

All release builds, fast runner (OOF counts below), `--no-test-draft`, against `variants/oc-esc-merge`.
- **Screens:** `esc2-dev-s20`, the first 20 seeds of `maps/suites/merged/esc2-dev` (fresh-1700000..1700019, 5,120
  maps, both sides).
- **Final:** `maps/suites/merged/plan2-dev`, unused by any screen.

| A/B | variant | suite | games | win % (95% CI) | OOF CAND / REF |
|---|---|---|---:|---:|---:|
| cv-fut-esc2s20 | cv-fut: the verdict, gate 50k | esc2-dev-s20 | 10,240 | 50.7 (49.7-51.6) | 143,126 / 114,869 (+24.6%) |
| cv-fut-pre-esc2s20 | cv-fut-pre: + the first-turn strike precheck | esc2-dev-s20 | 10,240 | 50.8 (49.8-51.8) | 125,749 / 115,576 (+8.8%) |
| cv-v2-esc2s20 | **cv-v2**: + the audit fixes | esc2-dev-s20 | 10,240 | **51.5 (50.5-52.5)** | 126,970 / 114,715 (+10.7%) |
| cv-final-v2 | **cv-v2** | plan2-dev | 40,960 | **51.7 (51.3-52.2)** | 497,633 / 460,838 (+8.0%) |

Debug batches of 1,280 games (default suites, not judged by win rate): cv-shadow 50.3%, cv-shadow2 50.1%, cv-fut
52.7%, cv-v2 53.4% (50.7-56.2).

## Metrics

Debug batches on the same 1,280 games: each candidate's games against oc-esc-merge, paired by map and side with
cv-shadow's (= oc-esc-merge's behaviour). Per team-game, mean difference ± 95% (`tools/cv_paired.py`, from
`tools/cv_metrics.py`).

| metric | base (cv-shadow) | cv-fut | cv-v2 |
|---|---:|---:|---:|
| kills | 5.50 | −0.41 ±0.32 | −0.31 ±0.30 |
| deaths | 8.02 | −0.30 ±0.43 | −0.51 ±0.43 |
| deaths to champions | 7.28 | −0.34 ±0.43 | −0.55 ±0.43 |
| chaser deaths (within 3 of a C turn) | 0.45 | −0.08 ±0.06 | −0.14 ±0.06 |
| chase episodes | 60.4 | −14.0 ±1.6 | −12.6 ±1.6 |
| chase episodes with a kill | 5.00 | −0.82 ±0.30 | −0.69 ±0.30 |
| no-kill chase turns | 198 | −85 ±7 | −81 ±7 |
| chase turns | 222 | −93 ±7 | −88 ±7 |
| farm turns | 2,815 | +56 ±25 | +58 ±25 |
| hold turns | 182 | +16 ±15 | +17 ±14 |
| retreat turns | 348 | −15 ±11 | −14 ±11 |
| tributed gems @600 | 420 | +13.7 ±11.7 | +17.7 ±11.4 |
| enemy tributed gems @600 | 419 | +6.2 ±11.7 | +10.6 ±11.0 |
| gold earned @600 | 3,048 | +71 ±51 | +83 ±49 |
| captures | 60.5 | +0.82 ±0.89 | +1.23 ±0.86 |
| enemy captures | 60.1 | +0.70 ±0.90 | +0.35 ±0.88 |
| denials (enemy holds reset) | 2.22 | −0.01 ±0.26 | +0.79 ±1.60 |
| OOF trace lines (debug) | 10.7 | +2.5 ±0.8 | +0.6 ±0.7 |

- **Fuel.** A chase build costs ~8-11k: 10.4k mean over cv-fut's debug builds, ~370 a team-game.
  - cv-fut's OOF excess (+24.6%) was the build on turns where the target was plainly in reach. The precheck
    removed most of it (+8.8%).
  - Debug OOF lines by phase, a team-game: base decide 7.7 / queue 3.0; cv-fut decide 9.8 / queue 3.3; cv-v2 decide
    8.3 / queue 2.9.
  - The rest is the build before the strike search (`chase_aim`), which has no fuel gate of its own.

## Mechanism

The rule removes ~40% of chase turns: 88 a team-game, nearly all of them chases that end without a kill.
- **Where those turns go:** they return to farming and holding.
  - +58 farm turns and +17 hold turns.
  - +18 gems tributed and +83 gold by round 600.
  - +1.2 captures.
- **Deaths fall,** mostly the chasers' own (−0.14 of −0.51). A futile chase walks a champion deep, towards the
  enemy's spawn and its friends.
- **The cost is kills:** −0.3 a team-game, from chases that would have caught a target the plan says can walk home.
  These are targets that fled badly or turned back.
- **Second- and third-order effects:**
  - Less pressure lets the enemy bank a little more (+10.6 gems at 600, within noise).
  - Allies lose nothing they counted on: each champion's verdict counts its visible allies as pursuers, so a team
    pursuit that can land a hit goes on.
- Earlier chase-dropping filters lost because they gave up kills for farm time at break-even (b3 race home, b4
  chase value v1/v2). This verdict drops only chases that the whole visible team's best pursuit cannot touch, and
  those kill at a quarter of the rate of the rest.

## Recommendation

**Merge cv-v2.** It reads **51.7% (51.3-52.2) of 40,960 games** on the fresh plan2-dev suite against oc-esc-merge.
- Its CI excludes 50.
- The final agrees with its screen (51.5%).
- Our own escape plan is byte-identical.
- The mechanism is measured: fewer futile chases, more farming and holding, fewer chaser deaths, a third of a kill
  given up.

Follow-ups, not tried here:
- **The remaining OOF excess (+8%)** is mostly the aim's verdict before the strike search. A gate on the fuel the
  search still needs, or reusing a teammate's verdict through comms, might recover some of it.
- **The doomed-first target order** (the report's step 2): built and counted; too rare to matter (EXPERIMENTS).
- **Modelling the turn-order flips** in both races.

## Tools

- `tools/cv_shadow.py`: CV lines joined with outcomes.
- `tools/cv_metrics.py`: per team-game metrics from D lines and replays.
- `tools/cv_paired.py`: the same metrics, paired by game.
- `tools/cv_fuel.py`: OOF trace phases and chase builds.

The extracts are `replays/cv-shadow-ex`, `replays/cv-shadow2-ex`, `replays/cv-fut-dbg-ex` and `replays/cv-v2-dbg-ex`;
their batches hold a `.keep`.

## Fuel gate (cg-aimgate2, 2026-11-09)

The question: cv-v2 ran out of fuel (OOF) on 8.0% more turns than oc-esc-merge. Where do those turns come from,
and can a gate recover them without losing the win rate?

**Answer: the excess is mostly chase_aim's build, before the strike search.** Gating that build on the fuel the
search needs after it halves the excess and reads level with cv-v2.

### Measurement

`tools/cg_instrument.py` patches debug checkpoints into a copy, all inside `debug_block`:
- the fuel at chase_aim, after it, after `plan_strikes` and at prey;
- the last checkpoint passed;
- every chase build: its caller, the fuel at the ask and the cost; gated asks;
- whether the search read the aim, and the prey loop's verdicts and sims.

`trace_verdict` is switched off, since its free debug builds would be cached for later asks. The run: `cg-inst`
(cv-v2) against `cg-inst-ref` (oc-esc-merge), debug, 5,120 games on `cg-meas`, seeds 1700020-29 of
`merged/esc2-dev` (none of the screen's seeds). OOF lines: CAND 62,745 against REF 58,066 (+8.1%), the release
excess. Parsers: `cg_parse.py` and `cg_excess.py`.

**Where the excess falls** (OOF turns per 100 team-games by the last checkpoint passed, CAND − REF; total +91):
- in the strike search after chase_aim +17.7;
- after the search, before chase +22.3;
- after prey +28.7 (the chase walk, or the farm after a dropped chase);
- the act tail +16.4;
- retreat −10.3 (fewer retreats).

**The builds** (per team-game):

| caller | builds | mean cost | OOF after (per 100 team-games) | of which from the build's fuel |
|---|---:|---:|---:|---:|
| chase_aim (before the search) | 40.7 | 11.4k | 75.6 | **68.4** |
| prey (pressed 15.6, loop 214) | 219 build turns | 11.6k | 64.8 | 48.4 |

- "From the build's fuel" is the sum over build turns of P(X) − P(X + c), where X is the fuel left after the build,
  c is its cost, and P is the hazard of that caller's own build turns by X. It assumes the work after the build does
  not depend on the build. fuel-gate.md found that for the retreat's plan.
- The two together (117) exceed the net +91: the verdict's own behaviour (fewer retreats and chases) saves some.
- **Per build, chase_aim's is ~8x as dangerous as prey's** (1.7% of its turns run out because of it, against 0.22%).
  Both are gated at the same 50k, but chase_aim's comes before the strike search:

| fuel left after the build | 34k | 38k | 42k | 46k | 50k | 54k | 58k |
|---|---:|---:|---:|---:|---:|---:|---:|
| chase_aim build turns that ran out | 16.7% | 10.6% | 6.4% | 3.9% | 1.9% | 0.8% | 0.3% |
| prey build turns that ran out | 1.2% | 1.0% | 0.6% | 0.4% | 0.2% | 0.1% | 0.1% |

- At the 50k gate, chase_aim leaves ~39k at the mean build. That is a 10% hazard where prey's is 1%.
- The heavy turns are those whose search ranks its walk by the aim (8 of the 40.7 a team-game). Their OOF is 56.5
  of the 75.6, and their hazard at X = 50k is 7.5%.
- **What those turns lose:** of chase_aim's 75.6:
  - 12 ran out inside the search, losing its strikes and walk;
  - 26 between the search and chase (the goal's step, carry or guard);
  - 12 after prey;
  - 15 in act's tail (ward, lock, recall feint, strike_after);
  - the rest in turn order and comms.
- **The prey loop:** 79% of its verdicts say "escapes" (168 of 214 a team-game). Each of those spares a fight sim,
  which costs 5.6k mean. 70% of the sims that run are lost.
  - Running the sim first would build only after a won fight. It would also be exact in outcome. But it would add
    those sims back, and it nets only ~0.4M fuel a team-game. Not built.
- **The aim is read rarely:** the search reads the aim on 20% of the turns chase_aim builds. A lazy verdict
  computed only there would save the other turns' builds, which carry 16.8 of the 68.4. A gate saves most of those
  too (below). Not built.

### The change (`cg-aimgate2` = this branch's `bots/ocean`)

- `chase_aim`'s verdicts ask for `escape::chase_cost_estimate() + search_reserve` instead of `min_fuel`.
  - `search_reserve` (util.h) is `act_reserve + 30000`. It is the floor `goal_field` already set for a full
    search's growth and the goal's work after it, now named and shared.
  - `chase_cost_estimate()` is the running mean (1/8) of this instance's fuel-gated chase builds. It is measured
    after the game's one-off boards, and a build that resumed in a later round is not counted.
- **The audit.** A read-only auditor found no release bug.
  - It found one debug-only problem: `trace_verdict`'s builds (need 0, inside `debug_block`, fuel paused) fed the
    mean with ~0 and loosened the gate in debug builds. `cg-aimgate2` counts only builds with need > 0.
  - Release plays the same as `cg-aimgate`, which the screen ran: trace_verdict is compiled out there.
  - The instrumented check below had trace_verdict off, so it is unaffected.
  - Left as is: the slack pass (~1k, its own 40k gate) can run after a build that just clears the gate, so the
    search can get a little less than the reserve.
- So the build must leave the strike search ~50k. Its hazard there is 1.9%, about where prey's asks run. prey's
  asks keep `min_fuel`, as the retreat's do.
- A gated verdict reads "catchable", the old behaviour; prey may still ask later at its own gate.
- No other change. The retreat plan is untouched; `goal_field`'s floor is the same value.
- Predicted from the traces: 24% of chase_aim's builds gated (9.6 a team-game, 2.1 of them escapes), saving ~56 of
  the +91.

**Check** (instrumented `cg-inst-gate` against `cg-inst-ref`, the same 5,120 games, 2 runner failures during the
cambc 5.0.1 switch):
- OOF lines CAND 62,271 against REF 59,868: **+4.0%**, from +8.1%.
- chase_aim's builds: 32.4 a team-game (−20%). The fuel left after them is now p10 51.7k (from 43.9k).
- OOF after them: 19.3 per 100 team-games (from 75.6); from their fuel, 17.7 (from 68.4).
- In the search: +1.8 against REF (from +17.7).
- prey's builds: 222 (from 219), with OOF from its fuel unchanged at 47.6.

### A/Bs

Release, fast runner, `--no-test-draft`.

| A/B | CAND / REF | suite | games | win % (95% CI) | OOF CAND / REF |
|---|---|---|---:|---:|---:|
| cg-aimgate-esc2s20 | cg-aimgate / cv-v2 | esc2-dev-s20 | 10,240 | 50.2 (49.2-51.2) | 117,482 / 122,314 (−4.0%) |
| cg-final-aimgate2 | cg-aimgate2 / oc-esc-merge | plan3-dev | 40,960 | **51.7 (51.2-52.2)** | 473,042 / 452,955 (**+4.4%**) |

- For comparison, cv-v2 against oc-esc-merge read 51.7 (51.3-52.2) on plan2-dev, with OOF +8.0%. Its esc2-dev-s20
  screen read OOF 126,970 / 114,715.
- One screen was enough: it read level with OOF down, as the traces predicted.
- Variants not screened, and why:
  - the 1%-hazard reserve (53k): it predicts 61 saved instead of 56;
  - a lazy aim: it saves at most ~3 per 100 beyond the gate;
  - sim-first prey: ~0.4M fuel.
  None can be told apart from this gate in a 10,240-game screen.

**Reading.**
- The final is level with cv-v2's: 51.7 (51.2-52.2) on fresh plan3-dev, against 51.7 (51.3-52.2) on plan2-dev.
- The OOF excess over oc-esc-merge falls from +8.0% to +4.4%, as the debug check measured (+8.1% → +4.0%).
- The final ran on cambc 5.0.1 and cv-v2's on 5.0.0, a bug-fix release.
- The rest of the excess is prey's verdicts, at the hazard its flat gate shares with the retreat's (~1%). It is the
  verdict's price at the gate fuel-gate.md found par-optimal.

**Recommendation: merge cg-aimgate2.**
- It keeps the verdict's full gain.
- It halves its OOF cost.
- The change is a fuel gate built from existing reserves and a measured cost: no tuned number.

Safe to delete (untracked, main checkout):
- `bots/variants/cg-inst`, `cg-inst-ref` and `cg-inst-gate` (instrumented copies);
- `cg-aimgate` (plays as cg-aimgate2 in release);
- the batches of `cg-meas3`, `cg-meas-gate`, `cg-runner-probe` and `cg-runner-probe2`.

Tools: `tools/cg_instrument.py` (checkpoints; `--ref` for a bot without the verdict), `cg_parse.py` (OOF by
checkpoint, builds, hazards), `cg_excess.py` (each caller's excess from its fuel), `cg_gate_sim.py` (a gate's
predicted saving), `cg_preyloop.py` (prey's verdicts and sims).
