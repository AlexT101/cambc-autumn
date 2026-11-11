# Common brief for CALYPSO implementation agents

You implement one macro change in a C++ Battlecode bot (Cambridge Battlecode, engine cambc 5.0.1). You are
an implementer working for an orchestrator who designs and tests; it will run the large A/B tests itself.

## Where

- Worktree: `/home/ubuntu/wt/macro-o3` (git branch `macro-o3-20261111`). Python: `source /home/ubuntu/venv/bin/activate` (`py` on PATH).
- Edit ONLY files inside your variant directory `/home/ubuntu/wt/macro-o3/bots/variants/<NAME>/` (named in your task).
  Never edit `bots/charybdis`, `bots/variants/charybdis-ref`, other variants, tools, or anything outside the worktree.
  Never read or touch `/home/ubuntu/cambc-autumn` (except running the fastrunner binary named below) or other
  directories under `/home/ubuntu/wt/`. Do not commit, do not push.
- Your variant starts as an exact copy of `charybdis`, a mature, heavily engineered bot (~38k lines).
  Structure: `src/bot.cc` is the turn (`decide()` takes the first branch that applies); `economy/` (farm.cc = the
  farm loop choosing which camp group to work, camps.cc = camp valuation helpers, bank.cc = banking/tribute
  timing, crew.cc = crews on strong groups, capture.cc, shop.cc, home.cc, siege.cc), `combat/`, `model/`
  (world.h/.cc = beliefs about every champion and camp, pathing, safety, comms = the 8 shared bytes),
  `draft/`, `params.h` (constants). `unity.cpp` includes every `.cc`: a new `.cc` must be added there.
- Read as needed: `/home/ubuntu/wt/macro-o3/AGENTS.md` (project guide), `cambc-rules.yaml` (engine-verified
  game rules: the source of truth), `docs/api/cpp.md` and `sdk/cpp/cambc.h` (the C++ API).

## Rules

- Do NOT change drafting choices or emblem/shard selection logic (draft/, which emblem shop.cc buys). Keep
  `params::test_draft` false.
- Debug output only inside `debug_block({ ... });` (plain printf changes the game). Use printf, never std::cout.
- Every change must make conceptual sense and tie to a game mechanic. Avoid magic numbers: derive constants
  from the rules or from measured quantities named in your task; when you must pick a value, say why.
- Integrate into the existing structure (extend the system that already decides the thing) rather than
  bolting a separate mode on top.
- Fuel: tests run at 2x fuel (200k a turn), so do not spend effort on fuel optimisation, but no gratuitous waste:
  no per-turn work that scales badly (e.g. O(groups^2) full-field floods every turn); reuse kept fields/caches
  that exist. The bot must not crash or throw uncaught errors. Comment only counterintuitive behaviour, concisely.
- Thrown-and-caught `cambc::error` costs ~3.9k fuel; prefer checks that avoid errors.

## Build and smoke test

Build (release, ~1-3 minutes; a compile error shows here):
```
source /home/ubuntu/venv/bin/activate && cd /home/ubuntu/wt/macro-o3 && cambc build bots/variants/<NAME> --release
```
Smoke A/B, 48 games (24 maps both sides) against the frozen reference; run it in the background (it takes a few
minutes including building both bots) and wait for it to finish:
```
cd /home/ubuntu/wt/macro-o3 && CAMBC_SLOTS=86 PATH=$HOME/.cargo/bin:$PATH CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native py tools/ab.py variants/<NAME> variants/charybdis-ref --no-test-draft --fuel 200000 --suites maps/macro-smoke --threads 16 --name mo3-smoke-<NAME>-<N> > /tmp/claude-1000/-home-ubuntu-cambc-autumn/951f1bac-215c-4bb4-8e29-669b32344dfb/scratchpad/smoke-<NAME>-<N>.log 2>&1
```
Results: `replays/ab/mo3-smoke-<NAME>-<N>/summary.md` (win %, failed matches, out-of-fuel turns per bot, early-loss flags
such as DRAFT-UNFINISHED / PLAN-CHECK). The win rate of 48 games is noise; you only check that nothing fails,
nothing crashes, the out-of-fuel count is not wildly above the reference's, and the behaviour you added actually
fires. For that, add `debug_block` trace lines for your new decisions and run one smoke with `--debug` (debug builds;
the traces land in each replay zip as `team-a.stdout` / `team-b.stdout`: `unzip -p FILE.repl26a team-a.stdout`);
batch replays are in `replays/batch-*-mo3-smoke-<NAME>-<N>-macro-smoke/`. Count how often your logic fires and
check a few cases are sensible. Do not run anything bigger than the smoke suite.

## Done

When the code is complete, builds, and the smoke run is clean: spawn a read-only auditor subagent (Agent tool,
subagent_type "Plan", which cannot edit) and give it the design (from your task), the variant path and the list
of changed functions; ask it to verify the change against the design and hunt for bugs (wrong signs, stale
caches/kept values that your new inputs invalidate, prune bounds your change breaks, units, off-by-one rounds,
paths where the logic silently never fires). Fix what it finds that is real, rebuild, re-smoke. Then finish with a
report: what you changed (files and functions), the exact semantics of each new rule, how you checked it (smoke
result: games, failures, OOF counts for both bots, how often each new rule fired), and any concerns or ideas for
the orchestrator. Stop there.
