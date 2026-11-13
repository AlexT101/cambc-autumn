# T3 `funnel`: allies leave near clears to the Prism for as long as its premium pays the wait

You are an implementation subagent for THEIA, the orchestrator of a macro refactor of our Cambridge Battlecode bot
`charybdis` (C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-theia` (branch
`mx-theia-20261113`). Do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`. Other implementers may be working in other
`bots/variants/*` directories: touch only your own.

Read first: `/home/ubuntu/wt/mx-theia/AGENTS.md`, `cambc-rules.yaml` (engine-verified rules; capture timing, respawn,
reward split), and the source below.

## Setup
- Reference bot (never edit): `bots/variants/chy-ref` (= charybdis 529). Your base: `bots/variants/orbit-a` (chy-ref +
  T2 "orbit": feeders price the Prism's premium on groups near it; `research/mx-theia/patches/orbit-a.diff`,
  brief `research/mx-theia/briefs/t2-orbit.md`). Never edit orbit-a.
- `cd /home/ubuntu/wt/mx-theia && ./copybot variants/orbit-a variants/orbit-b` (never copy `.cambc/`).
- Build: `cd bots/variants/orbit-b && cambc build` (debug) / `cambc build --release`. Debug output only inside
  `debug_block({ ... });`.

## Why (1,019 chy-ref mirror games, r1-600)
- Non-Prism allies capture ~125 gems a team-game in groups within 12 tiles (Chebyshev) of their living Prism without
  the Prism taking a share; half of them within 6 tiles. At their hold start the Prism was farming ('F' branch) in 63%
  of those gems, holding its own capture in 8%, tributing in 10%; an enemy was within 8 of the capturer in only 27%.
- The funnel (`leave_for_prism`, economy/capture.cc ~line 560-630) leaves a cleared group to the Prism only when
  `prism_eta` (~line 487) puts it there within `capture_time` rounds of our first sight of it cleared (the unclaimed
  `near` path), and `prism_eta` returns "past the bound" whenever the Prism is busy on a live group (it cannot time a
  clear). So whenever the Prism is clearing something, nothing near it is ever left to it.
- The rules make a wait cheap: a cleared group stays empty until captured, and its respawn timer starts only at the
  payout (camps.respawn, capture.timing), so leaving it k rounds delays its next return by k rounds: at most k/cycle
  of one capture. `worth_wait` already prices exactly that (premium x (respawn + capture) > late), but the lapse rule
  (capture_time from first sight) cuts the wait far below what the premium pays for (premium ~1-3 early: 50-200 rounds).

## Design
Make the funnel's horizon the economics it already states:
1. **Wait horizon.** In the unclaimed `near` path, replace the fixed `capture_time` lapse (both `remaining` and the
   `world.round - left.first >= capture_time` test) by W = the longest wait `worth_wait` accepts for this Prism and
   group: W = floor(prism_premium(world, a, G.gems) * (G.respawn + capture_rounds(false))), capped at G.respawn (a
   wait never costs more than one return of the group) and at least capture_time (never shorter than today). The
   lapse then runs W rounds from first sight; `prism_eta`'s bound is W minus the rounds already waited.
2. **Timing a live clear.** In `prism_eta`, when the Prism's task h is a live group (alive, not cleared), estimate
   its rounds to finish instead of returning bound + 1: h's remaining health (world.camps[h].health summed over live
   members, or the members' max health if unseen/respawning) over the summed camp_output of the allies claiming h (the
   Prism included; `crew_output`/`camp_output` in economy/camps.cc and crew.cc), then its hold
   (capture_rounds(a.fast_capture) - 1), then the walk on from h to g. Respawning h stays past the bound.
3. **Keep the safety gates.** Unchanged: no leave with an enemy in sight (`enemy_seen`), to a dominant or hurt Prism,
   for a winning bag, near the end of the game, on a Monolith; a lapsed leave is not resumed.
4. **The Prism comes.** Check the Prism's own farm prices a cleared group left to it as the cheap job it is (no
   clear; walk + hold): confirm that a cleared, unheld gem group near a keeping Prism is picked without further change,
   and if a test or prune keeps it out (e.g. `left_for_prism` itself, `ally_holding`, claims), fix that so the left
   group is collectable. Do not add a separate "go collect" system: it must come out of the farm's pricing.

5. **Orbit consistency (T2's auditor flagged these).** Make the orbit's q match what the funnel can deliver:
   anchor on the Prism's recent tile first (`recent_tile`, the tile the funnel's prism_eta measures from), its
   claimed group's centre only as a fallback; and q = 0 off the Prism's claimed group while `enemy_seen(world)` (the
   funnel leaves nothing then). Keep q <= 1 so keep_most still bounds it.

Leave alone: the draft, emblems, holders' value pricing, every other system.

## Tracing
`debug_block` lines: `FUNNEL <round> <handle> <group> <W> <eta> <decision>` when the near path decides on a group
whose eta came through a live clear or whose wait exceeded capture_time; `FUNNEL-TAKE <round> <prism handle> <group>`
when a Prism captures a group left to it.

## Audit, build, smoke (before returning)
1. Spawn a **read-only** auditor subagent (general-purpose; tell it explicitly: do not edit, create or delete any file)
   with this brief and your diff (`diff -ru bots/variants/orbit-a/src bots/variants/orbit-b/src`), asking it to check
   the change against the design and the rules for bugs: the wait arithmetic (premium is 0 when the Prism does not
   keep its bag), the lapse bookkeeping in `left_for_prism` (LeftRecord), the live-clear estimate (units: health over
   output per round; division by zero; unseen health), prism_eta's per-round cache and its `bound` semantics, every
   caller of leave_for_prism / left_for_prism / prism_eta and whether a longer leave can deadlock (ally waits, Prism
   never comes, group never captured).
2. Fix what it finds.
3. Smoke: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-theia && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/orbit-b variants/chy-ref --no-test-draft --fuel 200000 --name mx-theia-t3-smoke`
   (256 ladder games). Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Report win rate and OOF (a smoke,
   not a read: do not iterate on it). Run long commands in the background (no foreground sleep loops).
4. One `--debug` smoke (add `--debug --name mx-theia-t3-dbg`) and count FUNNEL / FUNNEL-TAKE lines per game from the
   replays' team-?.stdout (zip members), to confirm leaves happen and Prisms collect them.

## Stop condition
Return when orbit-b builds, passes the audit and the smoke. No 10k-game A/Bs, no constant tuning, no other changes.
Report what you changed, the auditor's findings and fixes, the smoke results and trace counts, and anything in the
design you found wrong or risky. Save the diff as `research/mx-theia/patches/orbit-b.diff` (against orbit-a) and
`orbit-b-full.diff` (against chy-ref).
