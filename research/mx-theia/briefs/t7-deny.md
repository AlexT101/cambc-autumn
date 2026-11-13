# T7 `deny`: port scylla's tribute denial into charybdis

You are an implementation subagent for THEIA, the orchestrator of a macro refactor of our Cambridge Battlecode bot
`charybdis` (C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-theia` (branch
`mx-theia-20261113`). Do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`. Another implementer works in
`bots/variants/relay-*`: leave those and every other variant alone.

Read first: `/home/ubuntu/wt/mx-theia/AGENTS.md`, `cambc-rules.yaml` (engine-verified rules: tribute, lock, stun,
wards), research/ideas-2026-11-12/vfish/README.md section "Wave 2, kill" and research/hyperion/CHANGES.md entry 526.

## Setup
- Reference bot (never edit): `bots/variants/chy-ref` (= charybdis 529). Source of the port: `bots/scylla` (= charybdis
  525 + a Vesper line + the denial), whose denial is `research/ideas-2026-11-12/vfish/patches/kill.patch` (against
  scylla's m1, i.e. 525-based). chy-ref has moved on since 525 (CHANGES 527-529: Prism premium, Willow medic, Prism
  shop timing, NYX value-placed wards, 528, 529): port the denial onto chy-ref's code, do not copy scylla files.
- `cd /home/ubuntu/wt/mx-theia && ./copybot variants/chy-ref variants/deny-a` (never copy `.cambc/`).
- Build: `cd bots/variants/deny-a && cambc build` (debug) / `cambc build --release`. Debug output only inside
  `debug_block({ ... });`.

## Why (measured on 1,019 chy-ref mirror games)
- Big tributes (200+ gems) are ~9 a game; the eventual winner starts 7.4 and only ~1.15 complete. chy-ref stops only
  *winning* tributes it *sees*, and stops them *at once*: stun cancels come a mean 18 turns into channels of ~93 turns
  (64% in the first fifth), after which the channel restarts whole (rules: b = ceil(gems / 10) turns; a stun or a lock
  cancels; the gems stay carried; no refund). Channels never seen complete 86%.
- In scylla vs charybdis 525 the package was worth +4 (33.3 -> 37.5 on 4,080 games; 35.6 on 20,400 fresh): late stops
  (in the channel's last turns) multiply the time the enemy wastes per stop by ~5; stopping at once instead read 29.9
  vs 38.4. The watch ward and the alarm were each worth 1.5-3.

## Design: the five pieces, adapted
- `deny_late`: time every stop (the existing winning-tribute stop `stop_game_ender` / `stoppable_winning_tribute` /
  `game_ender` in combat/fight.cc, and the new hoard stops) for the channel's last turns: stop when the turns left
  minus our stop's walk is at most 1 + the living enemy stunners (scylla's margin; it is derived from the rules: each
  living enemy stunner can stun our stopper once in that window).
- `deny_alarm`: a seer posts the altar and the channel's end round in the shared bytes so teammates out of its sight
  walk in time. chy-ref's 8 shared bytes are used (model/comms.h: bags, claims, camp record, ally tile): fit it in the
  layout if you can without breaking what is there, as scylla did or otherwise (priority payload?); if it cannot fit,
  leave it out and say so.
- `deny_watch`: one teammate (the last pick that is not the Prism, a linked body or a healer) leaves its ward for good
  beside the altar nearest the enemy spawn. Merge with chy-ref's NYX value-placed wards (bot.cc ward placement): that
  body's ward goes to the watch, the others keep NYX's placement.
- `lock_first`: the lock is bought before shards (economy/shop.cc), as scylla does (a lock is a consumable, not an
  emblem: allowed).
- `deny_hoards`: a tribute of at least half of what the enemy still needs (and longer than a stun's cooldown) is
  stopped as a winning one is, by any body but our Prism holding a lock or a stun. In the mirror, a stopped
  non-winning hoard stays as Focus in the enemy Prism's bag (+1.5 a gem): build `deny-a` with it on and `deny-b` with
  `deny_hoards` off (everything else on), so THEIA can attribute it. Our Prism keeps chy-ref's behaviour (it still
  stops winning tributes as today; it is not sent after hoards).
Keep everything else unchanged (draft, emblems, farm).

## Tracing
`DENY <round> <handle> <altar x> <altar y> <turns left> <kind>` when a stop is made or planned; scylla's traces if they
exist.

## Audit, build, smoke (before returning)
1. Spawn a **read-only** auditor subagent (general-purpose; tell it explicitly: do not edit, create or delete any
   file) with this brief, the scylla patch and your diff (`diff -ru bots/variants/chy-ref/src bots/variants/deny-a/src`),
   asking it to check the port against scylla's behaviour and chy-ref's newer code: comms layout collisions, NYX ward
   interplay, the stop timing arithmetic (turn ends, the turn order within a round, our walk), the Prism exemption,
   lock purchase, fuel.
2. Fix what it finds.
3. Smoke each variant (256 ladder games): `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-theia && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/deny-a variants/chy-ref --no-test-draft --fuel 200000 --name mx-theia-t7-smoke-a`
   (and `-b`). Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Report win rate and OOF counts (a smoke,
   not a read: do not iterate on it). If cheap, on ~20 debug games report the share of the enemy's channel run before
   our cancels (should move from ~0.25 to ~0.65). Run long commands in the background; while waiting, keep working or
   block on a bounded wait, and do not end your turn until you hand back: ending your turn ends your run.

## Stop condition
Return (SubagentHandback) when both variants build, pass the audit and the smoke. No 10k-game A/Bs, no constant
tuning. Report what you changed (files, functions), what of scylla's package you could not port and why, the
auditor's findings and your fixes, the smoke results, and risks. Save diffs as `research/mx-theia/patches/deny-a.diff`
and `deny-b.diff`.
