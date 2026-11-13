# T8 `conceal`: start big tributes where no enemy can see them

You are an implementation subagent for THEIA, the orchestrator of a macro refactor of our Cambridge Battlecode bot
`charybdis` (C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-theia` (branch
`mx-theia-20261113`). Do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`. Leave every other `bots/variants/*` alone.

Read first: `/home/ubuntu/wt/mx-theia/AGENTS.md`, `cambc-rules.yaml` (vision: shadowcast radius 8, bushes, wards
radius 6; tribute: b = ceil(gems/10) turn ends, stun or lock cancels and the channel restarts whole; unit abilities
need a visible target; locks are placed within 2 of an altar), `docs/api/cpp.md` (bitboard::shadow_cast and its price
in tools/README.md).

## Setup
- Reference bot (never edit): `bots/variants/chy-ref` (= charybdis 529).
- `cd /home/ubuntu/wt/mx-theia && ./copybot variants/chy-ref variants/conceal-a` (never copy `.cambc/`).
- Build: `cd bots/variants/conceal-a && cambc build` (debug) / `cambc build --release`. Debug output only inside
  `debug_block({ ... });`.

## Why (measured on 1,019 chy-ref mirror games)
- The first team to start a winning-size tribute (score + bag >= 1,000) wins 93%; from that start to the end, median 45
  rounds, p75 169. Big tributes (200+ gems) are ~9 a game; the eventual winner starts 7.4 and ~1.15 complete.
- Channels an enemy saw in their first 3 rounds complete 7%; channels not seen early 49%; never seen 86%. The game's
  winning tribute was seen early in only 51% of games against 86% of all big starts. 68% of the sightings are an enemy
  champion within 8, 32% a ward or a farther champion.
- The bot's tribute decision is threat-based only: economy/bank.cc `tribute_safe` (~L153), `tribute_ok`/`any_risk`
  (~L917-930), `submit_here` (~L943), `carry_bag` (~L1566, altar choice ~L1585: nearest, or wait-then-next);
  `enemy_may_see` (capture.cc ~L323) is a radius test without line of sight.

## Design
For a tribute whose channel is long (more turns than a stun cooldown, 8: a short one completes before a seen stop can
come back), price concealment:
- For each altar's tribute tiles (within 1 of the altar, open, not occupied), the exposure of standing there for the
  channel: whether any tracked enemy (seen positions, and the unseen ones' `possible` boards in model/world, aged by
  their walk) could stand on a tile in `shadow_cast(tile, 8)` (sight is symmetric for fixed opaque tiles) within the
  channel's first turns, plus visible enemy wards within 6 (their shadow cast). Bush tiles are seen only from their own
  cluster. One host shadow_cast per candidate tile; bound the candidates (fuel).
- Choose altar, tile and start (now vs wait some rounds for an enemy to leave) by the expected rounds to complete:
  walk + channel / P(complete), with P(complete) from exposure (use the measured ~0.86 unseen vs ~0.07 seen-early as
  the two ends, or a derivation you state). Concealment is a price, not a gate: a winning tribute that cannot be hidden
  still starts when the threat logic allows.
- Apply it to the bag tributes of every body (the Prism's big bags matter most). Do not change when the bot decides to
  bank or tribute (bag size thresholds, EOQ), only where and when within that decision.
- Keep everything else unchanged.

## Tracing
`CONCEAL <round> <handle> <gems> <chosen altar x> <y> <tile exposure> <alternative exposure> <extra walk>` at each big
tribute decision.

## Audit, build, smoke (before returning)
1. Spawn a **read-only** auditor subagent (general-purpose; tell it explicitly: do not edit, create or delete any
   file) with this brief and your diff (`diff -ru bots/variants/chy-ref/src bots/variants/conceal-a/src`), asking it
   to check: sight symmetry and bush handling, the possible-board ageing, fuel (shadow_cast count per turn), waiting
   loops (a carrier that waits forever), the endgame timing guards (rounds left), Cassi/Issac.
2. Fix what it finds.
3. Smoke (256 ladder games): `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-theia && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/conceal-a variants/chy-ref --no-test-draft --fuel 200000 --name mx-theia-t8-smoke`.
   Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Report win rate and OOF counts (a smoke, not a read).
   If cheap, on ~20 debug games report how often CONCEAL chose a different altar/tile/time than the reference would.
   Run long commands in the background; while waiting, keep working or block on a bounded wait, and do not end your
   turn until you hand back: ending your turn ends your run.

## Stop condition
Return (SubagentHandback) when conceal-a builds, passes the audit and the smoke. No 10k-game A/Bs, no constant
tuning. Report what you changed, the auditor's findings and your fixes, the smoke result and risks. Save the diff as
`research/mx-theia/patches/conceal-a.diff`.
