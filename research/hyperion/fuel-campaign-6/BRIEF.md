# Fuel campaign 6 (2026-11-04): shared brief for worker agents

Goal: undo the fuel cost of CHANGES 337 (d6e74b6f, the oscillation fixes) without changing its play. Target:
**out-of-fuel (OOF) turns -50% against d6e74b6f at scale.** Metrics, worst case first: OOF turns, p90 fuel a turn,
turns over 100k, large-map fuel, round 1 and 2 (the 200k first turn and the warm-up), shortcut firings
(`note_shortcut`), then mean fuel a turn. A change that lowers the worst case and raises the mean a little is welcome.

Paths: MAIN = `/home/ubuntu/cambc-autumn` (primary checkout, branch `main`; other sessions use it: never edit,
build or commit there). Make your own worktree and branch from main's tip:
`git -C MAIN worktree add MAIN/.claude/worktrees/fc6-<area> -b fc6-<area> main`, then link the generated maps:
`for d in MAIN/maps/*/; do ln -sfn "$d" maps/; done` (never commit the links). Read MAIN's `AGENTS.md` and
`cambc-rules.yaml` first (the rules override `docs/`). Shell: `source /home/ubuntu/venv/bin/activate`; for games
`export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86 CAMBC_BIN=MAIN/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native`.

## What d6e74b6f cost (20,480 games against its parent 088bf3f4, fresh-88001..88040, own drafts)

| | d6e74b6f | 088bf3f4 |
|---|---|---|
| OOF turns | 458,674 | 111,324 |
| fuel a play turn mean / p50 / p90 / p99 | 52,793 / 52,150 / 86,750 / 96,550 | 49,911 / 48,250 / 86,250 / 92,950 |
| turns at/over 100k | 0.56% | 0.22% |
| shortcuts (without OOF) | 7.78M | 5.47M |
| farm-partial-evaluation / step-guard-entry / turn-order | 4.68M / 1.18M / 741k | 3.53M / 935k / 233k |
| prey-cut-short / comms-stale-vision / static-descend / farm-no-route | 299k / 284k / 138k / 146k | 236k / 105k / 40k / 85k |

OOF without shared-gem maps (`tools/fuel/census/batch_oof.py`), d6e74b6f vs 088bf3f4:
- by round: **1: 33,248 vs 9,715** (all farm branch), 2-10: 29,849 vs 12,655, 11-60: 40,741 vs 16,069,
  61-300: 104,775 vs 22,972, **300+: 235,949 vs 47,481**;
- **by game: games with 50+ OOF turns hold 230,077 vs 22,442** (runaways: the same heavy work repeated turn after
  turn in a standoff), 10-49: 175,825 vs 55,101;
- phase: decide 70%, queue (the turn-end queue) 30%; 81% of first-in-streak OOF turns end before the turn's branch
  line (`?`): inside the fight/safety/goal work;
- worst maps (first-in-streak): gen-fortress-8800602214 1033, gen-classic-8804000019 947, mut-the-pack-8802001811
  898, gen-topo-necks-8803507009 720, gen-continent-8804002803 618, gen-huge-shared-8801705217 605,
  gen-topo-gatehouse-8800607302 603, then many gen-arena (all in `maps/fresh-880xx/`). The `osc` bench set is these
  24 maps.
- The 20k replays (d6e74b6f is bot 1, debug build with `SHORTCUT`/`OOF` lines): `MAIN/replays/batch-20261104-051316-ab-osc-int-20k-osc-fix-20k/`.

Census of the baseline (instrumented copy `bots/variants/astraeus-d6e-cen`, 50 games on `tools/fuel/census/maps.txt`
at the real budget): `MAIN/replays/fuel/fc6/cen-base.txt` (tables) and `cen-base/` (games). Headlines on OOF-first
turns: `goal` in 83% (mean 58k inclusive), `s.lethal` 93% (7k), `channels` 85% (17k), `world`/`update` 100% (14k),
`strike_search` 47% (20k), `s.fight_of` 49% (11k), `farm.post` 42% (27k), `farm.loop` 43% (18k), `chase` 68% (12k),
`carry_bag` 10% (54k), `retreat` 3% (38k). Innermost scope at the OOF: farm.post 20%, goal 19%, s.fight_of 14%,
act_end 13%.

