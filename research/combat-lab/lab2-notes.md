# Lab v2: forks of real games (PLAN2 Phase 1, 2026-11-08)

This lab forks real local games. At chosen rounds it captures the whole state and replays the deciding champion's
turn with every legal action forced, then lets the bots play on for 60 rounds and scores each line at marks.
The runner's design, checks and limits are in
[RUNNER.md "Forks of real games"](../fastengine/RUNNER.md#forks-of-real-games-fastrunner-forkgame-2026-11-08).

## Setup

```
py tools/combatlab/labify.py variants/oc-cl2-base variants/lab-cl2 && cambc build bots/variants/lab-cl2 --release
cd tools/fastengine/runner && CARGO_TARGET_DIR=target-lab2 cargo build --release
```

- `labify.py` now also patches in `lab_act_run` (the forced-action block, `LabAct` in `tools/combatlab/lab.h`) at
  the start of ocean's `decide`.
  - The anchor is optional: astraeus copies still labify, but without forced actions.
  - The "plan early" anchor takes two spellings, since oc-cl2-base dropped `ready_known`.
- `lab-cl2` has `test_draft` off.

## Driver

```
py tools/combatlab/fork_sweep.py --games 16 --both-sides --seed 1 --out DIR --jobs 16 [--holds 1,3] \
    [--bot-a variants/lab-cl2 --bot-b variants/lab-cl2] [--maps maps/suites/merged/cl2-dev] \
    [--trigger near:6,branch:RC] [--max-forks 8] [--gap 20] [--marks 10,30,60] [--arms none,sweep] \
    [--weights trib=1,gems=0.5,wealth=0.02,kills=40,deaths=-40,work=0.25,self_dead=-20] [--runner-args "--hash --full"]
py tools/combatlab/fork_sweep.py --analyze DIR [--weights ...]      # re-score without replaying
```

- **Inputs.** It samples `--games` maps (0: all) and writes `DIR/games.jsonl`.
- **Run.** It runs `fastrunner forkgame` with `target-lab2`'s library, the wasm engine and native bots, taking CPU
  slots from the shared pool.
- **Outputs.**
  - `DIR/forks.jsonl`: the runner's game, fork and arm lines.
  - `DIR/regret.jsonl`: one row per fork and mark, with each arm's value and parts, the best arm, ocean's rank and
    the regret.
- **Values.** They are from the decider team's view, as changes since the fork, own minus enemy: tributed gems,
  gems carried, wealth (gold + items), kills, deaths, work turns (lab bots only), and whether the decider is dead.
- **Weights.** The defaults are placeholders: fit them before reading regret as a loss.
- **Summary.** It prints the determinism checks, CPU throughput, and per mark the regret mean and median, how often
  ocean was best, the best arm's kind, regret by trigger, and best minus ocean per part.

Direct runner use, for one map:

```
FASTRUNNER_LIB=$PWD/tools/fastengine/runner/target-lab2/release/libfastrunner.so FASTRUNNER_ENGINE=wasm FASTRUNNER_MODE=native \
  tools/fastengine/runner/fastrunner forkgame --bot-a variants/lab-cl2 --bot-b variants/lab-cl2 \
  --maps maps/00ambush.map26a --max-forks 4 --arms none,sweep,end,home:0:5 --holds 1,3 --out OUT.jsonl
```

## Validation

- **Identity of the lab copy at 100M fuel**, lab-cl2 against oc-cl2-base, 24 ladder maps on both sides: 47 of 48
  replays are identical.
  - The odd one is a one-tile step at round 39 of 00elkring; the result is the same.
  - The cause is ocean's turn-end queue, which budgets relative to the turn's start fuel. The hooks' 224-324 fuel a
    turn therefore moves its cache filling.
  - With `FASTRUNNER_UNLIMITED_BOTS=lab-cl2,oc-cl2-base`, all 48 are identical.
- **Pass 1 against `fastrunner run`:** byte-identical replays, 4 of 4.
- **Determinism**:
  - The `none` arms match pass 1's digests in all 254 forks over 60 rounds.
  - The main line after the forks matches pass 1 in 32 of 32 games.
  - `--full` gives identical final replays.
  - Arm results do not depend on the order the arms are played in (636 of 636).
  - Reruns are identical.
- **Scenario mode unchanged:** sorted-identical rollout lines against the HEAD build on 60 bank0 frames, in plain,
  alt, and hitlog/decisions/marks/hash modes.

## Throughput

Run: 32 cl2-dev games (16 maps, both sides), lab-cl2 against itself, `--holds 1,3`, 16 jobs.

| | per run | per core |
|---|---|---|
| forks | 254 | 3.4 forks/s |
| arms | 5466, at 60 rounds | 74 arms/s |
| time | 6.2 s wall, 74 s CPU | ~14 ms CPU an arm |

- Pass 1 takes 0.2 s a game.
- A snapshot is 7-26 MiB. Taking one costs ~2 ms, and restoring it costs ≤1.5 ms an arm.
- A thousand games with 8 forks each is ~40 CPU-minutes, about half a minute on the 86-slot pool.

## First read (default weights, not fitted)

Same run. Ocean's own arm ranks ~9th of ~21 arms on average.

| mark | regret mean | regret median | ocean best or tied |
|---|---|---|---|
| 10 | 12 | 0.5 | 76 of 254 |
| 30 | 54 | 19 | 42 of 254 |
| 60 | 89 | 56 | 47 of 254 |

- The best arms are mostly walks (163 of 207 at mark 60). Their gain is mainly in gems, wealth and tribute, not
  kills.
- `branch:RC` forks show more regret than `near` ones (93 against 78 at mark 60).
- These numbers are inflated by max-of-K selection over chaotic single continuations. With holds 1 only (about half
  the arms), the mean at mark 60 was 66. Before any of this is read as a behaviour gap, it needs a noise floor, for
  example:
  - repeated arms under small perturbations;
  - ocean's own first action, forced, as a placebo arm;
  - a second opponent.

## Noise replicates, traces and the pattern analysis (analyst, 2026-11-08)

Findings: [analyst-findings.md](analyst-findings.md). All of it is backward compatible: without the new options,
forkgame's output is unchanged.

- **`forkgame --jitter J,J,...`**: every arm is played once more per J, with every bot's per-turn fuel shifted by J
  from each bot's next turn on. The fork turn itself plays as it did. These rows carry `"rep"` and `"jitter"`, and
  the `none` digest check runs on rep 0 only.
  - `--jitter 0` replays identically: a restore check.
  - It is a weak perturbation. At +1500 only 10% of arms diverge by mark 10 (26% by mark 30); at +-10k and +30k,
    20-25% (about half). Ocean's play barely depends on fuel at these margins.
- **`forkgame --skip-reps K`**: rep k ends the turn (LabAct op 7) of the k-th farthest live lab champion from the
  decider, in the round after the fork. The rows carry `"skip"`. This is the stronger perturbation, and has no
  bearing on the decision: the local combat score moves in about 14% of forks at mark 10 and 29% at mark 30.
- **`forkgame --trace N`**: arm rows carry `trace`, every champion's `[id, x, y, hp, alive]` at each of the arm's
  first N round starts, for reading examples. Rerunning the same games with the same trigger, gap, max-forks and
  seed options gives the same forks.
- **Placebo:** forcing ocean's own first action (the sweep arm matching the `none` arm's tile, hits and cooldowns)
  reproduces its continuation exactly in 217 of 241 matched forks. The forcing mechanism adds no noise of its own,
  so a placebo arm measures nothing; replicates are needed.
