# T2 `orbit`: allies farm where the Prism can collect

You are an implementation subagent for THEIA, the orchestrator of a macro refactor of our Cambridge Battlecode bot
`charybdis` (C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-theia` (branch
`mx-theia-20261113`). Do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`. Another implementer is working in
`bots/variants/front-*`: leave those alone.

Read first: `/home/ubuntu/wt/mx-theia/AGENTS.md`, `cambc-rules.yaml` (engine-verified rules), and the source below.

## Setup
- Reference bot (never edit): `bots/variants/chy-ref` (= charybdis 529).
- `cd /home/ubuntu/wt/mx-theia && ./copybot variants/chy-ref variants/orbit-a` (never copy `.cambc/`).
- Build: `cd bots/variants/orbit-a && cambc build` (debug) / `cambc build --release`; ab.py builds too. Debug output only
  inside `debug_block({ ... });` (plain printf changes the game).

## Why
- charybdis's economy is Prism-centred: a Prism gains 1.5 Focus a carried gem, and the team's gems go to its bag
  (CHANGES 507: +6.8 vs ocean; CASTOR's consistent premium pricing, CHANGES 527: ~+3 more). A fit of 1,023 mirror
  games: at equal team totals, a Prism share of team gems 10 points higher wins 58-61% (r200-400). CASTOR's premium
  raised the share from ~0.51 to ~0.57; its gain ran through the Prism duel.
- The premium reaches the feeders' (non-Prism allies') target choice only for the one group the Prism claims
  (economy/farm.cc farm_turn, `keep_bonus`, ~line 1013-1040: `fed_claim[i] == g`). Every other group an ally might
  clear is priced as if its gems stay with the ally, even when the Prism is next to it and the funnel
  (`leave_for_prism`, economy/capture.cc ~line 600) would hand it to the Prism on the clear. So the allies' choice and
  the funnel disagree: allies spread to groups the Prism cannot collect, and their gems are banked at face value.

## Design: the Prism's orbit
Price, in each feeder's farm choice, the premium on every group the Prism ally can collect, weighted by how likely it
is to collect it. The team's territory then forms around its carry without any rule telling allies where to go: groups
near the Prism are worth more to feeders (its premium), groups far from it are worth their face value.

- In farm_turn's feeder branch, build `fed_by` from every alive keeping Prism ally (prism_premium(world, a, 1) > 0),
  not only claiming ones. For each, an anchor: the centre of its claimed group (comms::claim_of >= 0, a group index),
  else its recent tile (`recent_tile` in capture.cc: seen or posted within 2 rounds), else none.
- `keep_bonus(G)` off Prism = max over fed Prisms a of prism_premium(world, a, G.gems) * q_a(g), where
  q_a(g) = 1 if g is a's claimed group; else, with d = Chebyshev(anchor, G.centre) and R = carry_reach()
  (2 x capture_time: the walk a Prism makes while a capture counts down twice, the funnel's own reach):
  q = 1 for d <= R, falling linearly to 0 at d = 2R, and 0 with no anchor.
- q <= 1 everywhere, so `keep_most` (the premium at one gem, over fed Prisms) still bounds every group's bonus and the
  prunes stay sound: check this, and that `keep_most` now includes non-claiming Prisms.
- Same guards as today: no bonus on a Monolith, on a capture that wins (G.gems >= short_by), or when the Prism does not
  keep its bag (prism_premium returns 0 then). Not while `prism_dominant(world, a)` holds (the funnel does not leave
  groups to a dominant Prism, so its premium would not be collected): q = 0 then except on its claimed group.
- Leave the Prism's own pricing (the `keeper` branch), leave_for_prism, the holders, the draft, emblems, and every
  other system unchanged.

## Tracing
One `debug_block` line per feeder turn whose chosen group got a non-zero q from a non-claimed group:
`ORBIT <round> <handle> <group> <q> <premium>`.

## Audit, build, smoke (before returning)
1. Spawn a **read-only** auditor subagent (general-purpose; tell it explicitly: do not edit, create or delete any file)
   with this brief and your diff (`diff -ru bots/variants/chy-ref/src bots/variants/orbit-a/src`), asking it to check
   the change against the design and the rules for bugs: prune-bound soundness (keep_most, bound_tribute, any SIMD
   pre-bounds that read keep_most), caching (the kept group facts hold no premium: confirm), index ranges, the
   anchors (claims are group indices, tiles may be stale or off-map), Cassi/Issac and Willow as feeders.
2. Fix what it finds.
3. Smoke: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-theia && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/orbit-a variants/chy-ref --no-test-draft --fuel 200000 --name mx-theia-t2-smoke`
   (256 ladder games). Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Report win rate and OOF counts (a
   smoke, not a read: do not iterate on it). Run long commands in the background (no foreground sleep loops).

## Stop condition
Return when orbit-a builds, passes the audit and the smoke. No 10k-game A/Bs, no constant tuning, no other changes.
Report what you changed (files, functions), the auditor's findings and your fixes, the smoke result, and anything in
the design you found wrong or risky. Save the diff as `research/mx-theia/patches/orbit-a.diff`.
