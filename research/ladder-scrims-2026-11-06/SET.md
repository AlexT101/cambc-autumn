# Frozen scrim set v1 (2026-11-06)

Every version we scrim plays exactly these games, so two versions are compared map by map, side by side, against the
same opponent bot. `data/set-v1.json` is the machine copy (map names and platform ids); this file is its record.
Never edit v1: a changed set is v2, with its own file.

## Design

- **Pool:** the 128 published ladder maps (`cambc match-groups quota` lists them; all 128 are the ladder pool).
- **Core (40 maps):** 21 chosen by hand for the map styles local suites cover worst (one altar, home or near-spawn
  Monoliths, sunburst, huge or long maps, many altars, adjacent spawns, dash and teleport access), then 19 by
  greedy facility location over the draft lab's map features (`tools/draftlab/features.mjs`), which adds the map that
  most lowers the summed distance from every pool map to its nearest chosen map: these represent the bulk of the pool.
  Pick-count quotas 9 / 9 / 22 for 3 / 4 / 5 picks (the pool is 21 / 26 / 81). Features: log area, aspect, log
  altars, one-altar flag, Monolith flag and distance to spawn, golems, spawn distance, log gems a side, shared and
  contested camp shares, walls, bushes, holes, spawn ring, dash/teleport access, symmetry (z-scored).
  Result: 14 one-altar maps (pool 25%, here 35%), 13 with Monoliths, 8 of 70x70 or more, 4 dash/teleport.
  Scripts: `makeset.py` (selection), `homemono.mjs` (Monolith distance to spawn), `settable.py` (this table).
- **Ext (88 maps):** the rest of the pool, in a fixed shuffled order (seed 20261106), so core + ext is the whole pool.
- **Sides:** both. A group must hold five different maps, so each block of five maps is two groups: sides
  a,b,a,b,a and then b,a,b,a,b. Core is 8 blocks = 16 groups = 80 games per opponent.
  Ext is 17 blocks plus 3 maps; its last block is filled with core's first two maps (04sunburst, 03homonoliths,
  marked `filler`), which repeat core games exactly and double as determinism checks.
- **Opponents:** Intercontinental Fish and Mite (the two strongest; most of the budget), both sides of every map.
  Calibration teams play core with one side per map, alternating (8 groups, 40 games each): Vvvvv and Ad Astra
  first, NEETCoders after ext.
- **Opponent pin (ref r1):** the first group against each opponent is queued unpinned and becomes its ref;
  every later group against it passes `--source-group <ref>`, so it plays the opponent's bot from that group even if
  they submit a new one. Every version of ours therefore meets the same opponent bot on the same games, and a
  comparison between our versions is paired game by game. The refs are the `is_ref` rows of `data/events.jsonl`.
  A new ref set (`--refset r2`) is how we would measure against an opponent's newer bot.
- **Order:** per version, core against Fish and Mite (priority 50), calibration core (40), ext against Fish and Mite
  (30), the later calibration (20). Opponents alternate group by group, so a partial run stays balanced.

## Core maps, in order

