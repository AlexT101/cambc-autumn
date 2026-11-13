# T6 `relay`: allies clear the Prism's next group while it holds

You are an implementation subagent for THEIA, the orchestrator of a macro refactor of our Cambridge Battlecode bot
`charybdis` (C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-theia` (branch
`mx-theia-20261113`). Do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`. Leave other `bots/variants/*` alone.

Read first: `/home/ubuntu/wt/mx-theia/AGENTS.md`, `cambc-rules.yaml` (engine-verified rules), and the sources named below.

## Setup
- Reference bot (never edit): `bots/variants/chy-ref` (= charybdis 529).
- `cd /home/ubuntu/wt/mx-theia && ./copybot variants/chy-ref variants/relay-a` (never copy `.cambc/`).
- Build: `cd bots/variants/relay-a && cambc build` (debug) / `cambc build --release`. Debug output only inside
  `debug_block({ ... });` (plain printf changes the game).

## Why (measured on 1,019 mirror games, chy-ref vs itself)
- The early Prism is the economy: by r150 the winner's and loser's capture gems differ only in the Prism's (107 vs 95;
  every other body equal), and the first Prism to die (duels go to the bigger bag: +1.5 Focus a gem) loses 89%.
- The Prism's capture cycle (r<=600): ~30 gems a capture; walk 14.7 rounds, clear 4.8 (6.2 before r150), hold 6.
  During its 6-round holds it stands on the tile (economy/capture.cc `hold_capture`).
- Allies deal 3x the Prism's camp damage early (13.4k vs 4.1k a team-game by r150), but only 44% of it goes to groups
  the Prism collects; 53% goes to allies' own captures (~64 gems by r150, at face value). With the Prism's premium at
  1-3 early (`prism_premium`), a gem in the Prism's bag is worth 2-4 face gems.
- Allies help clear the group the Prism is working on (they price the premium only on the Prism's posted claim,
  farm.cc `keep_bonus`, `fed_claim`), so the Prism still spends its clear rounds there; its next group is untouched
  until it walks there.

## Design: a relay
While the Prism holds a capture (and in the last rounds of a clear when its payout is certain), it decides its next
job and announces it, and the feeders' existing premium pricing applies to that group, so allies clear the Prism's
next group during its hold and walk; it arrives at a cleared (or nearly cleared) group and only holds.
- **Next job**: the Prism's farm choice evaluated from the held group's tile, excluding the held group (re-use
  farm_turn's machinery if feasible within fuel; e.g. run the farm's ranking in a mode that only records the best
  group, or keep the farm's own second-best/best-other-than-held from the turn it started the hold). Recompute at most
  once every few rounds or when the candidate becomes invalid (captured, enemy on it). Check fuel.
- **Announcement**: allies must read it. Today the Prism posts `memory.claim = held` during a hold (comms claim). Find
  the cleanest channel: e.g. post the next group as the Prism's claim during its hold if nothing else needs the held
  group's claim (check every reader of comms::claim_of: holders, yield, crews, funnel, takeovers), or add a separate
  `next` field to the comms/priority payload if bytes allow (model/comms.h, comms.cc; 8 shared bytes + priority
  payload). Explain your choice.
- **Pricing**: in farm.cc keep_bonus, a feeder prices the Prism's next group exactly like its claimed group (premium on
  the gems the Prism will be paid), as long as the Prism will arrive before the allies would capture it themselves: the
  funnel (`leave_for_prism`, capture.cc) must hand the cleared group over to the arriving Prism (it already waits up to
  `capture_time` / `worth_wait` for a near Prism: check that the Prism's hold-remaining + walk fits, and extend the
  funnel's ETA to count the Prism's remaining hold rounds when it is holding). No new magic numbers: the window is the
  Prism's remaining hold plus its walk.
- Keep everything else unchanged (draft, emblems, combat). The Prism's own farm already values pre-cleared groups.

## Tracing
`RELAY <round> <prism handle> <next group> <eta>` when the Prism announces; `RELAYC <round> <handle> <group>` when a
feeder's chosen group is the Prism's next group.

## Audit, build, smoke (before returning)
1. Spawn a **read-only** auditor subagent (general-purpose; tell it explicitly: do not edit, create or delete any
   file) with this brief and your diff (`diff -ru bots/variants/chy-ref/src bots/variants/relay-a/src`), asking it to
   check: every claim reader, prune-bound soundness (keep_most), fuel, stale announcements (Prism dead, recalled, next
   group taken), Cassi/Issac and Willow, and that the funnel hands the group to the Prism.
2. Fix what it finds.
3. Measure in a debug build on ~20 games (`--debug`): how often RELAY fires per Prism hold, and in how many of the
   Prism's next captures the group was cleared before it arrived (vs chy-ref). Then smoke the release build:
   `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-theia && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/relay-a variants/chy-ref --no-test-draft --fuel 200000 --name mx-theia-t6-smoke`
   (256 ladder games). Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Report win rate and OOF counts (a
   smoke, not a read: do not iterate on it). Run long commands in the background; while waiting, keep working or block
   on a bounded wait, and do not end your turn until you hand back: ending your turn ends your run.

## Stop condition
Return (SubagentHandback) when relay-a builds, passes the audit and the smoke. No 10k-game A/Bs, no constant tuning.
Report what you changed (files, functions), the auditor's findings and your fixes, the debug measurements, the smoke
result, and anything in the design you found wrong or risky. Save the diff as `research/mx-theia/patches/relay-a.diff`.
