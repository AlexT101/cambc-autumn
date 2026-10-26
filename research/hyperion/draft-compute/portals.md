# Maze portals (DRAFT-COMPUTE #3): not built; the stalls were a search cap

2026-10-26, branch `worktree-agent-a77d68b4423eaf3af`, on 3b2677b3. **No portal section was built and the plan
layout is unchanged** (v4; `distances_at` stays 0, 0 bits on every map). Step 1 found that almost no suite or ladder map
has a full field above ~40k. The routing failures it found had another cause: the approach search's uninformed cap
of width + height is shorter than the real walk on two winding maps, so a champion stalled there all game. That cap
is fixed (commit a1e19f2a, `Pathing::walk_cap`), and it reads level. Portals would only matter on maps much larger
and more winding than any in the pool: 80-94 tile serpentines, whose fields cost 100-140k. Per the brief, this is the
evidence and the stop.

Scripts are in [portals/](portals/):
- `fieldcost.mjs`: each map's deepest field and its estimated price;
- `shortcuts.py`: SHORTCUT lines by map and kind;
- `stuck.py`: champion-games with many routing shortcuts;
- `perbot.py`: routing shortcuts and stalls per bot in an A/B;
- `genmaze.sh`: the maze suite's candidates.

## Step 1: how big is the problem

### Field prices

`fieldcost.mjs` labels walking distances (walls, holes, altars and the enemy spawn block; camps don't, as in
`blocked_for_us`) from every farmed group's centre and from our spawn. It prices the deepest of these by
`search_cost_estimate` (4000 + chunks x (20 + layers)).

| Set | Maps | Deepest field > 40k | > 30k |
|---|---|---|---|
| ladder (`maps/`) | 70 | 0 | 3 (01big-world 36.8k, 02tangle 32.6k, 02harvest 31.4k) |
| `maps/gen` | 256 | 0 | 2 (gen-dense-camps-120105502 39.2k, mut-big-world 36.8k) |
| `maps/gen-s1` | 256 | 1 (gen-gem-centre-120205105 48.9k) | 1 |

- The median map's deepest field is 8.7k.
- The suites' maze-like presets (maze, labyrinth, serpentine, spiral, tunnels, caves, dungeon, cells) are 30-80 tiles,
  and none of their fields costs over 21k.
- The 100x100 "~70k maze" in DRAFT-COMPUTE's arithmetic does not occur in the pool.

### Routing fallbacks in play

The `cheb-final` A/B (astraeus against astraeus, 1164 games, debug builds) prints SHORTCUT lines:

| Kind | Lines |
|---|---|
| crow-flies-farm | 11,285 |
| static-descend | 2,515 |
| farm-no-route | 2,110 |
| farm-kept-target | 632 |
| siege-route-fuel | 331 |
| **total** | 16,873 |

- **10,282 (61%) come from 4 games on 2 maps:** gen-s1/gen-gem-centre-120205105 and gen/gen-dense-camps-120105502,
  the two costliest fields in the pool. Each is 9 champion-games, and 6 of them hold over 1,000 lines each: one
  champion repeats crow-flies-farm every turn of the game.
- **The other 6,591 lines are spread thin.** Of 4,199 other champion-games, none has 50 or more; overall that is
  ~0.15% of champion turns, transient fallbacks, not stalls.
- The ladder's worst is adgato-gemcombat5, with 163 lines in 2 games and no stall.

### What the stall is

On gem-centre, team B's Vesper Vale stood at (43,4) for 1,900 turns, aiming at group 12 at (24,87).
- With no field bounding the walk (no centre field yet, the spawn field not built because the plan carries the steps,
  and the champion off its spawn), `approach_steps` is -1. `search_approach` then caps the search at width + height
  = 180 layers.
- The walk is 221 (dense-camps: 210 against a cap of 170), so the search failed every turn. Each failure cost ~31k.
- `step_closer` then stepped into a crow-flies local minimum.
- The ~31k a turn also kept warm_centres from ever building the centre field that would have unstuck it
  (`centres_ready` stayed 0 all game).
- `approach_steps` also clamped known steps to width + height, which fails the same way.

### How those maps' results differ

The stalling side was fixed by the map, so the side decided both maps:
- gem-centre: team A won both games;
- dense-camps: team B won both;
- a local replay ended 1012-110 in gems.

A mirror A/B hides this: each bot wins one of the two games. Two maps of 582, 4 games of 1164, cannot move an A/B.

## Method: the fix instead of portals

- `Pathing::walk_cap()` is width + height until an approach search with no bound on the walk is cut off at it. A
  search is cut off when its layer count reaches the cap, as opposed to running dry. The cap then doubles, up to
  width x height.
- `approach_steps` clamps to it, and `approach_cost` and `prepare_approach`'s fuel check use it in place of width +
  height.
- No fuel gate was added.
- On maps where width + height always suffices, nothing changes.

## Bits per map

0. There is no new section and no header change.

## Fuel

- **Before:** a stalled champion spent ~31k a turn on a search that could not succeed (its estimate was
  `search_cost_estimate(166)` = 30.8k, at 144 chunks).
- **After:** one search is cut off at 180 layers (~30k). The next, capped at 360, stops on reaching us at 221 layers
  (~38k). That approach field is then kept for the walk (`approach_ready`).
- Elsewhere the code is unchanged. Out-of-fuel turns in the A/B: CAND 4,606, REF 4,566.

## A/B

Against astraeus at 3b2677b (`bots/variants/astraeus-3b2677b`), both on their own drafts:

| A/B | Games | CAND win % | 95% CI |
|---|---|---|---|
| `walkcap`, full (ladder 48.6, gen 50.8, gen-s1 50.4) | 1164 | 50.3 | 47.5-53.2 |
| `walkcap-maze`, 48 generated winding maps | 96 | 50.0 | 40.2-59.8 |

- **Full suite.** CAND has no stalled champion-games (300+ routing shortcuts); REF has 2, both on its stalling side.
  - dense-camps: CAND won both games, against a fixed side winner before.
  - gem-centre: team A still won both, so its home side is stronger anyway.
- **Maze suite.** The suite is `genmaze.sh`'s 195 candidates at 80-100 tiles, ranked by deepest field / (width +
  height), top 48: 15 serpentines, plus chambers, maze, labyrinth and tunnels.
  - Crow-flies-farm lines fell from 22,780 (REF) to 8,263 (CAND).
  - Stalled champion-games fell from 17 to 8.

## What is left, and where portals would apply

- **What stays stalled.** CAND's remaining stalls are all on serpentines of 87-94 tiles with fields of 600-1,100
  layers (83-140k). Once walk_cap passes ~600 layers, `prepare_approach`'s estimate (over 90k plus the 10k floor) never
  fits a turn. A centre field capped at its group's spawn steps should cost about as much, so warm-up likely never builds one
  either (not traced).
- **What would fix them.** This is the case HPA*-lite is for: a route made of pieces, each a capped field that fits
  a turn. The draft could send waypoints along the corridor, and champions descend capped fields between them.
- **Why it wasn't built.** No ladder or suite map comes near it:
  - the ladder's deepest field is 200 layers (02tangle);
  - the suites' serpentines are 31-52 tiles, with fields of 15.8k at most.
- **Smaller gains not taken.**
  - A distance estimate from the plan (e.g. the drafted spawn steps) would let the first uninformed search skip its
    cut-off try. One wasted search per map is not worth the code.
  - Pricing the uninformed search at the lesser of the cap and a full field would change fuel decisions on open
    maps too: a broad play change.
