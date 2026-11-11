# Fuel campaign 5 (2026-11-03): shared brief for worker agents

Goal: cut astraeus's fuel where it hurts. Metrics, **worst case first**: out-of-fuel (OOF) turns (campaign target:
**-30% against the baseline** in a 10k-game real-budget A/B), p90 fuel a turn, shortcut firings (`note_shortcut`),
then mean fuel a turn. Turns over 100k at 100M, p99/max, round 1, rounds 300+ and large maps count with the worst
case. A change that lowers those and raises the mean a little is welcome.

Paths: MAIN = `/home/ubuntu/cambc-autumn` (primary checkout: other agents use it; never edit or commit there). The
integration branch is `fuel5-orch` (worktree `MAIN/.claude/worktrees/fuel5`; only the orchestrator and merge agent
commit there). Make your own worktree and branch from its tip:
`git -C MAIN worktree add MAIN/.claude/worktrees/fc5-<area> -b fc5-<area> fuel5-orch`. Read MAIN's `AGENTS.md` and
`cambc-rules.yaml` first (the rules override `docs/`).

## Read before designing anything (what already won or lost)

Four campaigns ran before this one; most obvious ideas were tried. Read the parts for your area and don't redo a
"dropped / lost / no gain" item unless your idea is concretely different (say how).
- **`research/hyperion/fuel-campaign-4/NOTES.md`** (the latest: its "Campaign summary" first, then your area's
  worker and merge sections: profiles, kept/dropped work with numbers, open leads, the merge rounds' arguments for
  exactness) and its `BRIEF.md`. Campaign 3's and 2's NOTES for older leads.
