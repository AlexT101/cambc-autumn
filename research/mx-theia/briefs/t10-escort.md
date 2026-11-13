# T10 `escort`: allies guard our winning tribute

You are an implementation subagent for THEIA, the orchestrator of a macro refactor of our Cambridge Battlecode bot
`charybdis` (C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-theia` (branch
`mx-theia-20261113`). Do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`. Leave every existing `bots/variants/*` alone
(read them freely); another implementer works in `bots/variants/denyfix-*`.

Read first: `/home/ubuntu/wt/mx-theia/AGENTS.md`, `cambc-rules.yaml` (tribute: b = ceil(gems/10) turn ends, damage
does not interrupt, a stun cancels and the channel restarts whole; locks within 2 of an altar cancel every tribute
there and block the other team's; five basic attacks remove a lock; unit stuns need a visible target within 4;
stuns remove the target's next turn; vision), and `bots/variants/deny-a` vs `chy-ref` (`research/mx-theia/patches/deny-a.diff`).

## Setup
- Start from `bots/variants/deny-a` (= chy-ref 529 + scylla's tribute denial; our current best, 50.8 pooled held-out).
- `cd /home/ubuntu/wt/mx-theia && ./copybot variants/deny-a variants/escort-a` (never copy `.cambc/`).
- Build with `cambc build` (debug) / `cambc build --release`. Debug output only inside `debug_block({ ... });`.

## Facts (deny-a vs chy-ref, 1,000 dev games; mirror chy-ref vs itself, 1,019 games)
- The first team to start a winning-size tribute (score + bag >= 1,000) wins 93%; median 45 rounds from that start to
  the end (p75 169).
- Our winning channels against chy-ref: 381 completed, 2,170 stunned and 786 locked by chy-ref, 688 cancelled by us.
  chy-ref stops at once (~20% into the channel), so each stop costs us ~20% of a channel plus the restart, and every
  restart gives the enemy time (when it starts its own winning tribute first we win only ~14%).
- economy/altar_guard.cc already holds the altar with our strongest bodies on one-altar maps while one of us carries a
  winning bag; on multi-altar maps nothing guards our tribute.

## Design
While one of our bodies carries a winning bag (score + bag >= 1,000) and is walking to or channelling at an altar:
- The channeller's altar is the guarded site (announce it in comms if the existing records do not already let allies
  infer it: the bag record, the claim, the camp record; the deny-a alarm record may be reused for our own tribute).
- Allies within a reach derived from the channel's remaining turns (they must arrive before it ends) converge on the
  site and screen it: they prefer tiles between the channeller and the enemies' likely approach (seen enemies, and the
  `possible` boards of unseen ones), they prioritise stunning or killing any enemy that comes within stun range (4) or
  lock range (2) of the channeller/altar (the strike search's priorities), and they break enemy locks on that altar.
- Reuse altar_guard.cc's machinery where it fits (extend it from one-altar maps to the channeller's altar), rather
  than a parallel system. The Prism, if it is not the channeller, joins the screen (its stun is the strongest), unless
  its own winning bag is the channeller.
- Do not change when or where the bot tributes; only the allies' behaviour while a winning tribute is pending.
Build `escort-a`.

## Tracing
`ESCORT <round> <handle> <site x> <y> <turns left> <role>`.

## Audit, build, smoke (before returning)
1. Spawn a **read-only** auditor subagent (general-purpose; tell it explicitly: do not edit, create or delete any
   file) with this brief and your diff (`diff -ru bots/variants/deny-a/src bots/variants/escort-a/src`).
2. Fix what it finds.
3. Smoke (256 ladder games, release): `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-theia && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/escort-a variants/chy-ref --no-test-draft --fuel 200000 --name mx-theia-t10-smoke`.
   Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Report win rate and OOF (a smoke, not a read). If
   cheap, on a debug batch report our winning channels' outcomes (completed / stunned / locked) vs deny-a's (script:
   `research/mx-theia/scripts/winchan.py <extract dir>`; extract with `node tools/replay/extract.mjs <batch> --threads 32 --out <dir>`).
   Run long commands in the background; while waiting, keep working or block on a bounded wait, and do not end your
   turn until you hand back: ending your turn ends your run. Delete your debug replay batches when done.

## Stop condition
Return (SubagentHandback) when escort-a builds, passes the audit and the smoke, or by 20:15 UTC (check `date -u`)
with whatever is finished. No 10k-game A/Bs. Report what you changed, the auditor's findings and your fixes, the smoke
result and risks. Save the diff (against chy-ref) as `research/mx-theia/patches/escort-a.diff`.
