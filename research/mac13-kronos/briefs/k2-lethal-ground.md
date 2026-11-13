# Brief k2: enemy ground priced by how lethal the enemy is (two probe variants)

You are implementing probe variants of the Cambridge Battlecode C++ bot `charybdis` for the orchestrator of its macro
refactor. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md`, `cambc-rules.yaml` and what you need of `docs/api/cpp.md`.
Work ONLY in `/home/ubuntu/wt/mac13-kronos`; do not touch `/home/ubuntu/cambc-autumn` or other worktrees; do not commit.
Never edit `bots/variants/chy-ref` or `bots/charybdis`. Off limits: `src/draft/`, emblem choices.

## Why
The farm discounts groups toward the enemy spawn by a static weight (`economy/camps.cc` `home_ground`:
`min(1, 2 d_enemy / (d_ally + d_enemy))^home_power`, home_power 1.89) and prices the middle band at `mid_exposure`
(`economy/farm.cc` `exposure_of`). Both are fixed over the game. But the cost of standing on enemy ground is the
chance of being killed there, and that changes over the game: early the enemy Prism's burst (stun 1.5x Focus +
ground 1x Focus, Focus 90 + 1.5 a carried gem) is a fraction of our health, kills by round 300 are ~1 a game, and
late a Prism one-shots anything. In mirror games the team whose Prism has 1.5x the other's bag at round 300 wins 80%
(25% of games), and that Prism got twice the capture gems, 3x as many from mid and enemy-side groups. Prior probes
of the static weight all game: home_power 0 lost 2.2 points, x0.5 level. Hypothesis: the discount should scale with
the enemy's lethality, near zero early, full late.

## Variants (each a copy: `./copybot variants/chy-ref variants/NAME`, never copy `.cambc/`)
1. `k2-leth`: a lethality factor L in [0,1], computed once per turn from our beliefs: L = min(1, B / H) where H is
   our own max health and B the largest burst any living enemy champion could put on us in one exchange, from its
   believed stats (the world model's enemy beliefs: strength, focus, abilities' damage multipliers; for each enemy:
   two basic attacks plus every damage ability's multiplier x its Focus; use what `safety` or `combat` already
   computes if there is a ready helper, otherwise this formula). Enemies never seen use their base stats plus, for a
   Prism, the Focus its bag would give at the enemy team's tributed+estimated capture pace if the code has such an
   estimate, else base. Apply it where the farm uses the home weight w and the mid band m: w' = 1 - L (1 - w),
   m' = 1 + L (m - 1) (so with L = 0 every group weighs 1, with L = 1 as today). Do it at use time (the home weight
   is cached per group; keep the cache, scale where it is read). Keep every prune bound valid: bounds that assume a
   weight of at most 1 or at most `exposure_most` must still hold (w' <= 1, m' <= m).
2. `k2-early`: the same scaling but with L a fixed ramp by round: L = 0 up to round 100, rising linearly to 1 at
   round 300, 1 after. (A control for whether the lethality reading matters or only the phase.)
Add a debug-only trace (`debug_block`) printing `LETH <round> <id> <L>` every 50 rounds so the factor can be checked.

## Stop condition
1. Both build. 2. Spawn a read-only auditor subagent (tell it explicitly not to edit anything) to check both diffs
against this brief and the rules (prune bounds, every reader of the weight, cached values, fuel); fix what it finds.
3. Smoke each: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/NAME variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-NAME-smoke`
(256 ladder games): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. One debug smoke of k2-leth (`--debug --name
mac13-kronos-k2-dbg`) to read the LETH values at r50/150/300/600 (median over games).
4. Save diffs to `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/NAME.diff`
(`diff -ru bots/variants/chy-ref/src bots/variants/NAME/src`). Return what changed, auditor findings and fixes, smoke
results and the LETH medians. Do not run dev A/Bs.
