# Fuel campaign 12: ocean (2026-11-07)

Goal: cut `bots/ocean`'s fuel **without changing its play**. Metrics, in priority order:

1. out-of-fuel (OOF) turns at the real budget — target **-20% or better** against `variants/oc-base13`;
2. p90 / p99 / max fuel a turn, and fuel on big maps (8100+ tiles);
3. shortcuts taken (`SHORTCUT` lines: farm-partial-evaluation, step-guard-entry, turn-order, prey-cut-short, ...);
4. mean fuel a turn.

Worst case beats average: a change that raises the mean slightly but cuts heavy turns, OOF turns or big-map peaks is
wanted (e.g. precomputing once what several consumers rebuild, amortised caches, a bounded structure in place of an
unbounded one).

## Rules of the campaign

- **Exact only.** Every change must leave the bench's 100M replays byte-identical to oc-base13's on all six sets below.
  Fuel-aware behaviour (new gates, budgets, reserves, cheaper-but-different methods) is out of scope: past rounds show
  re-allocating fuel is level (EXPERIMENTS "Fuel budgeting"); only cheaper identical work has paid.
- Work in your own copy (`./copybot ocean variants/<yours>`); never edit `bots/ocean`, `bots/baselines/` or another
  agent's copy. Don't commit; the merge agent does.
