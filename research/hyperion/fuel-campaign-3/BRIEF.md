# Fuel campaign 3 (2026-11-01): shared brief for worker agents

Goal: cut astraeus's fuel where it hurts, measured by out-of-fuel (OOF) turns, shortcut firings (`note_shortcut`),
p90 and mean fuel a turn. **Worst case first**: OOF turns, turns over 100k at 100M, p99/max, round 1, large maps.
A change that lowers those and raises the mean a little is welcome. Campaign target: OOF turns -50% against the
frozen baseline `astraeus-fc3b` in a 10k-game real-budget A/B.

Paths: MAIN = `/home/ubuntu/cambc-autumn` (primary checkout: never edit or commit there). The integration branch is
`fuel3-orch` (worktree `MAIN/.claude/worktrees/fuel3`). Work in your own worktree on your own branch made from
`fuel3-orch`'s tip (`git checkout -b fc3-<area> fuel3-orch` if your worktree started elsewhere). Read MAIN's
`AGENTS.md` and `cambc-rules.yaml` first (the rules override `docs/`).

## Read before designing anything (what already won or lost)

Two campaigns ran before this one; most obvious ideas were tried. Read the parts for your area, and don't redo a
"dropped / lost / no gain" item unless your idea is concretely different (say how).
- `research/hyperion/FUEL-GATES.md`: the gates, why they are the fight turns' brakes, what removing each did.
- `research/hyperion/FUEL-AUDIT.md`: every gate's fallback logic, risks and proposed fixes.
- `research/hyperion/fuel-campaign-2/NOTES.md`: campaign 2 (2026-10-31), profiles, kept and dropped attempts, open
  leads per area, and the two "quill" sections (crew economics, CHANGES 256/260/262) at the end.
