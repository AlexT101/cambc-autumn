# Fuel campaign: shared brief for worker agents (2026-10-29)

Goal: cut astraeus's fuel where it hurts. In order of priority: out-of-fuel (OOF) turns, p90 and the tail (turns
over 100k), shortcut firings (`note_shortcut`), large maps, rounds 1-2, then mean fuel. Target for the whole campaign: OOF
turns -50%.

Main repo: `C:/Users/alext/Github/cambc-autumn` (call it MAIN). You work in your own git worktree, a branch made
from main. Read MAIN's `AGENTS.md` and `cambc-rules.yaml` first (the rules override `docs/`).

## Read before designing anything (what already won or lost)

- `research/hyperion/FUEL-GATES.md`: the gate list and why gates are the fight turns' brakes.
- `research/EXPERIMENTS.md`, section `## Fuel` (line ~2107 to end): every exact cut tried, with results. Don't redo a
  "lost / no gain / dropped" item unless you have a concretely different idea, and say why it differs.
- `research/hyperion/TODO.md` items 1-4 and 10; `research/hyperion/DANGER-MODELS.md` for who computes danger.
- `tools/README.md` "Fuel" section: bench.py, oof.py, host-call prices.

## Where the OOF turns are (baseline A/B, HEAD 8ec2c4d, real budget, 1676 games, 17282 OOF turns)

Almost all inside `decide`. Two shared-gem maps hold over half of them: `maps/fresh-82801/gen-shared-gems-8280101604`
(4515 in 2 games) and `maps/fresh-82802/gen-shared-gems-8280201605` (4294), plus `-8280201600` (574). In those games one or two
champions run out on every other turn for ~1200 rounds: a resumed turn finishes, then the next fresh turn runs out
again (e.g. `replays/batch-20261029-010417-ab-parts23v-fresh-82801/393-gen-shared-gems-8280101604-12.repl26a`,
team b, champion 6: `SRCH ... read 15265 grow 6905 price 28662` with only 6 tiles priced, then OOF). Other top maps:
gen-huge-shared-8280205201, gen-arena-8280202604/-8280302619, gen-blob-8280303700, mut-concentrated-wealth-8280301849,
01concentrated-wealth, 01yellow-brick-road, 00road-of-riches, 01elk-arena, adgato-gemcombat5. Read replays' stdout
with `zipfile` (`team-a.stdout`/`team-b.stdout`, strip NULs): `OOF round phase`, `SHORTCUT round champ what`,
`SRCH ...` lines. `py tools/fuel/oof.py <batch dirs>` summarises a batch.

## Measuring (baselines are ready in MAIN/replays/fuel/orch/, made from frozen HEAD `bots/variants/astraeus-8ec2c4d`)

- `base-wide-100M.json`, `base-wide-real.json`: `--set wide --test-draft` (52 games vs hecate).
- `base-oof-100M.json`, `base-oof-real.json`: the OOF set (maps listed in `MAIN/replays/fuel/orch/oofset.txt`), own
  drafts, `--opp <MAIN>/bots/variants/astraeus-8ec2c4d`.
- If a file isn't there yet, the baseline is still running: wait for it (it appears within ~30 min of your start)
  and do your reading/profiling meanwhile.
- Your candidate: `py tools/fuel/bench.py run <your worktree>/bots/astraeus --set wide --test-draft --per-map --jobs 7 --out <file>`
  then `py tools/fuel/bench.py compare <MAIN>/replays/fuel/orch/base-wide-100M.json <file>`. Same for the OOF set:
  `--opp C:/Users/alext/Github/cambc-autumn/bots/variants/astraeus-8ec2c4d --maps $(cat <MAIN>/replays/fuel/orch/oofset.txt)`
  (map paths are relative to the repo root; run from your worktree root, which has the same maps).
