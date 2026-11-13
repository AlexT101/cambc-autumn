# T9 `denyfix`: why enemy winning tributes still complete under the ported denial

You are an implementation subagent for THEIA, the orchestrator of a macro refactor of our Cambridge Battlecode bot
`charybdis` (C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-theia` (branch
`mx-theia-20261113`). Do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`. Leave every existing `bots/variants/*` alone
(read them freely).

Read first: `/home/ubuntu/wt/mx-theia/AGENTS.md`, `cambc-rules.yaml` (tribute, lock, stun, vision, turn order),
`research/mx-theia/briefs/t7-deny.md` and `research/mx-theia/patches/deny-a.diff` (the port you start from).

## Setup
- Start from `bots/variants/deny-a` (= chy-ref 529 + scylla's tribute denial, flags in params.h). Reference opponent:
  `bots/variants/chy-ref` (never edit).
- `cd /home/ubuntu/wt/mx-theia && ./copybot variants/deny-a variants/denyfix-a` (never copy `.cambc/`).
- Build with `cambc build` (debug) / `cambc build --release`. Debug output only inside `debug_block({ ... });`.
- Debug A/Bs: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-theia && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/denyfix-a variants/chy-ref --no-test-draft --fuel 200000 --debug --suites maps/suites/mx-theia/study --name mx-theia-t9-dbg` (add `--max-games N` or similar if ab.py has it; check `py tools/ab.py --help`). Extract replays with `node tools/replay/extract.mjs <batch dir> --threads 32 --out <dir>`; D traces are in each replay zip's team-a/b.stdout. Analysis examples: `research/mx-theia/scripts/winchan.py` and `winrace.py` (run `py research/mx-theia/scripts/winchan.py <extract dir>`; in an ab.py batch our bot is team A in `-12` replays, B in `-21`).

## Facts (1,000 deny-a vs chy-ref dev games, 2x fuel)
- deny-a wins 50.9% (10,200 dev games; pooled held-out 50.8 of 30,600). When chy-ref starts a winning-size tribute
  first (score + bag >= 1,000; 434 games) deny-a wins 14.3%, double the mirror's 7%; when deny-a starts first (381)
  it wins 93.7%; but deny-a is first less often (381 vs 434).
- chy-ref's winning channels against deny-a: 349 completed, 1,048 stunned, 483 locked, 1,473 cancelled by chy-ref
  itself, 150 still running at the end. For the completed ones our bodies were alive (3.5 on average), the nearest at
  the start a median 10 tiles off, at its nearest during the channel a median 7, and within 4 (stun range) at some
  point in only 19%: our stoppers come near but do not stop.
- Our own winning channels: 381 completed, 2,170 stunned and 786 locked by chy-ref (which stops at once, ~20% into the
  channel), 688 cancelled by us.
- Ablations (dev, 10,200 each): without the watch ward 51.7, without lock_first 50.6, without the alarm 50.0.

## Task
1. **Diagnose** on debug games (study suite, a few hundred games): for chy-ref's winning channels that complete, why no
   stop: no stopper assigned, stopper waiting on deny_late's margin and then too late (walk estimate, stunned, blocked,
   died), stopper without a lock or a ready stun, deny_late not engaged because the tribute was not seen/alarmed,
   chy-ref guards killing our stopper, our stopper's stop branch pre-empted by another branch (retreat, recall, farm).
   Classify the completed channels into causes with counts. Same for the 1,473 self-cancels if cheap (likely chy-ref
   seeing our stopper).
2. **Fix** the top causes in `denyfix-a`, each tied to the rules (e.g. a margin that counts turn order and the
   stopper's walk by pathing, not Chebyshev; commit earlier when the stopper's path is contested; a second stopper when
   the first is threatened). No magic numbers; no tuning sweeps.
3. Also build `denyfix-w` = denyfix-a with `deny_watch = false` (the ablation read better without the watch ward).

## Audit, build, smoke (before returning)
1. Spawn a **read-only** auditor subagent (general-purpose; tell it explicitly: do not edit, create or delete any
   file) with this brief, your diagnosis and your diff (`diff -ru bots/variants/deny-a/src bots/variants/denyfix-a/src`).
2. Fix what it finds.
3. Smoke each variant (256 ladder games, release): `... py tools/ab.py variants/denyfix-a variants/chy-ref --no-test-draft --fuel 200000 --name mx-theia-t9-smoke-a` (and `-w`). Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Report win rate and OOF (a smoke, not a read). Then re-run the diagnosis counts on a debug batch to show the completed-channel count moved.
   Run long commands in the background; while waiting, keep working or block on a bounded wait, and do not end your
   turn until you hand back: ending your turn ends your run. Delete your debug replay batches when done.

## Stop condition
Return (SubagentHandback) when both variants build, pass the audit and the smoke, or by 20:15 UTC (check `date -u`)
with whatever is finished (say what is not). No 10k-game A/Bs. Report the diagnosis table, what you changed, the
auditor's findings and your fixes, the smoke results, and the before/after counts. Save diffs (against chy-ref) as
`research/mx-theia/patches/denyfix-a.diff` and `denyfix-w.diff`.
