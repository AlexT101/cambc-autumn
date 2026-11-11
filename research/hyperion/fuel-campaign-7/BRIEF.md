# Fuel campaign 7 (2026-11-06): shared brief for worker agents

Goal: make **astraeus** cheaper without changing its play. Base: astraeus **5166d1c5** (CHANGES 423), frozen as
`bots/variants/astraeus-5166d1c`. Target: **out-of-fuel (OOF) turns -30% or more** against it at scale. Metrics,
worst case first: OOF turns, p90 / p99 fuel a turn, turns over 100k at 100M, large-map fuel, round 1, shortcut
firings (`note_shortcut`: `SHORTCUT round champion what` lines), then mean fuel a turn. A change that lowers the
worst case and raises the mean a little is welcome.

Paths: MAIN = `/home/ubuntu/cambc-autumn` (primary checkout, branch `main`; other sessions use it with uncommitted
work: **never edit, build or commit there**). Make your own worktree and branch from main's tip:
`git -C MAIN worktree add MAIN/.claude/worktrees/fc7-<area> -b fc7-<area> main`, then link the generated maps:
`for d in MAIN/maps/*/; do ln -sfn "$d" maps/; done` (never commit the links). Read MAIN's `AGENTS.md` and
`cambc-rules.yaml` first (the rules override `docs/`). Shell: `source /home/ubuntu/venv/bin/activate`; for games
`export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86 CAMBC_BIN=MAIN/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native`.
Work only in `bots/astraeus/` (plus probes and your notes).

## Read before designing (what already won or lost)