- OOF set maps, inline (some shells can't expand `$(cat ...)`): `--maps maps/fresh-82801/gen-shared-gems-8280101604.map26a maps/fresh-82802/gen-shared-gems-8280201605.map26a maps/fresh-82802/gen-shared-gems-8280201600.map26a maps/fresh-82802/gen-huge-shared-8280205201.map26a maps/fresh-82802/gen-arena-8280202604.map26a maps/fresh-82803/gen-blob-8280303700.map26a maps/fresh-82803/mut-concentrated-wealth-8280301849.map26a maps/fresh-82803/gen-arena-8280302619.map26a 01concentrated-wealth 01yellow-brick-road 00road-of-riches 01elk-arena adgato-gemcombat5 maps/fresh-82801/gen-serpentine-8280104501.map26a maps/fresh-82801/gen-golem-heavy-8280105000.map26a maps/fresh-82801/mut-corners-8280101814.map26a`
- Use `--jobs 7` (three agents share 22 cores). Fuel numbers are deterministic, so contention costs only time.
- **Required:** 100M replays byte-identical on the wide set AND the OOF set. If your change only triggers for some
  champion/map, also bench a set where it triggers (`--maps ...`, a `--test-draft` run, or a copy with a forced
  draft) and show identical replays there.
- Report the 100M deltas (mean, p90, p99, turns over 100k, round 1, rounds 2-10) and the real-budget run of the OOF
  set (OOF turns and SHORTCUT counts against `base-oof-real.json`; it's a small sample, so treat it as indicative).
- Profiling: `debug_fuel`/`FuelMeter` in util.h (~170 a meter, inflates inner loops), raw `fuel()` differences (~15),
  or the fuel-exact replay harness (`tools/replay/harness/README.md`). Debug output goes in `debug_block({...})`.

## Rules of the game for this work

- Byte-identical at 100M, or an **unambiguous** bug fix (no new behaviour, no tradeoff). A non-identical change must
  be argued in your report, with the diverging games traced.
- **No new fuel gates** (code that reads fuel and chooses worse). Removing an existing gate is welcome, but only once
  the work it guards is cheap or bounded by a limit that almost never binds; past removals multiplied OOF turns 4-5x.
- **Stay on big wins.** Spend your time on changes worth >= ~1k fuel on heavy turns, >= 0.3% total, or a visible drop
  in turns over 100k or OOF turns. Don't polish a working change for tens of fuel. Put smaller ideas in your report
  under "Open minor items" (one line each, with an estimate) and move on.
- Time box: ~2 hours. Stop when the time is up and report, even if some ideas are still untried.
- Think beyond micro-optimisation: is the work needed at all (impossible by the rules, result unused, already
  known)? Can several consumers share one precomputation? Is there a closed form instead of a simulation? Can a loop
  stop early exactly (a bound), or iterate in an order that lets it stop sooner? Can work move into a host call
  (flat price) or out of the hot turn into the end-of-turn queue, so long as no decision changes?
- Engine behaviour that `cambc-rules.yaml` doesn't settle: you may spawn ONE short probe subagent (see
  `tools/probes/README.md`) for a narrow question; it must update `cambc-rules.yaml` and the probes README table.
- Comment only counterintuitive behaviour, concisely; match the surrounding code style.
- Commit on your worktree branch (small commits, one idea each), no push. Don't edit `bots/baselines/` or
  `bots/hyperion`. Don't edit CHANGES.md/EXPERIMENTS.md (the merge agent does).

## Report (your final message)

Branch name and commit shas; for each change: what, why it's exact, measured deltas (100M wide + OOF set, identical
counts, real-budget OOF/shortcuts on the OOF set); what you tried and dropped (with numbers); open minor items.

## UPDATE (2026-10-29 08:50): campaign phase 2

- main is now m7 (squashed: e76e46a8, f5eff0de = late finish CHANGES 217, 09f3c1a8; plus 799d390a CPU slots). Frozen
  bot: `MAIN/bots/variants/astraeus-m7`. 100M references: `MAIN/replays/fuel/orch/m7-{wide,oof}-100M.json` (still
  byte-identical to base, so base JSONs work for identity; m7's for fuel deltas). Real budget: `m6-{wide,oof}-real.json`.
- CPU: benches and A/Bs now share one machine-wide slot pool (tools/cpu_slots.py, across worktrees). Pass the full
  `--jobs 22` / `--threads 22`; the pool divides the cores. Ignore the `--jobs 7` advice above.
- Lesson (CHANGES 222): an exact 100M cut can still RAISE real-budget OOF turns (freed fuel lets gated work run, then
  run out). Report the real-budget OOF set too (bench `--fuel 0`, or `py tools/fuel/oof_bot.py` on A/B batches).
- Tools: `tools/fuel/census/` (per-component fuel and the stack where fuel ran out, real budget; see tools/README),
  `tools/fuel/oof_bot.py`. `MAIN/replays/fuel/orch/OPEN-ITEMS.md` holds every phase-1 finding and dropped attempt:
  read the sections for your area first.
- Don't merge into main: commit on your worktree branch; the orchestrator merges.
