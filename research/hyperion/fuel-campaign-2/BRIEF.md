# Fuel campaign 2 (2026-10-31): shared brief for worker agents

Goal: cut astraeus's fuel where it hurts. Priority: out-of-fuel (OOF) turns, then the tail (100M turns over 100k,
p99, max, large maps, rounds 1-2), then shortcut firings (`note_shortcut`), then mean and p90. Worst case beats
average: a change that lowers OOF or the tail and raises the mean a little is welcome. Campaign target: OOF turns
-50% against the frozen baseline.

Paths: MAIN = `/home/ubuntu/cambc-autumn` (the primary checkout; don't edit or commit there). The integration branch is
`fuel-orch` (worktree `MAIN/.claude/worktrees/fuel-orch`). You work in your own worktree on your own branch, made from
`fuel-orch`'s tip: if your worktree started elsewhere, `git checkout -b <your-branch> fuel-orch` first. Read MAIN's
`AGENTS.md` and `cambc-rules.yaml` first (the rules override `docs/`).

## Read before designing anything (what already won or lost)

- `research/hyperion/FUEL-GATES.md`: the gates, why they are the fight turns' brakes, and what removing each did.
- `research/hyperion/FUEL-AUDIT.md`: every gate's fallback logic, risks and proposed fixes (2026-10-31).
- `research/hyperion/fuel-campaign/OPEN-ITEMS.md` (the first campaign, 2026-10-29): profiles, open leads with
  estimates, and every dropped attempt with numbers. Read the sections for your area: most obvious ideas were tried.
- `research/EXPERIMENTS.md` `## Fuel` (line ~2498 to the end): every exact cut tried. Don't redo a "lost / no gain /
  dropped" item unless your idea is concretely different; say why it differs.
- `research/hyperion/TODO.md`'s first section (two-turn loops from fuel cuts) and `DANGER-MODELS.md`.
- `tools/README.md` "Fuel": bench.py, oof.py, oof_bot.py, the census, simprof, host-call prices.
- `research/hyperion/fuel-campaign-2/NOTES.md` (in the fuel-orch worktree): this campaign's findings so far.

The macro overhaul (CHANGES 235-241), the emblem/draft labs (231-234) and the map-fuzzer fixes (242-246) landed after
the first campaign, so profiles from it may have moved: measure before you trust an old number.

## Baselines (frozen bot `MAIN/bots/variants/astraeus-fb0` = astraeus at f33d8e63)

In `MAIN/replays/fuel/orch2/`:
- `base-wide-100M.json`, `base-wide-real.json`: `--set wide --test-draft` (52 games vs hecate).
- `base-oof-100M.json`, `base-oof-real.json`: the OOF set (maps in `MAIN/replays/fuel/orch2/oofset.txt`, the maps
  heaviest in OOF turns in a real-budget mirror A/B of fb0), own drafts, `--opp MAIN/bots/variants/astraeus-fb0`.
- The mirror A/B batches: `MAIN/replays/batch-20261031-054814-ab-orch2-fb0-mirror-*` (real budget, ~1100 games):
  replays for the census or `py tools/fuel/oof_bot.py`.

Baseline numbers: wide 100M mean 47800, p90 85764, p99 98887, max 296169, over 100k 2308; wide real OOF 605,
shortcuts farm-partial-evaluation 3450, step-guard-entry 2694, comms-stale-vision 1235, prey-cut-short 1155,
turn-order 828, crow-flies-farm 291, farm-no-route 192, static-descend 191, step-guard-look 168, ward-* 233.
OOF set (48 games): 100M mean 52116, p90 87253, p99 122855, max 443323, over 100k 9235, round 1 mean 231954; real OOF
1547, shortcuts farm-partial-evaluation 11478, step-guard-entry 7353, comms-stale-vision 3130, turn-order 2231,
prey-cut-short 2092, farm-no-route 779, step-guard-look 770, crow-flies-farm 711, ward-* 736, static-descend 442.
Mirror A/B (1164 games, real budget): 4382 OOF turns per bot.

p90 (~86k) and much of the mean are the turn-end queue filling spare fuel to its floor by design: a cut in decision
work often shows as unchanged p90 and a mean that drops less than expected. Turns over 100k at 100M, p99, max and
real-budget OOF are the honest worst-case measures.

## Measuring

- **Worktree setup:** generated maps are not in git, so link them from MAIN: `for d in MAIN/maps/*/; do ln -sfn "$d" maps/; done`
  (remove the links before committing). `MAIN/bots/variants/astraeus-fb0` doesn't build from a worktree (its CMake
  cache): copy its `src/` into your worktree's `bots/variants/astraeus-fb0` and pass `--opp variants/astraeus-fb0`; its
  replays are identical to MAIN's baselines.
- **Bench a frozen copy, never the live `bots/astraeus`** (`cambc run` rebuilds it per game):
  `mkdir -p bots/variants/<name> && cp -r bots/astraeus/src bots/variants/<name>/` (no `.cambc/`), in your worktree.
- 100M, wide: `py tools/fuel/bench.py run variants/<name> --set wide --test-draft --per-map --jobs 52 --out <f>`, then
  `py tools/fuel/bench.py compare MAIN/replays/fuel/orch2/base-wide-100M.json <f>`.
