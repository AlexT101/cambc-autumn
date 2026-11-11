# Fuel campaign 4 (2026-11-03): shared brief for worker agents

Goal: cut astraeus's fuel where it hurts. Metrics, **worst case first**: out-of-fuel (OOF) turns (campaign target:
**-30% against the baseline** in a 10k-game real-budget A/B), p90 fuel a turn, shortcut firings (`note_shortcut`),
then mean fuel a turn. Turns over 100k at 100M, p99/max, round 1 and large maps count with the worst case. A change
that lowers those and raises the mean a little is welcome.

Paths: MAIN = `/home/ubuntu/cambc-autumn` (primary checkout: other agents use it; never edit or commit there). The
integration branch is `fuel4-orch` (worktree `MAIN/.claude/worktrees/fuel4`; only the orchestrator and merge agent
commit there). Make your own worktree and branch from its tip:
`git -C MAIN worktree add MAIN/.claude/worktrees/fc4-<area> -b fc4-<area> fuel4-orch`. Read MAIN's `AGENTS.md` and
`cambc-rules.yaml` first (the rules override `docs/`).

## Read before designing anything (what already won or lost)

Three campaigns ran before this one; most obvious ideas were tried. Read the parts for your area and don't redo a
"dropped / lost / no gain" item unless your idea is concretely different (say how).
- `research/hyperion/fuel-campaign-3/BRIEF.md` and `NOTES.md` (the latest: profiles, kept/dropped work, open leads,
  the merge rounds' review arguments for exactness). Campaign 2's NOTES and campaign 1's OPEN-ITEMS for older leads.
- `research/hyperion/FUEL-GATES.md` (each gate, what removing it did), `research/hyperion/FUEL-AUDIT.md` (each
  gate's fallback logic).
- `research/hyperion/TODO.md` `## Fuel` (items 1-10; item 1, dash travel's OOF tail from CHANGES 274, is open; item 2
  lists the fight model's rule simplifications).
- `research/EXPERIMENTS.md` `## Fuel` (line ~3581) and batches 4, 6, 7 (lines ~2611-2808: fight fuel, the bank-branch
  stalls, why trip-in-turns changes raised OOF).
- `tools/README.md` "Fuel": bench.py, oof.py, oof_bot.py, the census (`tools/fuel/census/`, `--trace`; its
  `instrument.py` may need `--lenient` or pattern updates), simprof, stats.py, host-call prices.
- This campaign's `research/hyperion/fuel-campaign-4/NOTES.md` on `fuel4-orch`: findings so far.

**Since campaign 3** (CHANGES 269-297) a lot landed: dash-aware travel in Pathing (274, TODO Fuel 1: +26-28% OOF),
fight play-out with reach (273), Willow heal value (270), Cassi and Issac pair valuation (271) and pair yield (294),
chases (289-291), cohesion (292), turn-order idling (293), kill bids (295), and **the team lock (296): on its own
drafts astraeus always picks Cassi & Issac and never Stellar**, so every own-draft game runs Cassi & Issac's code for
us (two bodies: two bot instances, two world inits in round 1). Measure before you trust an old profile.

## Baseline: `astraeus-fc4b` = main fc99b847

Frozen copy: `MAIN/.claude/worktrees/fuel4/bots/variants/astraeus-fc4b` (copy its `src/` into your worktree's
`bots/variants/astraeus-fc4b/`). Results in `MAIN/replays/fuel/fc4/` (`*-DONE` files mark finished runs):
- Bench JSONs `base-<set>-{100M,real}.json`, sets (map lists `<set>set.txt` there): **wide** (`--set wide
  --test-draft`, 52 games vs hyperion: test drafts, so Heart of Ruin, Ren, Stellar, Ryth, Vendetta etc. appear),
  and, own drafts against fc4b: **oof** (24 maps), **mg** (many groups, 12), **q** (topology / close-far spawns /
  dungeon, 24), **big** (90-100 a side, 16), **fs** (fuel-stress 100x100 ~220 groups, 12), **fight** (arenas, 15),
  **tgt** (camp-heavy: the pack, mega-groups, 8).
- `bench.sh TAG BOT [SETS]` there runs all of them for a frozen bot (from your worktree root).
- Mirror A/B, real budget, own drafts, fast runner, `maps/fresh-11000..11019` (10,240 games): `ab-fc4-mirror.log`,
  its batches `replays/batch-*-ab-fc4-mirror-*` under the fuel4 worktree. `ab.sh NAME CAND REF [SUITES]` runs one.
  Per-turn fuel stats for A/B batches: `py fuelstats.py <batch dirs>`; OOF: `py tools/fuel/oof.py` /
  `oof_bot.py`; shortcuts: `py tools/replay/debug_lines.py SHORTCUT -- <batches>`.

## Measuring

- **Worktree setup:** generated maps are not in git: `for d in MAIN/maps/*/; do ln -sfn "$d" maps/; done` (two
  exist already and warn: fine). Never commit the links.
- **Bench a frozen copy, never the live `bots/astraeus`:** `./copybot astraeus variants/<name>` (or copy `src/`).
  Build it once (`cambc build bots/variants/<name>`) before starting several benches of it: concurrent first builds
  of one directory collide in CMake (the same for the `bench-td-*` copy `--test-draft` makes).
- 100M: `py tools/fuel/bench.py run variants/<name> --opp variants/astraeus-fc4b --maps $(cat MAIN/replays/fuel/fc4/<set>set.txt) --per-map --jobs 94 --out <f>`
  (wide: `--set wide --test-draft` instead of `--opp/--maps`); compare with
  `py tools/fuel/bench.py compare MAIN/replays/fuel/fc4/base-<set>-100M.json <f>` and `py tools/fuel/stats.py`.
  bench.py plays on the fast runner when it is built (`--stock` for stock cambc), with stock's JSONs and bundles.
- Real budget: `--fuel 0`. Small benches swing by tens to hundreds of OOF once games diverge (one runaway game
  can add 500): indicative only. **The 10k-game real-budget A/B against fc4b is the judge of OOF** (`ab.sh`, a few
  minutes to ~20 on a busy box). Compare with the mirror's per-bot OOF and with the reference side in the same run
  (run-to-run noise ~600-800 OOF).
- The machine is shared (96 cores; other agents run batches). bench.py and ab.py share one CPU-slot pool: pass
  `--jobs 94` and let the pool divide. Run anything long in tmux (named `fc4-<area>-...`), not as a background task.
- Profiling: the census (real budget, per-component fuel and the stack where fuel ran out), `debug_fuel`/`FuelMeter`
  (util.h), raw `fuel()` laps inside `debug_block` (build without `--release`; work inside `debug_block` is not
  charged but codegen can shift), `tools/fuel/simprof`, the fuel-exact replay harness
  (`tools/replay/harness/README.md`). bench.py reproduces an A/B game exactly when run with the same two bots.
- Scratch files: `/tmp/fc4/<area>/` only.

## Rules of the work

- **Fuel-only changes are byte-identical at 100M** on every set (wide, oof, mg, q, big, fs, fight, tgt), plus any
  set where the change fires (a champion, map shape or situation the standard sets miss: build one with `--maps`,
  `--test-draft`, or a copy with a forced `draft_preference`; name it in your report). Check the turns that got
  DEARER (compare prints "cheaper N, dearer M"): moving cost onto fight or round-1 turns can raise real-budget OOF.
- **No new fuel gates** (code that reads `fuel()` and chooses worse). **Removing gates is a goal**: the user wants
  `note_shortcut` firings down and gates gone. A gate goes once the work it guards is cheap, or bounded by a fixed,
  measured limit that almost never binds (FUEL-GATES rule 2) with a deterministic fallback. Past removals multiplied
  OOF 4-5x because the guarded work was too dear: make the work cheap first, then remove, then show real-budget OOF
  and shortcuts on the benches and in a 10k A/B against fc4b.
- **Lifting fuel-motivated simplifications is a goal too**: places where the model is knowingly wrong to save fuel
  (TODO Fuel 2's list: Heart of Ruin's passive only at event turns, ground AoE / Varg splash / HoR landing / Ren
  reflection single-target, camp hits on our weakest once we fall, `walk_allies_in` ignoring walls; caps and magic
  numbers that exist for fuel). Find out why the straightforward version would run out, make it cheap, then lift it.
  Such a change need not be byte-identical, but it must be strictly more faithful to the rules (argue it from
  `cambc-rules.yaml`), not raise OOF, and be level or better in a 10k A/B.
- **Cases the rules make impossible** cost fuel for nothing (camps never move or regenerate, enemies never enter our
  spawn, Marcella is immune to stuns, a bush tile can't be seen from outside, a dead camp group stays empty until
  captured, respawns take 40+ rounds, shopping needs the spawn, ...). Dropping their handling is exact by the rules;
  say which rule.
- **Stay on big wins**: >= ~1k fuel on heavy turns, >= 0.3% total on a set, or a visible drop in turns over 100k,
  p99, round 1 or OOF. List smaller ideas as one-line "open minor items" with an estimate.
- **Think beyond micro-optimisation.** Fuel is ~1 per WASM instruction, so the big wins are work not done: results
  never read; work repeated across consumers or turns that one precomputation could serve (keyed exactly on what it
  reads); closed forms or bounds instead of simulation; exact early exits; an iteration order that lets a bound
  prune (best first); incremental updates instead of rebuilds; per-tile loops moved into flat-price host calls
  (bitboard, field, shadow-cast); vectorised flat arrays; fewer allocations (~420 each); moving work into the
  end-of-turn queue or the 200k first turn when no decision changes; the draft bot's 10M fuel and 1024 shared bytes
  (`memory.draft`); a failed search or evaluation repeated every turn of a standoff.
- **Engine behaviour `cambc-rules.yaml` does not settle:** spawn ONE short probe subagent (`tools/probes/README.md`)
  per narrow question; it settles only that question, updates `cambc-rules.yaml` and the probes README table, and
  commits those on your branch. Don't probe what the YAML already says. If the engine contradicts the YAML, say so
  in your report.
- Comment only counterintuitive behaviour, concisely; match the surrounding style. `farm_turn` is flattened
  (`[[gnu::flatten]]`): changes there shift codegen across every turn, so bench every set.
- Commit on your branch (one idea per commit), never push, never merge into fuel4-orch or main. Don't edit
  `bots/baselines/`, `bots/archives/hyperion`, `bots/hecate` or `bots/archives/demeter`. Don't edit CHANGES.md or EXPERIMENTS.md (the
  merge agent does). Append findings, dropped attempts with numbers and open leads to
  `research/hyperion/fuel-campaign-4/NOTES.md` on your branch under a `## <your area>` heading.

## Report (your final message)

Branch, worktree and commit shas; for each change: what, why it's exact (or, for a gate removal or a lifted
simplification, why the work is now bounded and why the new behaviour is more faithful), measured deltas against the
baseline JSONs (100M on all sets: identical counts, total, mean, p90, p99, max, over 100k, round 1; real budget: OOF
and shortcuts; A/B numbers if you ran one); sets where the change fires; what you tried and dropped, with numbers;
open minor items.