- `research/hyperion/FUEL-GATES.md` (each gate, what removing it did), `research/hyperion/FUEL-AUDIT.md` (each
  gate's fallback logic).
- `research/hyperion/TODO.md` `## Fuel` (item 2 lists the fight model's rule simplifications).
- `research/EXPERIMENTS.md` `## Fuel`.
- `tools/README.md` "Fuel": bench.py, oof.py, oof_bot.py, the census (`tools/fuel/census/`, `--trace`: its patterns
  may lag the bot; `instrument.py --lenient`), simprof, stats.py, host-call prices.
- This campaign's `research/hyperion/fuel-campaign-5/NOTES.md` on `fuel5-orch`: findings so far.

## Where campaign 4 left off (its handoff, in rough order of value)

- **farm-partial-evaluation** (the farm group loop's `room()` cut) fires 2.05M times in 10k games, two thirds of all
  shortcuts. The redesign described in NOTES "Farm loop": keep each camp group's position-independent value parts
  across turns, give every group a cheap upper bound in one vectorised pass, evaluate best-first and stop once no
  remaining bound can beat the best, so the loop finishes instead of being cut. Its result must first stop
  depending on evaluation order (ties, help_group, risky, from_altar_value).
- **Rounds 300+ hold 44% of OOF.** The fight-side tail: turn-order's non-quiet calls (`offer_kills`, `threats_at`,
  the escape pair) and the step guard's whole-guard placements in strike search and dash_landings.
- **A failure memo for standoff searches**: the same failing route searches repeat every turn (~50k a turn on
  wild-1100006217). A 3-slot cache was level; the key must match exactly when the search would fail again.
- **The post-loop reserve on later turns** misses `camp_cast` and attack-tile decodes the queue hasn't reached:
  make those cheap (camp_cast per group per round, decode only the walk's tiles) rather than reserve more.
- **The per-tile step guard** halved its shortcuts but raised OOF ~5% (3 versions). Untested: also walling guarded
  dash tiles two steps away when a dash is ready, as the whole guard did.
- **Heart of Ruin's damage scaling** (its passive applied only at event turns): a faithful model needs a closed form
  for the quiet stretches of a fight sim; six bounded variants cost +2.6-10% OOF (NOTES "Rules and assumptions").
- **ward-no-bushes-clusters**: unbounded growth costs 14k median on round 1, up to 61-92k on bush-carpet maps.
- **World init over 187k on fuel-stress maps**, so round 1 has little left for the opening loop.
- Minor: comms send skipping `observe` when no camp tile entered view; `refresh()` reading far camp members;
  camp_cast's per-slot `draw_alive_members` / `landing_threats` shared between slots; `enemy_cast` counting far
  unseen enemies; walk_on's descend plan twice.

## Baseline: `astraeus-fc5b` = main 1fe4a9f2's astraeus (= campaign 4's final m4)

- Frozen copies (in `MAIN/.claude/worktrees/fuel5/bots/variants/`, copy their `src/` into your worktree's
  `bots/variants/<same name>/`): `astraeus-fc5b` (the baseline) and `astraeus-fc4b` (the benches' opponent).
- **Benches**: opponent astraeus-fc4b, so campaign 4's m4 runs are this campaign's baselines:
  `MAIN/replays/fuel/fc5/base-<set>-{100M,real}.json` (links to `../fc4/m4-*`). Sets (map lists `<set>set.txt`
  there): **wide** (`--set wide --test-draft`, 52 games vs hyperion: test drafts, so Heart of Ruin, Ren, Stellar,
  Ryth, Vendetta etc. appear), and own drafts against fc4b: **oof** (24 maps), **mg** (many groups, 12), **q**
  (topology / close-far spawns / dungeon, 24), **big** (90-100 a side, 16), **fs** (fuel-stress 100x100 ~220
  groups, 12), **fight** (arenas, 15), **tgt** (camp-heavy, 8). `bench.sh TAG BOT [SETS]` there runs them for a
  frozen bot (from your worktree root).
- **A/B judge**: `MAIN/replays/fuel/fc5/ab.sh NAME CAND REF [SUITES]`: real budget, own drafts, fast runner,
  `maps/fresh-11000..11019` (10,240 games) by default. Mirror of fc5b: `ab-fc5-mirror.log`. Per-turn fuel stats:
  `py MAIN/replays/fuel/fc5/fuelstats.py <batch dirs>`; shortcuts: `py MAIN/replays/fuel/fc5/shortcuts.py <batch
  dirs>`; OOF: `py tools/fuel/oof.py` / `oof_bot.py`.

## Measuring

- **Worktree setup:** generated maps are not in git: `for d in MAIN/maps/*/; do ln -sfn "$d" maps/; done` (two
  exist already and warn: fine). Never commit the links.
- **Bench a frozen copy, never the live `bots/astraeus`:** `./copybot astraeus variants/<name>`. Build it once
  (`cambc build bots/variants/<name>`) before starting several benches of it: concurrent first builds of one
  directory collide in CMake (the same for the `bench-td-*` copy `--test-draft` makes).
- 100M: `py tools/fuel/bench.py run variants/<name> --opp variants/astraeus-fc4b --maps $(cat MAIN/replays/fuel/fc5/<set>set.txt) --per-map --jobs 94 --out <f>`
  (wide: `--set wide --test-draft` instead of `--opp/--maps`); compare with
  `py tools/fuel/bench.py compare MAIN/replays/fuel/fc5/base-<set>-100M.json <f>` and `py tools/fuel/stats.py`.
  bench.py runs on the fast runner by default (identical JSONs to stock; `--stock` forces stock).
- Real budget: `--fuel 0`. Small benches swing by hundreds of OOF once games diverge: indicative only. **The 10k-game
  real-budget A/B against fc5b is the judge of OOF.** Compare with the reference side in the same run (run-to-run
  noise ~600-800 OOF at ~57k).
- The machine is shared (96 cores; other agents run batches). bench.py and ab.py share one CPU-slot pool: pass
  `--jobs 94` and let the pool divide. Run anything long in tmux (named `fc5-<area>-...`), not as a foreground call.
- Profiling: the census (real budget, per-component fuel and the stack where fuel ran out), `debug_fuel`/`FuelMeter`
  (util.h), raw `fuel()` laps inside `debug_block` (build without `--release`; work inside `debug_block` is not
  charged but codegen can shift), `tools/fuel/simprof`, the fuel-exact replay harness
  (`tools/replay/harness/README.md`). bench.py reproduces an A/B game exactly when run with the same two bots.
- Scratch files: `/tmp/fc5/<area>/` only.

## Rules of the work

- **Fuel-only changes are byte-identical at 100M** on every set (wide, oof, mg, q, big, fs, fight, tgt), plus any
  set where the change fires (a champion, map shape or situation the standard sets miss: build one with `--maps`,
  `--test-draft`, or a copy with a forced `draft_preference`; name it in your report). Check the turns that got
  DEARER (compare prints "cheaper N, dearer M"): moving cost onto fight or round-1 turns can raise real-budget OOF.
- **No new fuel gates** (code that reads `fuel()` and chooses worse). **Removing gates is a goal**: shortcut firings
  down and gates gone. A gate goes once the work it guards is cheap, or bounded by a fixed, measured limit that
  almost never binds (FUEL-GATES rule 2) with a deterministic fallback. Past removals multiplied OOF 4-5x because
  the guarded work was too dear: make the work cheap first, then remove, then show real-budget OOF and shortcuts.
- **Lifting fuel-motivated simplifications is a goal too**: places where the model is knowingly wrong to save fuel
  (TODO Fuel 2: Heart of Ruin's passive only at event turns, ground AoE / Varg splash / HoR landing / Ren reflection
  single-target, camp hits on our weakest once we fall, `walk_allies_in` ignoring walls; caps and magic numbers that
  exist for fuel). Find out why the straightforward version would run out, make it cheap, then lift it. Such a
  change need not be byte-identical, but it must be strictly more faithful to the rules (argue it from
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
- Commit on your branch (one idea per commit, messages ending `Co-Authored-By: Claude Opus 5.5
  <noreply@anthropic.com>`), never push, never merge into fuel5-orch or main. Don't edit `bots/baselines/`,
  `bots/hyperion`, `bots/hecate` or `bots/archives/demeter`. Don't edit CHANGES.md or EXPERIMENTS.md (the merge agent does).
  Append findings, dropped attempts with numbers and open leads to `research/hyperion/fuel-campaign-5/NOTES.md` on
  your branch under a `## <your area>` heading.

## Report (your final message)

Branch, worktree and commit shas; for each change: what, why it's exact (or, for a gate removal or a lifted
simplification, why the work is now bounded and why the new behaviour is more faithful), measured deltas against the
baseline JSONs (100M on all sets: identical counts, total, mean, p90, p99, max, over 100k, round 1; real budget: OOF
and shortcuts; A/B numbers against fc5b); sets where the change fires; what you tried and dropped, with numbers;
open minor items.
