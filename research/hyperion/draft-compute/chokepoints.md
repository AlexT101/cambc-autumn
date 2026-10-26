# Chokepoints, corridors and dead-end pockets (DRAFT-COMPUTE #2): stopped, no consumer

2026-10-26, branch `worktree-agent-a7dfe91794ff776d3`, on 80db5f72. **Nothing shipped and no bot code changed.** The
step-1 consumer search found that dead-end pockets reachable on foot are not where our champions die more often.
The excess is on regions that no walk reaches (crystal and dash islands). Champions already compute those regions
(`StaticMap::hops()`, `Hop::pocket`, `foot()`), so draft memory adds nothing there. Per the brief, this is the
evidence and the stop.

## Data

- Games: the `cheb-order` A/B (astraeus against astraeus, 1164 games: ladder, `maps/gen`, `maps/gen-s1`, both sides),
  `replays/batch-20261026-030537-ab-cheb-order-*`. Extracted with `tools/replay/extract.mjs --out` into a scratch
  cache.
- Self-play means both sides run our code, so every death is one of ours.
- Scripts are in [chokepoints/](chokepoints/), and each takes the extract directory:
  - `precompute.py` and `protorate.py` cache the pockets per map;
  - `rate4.py` gives death rates by class;
  - `offfoot.py` breaks down the island deaths;
  - `trace.py` prints the 15 rounds before a death;
  - `proto.py` and `showproto.py` are the detector prototype.

## Detection (prototyped in Python, not built in C++)

Walls are `blocked_for_us` (walls, holes, altars, enemy spawn), or `dash_walls` for dashers. Tiles are 8-connected
(rules: `map.corners`).

1. **Candidates.** An open tile qualifies if its shortest open run along some axis is at most 3, and blocking its 3x3
   square splits the open ring at distance 2 into at least two pieces that touch the block.
   - Diagonal neighbours across a ring corner count as adjacent.
   - The ring test matters: without it, reps land on corridor edges whose blocks cut nothing, and the spacing then
     shuts out the real cut (00pilgrimage lost both of its 350-tile rooms).
2. **Representatives.** Candidates are taken greedily, narrowest run first, at least 4 apart (Chebyshev). No ring
   tile then falls inside another rep's block.
3. **Cells.** With every rep's block closed, the cells are the components of what remains open, one host flood each.
4. **Graph and cuts.** The graph is bipartite, cells against reps: a rep is joined to each cell holding one of its
   ring tiles next to an open tile of its block.
   - Tarjan from our spawn's cell gives the articulation reps.
   - A rep is sent if all of its separated subtrees miss the enemy spawn, hold at least 4 tiles, and do not lie inside
     another sent rep's pocket (outermost only).
5. **Rebuild (champion side).** Close the 3x3 blocks of the sent cuts and flood once from our spawn. The pocket is
   `foot() & ~reached & ~blocks`, and dashers use `dash_foot()`.

This agrees with a brute-force cut test (every narrow tile blocked in turn, with an alternating BFS) on pocket rooms
and branches. It misses alcoves shallower than the rep spacing. That gap does not matter, because the brute-force
pockets the prototype misses die at the base rate (x1.01, below).

**Estimated cost (not measured, since no C++ was built):**

- Draft: ring tests in WASM at about 200 a tile, at most ~2M on a 100x100 maze and far less on open maps. One flood a
  cell. Tarjan on a few hundred nodes.
- Champion: about 100 a Rice value to decode, then one flood of 5-25k, built lazily.

**Bits on the wide bench maps** (`proto.py`):

- The section would be a cut count (Rice k=2), a 4-bit Rice parameter, delta-coded tile indexes and one bit "dash
  cuts same as walk".
- Min 8 bits (19 of 26 maps have no cut), median 8, max ~80 bits (gen-monolith-heavy, 6 cuts; gen-city, 6 cuts).
- Over the 580 A/B-suite maps, 204 have any cut, with at most 15 cuts.
- So the section would have fit with no header field after the attack tiles, or in the free `distances_at` offset.