Where CHANGES 337's new costs are (each stream's notes in `research/oscillation-2026-11-04/*-fix.md` have a fuel
section; CHANGES.md 337 summarises):
- stream 2: `leaves_at` / the stand (`stand_lost_at`, `Safety::stand_roster`, `stand_trade`) at vetoed work-step
  landings (`work_veto`, `Pathing::set_veto`, combat/guard.cc, combat/fight.cc, model/safety.cc): ~16k each, ~1.2 a
  turn on 45% of heavy turns. Alone it tripled OOF (66k -> 208k in 10k games).
- stream 1: terrain-aware reach (`model/enemy_reach.{h,cc}`, `Safety::approach/walk_in/may_reach_within`).
- stream 3: farm prices groups by the walk's search records (economy/farm.cc, model/pathing.cc approach records,
  `labels_hold`).
- stream 4: the kite plan and siege stand checks (economy/siege.cc).

## Read before designing (what already won or lost)

Five fuel campaigns ran before this one; most obvious ideas were tried. Read the parts for your area; don't redo a
dropped / lost item unless your idea is concretely different (say how).
- `research/hyperion/fuel-campaign-5/NOTES.md` and `fuel-campaign-4/NOTES.md` (summaries first, then your area),
  `research/hyperion/FUEL-GATES.md`, `research/hyperion/FUEL-AUDIT.md`, `research/hyperion/TODO.md` `## Fuel`,
  `research/EXPERIMENTS.md` `## Fuel` and the campaign 4/5 entries near its end, `research/oscillation-2026-11-04/`.
- `tools/README.md` "Fuel": bench.py, stats.py, oof.py, oof_bot.py, the census (`tools/fuel/census/`;
  `instrument.py --fine --lenient`: one bot.cc pattern lags the code), `--trace`, simprof, host-call prices.

## Benches (opponent: the frozen baseline `bots/variants/astraeus-d6e74b6` = d6e74b6f)

- Copy the baseline into your worktree: `cp -r MAIN/bots/variants/astraeus-d6e74b6 bots/variants/` (skip `.cambc/`).
- Baselines: `MAIN/replays/fuel/fc6/base-<set>-{100M,real}.json`, headline stats in `base-stats.txt`. Sets (map lists
  `<set>set.txt` there): **wide** (`--set wide --test-draft`, 52 games vs hyperion, test drafts: Heart of Ruin, Ren,
  Stellar, Ryth, Vendetta...), and own drafts against the baseline: **oof** (24 maps), **mg** (many groups, 12),
  **q** (topology, close/far spawns, 24), **big** (90-100 a side, 16), **fs** (fuel-stress 100x100, 12),
  **fight** (arenas, 15), **tgt** (camp-heavy, 8), **osc** (the 24 worst maps above).
- `MAIN/replays/fuel/fc6/bench.sh TAG BOTNAME [SETS]` (run from your worktree root, BOTNAME under `bots/variants/`)
  runs them for a frozen bot and writes `MAIN/replays/fuel/fc6/TAG-<set>-{100M,real}.json`; use a TAG with your area
  in it. Compare: `py tools/fuel/bench.py compare BASE CAND` (identical replays; "cheaper N, dearer M") and
  `py tools/fuel/stats.py BASE CAND`.
- **Bench a frozen copy, never the live bot:** `./copybot astraeus variants/<name>` (from your worktree), build it
  once (`cambc build bots/variants/<name>`) before starting several benches of it.
- **Fuel-only changes are byte-identical at 100M** on every set, plus any set where the change fires (a champion,
  map shape or situation the standard sets miss: build one with `--maps`, `--test-draft`, or a forced draft; name it
  in your report). Check the turns that got DEARER.
