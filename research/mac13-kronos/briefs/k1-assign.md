# Brief k1-assign: nearest-claimer assignment of solo farm groups

You are implementing one macro change in the Cambridge Battlecode C++ bot `charybdis`. Read
`/home/ubuntu/wt/mac13-kronos/AGENTS.md`, `cambc-rules.yaml` (engine-verified rules) and the parts of
`docs/api/cpp.md` you need first. Work ONLY in the worktree `/home/ubuntu/wt/mac13-kronos` (branch
`mac13-kronos-20261113`); do not touch `/home/ubuntu/cambc-autumn` or any other worktree, do not commit, do not push.

## Setup
- `cd /home/ubuntu/wt/mac13-kronos && ./copybot variants/chy-ref variants/k1-assign` (never copy `.cambc/`).
  Edit only `bots/variants/k1-assign/src`. Never edit `bots/variants/chy-ref` or `bots/charybdis`.
- Off limits: `src/draft/` and emblem choices (`emblem_table.h`, which emblem is built). Leave fuel guards in place.

## Why (measured)
In 128 debug mirror games of charybdis, champions spend ~50% of alive rounds walking. Group claims are first-come:
`economy/farm.cc` treats a group an ally claims as `taken` (we become its crew, unless we claimed it first), so a
champion that decided earlier keeps a far group while a teammate standing much nearer walks elsewhere. Replaying the
farm decisions: about 42 decisions per team-game have a pairwise swap with a teammate's current claim that saves
walking, ~420 steps per team-game (~15% of all team walking). The cleared-group pick-up (`farm.cc` ~line 225, the
loop using `params::pick_up_radius`) already gives a group to the nearest claimer; live groups do not.

## The design
Make the claim of a *solo* group belong to the teammate that reaches it first, decided by the same test on both
sides so the two agree without extra comms:
1. **Steal.** In the farm loop, a group g claimed by ally B is not `taken` for us (we may pick it as our own, not as
   B's crew) when all hold:
   - g is a solo job: not a strong group / crew operation (`crew.cc` notion of strong), not a Monolith, siege, kite
     or open-plan step of B's, and not one B works as a carry for the Prism. If B is our Prism and g has gems, never
     steal (the Prism funnel). Our Prism may steal from anyone under the same test.
   - B has not begun on it: B is not within its attack range of a live member, not standing on its tiles, and the
     group has not been hit by B recently (if you cannot tell, B's distance to the group being greater than its attack
     range + 1 is enough).
   - our walk to g (the farm's own walk/ETA measure) + M < B's walk to g from B's known tile, where B's tile is its
     visible position (M = 1: we may be a round apart in turn order) or its told tile from `comms::told_ally` within
     its slack (M = 1 + slack). No known tile: no steal.
   Our own farm valuation still decides whether we want g; the change only removes the claim block.
2. **Yield.** When an ally A claims the group we claim and, by the same test seen from our side (A's known tile,
   same M, our walk), A reaches it first and we have not begun on it, we drop the claim: treat g as taken and choose
   again this turn (the farm loop's normal choice). Ties keep the claim with the lower ally index so the test is
   antisymmetric.
3. Keep everything else: crews, the Prism's 'G'/'L'/'Q' carry picks, `leave_for_prism`, sieges, help calls, open
   plan, stickiness. Comms layout unchanged.
4. Add a debug-only trace (`debug_block`, release builds print nothing) printing one line `ASN <round> <id> steal|yield
   <group>` so the firing rate can be counted in a `--debug` smoke.

Find where claims are read (`claimed_by_ally`, `taken`, `is_claimed`, `claim_most`, the pre-claim prune near line 1750
of farm.cc) and make the steal/yield test one shared helper used consistently (e.g. in `economy/capture.cc` or a small
new file added to `unity.cpp`). Keep fuel cost small: group walk fields are cached by `Pathing` (`group_walking_ready`,
`team_walk_to`); fall back to Chebyshev steps when a field is not ready, never build new fields for allies.

## Stop condition
1. It builds (`py tools/ab.py` builds it; or `cambc` build as the tools do).
2. Before returning, spawn a **read-only auditor** subagent (tell it explicitly: do not edit any file) to check the
   diff against this design and `cambc-rules.yaml` for bugs (antisymmetry of steal/yield, oscillation between two
   champions, crews/Prism-carry/siege untouched, release builds unaffected by the trace, fuel). Fix what it finds.
3. Smoke: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/k1-assign variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-k1-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`. Also one `--debug` smoke (add `--debug
   --name mac13-kronos-k1-dbg`) and count ASN lines per game (they are in the replay zips' team-a/b.stdout).
4. Write the diff to `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/k1-assign.diff`
   (`diff -ru bots/variants/chy-ref/src bots/variants/k1-assign/src`).
Return: what you changed (files, functions), the auditor's findings and fixes, smoke win % and failures, ASN
steal/yield counts per game. Do not run large A/Bs; the orchestrator does.