- `fork_sweep.py --analyze` treats reps as extra arms. Use the scripts below for runs with reps.
- **`tools/combatlab/mapjson.mjs OUT.jsonl MAP...`**: maps to JSON with both halves (spawns, walls, bushes, camps).
- **`tools/combatlab/fork_regret.py DIR... --out ROWS.jsonl`**: one row per fork, with its situation tags, ocean's
  action class, and per arm its geometric class (walk/dash x toward/away/side x home/out/level, attack near/other,
  casts, end) and per-rep scores at each mark. The combat score is C (all champions) or CL (the champions within
  12 of the decider at the fork), the economy score is E/W; see the docstring. Maps are cached in
  `research/combat-lab/.mapcache.jsonl`.
- **`tools/combatlab/fork_patterns.py --disc ROWS:0 --test ROWS:1 --test ROWS2`**: noise floor (naive regret,
  cross-fit regret over reps, replicate noise), then (situation, action class) patterns ranked on the discovery half
  and measured on held-out halves or other runs, with 95% CIs from a bootstrap over games.
- **Scores (fork_regret.py):** bags are capped at min(gems at the fork, 80) / 80 per dead champion; uncapped bags (500-
  1900 gem carriers) made the score all bag. KD = CL without the health term, bodies and bags only; it is the
  headline key because health share credits healing at home. Verdict arms (`home:V:N`, `chase:V:N`) get the classes
  `home=Vx{N}` / `chase=Vx{N}`; an arm whose branches and scores equal `none`'s is `same_as_ocean`, and its class is
  left out of that fork's gains. The `near_our_home` tag is the nearest enemy's steps to our spawn (`near_home` its
  own).
- **`tools/combatlab/fork_branch_table.py ROWS... --preds br=R,br=C --mark 10 --key KD`**: the a priori table, every
  action class's gain per predicate with both halves and `*`/`-` significance; no discovery step.
- **`tools/combatlab/fork_rules.py ROWS... --rule chase_dash`**: concrete rules that pick at most one arm per fork
  from geometry (chase_dash, chase_dash_any, retreat_dash, attack_low, stun_near), scored per half and per file.
- **`tools/combatlab/fork_verdicts.py ROWS...`**: verdict-arm gains by situation (branch, the target's health, home,
  bag, numbers, distance), per half and per file.
- **`tools/combatlab/fork_examples.py RUN ROWS --pick GAME@FORK@CLASS`**: reruns the picked forks' games with the
  run's own command plus `--trace` and prints the champions near the decider and both arms' trajectories. It needs a
  runner build that has `--trace` (`FASTRUNNER_LIB`, default `target-an2`).
- **Death-triggered forks are outcome-selected.** `death:5` fires on ocean's rep 0 dying, its own reps stay
  correlated with that death, and alternatives look better than they are; judge escapes on pre-decision predicates.