- Real budget (`--fuel 0`) small benches swing by hundreds of OOF once games diverge: indicative only. The judge of
  OOF is a 10k-game A/B: `MAIN/replays/fuel/fc6/ab.sh NAME variants/<cand> variants/astraeus-d6e74b6 SUITES` with
  SUITES = `maps/fresh-66101,...,maps/fresh-66120` (comma list; 10,240 games, ~15 min when the box is free). Those
  suites are reserved for this campaign's worker A/Bs; `fresh-66201..66220` for merges, `fresh-66001..66040` for the
  final run. Per-turn fuel: `py MAIN/replays/fuel/fc6/fuelstats.py <batch dir>`; shortcuts:
  `py MAIN/replays/fuel/fc6/shortcuts.py <batch dir>`; OOF by round/phase/branch/map:
  `py tools/fuel/census/batch_oof.py --bot 1 <batch dir>`. Compare OOF with the reference side of the same run.
- The box is shared (96 cores, 86 slots; another worker runs beside you). bench.py and ab.py share one CPU-slot
  pool. **One batch at a time per worker**, long runs in tmux (session `fc6-<area>-...`), waited on in the
  background (a `run_in_background` until-loop), never a foreground sleep. Scratch: `/tmp/fc6/<area>/`.

## Rules of the work

- **Gameplay must stay as d6e74b6f plays.** Its fixes cut ~22% of wasted champion turns (`tools/replay/osc_detect.py`).
  Fuel-only changes (byte-identical at 100M) keep that automatically: prefer them. A change that is not fuel-only
  (an approximation, a different model) needs a 10k-game A/B level or better on win rate, lower OOF, and an
  argument that it keeps the fixes' intent (name which fix and why it still holds).
- **No new fuel gates** (code that reads `fuel()` and chooses worse). Removing gates is welcome once the work is cheap.
- **Cases the rules make impossible** cost fuel for nothing (camps never move or regenerate, enemies never enter our
  spawn, Marcella is immune to stuns, a bush tile can't be seen from outside, a dead group stays empty until captured,
  respawns take 40+ rounds, ...). Dropping them is exact by the rules; cite the rule.
- **Think beyond micro-optimisation.** Fuel is ~1 per WASM instruction, so the big wins are work not done: results
  never read; work repeated across consumers or turns that one precomputation could serve (keyed exactly on what it
  reads); closed forms or bounds instead of simulation; exact early exits and cheap sufficient tests before an
  expensive one; an order that lets a bound prune (best first); incremental updates instead of rebuilds; per-tile
  loops moved into flat-price host calls (bitboard, field, shadow-cast); fewer allocations; moving work into the
  end-of-turn queue or the 200k first turn when no decision changes; the draft bot's 10M fuel and `memory.draft`;
  a failing search or a vetoed step repeated every turn of a standoff (the runaway games). Bridge files: a value
  computed in one place may already exist elsewhere this turn.
- **Engine behaviour `cambc-rules.yaml` doesn't settle:** spawn ONE short probe subagent per narrow question
  (`tools/probes/README.md`); it settles only that, updates `cambc-rules.yaml` and the probes README table, and
  commits those on your branch. If the engine contradicts the YAML, say so in your report.
- Stay on big wins (>= ~1k on heavy turns, a visible drop in OOF, turns over 100k, p90/p99, round 1). List smaller
  ideas as one-line open items.
- Comment only counterintuitive behaviour, concisely; match the surrounding style. `farm_turn` is flattened: changes
  there shift codegen across every turn, so bench every set.
- Commit on your branch (one idea per commit, messages ending `Co-Authored-By: Claude Opus 5.5
  <noreply@anthropic.com>`); never push, never touch `main`. Don't edit `bots/baselines/`, `bots/hyperion`,
  `bots/archives/demeter`, CHANGES.md or EXPERIMENTS.md (the merge agent does). Append findings, dropped attempts with numbers
  and open leads to `research/hyperion/fuel-campaign-6/NOTES.md` on your branch under `## <your area>`.

## Report (your final message)

Branch, worktree and commit shas; for each change: what, why it's exact (or why the new behaviour keeps the fixes'
intent), measured deltas against the baseline JSONs (100M on all sets: identical counts, total, mean, p90, p99, max,
over 100k, round 1; real budget: OOF and shortcuts), the 10k A/B (win %, OOF cand/ref, fuel stats) if run; sets where
the change fires; what you tried and dropped, with numbers; open items.