- `research/hyperion/fuel-campaign/OPEN-ITEMS.md`: campaign 1.
- `research/EXPERIMENTS.md` `## Fuel` (line ~2629 to the end).
- `research/hyperion/TODO.md` (open fuel items: crew economics' fuel, double route search, two-turn loops).
- `tools/README.md` "Fuel": bench.py, oof.py, oof_bot.py, the census (`--trace`), simprof, stats.py, host-call prices.
- This campaign's `research/hyperion/fuel-campaign-3/NOTES.md` on `fuel3-orch`: findings so far.

Since campaign 2, crew economics (quill, CHANGES 256) and its bounds (260, 262), drafts (261) and middle-band pricing
(264) landed: old profiles may have moved. Measure before you trust an old number.

## Baseline: `astraeus-fc3b` = main 4a7c25f6

Frozen copy `MAIN/bots/variants/astraeus-fc3b`. Bench JSONs and logs in `MAIN/replays/fuel/fc3/`:
`base-{wide,oof,mg,q,big}-{100M,real}.json`. Sets (map lists in the same directory):
- **wide**: `--set wide --test-draft` (52 games vs hecate; test drafts, so HoR, Ren, Stellar, Ryth often).
- **oof** (`oofset.txt`, 24 maps, 48 games): fb0's heaviest OOF maps. **mg** (`mgset.txt`, 12 maps): many-group.
  **q** (`qset.txt`, 24 maps): quill's heaviest OOF maps (topology, close/far spawns, dungeon). **big**
  (`bigset.txt`, 16 maps): the largest generated maps (90-100 a side). These four: own drafts, `--opp` the baseline.

| set | 100M mean | p90 | p99 | max | over 100k | round 1 mean / max | real OOF | real shortcuts (top) |
|---|---|---|---|---|---|---|---|---|
| wide | 54055 | 86904 | 116496 | 320361 | 5694 (2.3%) | 255471 / 531617 | 595 | fpe 14657, sge 2642, comms 2012, turn-order 1263 |
| oof | 56519 | 90348 | 193140 | 594115 | 20818 (7.7%) | 333174 / 887490 | 894 | fpe 20466, sge 5223, comms 3060, turn-order 2648 |
| mg | 61719 | 95340 | 175378 | 401771 | 9415 (8.9%) | 329263 / 625380 | 386 | fpe 7888, comms 1368, turn-order 1296, sge 1262 |
| q | 69654 | 113316 | 227093 | 517013 | 43157 (15%) | 319115 / 722721 | 2678 | fpe 70312, turn-order 11199, comms 7203, static-descend 4972 |
| big | 60334 | 88007 | 131958 | 290573 | 6866 (4.5%) | 294034 / 451383 | 151 | fpe 20116, comms 1055, turn-order 898, farm-no-route 766 |

(fpe = farm-partial-evaluation, sge = step-guard-entry.) Note round 1: at 100M its mean is 255-333k against a 200k
first-turn budget, so at the real budget round 1 is cut by gates (fpe) or runs out on most maps. farm-kept-target
fires 165 times on the q set even at 100M (a no-approach fallback, not fuel).

A 10k-game real-budget mirror A/B of the baseline (suites `maps/fresh-11000..11019`, made for this campaign) is in
`MAIN/replays/ab/fc3-mirror/` (log `MAIN/replays/fuel/fc3/ab-mirror.log`); its batches are `MAIN/replays/batch-*`
named in the per-suite logs, for `oof_bot.py` / the census. The merge agent judges OOF on these suites.

## Measuring

- **Worktree setup:** generated maps are not in git: `for d in MAIN/maps/*/; do ln -sfn "$d" maps/; done` (two
  directories already exist and warn; fine). Never commit the links. Copy the baseline into your worktree (a bot built
  in MAIN won't build from a worktree): `mkdir -p bots/variants/astraeus-fc3b && cp -r MAIN/bots/variants/astraeus-fc3b/src bots/variants/astraeus-fc3b/`.
- **Bench a frozen copy, never the live `bots/astraeus`:** `mkdir -p bots/variants/<name> && cp -r bots/astraeus/src bots/variants/<name>/`.
  Build it once (`cambc build bots/variants/<name>`) before starting several benches of it in parallel: concurrent
  first builds of one directory collide in CMake. The same goes for the `bench-td-*` copy `--test-draft` makes.
- 100M: `py tools/fuel/bench.py run variants/<name> --set wide --test-draft --per-map --jobs 94 --out <f>`; other sets
  `py tools/fuel/bench.py run variants/<name> --opp variants/astraeus-fc3b --maps $(cat MAIN/replays/fuel/fc3/<set>.txt) --per-map --jobs 94 --out <f>`
  (run from your worktree root). Compare: `py tools/fuel/bench.py compare MAIN/replays/fuel/fc3/base-<set>-100M.json <f>`.
- Real budget: add `--fuel 0`; compare OOF and SHORTCUT counts with `base-<set>-real.json`. 24-52 games swing by
  +-40-70 OOF a game once games diverge: indicative only; the merge agent runs the 10k A/B.
- The machine is shared (96 cores; other agents run batches): bench.py and ab.py share one machine-wide CPU-slot pool,
  so pass `--jobs 94` and let the pool divide the cores. Run anything long in tmux, not as a background task.
- **Required for a merge:** 100M replays byte-identical on all five sets (wide, oof, mg, q, big). If your change fires
  only for some champion, map shape or situation, also bench a set where it fires (`--maps ...`, `--test-draft`, or a
  copy with a forced `draft_preference`) and show identical replays there; name it in your report.
- Check the turns that got DEARER (compare prints "cheaper N, dearer M"): an exact cut that moves cost onto fight or
  round-1 turns can raise real-budget OOF.
- Profiling: the census (`tools/fuel/census/`, real budget, per-component fuel and the stack where fuel ran out;
  `--trace` records every fuel check before a run-out; `instrument.py` fails loudly when code moved, so update its
  patterns), `debug_fuel`/`FuelMeter` (util.h, ~170 a meter), raw `fuel()` differences (~15) inside `debug_block`,
  `tools/fuel/simprof`, the fuel-exact replay harness (`tools/replay/harness/README.md`). Build without `--release` to
  see debug output; work inside `debug_block` is not charged.
- Scratch files: `/tmp/fc3/<your-area>/` only.

## Rules of the work

- **Byte-identical at 100M**, or an unambiguous bug fix (no new behaviour, no tradeoff) argued with the diverging
  games traced.
- **No new fuel gates** (code that reads fuel and chooses worse). **Removing existing gates is a goal** (FUEL-GATES
  "Remaining gates"): a gate goes once the work it guards is cheap, or bounded by a fixed measured limit that almost
  never binds (FUEL-GATES rule 2) with a deterministic fallback. A removal changes real-budget play: show its
  real-budget OOF and shortcut counts on all five sets. Past removals multiplied OOF turns 4-5x because the guarded
  work was too dear, and a removal that looked level on the small benches raised rounds 1-10 OOF in the A/B (NOTES
  merge round 4): make the work cheap first.
- **Stay on big wins**: >= ~1k fuel on heavy turns, >= 0.3% total on a set, or a visible drop in turns over 100k, p99,
  round 1 or OOF. List smaller ideas as "Open minor items" (one line each, with an estimate).
- **Think beyond micro-optimisation.** Fuel is ~1 per WASM instruction, so the big wins are work not done:
  - Is the work needed at all? Results never read (or read only by debug traces); cases the rules make impossible
    (cambc-rules.yaml: camps never move or regenerate, enemies never enter our spawn, Marcella is immune to stuns, a
    bush tile can't be seen from outside, a dead camp group stays empty until captured, respawns take 40+ rounds,
    shopping needs the spawn, ...). Find the code paths that handle an impossible case and drop them.
  - Work repeated across consumers or across turns that one precomputation could serve (per map, per instance,
    per belief version), kept exact by keying on everything it reads.
  - A closed form or a bound instead of a simulation; an exact early exit; an iteration order that lets a loop stop
    sooner (best candidate first so a bound prunes the rest); incremental updates instead of rebuilding.
  - Per-tile loops moved into flat-price host calls (bitboard, field, shadow-cast); vectorised flat arrays (campaign 2
    won with SIMD lanes in find_members and stand_reach); fewer allocations (~420 each).
  - Moving work off the hot turn into the end-of-turn queue or the 200k first turn, as long as no decision changes;
    the draft bot has 10M fuel and 1024 shared bytes it could precompute into (`memory.draft`).
  - Fixed per-call work budgets that don't read fuel (bounded work, not a gate) where a count cap is the wrong unit.
  - Code that runs twice in a turn for the same answer (route searches after a failed one, re-sorts, rebuilt tables).
- Engine behaviour that `cambc-rules.yaml` doesn't settle: spawn ONE short probe subagent (`tools/probes/README.md`)
  per narrow question. It settles only that question, updates `cambc-rules.yaml` and the probes README table, and
  commits those on your branch. Don't probe what the YAML already says.
- Comment only counterintuitive behaviour, concisely; match the surrounding code's style. `farm_turn` is flattened
  (`[[gnu::flatten]]`): changes there shift codegen across every turn, so bench every set.
- Commit on your branch (one idea per commit), never push, never merge into fuel3-orch or main. Don't edit
  `bots/baselines/`, `bots/archives/hyperion` or `bots/hecate`. Don't edit CHANGES.md or EXPERIMENTS.md (the merge agent does).
  Append findings, dropped attempts with numbers and open leads to `research/hyperion/fuel-campaign-3/NOTES.md` on
  your branch under a `## <your area>` heading.

## Report (your final message)

Branch name and commit shas; for each change: what, why it's exact (or, for a gate removal, why the guarded work is
now bounded), measured deltas against the baseline JSONs (100M on all five sets: identical counts, total, mean, p90,
p99, max, over 100k, round 1; real budget: OOF and shortcuts); sets where the change fires; what you tried and
dropped, with numbers; open minor items.
