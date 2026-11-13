# T12 `alarm`: the tribute alarm in every game

You are an implementation subagent for THEIA, the orchestrator of a macro refactor of our Cambridge Battlecode bot
`charybdis` (C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-theia` (branch
`mx-theia-20261113`). Do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`. Leave every existing `bots/variants/*` alone
(another implementer works in `bots/variants/chip-*`).

Read first: `/home/ubuntu/wt/mx-theia/AGENTS.md`, `cambc-rules.yaml` (shared bytes: 8 zero-initialised bytes, a write
visible at once to teammates acting later; the priority payload; tribute b = ceil(gems/10) turn ends), and the
denial code: `research/mx-theia/patches/denyfix-a-vs-dnw-min.diff`, `research/mx-theia/patches/dnw-min.diff`
(chy-ref -> dnw-min), model/comms.h / comms.cc in `bots/variants/denyfix-a`.

## Setup
- Start from `bots/variants/denyfix-a` (our best: pooled held-out 52.5 vs chy-ref).
- `cd /home/ubuntu/wt/mx-theia && ./copybot variants/denyfix-a variants/alarm-a` (never copy `.cambc/`).
- Build with `cambc build` (debug) / `cambc build --release`. Debug output only inside `debug_block({ ... });`.

## Why
- The gain of the denial port comes from late stops (a stop in the channel's last turns wastes the whole channel;
  a channel restarts whole) and the alarm that brings stoppers in time: without the alarm the late stops read 49.8
  instead of 52.2 on dev.
- T9's diagnosis of 261 long enemy winning channels that completed against us: the top cause (86) was never seen and
  no alarm. **The alarm field is left out of the shared bytes in 830 of 2,040 games**, mostly when a healer is
  drafted (Willow's ally-position record takes the room). In 44 of the 88 never-seen cases the channeller had been seen
  carrying the winning bag ~9 rounds before it started.

## Design
Make the alarm fit in every game, losing as little as possible elsewhere:
- Measure first: for the shared-bytes layout on the 171 maps under `maps/` (and the dev suite if cheap), with and
  without a healer, which records take how many bits, and how many bits the alarm needs (altar index, end-round slot).
- Options, in order of preference: (1) a coarser end-round encoding (the stopper needs the end within the late-stop
  margin's resolution: derive the coarsest step that keeps the late timing within that margin, e.g. the alarm says
  "ends in [k, k + step)" and stoppers take the earliest), (2) altar index bits sized to the map's altars, (3) moving
  another record's least valuable bits (e.g. Willow's ally position resolution) only if (1)-(2) are not enough, and
  say what precision it loses. Do not remove other records.
- Keep the layout identical across teammates (every instance derives it from the map and the draft alone).
- Keep everything else unchanged.

## Audit, build, smoke (before returning)
1. Spawn a **read-only** auditor subagent (general-purpose; tell it explicitly: do not edit, create or delete any
   file) with this brief and your diff (`diff -ru bots/variants/denyfix-a/src bots/variants/alarm-a/src`): layout
   determinism, overflow, every reader of the changed records, the stopper timing with the coarser end.
2. Fix what it finds.
3. Report the alarm's coverage (maps x healer/no healer) before and after.
4. Smoke (256 ladder games, release): `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-theia && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/alarm-a variants/chy-ref --no-test-draft --fuel 200000 --name mx-theia-t12-smoke`.
   Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Report win rate and OOF. Run long commands in the
   background; while waiting, keep working or block on a bounded wait, and do not end your turn until you hand back:
   ending your turn ends your run. Delete your replay batches when done.

## Stop condition
Return (SubagentHandback) when alarm-a builds, passes the audit and the smoke, or by 20:45 UTC (check `date -u`)
with whatever is finished. No 10k-game A/Bs, no tuning. Save the diff against chy-ref as
`research/mx-theia/patches/alarm-a.diff` and against denyfix-a as `alarm-a-vs-denyfix-a.diff`.
