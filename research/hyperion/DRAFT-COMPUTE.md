# astraeus: spending the draft's 10M fuel, and the 1 KB draft memory

A plan (2026-10-26). The draft bot's first turn gets 100x fuel (10M). The plan is already compact (v3, CHANGES 150), so
most of the 1 KB is free. This covers what is worth computing with the rest of the fuel and how to fit the results into
those bytes. Numbers for the new items are estimates from host-call prices; none of them has been run.

## What limits us

- **Only the first draft turn gets the 100× fuel.** That's 10M on draft round 0; the other 2–4 draft turns get 100k each. Each round has to write memory before picking, because writes fail after a pick. The last write happens before the enemy's last pick is known; champions see the full draft.
- **Champions already know the whole map.** They run the same `StaticMap::build()`, so the draft can't tell them anything they couldn't compute. Draft memory is only worth spending on:
  1. results of searches champions can't afford (hundreds of thousands of fuel or more), with small answers;
  2. things needed in the first ~10 rounds, before champions finish warming up;
  3. plans that must agree across champions (shared memory is only 8 bytes).
- **The draft's budget is host calls, not instructions.** 10M instructions of plain loops isn't much; 10M of host calls is a lot:
  - A full distance field costs about 2.5–5k on 50×50 maps and 25–70k on 100×100 (70k on mazes). That's roughly 150–400 fields on a big map and 2,000+ on a small one.
  - A radius-8 shadow cast is about 270, so the vision of every tile on a 100×100 map is about 2.7M.
- **The draft uses 0.2–1.2M of the 10M today** (bench maps).
- **Champions pay to decode what we send, on their first turn.** It has 200k, and warm-up already spills past it. Decoding in WASM costs about 100 fuel per Rice-coded value and about 100 per listed tile. Host calls cost a flat price, so rebuilding from a few tiles with fields, floods or shadow casts is cheap. A table of numbers decoded up front is not: 1,000 values cost ~100k.

## The plan today (v7)

- **Contents:**
  - steps to each camp group from our spawn, theirs and the altars;
  - each ally spawn tile's extra steps;
  - attack tiles at ranges 3 and 1 for every camp member;
  - each body's two guesses at its first farm choice (leads), and a dasher's dash steps from its spawn tile (v7,
    CHANGES 163; [round1-farm.md](draft-compute/round1-farm.md)).
- **Encoding:** one bit stream over all 1024 bytes: an 80-bit `PlanHeader` (CHANGES 155, 160, 163), then Rice-coded residuals. The layout is in the `DraftPlan` and `PlanHeader` comments in [draft.h](../../bots/astraeus/src/draft.h).
- **Size:** 12–219 bytes after the header on the bench maps (median ~60; measured on v3), so ~800–1000 of the 1024 are typically free.
  - The largest, gen-chambers-102106111 at 219, is mostly spawn-tile offsets that miss their no-wall guess (~34 bits a group). A better guess there is the cheapest saving if bytes get tight.
  - Worst cases are unbounded: ~10 bytes a group plus ~6 a camp member. Steps that don't fit drop the whole plan; attack tiles that don't fit stop at the last group that fits. Either way champions compute the rest, which costs fuel, never correctness.
  - New sections must therefore use whatever space is left at draft time, in priority order, and never assume a fixed size.
