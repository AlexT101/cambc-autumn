# T4 `prem`: one Prism premium wherever the Prism is paid

You are an implementation subagent for THEIA, the orchestrator of a macro refactor of our Cambridge Battlecode bot
`charybdis` (C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-theia` (branch
`mx-theia-20261113`). Do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`. Another implementer works in
`bots/variants/chase-*`: leave those alone.

Read first: `/home/ubuntu/wt/mx-theia/AGENTS.md`, `cambc-rules.yaml` (engine-verified rules), and the sources named below.

## Setup
- Reference bot (never edit): `bots/variants/chy-ref` (= charybdis 529).
- `cd /home/ubuntu/wt/mx-theia && ./copybot variants/chy-ref variants/prem-a` (never copy `.cambc/`).
- Build: `cd bots/variants/prem-a && cambc build` (debug) / `cambc build --release`. Debug output only inside
  `debug_block({ ... });` (plain printf changes the game).

## Why
charybdis's last big gain (CASTOR, CHANGES 527 in research/hyperion/CHANGES.md, ~+3) came from pricing consistency:
a gem in the Prism's bag adds 1.5 Focus and compounds (Prism duels go to the bigger bag; the first Prism to die loses
89% of games), so every decision must price a gem the Prism will receive with one function, `prism_premium`
(economy/capture.cc). An audit found three places where the allocation (who gets paid) and the pricing disagree:

1. **Monolith.** farm.cc farm_turn `keep_bonus` (~line 1031) returns 0 on `G.has_monolith`, so neither the Prism nor
   its feeders price the premium on a Monolith. But `sole_capture_holder` (capture.cc ~421-460) has no Monolith
   exclusion, so a Prism on a cleared Monolith may still be its sole holder, while `prism_carries`/`prism_takeover`
   (~915, ~938) and the funnel exclude Monoliths. Measured (1,019 mirror games): Monoliths are on 31% of maps and
   captured in 13% of games; of 88,700 Monolith gems the Prism received only 21%, allies 79%, 300 of 388 captures by
   one holder. A 200-gem Monolith in the Prism's bag is +300 Focus; in an ally's it is 200 face-value gems.
2. **Health cliff.** `keeps_bag` (capture.cc ~161) and its copies (`fit_on` ~316, `leave_for_prism` ~571,
   `prism_carries` ~918, farm.cc ~2118 and ~2359) zero the premium while a Prism is below `hurt_health_fraction`
   (0.453), but `keeps_gems`/`retaining_gems` (bank.cc ~905) keeps the bag at any health. The rules give +1.5 Focus a
   gem at any health; health changes only the bag's death risk until the next heal. (Measured: the Prism spends 2.7%
   of alive rounds r<=600 in [0.109, 0.453) of max health, 2.5 stretches a game of ~10 rounds: rare.)
3. **Dominance.** `prism_dominant` (capture.cc ~469, Focus >= 2x every enemy Prism) disables only one branch of
   `leave_for_prism` (~568); `holder_value`, `sole_capture_holder` and the feeders' `keep_bonus` pay a dominant Prism
   the full premium.

Prior evidence: C7 v2 (research/mac13-castor/NOTES.md) added a "threatened Prism gets no premium" cut and lost 1.3
points: cutting the premium on a risk proxy loses; consistency wins.

## Design
Make the allocation and the pricing agree, deriving every rule from who is paid at payout:
- **Monolith**: the Prism is paid on a Monolith exactly when it is among the holders at payout. Allow the premium on
  a Monolith in `keep_bonus` for the Prism (its expected share of the payout: whole while `sole_capture_holder` would
  pick it, else its `holders()` split, using whatever capture.cc already exposes for that) and for feeders on a
  Monolith the Prism claims; and let the hand-over paths (`prism_carries`, `prism_takeover`, `leave_for_prism`)
  treat a cleared Monolith like any other group, so that a Prism within reach of a cleared Monolith collects it.
  Keep `G.gems >= short_by` (a winning capture) excluded. Check the Monolith crew logic (farm.cc crew_hold/crew_cap,
  mono_contested) still works: crews clear a Monolith together; only the payout's holder changes.
- **Health**: replace the cliff in the premium (not in the holder fitness for holding a contested tile) by a
  continuous survival factor of the bag. Keep it simple and derived: e.g. scale the premium by the health fraction
  above the safe-recall line, or exp(-hazard x rounds to the next heal) if a per-round hazard is already available in
  bank.cc (`carrier_hazard`). Keep `prism_hold_threatened` for enemies in sight. If you find the cliff is load-bearing
  somewhere (e.g. it keeps a hurt Prism from holding into camp damage), keep it there and say so.
- **Dominance**: decide one way and apply it everywhere `prism_premium` is read: either fold `prism_dominant` into
  `prism_premium` (premium 0 when dominant) or drop the special case in `leave_for_prism`. Choose by the rules: a
  dominant Prism's extra Focus still raises its kill speed, but the duel is already won; state your reasoning. If
  unsure, drop the special case (one less rule).
- Keep `keep_most` a sound upper bound for every prune (it is the premium at one gem): check every SIMD/pre-bound
  that reads it, and that Monolith groups enter the bounds correctly.
- Leave the draft, emblems, combat and everything else unchanged.

Build two variants so THEIA can attribute the effect: `prem-a` = all three; `prem-m` = Monolith only (copy prem-a
and revert 2 and 3, or build it first and extend). Save diffs to `research/mx-theia/patches/prem-a.diff` and
`prem-m.diff`.

## Tracing
`debug_block` lines: `PREMM <round> <handle> <group> <premium> <share>` when a Monolith gets a premium in keep_bonus;
`PREMH <round> <handle> <factor>` when the health factor is below 1 for the Prism's own farm.

## Audit, build, smoke (before returning)
1. Spawn a **read-only** auditor subagent (general-purpose; tell it explicitly: do not edit, create or delete any
   file) with this brief and your diff (`diff -ru bots/variants/chy-ref/src bots/variants/prem-a/src`), asking it to
   check the change against the design and the rules: prune-bound soundness, Monolith crews and holders, every reader
   of keeps_bag / prism_premium / prism_dominant, Cassi/Issac and Willow, fuel.
2. Fix what it finds.
3. Smoke each variant: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-theia && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/prem-a variants/chy-ref --no-test-draft --fuel 200000 --name mx-theia-t4-smoke-a`
   (256 ladder games; same for prem-m with `-m`). Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Report
   win rate and OOF counts (a smoke, not a read: do not iterate on it). Run long commands in the background; while
   waiting, keep working or block on a bounded wait (e.g. a foreground `until` loop checking the log), and do not end
   your turn until you hand back: ending your turn ends your run.

## Stop condition
Return (SubagentHandback) when both variants build, pass the audit and the smoke. No 10k-game A/Bs, no constant
tuning, no other changes. Report what you changed (files, functions), the auditor's findings and your fixes, the smoke
results, and anything in the design you found wrong or risky.