- At 100M a few decisions still read measured fuel (e.g. `Pathing::route`'s `cheap_guard`, the turn-end queue,
  anytime loops): an exact saving can shift them. If a set diverges, find the first differing turn
  (`tools/fastengine/runner/scripts/cmp_bundles.py`) and decide whether it's a logic change (fix it) or a fuel-read
  switch (report it; don't hide it).
- **Coverage.** Identity only proves something if the changed code runs in the bench. If a change only triggers for
  some champion, emblem, map class (holes, bushes, monoliths, sealed altars, teleport access, 100x100) or phase, show
  that the bench executes it (a debug copy counting hits, or the per-function profiler), and add games that do
  (`bench.py run ... --maps <paths> [--test-draft]`, maps from `maps/gen*/`, `maps/suites/fresh/*`, or a mapgen
  preset such as fuel-stress) when the six sets don't.
- Use the fast runner (`CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native`); the box is shared
  (86-slot pool, other jobs running). Anything over ~30 s goes in the background.

## Benches (`replays/fuel/fc12/`)

`replays/fuel/fc12/bench.sh TAG variants/<yours> [SETS]` (a copy of campaign 7's; read its header). Sets: `def` (16 vs
hyperion), `wide` (52, test drafts: many champion types), `pool` (128 vs oc-base13, ladder-like), `big` (32, 8100+
tiles), `heavy` (50, OOF-heavy maps), `td` (64, ladder compositions); suffix `R` for the real budget (`poolR bigR
heavyR tdR`), `ALL=1` for all. oc-base13's baselines are `replays/fuel/fc12/base-<set>-{100M,real}.json`, games under
`g/base-*`.

- Identity: `py tools/fuel/bench.py compare replays/fuel/fc12/base-<set>-100M.json replays/fuel/fc12/TAG-<set>-100M.json`.
- Headlines: `py tools/fuel/stats.py base.json cand.json` (mean, p99, max, >100k, round 1, OOF, shortcuts); p50/p90 are
  in each JSON's `all` and in `bench.py compare`'s output.
- Real-budget benches swing by ±20 OOF turns a set: use them for direction, judge OOF turns with an A/B.
- A/B (OOF turns per bot are in its summary; win rate should read level, ~50%, for an exact change):
  `CAMBC_BIN=... FASTRUNNER_MODE=native py tools/ab.py variants/<yours> variants/oc-base13 --no-test-draft --suites maps/suites/merged/<yours> --name <name>`.
  Make the suite with `/home/ubuntu/tmp-offload/fuel11/mksuite.sh NAME FIRST LAST` (256 maps a seed; 20 seeds =
  10,240 games). Seeds are assigned per agent so suites stay unused.

## Where to find the fuel

- Tools: `tools/README.md` "Fuel: tools/fuel" — the census (`tools/fuel/census/`, `instrument.py --fine/--trace`,
  `census.py`, `trace.py`, `tail.py`, `gates.py`), the per-function profiler (`replays/fuel/fc7/prof/README.md`,
  `prof.sh`), simprof for fight simulations, `debug_fuel`/`FuelMeter`. instrument.py's patterns may no longer match
  ocean's code: `/home/ubuntu/tmp-offload/fuel11/cenpatch.py` and `cen.sh` adapted them for oc-base10.
- Host-call prices: tools/README.md's table. ~1 fuel per wasm instruction and per memset/memcpy byte; an allocation
  ~130 + ~290 to free; a thrown `cambc::error` ~3.9k. A host call has a flat price whatever its work, so moving a loop
  into bitboard / field / shadow-cast calls is usually the biggest saving.

## What history says (read before starting)

- research/EXPERIMENTS.md: "Fuel pass on oc-base10", "Fuel round 10", "Fuel round 9", "Fuel round 8", "Fuel budgeting",
  the "Fuel" section (~line 6762) and the campaign 4-7 entries. research/hyperion/: FUEL-AUDIT.md, FUEL-GATES.md,
  STRIKE-SEARCH.md, TODO.md "Fuel", fuel-campaign-*/ (briefs, NOTES, OPEN-ITEMS). research/ocfuel-*, rsvfuel-*,
  walkfuel-*, crewfuel-* (2026-11-05).
- **What paid:** exact ports of campaign 7 cut OOF turns 16.7% (round 8) and 16.0% (round 9): bitboarding per-tile
  host-call loops (the lock plan's wait: 3 x 729 tiles, 2-4 calls a tile -> one Not and one And), memoising by
  (round, observations), closed forms for loops, static boards built once.
- **What didn't:** ptw's own code is only ~1.7% of a turn; its +58% OOF is behaviour (wider threats send more turns to
  dear branches early), so fuel floors on it saved 1-2%. Make the *downstream* work cheaper instead. Memos whose
  upkeep equals the calls saved nothing. Sub-1% cuts don't show in OOF counts. Re-allocation, watchdogs and new gates
  lose or are level.
- **Census of OOF turns (oc-base7/oc-fuel10, real budget, self share):** strike search 24% (`plan_strikes`), farm loop
  9%, fight roster `s.fight_of` 7%, want_home 6% in decide + 6% in continue_recall (every recall turn's feint;
  `wh.outmatched`, channels), farm 5%, camps 3%, retreat 3%. Function profile on those turns: plan_strikes, act,
  update_champion, Reach, simulate, Search::grow, find_members, set_turn_order. Round 1 runs out on ~6% of champion
  first turns (farm loop, static camps, siege kite, init_beliefs; mapcond-q's `condition_on_map` ~9k, 29k on 100x100:
  a full spawn-to-spawn distance field). The oc-base10 census put the ptw rise in continue_recall's want_home
  (19.9k -> 23.9k a call). Re-measure on oc-base13 before choosing: the code has moved since.

## Thinking outside the box

Ideas that count as exact:
- early exits and bounds (branch-and-bound that provably can't change the argmax, ties included);
- better iteration order so cheap rejections come first; short-circuit evaluation of pure predicates;
- formulas or closed forms in place of simulation, when the formula is proven equal on every input (exhaustively when
  the domain is small);
- precomputing shared inputs once per turn (or once per game for static terrain) for several consumers; incremental
  updates in place of rebuilds; caching across turns with an exact invalidation key;
- **impossible cases from the rules**: code that guards against states `cambc-rules.yaml` forbids (a camp in a bush
  hiding from camps, enemies on their spawn's forbidden tiles, a stunned unit acting, a channel interrupted by damage,
  teleports cancelled...) can be dropped, and loops over tiles that can never qualify skipped;
- bitboard / distance-field host calls in place of per-tile loops; fewer allocations (reserve, reuse, arrays);
- cheaper representations (bitsets, small fixed arrays, integer in place of float where exact).

If a rule needed to justify a change is unclear from `cambc-rules.yaml`, you may spawn a short probe subagent (bounded
to that one question; see `tools/probes/README.md`); record the confirmed rule in `cambc-rules.yaml` (declarative, no
citations) and the probe in the README's table. If the engine contradicts the YAML, say so prominently in your report.

## Deliverable

- Your variant directory with the changes.
- `research/hyperion/fuel-campaign-12/<agent>.md`: each change (files, functions, idea, why it's exact), its identity
  evidence (sets, games, extra coverage), its fuel effect (mean / p90 / p99 / max per set at 100M; real-budget OOF and
  shortcuts), what you tried and dropped and why, and the A/B result.