- **Champion cost:** ~+10k on the first turn on average (v3 +11k; v4's buffered reader -1.3k). Decoding the steps is 4–34k (~80 a value); the rest indexes attack tiles. Play turns are flat.

## What to compute with the freed fuel and bytes

| # | Computation | Draft fuel | Bytes | What it fixes |
|---|---|---|---|---|
| 1 | Walking distances between camp groups (details below) | 1–5M (one field per group, half of them) | ~200–400 | TODO #1, the farm loop (44k a call on 132 groups): champions prune by walking distance with no fields |
| 2 | Chokepoints, corridors and dead-end pockets (details below) | ~0.5M | ~100 | TODO #6: lone champions picked off in tunnels. Also fight and retreat positioning |
| 3 | Maze portals (HPA*-lite), only on maps where a full field costs more than ~40k (details below) | 1–3M | ~150 | TODO #9: "the target's field never fits a turn" |
| 4 | A global ward plan (details below) | ~1–2M | ~40 | Wards are now a local greedy choice among nearby bushes ([bot.cpp:2810](../../bots/astraeus/src/bot.cpp#L2810)) |
| 5 | A coordinated opening schedule for the team (details below) | Whatever is left (anytime) | ~100–200 | Per-turn greedy farming; this is the only item that genuinely soaks up 10M |
| 6 | A map-aware pick | Reuses features from #2–#4 | 0 | Probably the biggest lever; uses no memory at all |

Details for the rows that need them:

- **#1 Group distances.**
  - Send residuals over Chebyshev distance, and only half by symmetry. On 100+ group maps, send a walking-distance tour order plus each group's nearest neighbours instead.
  - Decoding is the risk. 50 groups is ~1,225 pairs, ~120k to decode up front. So make entries fixed-width and read them on demand, or decode one row when it's first needed.
  - **Outcome (2026-10-26):** drafted walk orders for the farm loop did no better than the same order by Chebyshev distance (49.2% of 356 head to head), so only the Chebyshev order was kept (CHANGES 157) and `distances_at` stays 0 ([distances.md](draft-compute/distances.md)).
- **#2 Chokepoints.**
  - One multi-source field from the walls gives each tile's clearance. Narrow points along the middle of corridors are the candidate cuts; a capped field around each one checks that blocking it splits the map.
  - Send only the cut tiles. Champions rebuild the region graph themselves: the regions are the connected pieces of the open tiles once the cuts are blocked, one flood each.
  - Add one flag bit per region: dead-end pocket, or long narrow corridor.
  - **Outcome (2026-10-26):** stopped at the consumer search: walkable dead-end pockets die at the base rate (x1.04). 12% of deaths are on off-foot islands reached by dash or crystal (x21.8), regions champions already know (`StaticMap::hops()`), so that is hop and farm pricing (TODO 9), not draft memory ([chokepoints.md](draft-compute/chokepoints.md)).
- **#3 Maze portals.**
  - Send the portal tiles. Champions measure portal-to-portal distances with cheap capped fields (~1.2k each), then search the small portal graph.
  - On normal maps a host field already beats any search written in our own code. So I would not build HPA* in general, only for mazes.
  - **Outcome (2026-10-26):** not built: only 1 of 582 maps has a full field over ~40k. The stalls were the approach search's width + height cap, fixed instead (CHANGES 158, [portals.md](draft-compute/portals.md)).
- **#4 Ward plan.**
  - Shadow-cast every candidate ward tile at radius 6, then do a weighted coverage search over what matters: enemy routes to our camps, contested groups, altars and chokes.
  - Send an ordered list of ward tiles, coded as offsets from a group or altar (~8 bits each).
  - The same visibility data gives "stealth lanes", routes that stay out of sight of the enemy's side.
  - **Outcome (2026-10-26):** built as one ward tile per camp group and altar for that site's champion (sight is personal, so not a team-wide plan): 52.1% of 1164, 52.5% of 512 on an unused suite; plan v5 (CHANGES 159, [wards.md](draft-compute/wards.md)).
  - **Ward sight in play (2026-10-26):** already in every decision; comms now post the sighting a teammate lacks soonest (CHANGES 162): level, 49.4% of 1164, ceiling ~2% of deaths ([ward-sight.md](draft-compute/ward-sight.md)).
- **#5 Opening schedule.**
  - We know our own picks. Kill times come from champion stats and the camps' health; travel comes from #1. Simulated annealing assigns champions to clears, respawn windows and tribute trips over roughly the first 150–300 rounds.
  - Predict the enemy as our own bot mirrored. That gives first-contact groups and times.
  - Send each champion's sequence of group indices.
  - The farm scorer should treat the schedule as a bonus, not a script, so the bot still follows the rules-derived direction and falls back to greedy when the plan breaks.
  - **Outcome (2026-10-26):** built and not merged (branch `worktree-agent-a40911bd838aaa775`, f96ea98a). The enemy had to be our greedy farm reacting to us (plans tuned against a mirror lost 12.7% in the model). Calibrated before first contact (timing error 9-10 rounds), but plans followed strictly lost (45.4%, then 46.9% of 1164) and the bonus was level (51.9% of 1676 pooled, 49.0% on an unused suite). The search fits model noise: +26% predicted, -3.4% gems in real games. After contact (median round 56) the opening is fights and heal trips, which the draft cannot model without the enemy's picks ([schedule.md](draft-compute/schedule.md)).
  - **Round 1's farm loop (2026-10-26):** the draft cannot carry the first choice exactly (`per_gold`, allies' posted claims and first moves), so it sends each body's two leads and dashers' spawn steps, and round 1 visits the leads first and prunes by bounds exact in any order: plan v7, fuel only (52/52 identical; round 1 -2.7%, play turns +0.01%; CHANGES 163, [round1-farm.md](draft-compute/round1-farm.md)).
- **#6 Map-aware pick.**
  - Draft choices are compiled in today. Map features fed to a model fit offline would make them map-dependent; `tools/winrate` already values champions per map. Useful features: count of holes and altars a dash can cross (dash value), share of corridor tiles, bush density, camp mix, chokepoint count.

## Encoding ideas

- **Use symmetry.** Anything about the enemy's side is the mirror of ours: v3 sends enemy steps as differences from the mirror group's. A whole board mirrors with one host call (`Reflect`, ~1 fuel a chunk).
- **Send a cheap guess plus corrections.** The draft can afford to run the champion's own cheap rule everywhere and send only where it is wrong. For example, run "capped field plus greedy step towards the target" from every region to every target, and send detour waypoints only where it gets stuck.
- **Send what rebuilds the data, not the data,** especially when host calls do the rebuilding. For example, send the cut tiles and let champions find the regions by flooding.
- **Index into sets both sides can list.** For example, "the 37th bush tile" or an offset from a camp member costs far fewer bits than a 14-bit coordinate.
- **Delta-code sorted tile lists with Rice codes.** That gets close to the theoretical minimum. I'd skip arithmetic coding.
- **Add a header of section offsets.** Each map then spends its bytes where they're worth the most: portals only on mazes, matrices only on maps with few groups. Offsets also let champions decode a section only when they first need it.
- **Whole-map bitmaps fit on small maps only.** `import_linear_buffer` loads a bit-packed board, `(W*H+7)/8` bytes, at ~1 fuel a byte: 113 bytes on 30×30, 313 on 50×50, 1,250 on 100×100. The SDK comment's "one byte per tile" is wrong (`probe-shadowcast`).
- **Put pick-dependent data first.** A write starts at byte 0 and leaves the rest alone, so a later 100k draft turn can rewrite just a short front section, chosen from variants computed in round 0.

## Next

1. **The two items that hit open TODOs, judged by `ab.py`:** the group distances (#1) and chokes and pockets (#2), with the section-offset header.
2. **Then the ambitious two:** the opening schedule (#5) and the map-aware pick (#6).

## Background

### Rules this rests on ([cambc-rules.yaml](../../cambc-rules.yaml))

- `fuel.budget`: 100000 a turn; each bot's first turn gets 100x for the draft bot, 2x for a champion. Start-up is
  charged to the first turn; unused fuel is lost.
- `fuel.draft_exhaustion`: a draft bot that runs out after picking resumes in the next draft round. Running out before
  picking makes that pick and every later one random, and the draft bot never runs again (`draft.missed`).
- `memory.draft`: 1024 zero-initialised bytes, written in the draft, read-only in play. Each write starts at byte 0 and
  leaves bytes past its end unchanged.
- `memory.shared`: 8 bytes a team, read and written all match.
- `draft.information`: the draft bot sees terrain, spawns, altars and camp groups, no live units.
- `draft.picks`: 3–5 picks, one draft round per pick; a pick is hidden until both teams have picked that round.
- `map.symmetry_rule`: the symmetry maps team A's spawn, terrain, altars and camps onto team B's.
- `vision.occlusion`: walls and bushes block sight; holes do not. Sight is symmetric for a fixed set of opaque tiles. A
  bush tile cannot be seen from outside; from inside, your own cluster is transparent and other clusters are not.
- `vision.shadowcast_radius`: a shadow cast's tiles within r are the same at any radius of at least r, and always include
  the clear neighbours of its origin.

### The current draft code

- [draft.cpp](../../bots/astraeus/src/draft.cpp) `play_draft`: `analyse()` (resumable across draft turns, keeping
  `draft_reserve` = 40000), then `write_plan`, then the pick. The write comes first because a pick ends the turn's
  actions (later writes fail with error 18), and the draft bot may not run again after its last pick.
- `analyse()`: `StaticMap::build()` (~150k budgeted); fields from our spawn, theirs, every altar's tribute tiles and each
  ally spawn tile (up to 16); `write_steps`; then per member `find_bush_clusters` and `write_attack_tiles` (~20k a
  member budgeted). Both writers check that what they wrote decodes to what they computed.
- Layout: `DraftPlan` in [draft.h](../../bots/astraeus/src/draft.h), `current_version` 7: one 1024-byte bit stream.
  Its first 80 bits are `PlanHeader`: a 16-bit check (a hash of the version and the map's size, group count and first
  spawn tile; 0 is no plan), `field_layers` 14, `steps` / `mirrored` / `spawn_offsets` 1 each, the plan facts
  `tributes_walked` / `dash_spawn_steps` / `dash_altar_steps` 1 each (CHANGES 160), `dash_steps` 1 (the dash steps
  follow the leads, CHANGES 163), three 3-bit Rice parameters, `attack_groups` 8, and 13-bit offsets `wards_at` (the
  ward section, #4) and `leads_at` (the leads, where the attack tiles end; CHANGES 163) for lazily read sections (0:
  absent). After the attack tiles: the leads (6 bodies x 2 x `bit_width(groups)` bits, rewritten at every draft
  write), then with `dash_steps` per body a 2-bit dash kind and, for a dasher, a 4-bit spawn tile, 3-bit Rice
  parameter, 13-bit length and a Rice code per group, then the wards. The leads and dash steps are placed only if the
  whole ward section still fits after them. Sections decoded at build follow one another (the attack tiles start where the steps end); a lazy one
  gets an offset. `PlanWriter` and `PlanReader` (a buffered 57-bit window) read and write it. A new layout must bump
  the version, which the check covers.
- Consumers:
  - `decode_steps` runs when the static map is built ([world.cpp:1001](../../bots/astraeus/src/world.cpp#L1001)). A champion ignores a plan whose header check differs from `plan_check` (another version or map, but for a 1 in 65535 chance).
  - `StaticMap::drafted_*` and `ally_steps` / `enemy_steps` ([world.cpp:707-790](../../bots/astraeus/src/world.cpp#L707-L790)) are read in [pathing.cpp](../../bots/astraeus/src/pathing.cpp) (altar steps, spawn steps, attack slots, farm warm-up) and [bot.cpp:2463](../../bots/astraeus/src/bot.cpp#L2463) (spawn steps in the farm).
- Dashers skip the draft's walking steps on maps with crossable tiles (CHANGES: `draft_spawn_graph`, dashers' own
  `to_any_altar()` field), since a dash crosses holes and altars a walk cannot, unless `dash_spawn_steps` /
  `dash_altar_steps` say a dash field gives the same steps (CHANGES 160). Routing data sent for #1 or #3 is for
  walkers unless it is computed on `dash_walls` too.

### Fuel arithmetic

- A host search costs about 1.5k + (20 + layers) per 8×8 chunk ([util.h](../../bots/astraeus/src/util.h)
  `search_cost_estimate`). 100×100 is 169 chunks: ~120 layers on an open map is ~25k; ~400 layers on a maze is ~71k.
- Host prices (tools/README.md, 50×50): `is_set` or field get ~27, set ~16, whole-board op ~1 per chunk + 13 (~180 on
  100×100), `reachable_tiles` r1–r4 70–95, `shadow_cast` r1/r4/r8 125/173/270, capped field r2/r8 ~900/1200, new
  bitboard ~260.
- WASM costs ~1 fuel an instruction, and the stack machine needs ~3× the instructions the source suggests. Measured
  costs: a Rice value ~100, a 7×7 bitboard popcount ~450. Add ~1 per memset/memcpy byte, an allocation ~130 plus ~290
  to free, and a thrown and caught `cambc::error` ~3.9k. So the search in #5 needs cheap inner moves over a
  precomputed distance matrix, with no host calls or allocations per move.
- So whole-board host ops beat WASM for map-wide work and lose for a few tiles.

### Where champion fuel goes ([FUEL-PROFILE.md](FUEL-PROFILE.md))

Out-of-fuel turns are almost all fight turns inside `decide` (fight sims, the strike search, `Reach`). Their
terrain-only tables are per tile (`TableQueue`, ~6k a tile on 100×100), far too big to send, so the draft cannot cut
fight fuel directly. Its gains are in farming, routing and positioning (TODO #1, #6, #9) and in the first turns'
warm-up. Bush clusters, once the biggest warm-up cost on bushy maps (~89k a champion on 00ambush), are now labelled
in one pass (CHANGES 151).

### Testing, per AGENTS.md

- Fuel-only changes, such as re-encoding a section: `tools/fuel/bench.py` replays must stay byte-identical. Compare
  round-1 fuel too, since decoding lands there.
- Everything else changes play: `py tools/ab.py` against a frozen astraeus copy (~1100 games), with matching drafts. A
  map-aware pick (#6) is invisible on test drafts, so judge it on own drafts (`--no-test-draft`).
- Confirm a gain on an unused suite (`node tools/mapgen/mapgen.mjs suite`), and record the results in
  [EXPERIMENTS.md](../EXPERIMENTS.md).