| # | map | picks | size | altars | Monoliths (distance to spawn) | why |
|---|---|---|---|---|---|---|
| 1 | 04sunburst | 5 | 81x70 | 1 | - | sunburst (the ladder's invade move; EXPERIMENTS "sunfam") |
| 2 | 03homonoliths | 3 | 36x36 | 2 | 3 (1) | home Monolith (CHANGES 407; a Monolith 1 from spawn) |
| 3 | 03the_front | 5 | 61x41 | 34 | 5 (23) | 34 altars, 5 Monoliths, 1,324 gems a side |
| 4 | 00lanes | 5 | 90x30 | 18 | - | 18 altars, 90x30 lanes |
| 5 | 03one_gem | 5 | 51x41 | 2 | - | 3.5 gems a side: a tiebreak and kill map |
| 6 | 00great_wall | 5 | 50x40 | 4 | 2 (17) | 2 Monoliths, 2 golems, 702 gems, walled halves |
| 7 | 00reverse_spiral | 4 | 30x30 | 2 | - | spawns adjacent (spawn distance 0) |
| 8 | 02treasure_box | 5 | 35x35 | 1 | - | one altar, spawns 3 apart |
| 9 | 01boss_battle | 5 | 50x41 | 1 | 1 (19) | one altar and a Monolith |
| 10 | 00ambush | 5 | 100x100 | 4 | - | 100x100, dash access |
| 11 | 03ultrastarvation | 3 | 67x73 | 1 | - | one altar, dash access, 18 gems, 3 picks |
| 12 | 02the_pond | 3 | 30x30 | 2 | - | teleport access, 3 picks |
| 13 | 04spiral_moat | 3 | 31x31 | 1 | 1 (9) | one altar, Monolith 9 from spawn, 3 picks |
| 14 | 03showdown | 4 | 35x31 | 1 | 1 (13) | one altar, Monolith, 4 picks |
| 15 | 02guardians | 4 | 41x41 | 1 | 1 (18) | one altar, Monolith, 27% walls |
| 16 | adgato_gemcombat5 | 5 | 99x99 | 1 | - | 99x99, one altar, 47% holes |
| 17 | 04two_kingdoms | 5 | 85x85 | 1 | 1 (7) | 85x85, one altar, Monolith 7 from spawn |
| 18 | 02harvest | 5 | 100x100 | 6 | - | 100x100, 3 golems |
| 19 | 01starvation | 5 | 80x80 | 2 | 1 (41) | 80x80, spawn distance 182 |
| 20 | 03twisty | 5 | 90x70 | 2 | 1 (36) | 90x70, spawn distance 330 (the longest) |
| 21 | 04terraces | 5 | 91x90 | 3 | - | 91x90, 49% holes, spawn distance 181 |
| 22 | 00gem_fields | 5 | 50x40 | 4 | - | pool coverage (facility location) |
| 23 | 03colosseum | 5 | 51x51 | 1 | - | pool coverage (facility location) |
| 24 | 04wheel | 5 | 53x53 | 4 | - | pool coverage (facility location) |
| 25 | 04canyons | 5 | 61x71 | 4 | 1 (23) | pool coverage (facility location) |
| 26 | 00quarry | 4 | 35x29 | 2 | - | pool coverage (facility location) |
| 27 | 03ambush_field | 5 | 45x45 | 3 | - | pool coverage (facility location) |
| 28 | 00eight | 5 | 41x30 | 1 | - | pool coverage (facility location) |
| 29 | 04passageway | 5 | 80x30 | 2 | - | pool coverage (facility location) |
| 30 | 04hollows | 5 | 57x57 | 3 | - | pool coverage (facility location) |
| 31 | 03shrines | 4 | 35x35 | 4 | - | pool coverage (facility location) |
| 32 | 00rows | 4 | 50x50 | 2 | 1 (20) | pool coverage (facility location) |
| 33 | 04bowls | 4 | 45x41 | 3 | - | pool coverage (facility location) |
| 34 | 00rushbait_v2 | 4 | 30x80 | 2 | - | pool coverage (facility location) |
| 35 | 04courtyard | 4 | 35x33 | 3 | 1 (10) | pool coverage (facility location) |
| 36 | 02the_pack | 3 | 45x45 | 1 | - | pool coverage (facility location) |
| 37 | 00collision | 3 | 41x41 | 2 | - | pool coverage (facility location) |
| 38 | 04plaza | 3 | 28x28 | 2 | - | pool coverage (facility location) |
| 39 | 04compass | 3 | 35x37 | 1 | - | pool coverage (facility location) |
| 40 | 00breadcrumbs | 3 | 29x29 | 1 | - | pool coverage (facility location) |

## Ext maps, in order

00corners, 03reef, 00pilgrimage, 02cuts, 04braided_river, 01elk_arena, 04butterfly, 00vault, 01yellow_brick_road, 02fields, 02arena, 04horseshoes, 04sanctum, 04gap, 00galaxy, 00fragment, 04dunes, 00packs, 04comb, 01gold_rush, 04barbell, 04keyhole, adgato_gemcombat3, 03fan, 04lines, 04bridges, 00road_of_riches, 04hourglass, 00swirl, 02uncharted_lands, 04restricted_area, 04tidepools, 04pinwheel, 00split, 04atoll, 01corridors, 00monolith, 04crossroads, 01big_world, adgato_gemcombat2, 00ribs, 04duel_ring, 00elkring, 03contours, 00happy_halloween, 04waves, 04mountain_pass, 04mesas, 01broken_curve, 02stalactites, 00the_line, 00dunes, 00lost_world, 02gift_wrapping, 04orchard, 01islands, 03honeycomb, 04gem_caverns, 02tangle, 03riverbed, 01hooks, 04bullseye, 01the_farm, 00gemfight, 04gem_rush, 04fault_lines, adgato_gemcombat4, 04wilds, 02geodes, 04meander, 02crossing, 00stampede, adgato_gemcombat1, 01shortcut, 01concentrated_wealth, 00oasis, 00crater, 00contest, 01starfish, 03membrane, 02famine, 04standing_stones, 00anvil, 01fracture, 00quadrants, 00interlock, 00expanse, 04yin_yang.

## Running the set for a new version

```
cambc submit bots/<bot> --note "..."             # becomes live once built (mode: follow newest ready version)
py tools/ladder_scrims.py plan --version N --sets core --opps fish,mite --priority 100   # may use the quota reserve
py tools/ladder_scrims.py plan --version N --sets ext --opps fish,mite
py tools/ladder_scrims.py report --by side       # paired with the earlier version: same task ids but vN
```

The running job picks the tasks up by itself while version N is live; tasks of a version that is not live wait.
