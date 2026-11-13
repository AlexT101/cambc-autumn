# T11 `chip`: free damage from beyond a camp's reach while holding or waiting

You are an implementation subagent for THEIA, the orchestrator of a macro refactor of our Cambridge Battlecode bot
`charybdis` (C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-theia` (branch
`mx-theia-20261113`). Do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`. Leave every existing `bots/variants/*` alone
(another implementer works in `bots/variants/denyfix-*`).

Read first: `/home/ubuntu/wt/mx-theia/AGENTS.md` and `cambc-rules.yaml`: camps (types with range: wolf 3, elk 4,
golem 4, monolith 5, clusters never attack; "Each awake monster attacks once per camp phase ... the nearest champion of
either team within its range"; "sleeps after 2 consecutive camp phases with no champion within its own range";
"Damage ... wakes every asleep member of its group"; "Camps never regenerate"; "Monsters never move"), abilities
(ability range 4, ground spells hit a 3x3 around a target tile within 4, cooldown 8; ranged basic attack range 3).

## Setup
- Start from `bots/variants/dnw-min` (our best: chy-ref 529 + tribute denial late stops + alarm).
- `cd /home/ubuntu/wt/mx-theia && ./copybot variants/dnw-min variants/chip-a` (never copy `.cambc/`).
- Build with `cambc build` (debug) / `cambc build --release`. Debug output only inside `debug_block({ ... });`.

## Why (1,019 chy-ref mirror games)
- During its capture holds (6 rounds standing on the tile, ~65 rounds a Prism per 600) the Prism deals camp damage in
  only 5% of hold rounds; its ground slot is ready with a live group within 5 in 15% of them. Walking is half the
  Prism's capture cycle; clearing ~5-6 rounds a capture.
- economy/capture.cc `hold_capture` already hits groups that cannot hit back or are already awake (`free_hit`) and
  casts at awake groups in cast reach, but never wakes an asleep group, even one whose every member is out of reach
  of all our champions: such a group wakes, cannot attack anyone, sleeps again after 2 camp phases, and keeps the
  damage (no regeneration). That damage is free: it shortens a later clear at no walk, no camp damage and, for a slot
  that would be ready again by the next clear anyway, no lost cast.

## Design
- Extend the hold's free work (and the same at a wait by a respawning/cleared group if there is such a branch:
  `Branch::wait_altar` is not one; look for waits by camps in farm.cc / capture.cc) to asleep or awake groups whose
  every living member, once awake, has no champion of ours (nor an enemy we would make it target, irrelevant) within
  its own range: test each member's range against every visible ally tile including our own after the action, so the
  wake costs nothing. Clusters (strength 0) are already free.
- Basic attacks reach 3 (ranged) or 1 (melee); a camp with range >= our distance can always answer, so in practice the
  free targets are: ground spells on a tile within 4 whose 3x3 hits members at distance 4-5 from us out of their range,
  unit spells at distance 4 on wolves (range 3), and any hit on clusters.
- Slots: keep chy-ref's duel reservations (the unit stun is held while enemies are near: reuse the existing
  `engagement_near` / duel-gate tests). Cast a slot only if it will be ready again (8 rounds) by the time the next
  clear can use it, or if it is the ground slot and the Prism's next clear is at least 8 rounds away (hold remaining +
  walk to the next claimed or best group); keep it simple and derived.
- Prefer the group we are most likely to clear next (our claim after this hold, else the nearest by walk).
- Applies to every body, but it matters mostly for ranged casters (Prism, Stellar, ...).

## Tracing
`CHIP <round> <handle> <group> <slot or basic> <damage dealt>`.

## Audit, build, smoke (before returning)
1. Spawn a **read-only** auditor subagent (general-purpose; tell it explicitly: do not edit, create or delete any
   file) with this brief and your diff (`diff -ru bots/variants/dnw-min/src bots/variants/chip-a/src`), asking it to
   check the free-wake test (every member's range vs every visible ally, after our move), slot reservations, fuel.
2. Fix what it finds.
3. Smoke (256 ladder games, release): `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-theia && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/chip-a variants/chy-ref --no-test-draft --fuel 200000 --name mx-theia-t11-smoke`.
   Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Report win rate, OOF and, from a small debug batch,
   CHIP firings and damage per game. Run long commands in the background; while waiting, keep working or block on a
   bounded wait, and do not end your turn until you hand back: ending your turn ends your run. Delete your replay
   batches when done.

## Stop condition
Return (SubagentHandback) when chip-a builds, passes the audit and the smoke, or by 20:30 UTC (check `date -u`) with
whatever is finished. No 10k-game A/Bs, no tuning. Save the diff (against chy-ref) as
`research/mx-theia/patches/chip-a.diff` and against dnw-min as `chip-a-vs-dnw-min.diff`.