- 100M, OOF set: `py tools/fuel/bench.py run variants/<name> --opp MAIN/bots/variants/astraeus-fb0 --maps $(cat
  MAIN/replays/fuel/orch2/oofset.txt) --per-map --jobs 52 --out <f>` and compare with `base-oof-100M.json`. Map paths
  in oofset.txt are relative to a repo root; run from your worktree root, which has the same maps.
- Real budget: the same commands with `--fuel 0`, compared by OOF and SHORTCUT counts against the `*-real.json`.
  Small samples (52-60 games), so indicative: the merge agent runs the full A/B.
- The machine is shared (96 cores, other agents running): benches and A/Bs take CPU slots from one machine-wide pool,
  so pass the large `--jobs` above and let the pool divide the cores. Run long jobs in the background.
- **Required for a merge:** 100M replays byte-identical on the wide set AND the OOF set. If your change only fires for
  some champion, map shape or situation, also bench a set where it fires (`--maps ...`, a `--test-draft` run, or a
  copy with a forced `draft_preference`) and show identical replays there; say which.
- Exactness also needs the turns that got DEARER checked (bench compare prints "cheaper N, dearer M"): an exact cut
  that moves cost onto fight turns can raise real-budget OOF (CHANGES 222).
- Profiling: the census (`tools/fuel/census/`, real budget, per-component fuel and the stack where fuel ran out;
  `instrument.py` fails loudly when the bot's code moved, so update its patterns), `debug_fuel`/`FuelMeter`
  (util.h, ~170 a meter), raw `fuel()` differences (~15), `tools/fuel/simprof`, and the fuel-exact replay harness
  (`tools/replay/harness/README.md`). Debug output goes in `debug_block({...})`; build without `--release` to see it.

- **Current reference** (from round 2): the merged bot `MAIN/bots/variants/astraeus-orch2-m2`, results
  `MAIN/replays/fuel/orch2/m2-{wide,oof,mg}-100M.json` and `m2-{wide,oof}-real.json` (identical to fb0 at 100M, so
  either baseline works for identity; use m2 for deltas). Many-group set: the 12 maps in NOTES' "Merge round 2".
- The census has a `--trace` mode (round 2): every fuel check and read before a run-out, with `trace.py` grouping
  run-outs by the last check passed; `tools/fuel/stats.py` puts bench JSONs side by side.
- **Scratchpad:** the session scratchpad is shared by every agent: use only your own subdirectory
  (`/tmp/claude-1000/-home-ubuntu-cambc-autumn/7668d749-a298-4408-baa9-b305a346e4df/scratchpad/<your-area>/`).

## Rules of the work

- **Byte-identical at 100M**, or an unambiguous bug fix (no new behaviour, no tradeoff). A non-identical change must be
  argued in your report with the diverging games traced.
- **No new fuel gates** (code that reads fuel and chooses worse). **Removing existing gates is a goal**: a gate goes once
  the work it guards is cheap, or bounded by a fixed limit set from measurements that almost never binds (FUEL-GATES
  rule 2) with a deterministic fallback. A gate removal changes real-budget play by design: show its real-budget OOF
  and shortcut counts (wide + OOF set, both no worse) and say so; the merge agent A/Bs it. Past removals multiplied OOF
  turns 4-5x because the work they guard was too dear, so make the work cheap first.
- **Stay on big wins**: changes worth >= ~1k fuel on heavy turns, >= 0.3% total, or a visible drop in turns over 100k or
  OOF turns. Put smaller ideas in your report under "Open minor items" (one line each, with an estimate).
- Think beyond micro-optimisation:
  - Is the work needed at all? Results that are never read, cases the rules make impossible (cambc-rules.yaml: e.g.
    camps never move, enemies never enter our spawn, Marcella is immune to stuns, a bush cannot be seen from outside),
    work repeated across consumers that could share one precomputation.
  - A closed form or bound instead of a simulation; an exact early exit; an iteration order that lets a loop stop
    sooner; incremental updates instead of rebuilding.
  - Moving per-tile loops into flat-price host calls (bitboard, field, shadow-cast); moving work out of the hot turn
    into the end-of-turn queue or into the 200k first turn, so long as no decision changes.
  - Fixed per-call cost budgets that don't read fuel (bounded work, not a gate) where a count cap is the wrong unit.
- Engine behaviour `cambc-rules.yaml` doesn't settle: you may spawn ONE short probe subagent (`tools/probes/README.md`)
  for a narrow question. It settles only that question, updates `cambc-rules.yaml` and the probes README table, and
  commits those on your branch.
- Comment only counterintuitive behaviour, concisely; match the surrounding code's style. `farm_turn` is flattened
  (`[[gnu::flatten]]`): changes there shift codegen across every turn, so bench the whole set.
- Commit on your branch (one idea per commit), never push, never merge into fuel-orch or main. Don't edit
  `bots/baselines/` or `bots/hyperion`. Don't edit CHANGES.md or EXPERIMENTS.md (the merge agent does); do append your
  findings, dropped attempts with numbers and open leads to `research/hyperion/fuel-campaign-2/NOTES.md` on your branch
  under a `## <your area>` heading.

## Report (your final message)

Branch name and commit shas; for each change: what, why it's exact (or, for a gate removal, why the guarded work is
now bounded), measured deltas (100M wide + OOF set: identical counts, mean, p99, max, over 100k, round 1; real-budget
OOF and shortcuts against `*-real.json`); what you tried and dropped, with numbers; open minor items.
