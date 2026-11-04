# Oscillation hunt, phase 2: fixer brief

Phase 1 traced ~7,700 games of astraeus and explained why champions oscillate, get stuck or switch targets:
`BRIEF.md` (data, trace format, reruns) and `A-findings.md`, `B-findings.md`, `C-findings.md` (mechanisms with
file:line, examples, prevalence, fix sketches) in this directory. Each phase 2 fixer owns one stream (below). Read
`AGENTS.md`, `cambc-rules.yaml`, `BRIEF.md` and the findings your stream covers before planning.

## Principles (from the user)

- **Robust, well-integrated solutions over patches.** Fix the cause in the model or decision, where it lives, so it
  holds in every caller; not a special case for the example that showed it.
- **Oscillation between two models: align them.** When one piece of code chooses a step or target and another
  undoes it next turn, the cure is not memory or hysteresis. A sound decision is *monotonic*: if moving forward was
  worth it, the value of being there must not drop just because we arrived. So the model that chooses a move must
  judge the destination the way the model that will act there next turn judges it. That means the same reach, the
  same pursuers, the same flags, evaluated for the round we will be there. Best of all, unify the two into one
  evaluation, or restructure them so they agree by construction.
- **Accurate models over shortcuts.** Where a shortcut (straight-line distance instead of walk distance, visible-only
  instead of believed positions, a static field instead of the live route) causes the bad behaviour, replace it with
  the accurate model even if it costs fuel or adds some out-of-fuel turns. Keep the cost reasonable: bounded fields,
  caching, host calls (prices in `tools/README.md`); no full forward simulations. Optimising comes later. Still
  **no new fuel gates** (AGENTS.md, `research/hyperion/FUEL-GATES.md`): make work cheap or bounded rather than
  choosing worse when fuel is short.
- Comment only counterintuitive behaviour or reasoning, concisely (AGENTS.md).

## Process

1. **Plan**: read the code paths in the findings, confirm the mechanism in the source, design the fix (what model
   changes, every caller it affects, fuel cost). Write the plan at the top of your notes file.
2. **Implement** in your worktree (below).
3. **Audit**: spawn one read-only auditor subagent (Agent tool) to review your diff. Tell it the stream's goal and
   principles and ask for correctness bugs, callers or cases missed, consistency between the models it touches, and
   fuel risks. It **must not run code, builds, games or tests**, only read. Address its findings or note why not.
4. **Test** (below), then iterate if needed.

## Where to work

- Your worktree is `/home/ubuntu/wt/osc-<stream>` on branch `osc/<stream>`: edit `bots/astraeus` there. Commit to
  your branch as you go (`git -C <worktree> add <files>`; never `git add -A`, never touch `main` or other branches,
  never push). Don't edit `research/EXPERIMENTS.md` or `research/hyperion/CHANGES.md` (merges would conflict); write
  everything in `research/oscillation-2026-11-04/<stream>-fix.md` **in the primary checkout**
  (`/home/ubuntu/cambc-autumn`), not in your worktree.
- **Run all tools, games and builds from the primary checkout** `/home/ubuntu/cambc-autumn` (generated maps, the
  fast runner, bot variants and replays live only there). Put your bot copies under its `bots/variants/` with
  your stream number in the name (`osc<N>-...`), e.g. sync your working tree:
  `rsync -a --delete /home/ubuntu/wt/osc-<stream>/bots/astraeus/src/ bots/variants/osc<N>-wip/src/`, or a commit:
  `./copybot -r <sha> astraeus variants/osc<N>-<sha7>`. Never edit `bots/astraeus`, `bots/baselines`,
  `bots/variants/astraeus-088bf3f` (the frozen baseline: astraeus at 088bf3f4, your branch point) or another
  stream's files.
- Env for every game run: `source /home/ubuntu/venv/bin/activate; export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86
  CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native`. Other fixers share
  the box: one batch at a time, leave `--threads` alone, run long batches in tmux (`tmux new -d -s osc<N>-x '... 2>&1
  | tee LOG'`) and wait on them with a background task, not foreground sleeps.

## Testing

1. **Episodes**: make a traced copy of your bot: rsync your src into `bots/variants/osc<N>-trace/src/`, then
   `cd bots/variants/osc<N>-trace && patch -p1 < /home/ubuntu/cambc-autumn/research/oscillation-2026-11-04/trace.patch`
   (the phase 1 trace hooks; fix up by hand any hunk your changes moved). Rerun your stream's examples exactly
   (`fastrunner run`, same opponent and sides as the original, BRIEF.md) and show the pathology is gone, with the
   D lines before and after.
2. **Detector**: `CAMBC_LOG_LIMIT=16000000 py tools/ab.py variants/osc<N>-trace baselines/v69 --no-test-draft
   --suites gen,fresh --name osc<N>-detect-<tag>` (1,024 games on `maps/gen` and `maps/gen-s1`), then
   `py tools/replay/osc_detect.py replays/batch-*-ab-osc<N>-detect-<tag>-* --out replays/osc/osc<N>-<tag>` and compare
   with the same maps and opponent before the fix:
   `py tools/replay/osc_detect.py replays/batch-20261104-021505-ab-osc-trace-v69-gen replays/batch-20261104-021505-ab-osc-trace-v69-fresh-gen-s1 --out replays/osc/before-v69`
   (run once; reuse if present). Show your groups shrink and no other kind grows.
3. **A/B (the verdict)**: an untraced copy of your commit against the frozen baseline, 10,240 games on fresh maps no
   one has used:
   `py tools/ab.py variants/osc<N>-<sha7> variants/astraeus-088bf3f --no-test-draft --suites maps/osc-fix-10k --name osc<N>-<tag>`.
   Report the win % with its CI, out-of-fuel turns per bot (fuel cost of your change) and per-suite splits. Noise is
   about ±1 point at 10k. `maps/osc-fix-20k` (20,480 games, a superset) is for shipping; leave it to the orchestrator
   unless asked.
4. If the A/B loses, find out why (`tools/replay/ab_compare.py`, flipped games, detector deltas) and iterate.
   **Stop** when you have a committed version that removes your stream's pathologies and does not lose at 10k, or
   when you can show why the approach can't, with what you tried.

## Deliverable

`research/oscillation-2026-11-04/<stream>-fix.md`: plan, what changed and why (models unified or corrected, callers
affected), the auditor's findings and your responses, episode before/after, detector before/after, A/B results with
fuel, and open issues. Your final message: branch, final commit, A/B result, fuel change and what remains.