Seven fuel rounds ran on astraeus/ocean before this one; most obvious ideas were tried. Read the parts for your area;
don't redo a dropped or lost item unless your idea is concretely different (say how).
- `research/hyperion/fuel-campaign-6/NOTES.md` (each area's "Open" list is a seed list) and its `BRIEF.md`,
  fuel-campaign-4/5 NOTES, `research/hyperion/FUEL-GATES.md`, `FUEL-AUDIT.md`, `GATE-PLACEMENT.md`,
  `research/hyperion/TODO.md` `## Fuel`.
- `research/ideas-2026-11-05/fuel.md`, `fuel4.md`, `fuel5.md`, `fuel6.md`, `fuelbud.md` (ocean's fuel rounds:
  probes of where farm loop and strike-search fuel goes, what exact repeats exist), `research/EXPERIMENTS.md` `## Fuel`
  and the "Fuel campaign" / "Fuel round" / "Farm turn fuel" / "Fuel gates census" entries, CHANGES.md entries tagged fuel.
- Lessons that recur: cross-turn fight memos found only ~6-10% exact repeats (not worth a key); the farm loop's cut
  is mostly the banking loop on big maps with no enemy in sight, stopped by a reserve sized for an uncached route
  search; 56% of OOF turns pass no fuel check at all (fight turns: strike search, `stand_lost_at`, post-strike walk's
  veto); additions inside the fight sim tend to read dearer through codegen; `farm_turn` is flattened, so any change
  there shifts codegen across every turn. Approximations that change play (shorter horizons, search caps, crude farm
  loops) have lost or been level: this campaign is about **exact** savings.
- `tools/README.md` "Fuel": bench.py, stats.py, oof.py, oof_bot.py, the census (`tools/fuel/census/`), `--trace`,
  `tail.py`, `gates.py`, simprof, host-call prices (a host call is a flat price: moving per-tile loops into bitboard,
  field and shadow-cast calls is usually the biggest saving).

## Where the fuel goes now (census of the base)

Instrumented copy `bots/variants/fc7-cen` (`instrument.py --fine --trace --lenient`), real budget against the base,
heavy + big + 32 pool maps, both sides: games in `MAIN/replays/fuel/fc7/cen/`, tables in
`MAIN/replays/fuel/fc7/cen-tables.txt` (census.py), `cen-tail.txt` (tail.py: last check passed, work after it, OOF
turns that passed none), `cen-gates.txt` (gates.py). Read the tables for your area before choosing targets; re-run the
census on your own instrumented copy to measure a specific turn class.

**Function-level fuel profiler** (no bot instrumentation; any built copy): `MAIN/replays/fuel/fc7/prof/README.md`.
Self and inclusive fuel per wasm function on heavy turns, from a patched fast runner. Rank targets with it before
designing; function level is reliable, line level undercounts inlined code. Fight round 1 found on fight-heavy
turns: stand check ~21.8k (`stand_reach` 7.9k, `stand_trade` 10.4k of which the sim 7.5k), strike search ~25k
(read 9.8k incl. `read_geometry` 4.9k, grow 6.7k, price 5.9k); the fight memo almost never hits.

## Benches (opponent: the frozen base `bots/variants/astraeus-5166d1c`)

- `MAIN/replays/fuel/fc7/bench.sh TAG BOT [SETS]` (run from your worktree root; BOT is a frozen copy under `bots/variants/`, synced into MAIN's `bots/variants/` by the script, e.g.
  `variants/fc7-<area>-x`) writes `MAIN/replays/fuel/fc7/TAG-<set>-{100M,real}.json`. Use a TAG with your area in it.
  Sets (100M): `def` (16 vs hyperion), `wide` (52 vs hyperion, test drafts: many champion types), `pool` (128, 64
  ladder-like maps), `big` (32, 8100+ tiles), `heavy` (50, OOF-heavy maps), `td` (64, both bots on test drafts:
  ladder compositions with HoR, Prism, Ren, Stellar, Cassi & Issac...). Real budget: `poolR bigR heavyR tdR`.
  `ALL=1` runs all ten. Base JSONs: `MAIN/replays/fuel/fc7/base-*.json`.
- Compare: `py MAIN/tools/fuel/bench.py compare BASE CAND` (identical replays; cheaper/dearer turns; mean/p90/p99)
  and `py MAIN/tools/fuel/stats.py BASE CAND`.
- **Bench a frozen copy, never a live bot dir you keep editing:** `./copybot astraeus variants/fc7-<area>-<x>`
  (from your worktree; it leaves out `.cambc/`).
- **Fuel-only changes are byte-identical at 100M on every set** (all six), plus any set where the change fires that
  these miss (a champion, map shape or situation: build one with `--maps`, `--test-draft`, or a forced draft; name
  it in your report). Check the turns that got DEARER, not only the totals.
- Real-budget small benches swing by ±10-20% OOF once games diverge: indicative only. The judge of OOF is a 10k-game
  A/B: `MAIN/replays/fuel/fc7/ab.sh NAME variants/<cand> variants/astraeus-5166d1c w` (suite `fc7-w`, seeds
  770201-770220, reserved for worker A/Bs; `m` is for merges, `f` for the final run: never use those). It writes
  `MAIN/replays/fuel/fc7/ab/NAME.{log,fuel,shortcuts,oof}`. Run one only for a candidate whose bench shows a real
  gain; the merge agent runs one per batch anyway.
- The box is shared (96 cores, 86 slots; other sessions and another worker run beside you; bench.py and ab.py share
  one CPU-slot pool). **One batch at a time**, long runs in tmux (session `fc7-<area>-...`) or as a
  `run_in_background` command, waited on in the background, never a foreground sleep loop. Scratch:
  `/tmp/fc7/<area>/`. Delete game dirs you no longer need (`MAIN/replays/fuel/fc7/g/<tag>-*`).

## Rules of the work

- **Play must stay as the base plays at 100M.** Fuel-only changes (byte-identical at 100M) keep that automatically:
  that is the bar. A change that is not byte-identical needs a 10k-game A/B level or better on win rate and lower
  OOF, and must be reported as such; prefer exact.
- Gates: reordering work so that cheap exact work comes first, or moving work into the turn-end queue / round 1's
  200k turn, is fine when 100M stays identical. **Fuel gates** (code that reads the fuel left and takes a cheaper
  or worse path: an anytime search keeping its best so far, a bound instead of a sim, skipping optional work) are
  allowed **only if they significantly improve win rate**: a level A/B, or lower OOF alone, is not enough. Bar: a
  10k A/B on `fc7-w` reading above 50%, then a 20k confirmation on fresh seeds no A/B has used (make a suite per
  AGENTS.md "Confirm a gain") whose 95% CI lies wholly above 50%. A gate must also never fire at 100M (all six sets
  byte-identical) and must log `note_shortcut` with its own tag. Exact savings remain the main road.
- **Cases the rules make impossible** cost fuel for nothing (camps never move or regenerate, enemies never enter or
  land on our spawn, Marcella is immune to stuns, a bush tile can't be seen from outside, a dead group stays empty
  until captured, respawns take 40+ rounds, wards never expire or block, the cooldown is 8 rounds, ...). Dropping
  them is exact by the rules; cite the rule.
- **Think beyond micro-optimisation.** Fuel is ~1 per WASM instruction, so the big wins are work not done: results
  never read; work repeated across consumers or turns that one precomputation could serve (keyed exactly on what it
  reads); closed forms or bounds instead of simulation; exact early exits and cheap sufficient tests before an
  expensive one; an order that lets a bound prune (best first); incremental updates instead of rebuilds; per-tile
  loops moved into flat-price host calls (bitboard, field, shadow-cast); fewer allocations; moving work into the
  end-of-turn queue or the 200k first turn when no decision changes; the draft bot's 10M fuel and `memory.draft`
  (1024 bytes readable all game); a failing search or a vetoed step repeated every turn of a standoff (runaway games).
  Bridge files: a value computed in one place may already exist elsewhere this turn.
- **Engine behaviour `cambc-rules.yaml` doesn't settle:** spawn ONE short probe subagent per narrow question
  (`tools/probes/README.md`); it settles only that, updates `cambc-rules.yaml` (declarative, no citations) and the
  probes README table, and commits those on your branch. If the engine contradicts the YAML, say so in your report.
- Stay on big wins (>= ~1k on heavy turns, a visible drop in OOF, turns over 100k, p90/p99, round 1). List smaller
  ideas as one-line open items.
- Comment only counterintuitive behaviour, concisely; match the surrounding style.
- Commit on your branch (one idea per commit, messages ending `Co-Authored-By: Claude Opus 5.5
  <noreply@anthropic.com>`); never push, never touch `main`. Don't edit `bots/baselines/`, `bots/archives/hyperion`, other
  bots, CHANGES.md or EXPERIMENTS.md (the merge agent does). Append findings, dropped attempts with numbers and open
  leads to `research/hyperion/fuel-campaign-7/NOTES.md` on your branch under `## <your area>`.

## Report (your final message)

Branch, worktree and commit shas; for each change: what, why it's exact, measured deltas against the base JSONs
(100M on all sets: identical counts, total, mean, p90, p99, max, over 100k, round 1; real budget: OOF and
shortcuts), the 10k A/B (win %, OOF cand/ref, fuel stats) if run; sets where the change fires; what you tried and
dropped, with numbers; open items.
