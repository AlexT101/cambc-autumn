# T1 `front`: dynamic territory in charybdis's farm target choice

You are an implementation subagent for THEIA, the orchestrator of a macro refactor of our Cambridge Battlecode bot
`charybdis` (C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-theia` (branch
`mx-theia-20261113`). Do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`.

Read first: `/home/ubuntu/wt/mx-theia/AGENTS.md`, `cambc-rules.yaml` (engine-verified rules), `docs/api/cpp.md`
as needed, and the source below.

## Setup
- Reference bot (never edit): `bots/variants/chy-ref` (= charybdis 529).
- Make your copies: `cd /home/ubuntu/wt/mx-theia && ./copybot variants/chy-ref variants/front-a` and, once front-a
  works, `./copybot variants/front-a variants/front-b` for the second variant (below). Never copy `.cambc/`.
- Build check: `cd /home/ubuntu/wt/mx-theia/bots/variants/front-a && cambc build` (debug) or `cambc build --release`;
  ab.py builds them too. Debug output via `debug_block({ ... });` only (plain printf changes the game).

## Why (measured on 1,019 mirror games of chy-ref)
- The winner's capture edge is almost all contested ground: captured gems own side 817 vs 747, mid 309 vs 151, enemy
  side 164 vs 86, Monolith 451 vs 201 a game.
- Champions spend ~1% of alive time on the enemy side (spawn-distance ratio < 0.4), and still only 3.3% while half or
  more of the enemy team is dead. Enemy-side supply goes 93-96% unused.
- The cause is in the farm's group weight: `home_ground()` (economy/camps.cc) is static: weight =
  min(1, 2*from_them/(from_us+from_them))^home_power, from_us / from_them = walking steps from our / the enemy spawn.
  It never learns who is alive or where the enemies are, so territory never moves.

## Design: the front
Replace the static enemy-distance term in the farm's side weight by the enemy team's live presence, so the territory
boundary moves with deaths and sightings. The formula and its tuned power stay; only `from_them` becomes dynamic:

- For each enemy champion e (world.enemies), its effective arrival steps at group g:
  - dead: max(0, e.respawn_earliest - world.round) + map.enemy_steps(g) (static enemy-spawn walk, as now).
    Rules: a champion that died in round D respawns at D+60/61 with full health on its own spawn.
  - alive and seen within the last `fresh` rounds (world.round - e.pos_round <= fresh, `fresh` = 8: the rounds an
    enemy needs to walk out of our sight radius of 8): min(prior, max(0, cheb(e.pos, g.centre) - (round - pos_round))),
    prior = map.enemy_steps(g). A recent sighting can only bring the enemy closer than the prior.
  - otherwise (alive, unseen or stale): prior = map.enemy_steps(g).
- from_them_live(g) = min over enemies of those arrival steps (every enemy can kill a lone farmer; keep it a plain
  min). If the enemy team has no champions (cannot happen) fall back to the prior.
- weight_live(g) = the same formula as home_ground with from_them_live in place of from_them; still in [0, 1].
  With every enemy alive and unseen it equals today's home_ground exactly (that must hold: check it).

### Variant front-a: enemy presence only (the above).
### Variant front-b: front-a plus our support
- from_us_live(g) = min(map.ally_steps(g) [static, as now], min over *other* alive allies a with a posted claim c
  (comms::claim_of(world, a.index) = c >= 0, a group index) of cheb(groups[c].centre, g.centre)). An ally working a
  group next to g makes g home ground: the team's ground is where its farmers stand, not only its spawn. Use claims, not
  positions: a claim is where the ally will be, and is posted every turn.
- weight_live uses both from_us_live and from_them_live.

## Where it plugs in (economy/farm.cc farm_turn and economy/camps.cc)
- `known.home = home_ground(map, g, opening)` (farm.cc ~1856) is cached in `group_facts[g]` under `known.context`; the
  weight multiplies `known.gems`/`known.gold` and is reused while the context holds. The live weight changes from turn
  to turn: recompute it per turn (cheap: <= 5 enemies x Chebyshev) and make the cached facts follow it (e.g. fold a
  per-turn weight version into the context check, or apply the live/static ratio outside the cache). Keep the Monolith
  rule (`weight *= known.home` again) with the live weight.
- The pre-facts prunes bound worth with the weights read so far (`home_weights()` in camps.cc, `known_weights()` /
  PreUpper in farm.cc, ~line 412 and ~1676/1745). Those bounds must stay true upper bounds: a live weight may be higher
  than the static one (an enemy dead), so the bound table must hold the live weight (or 1) for every group the loop
  can price this turn. A prune that skips a group whose live weight rose is a bug. Prefer correctness over fuel: we
  test at 2x fuel.
- The opening (first turn, `opening` instance) has every enemy alive at spawn: live == static there; leave it alone.
- Leave alone: `home_side()` and the mid-band `exposure()` (mid_exposure stays static), the comeback pull, the draft
  (`draft/`), emblem choices, every other system.
- Add a cheap per-turn cache: compute the live weights for all groups once per turn (a small static array by group,
  keyed by round) and read them in the loop.

## Tracing
Add one `debug_block` trace line per turn when any live weight differs from static (e.g. `FRONT <round> <handle>
<n groups changed> <max ratio>`), for later replay study. debug_block compiles out of release builds.

## Audit, build, smoke (before returning)
1. Spawn a **read-only** auditor subagent (general-purpose; tell it explicitly: do not edit, create or delete any file)
   with this brief and your diff (`diff -ru bots/variants/chy-ref/src bots/variants/front-a/src`), asking it to check
   the change against the design and the rules for bugs: prune-bound soundness, cache invalidation, units, dead/unseen
   enemy handling, index ranges (groups >= 256), the equality with static when nothing is known.
2. Fix what it finds.
3. Smoke each variant (from the worktree root):
   `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-theia && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/front-a variants/chy-ref --no-test-draft --fuel 200000 --name mx-theia-t1-smoke-a`
   (256 ladder games). Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Report the win rate and OOF counts
   (it is a smoke, not a read; do not iterate on it). Run long commands in the background (no foreground sleep loops).
4. Optional, if cheap: one `--debug` smoke of front-a to confirm the FRONT trace fires (dead enemies open the map).

## Stop condition
Return when both variants build, pass the audit and the smoke. Do not run 10k-game A/Bs, do not tune constants,
do not start other changes. Report: what you changed (files, functions), the auditor's findings and your fixes, the
smoke results, and anything in the design you found wrong or risky. Save the diffs as
`research/mx-theia/patches/front-a.diff` and `front-b.diff` (`diff -ru` against chy-ref's src).