## Why no consumer

**Champion deaths by where they died**, per champion-round alive (`rate4.py`). "Within-map" is the death count
against the map's own "rest" rate times the champion-rounds in the class.

| Class | Champion-rounds | Champion deaths | Per 1k | Within-map |
|---|---|---|---|---|
| Dead-end pocket on foot (prototype) | 300k | 126 | 0.42 | x1.42 (x1.04 with narrow tiles left in "rest") |
| Brute-force pocket on foot, not prototype | 59k | 44 | 0.74 | x1.01 |
| **Off foot** (no walk from our spawn: crystal or dash islands) | 217k | **995** | **4.59** | **x21.8** |
| Narrow tile on foot, run width 1 / 2 / 3 | 332k / 553k / 831k | 384 / 766 / 935 | 1.16 / 1.39 / 1.12 | x1.76 / x1.39 / x1.41 |
| Rest | 7.75M | 6071 | 0.78 | x1.00 |

- **Dead ends reached on foot cost 126 deaths in 1164 games.** That is about 0.05 a side a game. The excess is at
  most ~40 in all, and pockets are narrow anyway, which confounds it.
  - The trap pattern is real in traces: a hurt or outmatched champion flees out of reach into a dead end, and its
    recall is cancelled while the pursuer holds the exit (`retreat_step`'s "longer" steps).
  - But removing every such death would be noise in a ~1100-game A/B (±1.5 points).
  - The obvious consumer was to keep `retreat_step`'s longer steps out of pockets, then to have `want_home` in a
    pocket count enemies able to reach the exit before we pass it. Neither was built.
- **My first measurement was wrong, and that is a trap for the next person.** A brute-force pass that called every
  spawn-free side of a cut a pocket showed x3.1 within-map. Most of that was crystal or dash islands, which no walk
  from a spawn reaches.
  - Cuts inside such an island make its pieces spawn-free "sides". Restricted to tiles reached on foot, the excess
    vanishes (x1.01 to x1.04).
- **Corridors (narrow tiles) die at 1.4-1.8x.** Fights run along paths, and a corridor is a path, so this is
  confounded.
  - Champions can compute narrowness themselves for a few k of bitboard shifts, so it needs no draft memory either.
  - I found no decision it would change. A fight's outcome there is already priced by `stand()` and the fight sims
    with walls.

## Where the deaths actually are (for TODO 9, not this item)

The 995 off-foot champion deaths (12% of all champion deaths, from 2.2% of the time alive) fall in 84 of the 1164
games:

- **Maps:** gen-atoll 532, gen-archipelago 267, mut-the-pond 64, mut-hooks 41.
- **How the victim arrived:** crystal 588, dash 407.
- **Reach:** 731 died on dash-reachable tiles and 264 on crystal-only tiles.
- **Victims:** 572 walkers and 423 dashers.
- **Killers and bags:** killers 1/2/3+: 371/350/274. 448 carried gems.

This is TODO 9's "farm hops' pocket deaths (no retreat from a pocket)". The regions are already in `StaticMap::hops()`
(`pocket`, `landings`) and `dash_foot()`.

- A consumer would weigh the hop's exit: a recall of 5 undamaged turns, or a crystal back. It would weigh that
  against enemies who can follow, by dash over the same holes or by crystal.
- That work is in-play; it is not a draft computation.

## What I'd do next

- Off-foot regions: price in the farm and hop decisions (`cross`, `take_hop`, the farm scorer's `toll`) that leaving a
  hop region takes a recall or a crystal. An enemy that can reach the region (a dasher next to crossable tiles, or a
  carried crystal) makes the stay risky the way `stand()` prices an open fight.
- Keep this detector for #6 (a map-aware pick), where "pocket tiles" and "cut count" are features.
