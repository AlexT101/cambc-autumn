# Bridging the fuel gap (ocean, 2026-11-10)

Current ocean (`bots/ocean` at d4f6e68a6, CHANGES 495; frozen as `bots/variants/oc-ceil-ref`) wins 54.2% against
itself when it has 10M fuel a turn. Of that +4.2:
- About +1.3 is out-of-fuel turns. This programme leaves them alone.
- +2.55 ±0.89 is work its own fuel checks cut short. That is this programme's target.

The split by subsystem is in EXPERIMENTS.md ("Fuel ceiling re-measured"):
- World update free: +1.14.
- Farm free: +1.11.
- Prey +0.43, strike search +0.20.
- Step guard, turn order, turn-end queue and fight trade: about 0.

**The approach is not exact fuel cuts.** Those now come at 0.3-0.7% a change after ~16 campaigns. Instead the work
should get more out of the same fuel:
- changing the order of computation (within a turn, or across turns);
- using partial information;
- reusing information across turns where it is provably not stale;
- making shortcut logic smarter.

Changes may change play; win rate judges them.

## Rules for every lane

- **Read first:** `AGENTS.md`, `cambc-rules.yaml` (`fuel:` especially), `research/fuelcap-2026-11-09/README.md`,
  `research/fuel-2026-11-10/README.md`, and the EXPERIMENTS.md sections your lane brief names.
- **Where to work:** only in your own copies, `bots/variants/fg<lane>-*`, made with
  `./copybot bots/variants/oc-ceil-ref bots/variants/fg<lane>-<name>`. Also your own notes file,
  `research/fuelgap-2026-11-10/lane<X>.md`, and patches beside it.
- **What not to touch:**
  - `bots/ocean`, other lanes' copies and `research/EXPERIMENTS.md` (the coordinator records results).
  - Git: no `git add`, `commit`, `checkout`, `stash` or `reset`. The checkout is shared and holds teammates'
    uncommitted work.
- **Running games:**
  - Fast runner prefix: `CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native`.
  - Set `CAMBC_SLOT_WEIGHT=15` on every game-running command (the box is loaded).
  - Anything over ~30 s runs in the background or in tmux, never a foreground sleep loop.
  - Own drafts on both sides (`--no-test-draft`).
- **No win-rate A/Bs.** Judging happens after a read-only audit, by the coordinator. You may run:
  - mechanism checks: debug builds with `debug_block` traces, `tools/fuel/census`, `tools/fuel/fuelprof`;
  - `tools/fuel/bench.py`, including 100M identity;
  - up to ~1,300 games per check, to show that the mechanism fires, how often, and what it changes. Example metrics:
    `farm-partial-evaluation` count, fuel left at a site, how often a choice differs from the 10M choice.
- **Measurement in this programme's style:**
  - The refund build (`bots/variants/oc-fz2-dev`: `fz_scope`, `FreeScope<N>` in util.h) can price a narrower
    scope than step 0 did. Add a scope number, run that arm at `FASTRUNNER_BOT_FUEL=<dir>:10000000` against
    oc-ceil-ref on `maps/suites/merged/fceil-2020`, and pair it by map against
    `replays/ab/fz2-view/fceil-2020.log` (results per game are in that log).
  - That is a measurement, not a judgement: 20,480 games, about 15 minutes at weight 15.
  - At most 3 such scope runs per lane.
- **Code style:** comment only counterintuitive behaviour, concisely. No `printf` outside `debug_block`.
- **Deliverable:** up to 3 candidates, each a frozen copy `bots/variants/fg<lane>-<name>` with its patch against
  oc-ceil-ref in this directory. Your `lane<X>.md` covers:
  - the measurement and its go / no-go;
  - each candidate's mechanism and the evidence that it fires;
  - what it should change;
  - its risks, and why it is not a re-run of a listed past failure.
- **Stop when:**
  - the measurement says no-go; or
  - you have 3 candidates; or
  - two candidates in a row show, by your own mechanism checks, that they don't change what they were meant to.

  Then report: candidates, evidence, open questions.

## Files

- Results and verdicts: EXPERIMENTS.md "Fuel ceiling re-measured"; lane notes `laneA.md`, `laneB.md`, `laneC.md`.
- `step0-*.patch` rebuild the measurement copies in `bots/variants`, which are gitignored:
  - `step0-ceil-view.patch`: `oc-ceil-ref` to `oc-ceil-view`;
  - `step0-fz2-dev.patch`: `oc-ceil-ref` to `oc-fz2-dev`;
  - `step0-fz2-fout.patch` and `step0-fz2-rep.patch`: `oc-fz2-dev` to those arms.
- Each step-0 arm is `oc-fz2-dev` with its `fz_scope` set; `oc-fz2-t1` has `t1_mult` 50.
- Lane B's 100M bench JSONs are in `~/tmp-offload/fuelgap/laneB-bench/`.
