# astraeus: the draft memory and the draft's fuel

What the draft bot computes, what it sends champions in the 1 KB draft memory, and how champions use it. This is plan
v7 (`DraftPlan::current_version` 7, [draft.h](../../bots/astraeus/src/draft.h) and
[draft.cpp](../../bots/astraeus/src/draft.cpp)). Byte and fuel figures are from the 26-map wide bench
(`tools/fuel/bench.py --set wide`) unless a map is named.

## What limits us

- **Only the first draft turn gets the 100x fuel.** That's 10M on draft round 0; the other 2-4 draft turns get 100k
  each. Each round writes memory before picking, because writes fail after a pick (error 18). The last write happens
  before our last pick and the enemy's last pick are known; champions see the full draft.
- **Champions already know the whole map.** They run the same `StaticMap::build()`, so draft memory is only worth
  spending on:
  1. results of searches champions can't afford, with small answers;
  2. things needed in the first turns, before champions finish warming up;
  3. facts that let champions skip work they would otherwise do;
  4. plans that must agree across champions (shared memory is only 8 bytes).
- **Champions pay to decode on their first turn,** which has 200k fuel and is already near it. A Rice-coded value
  costs ~80-150 fuel to decode and a fixed-width read less. Host calls cost a flat price, so sending what rebuilds
  data with a few fields or floods is cheap, while a table decoded up front is not (1,000 values ~100k). Sections a
  champion doesn't need while building the static map are read lazily, at first use.
- **The draft's budget is host calls.** A full field costs 2.5-5k on 50x50 and 25-70k on 100x100; a radius-8 shadow
  cast ~270.

## Layout

One bit stream over all 1024 bytes, least significant bit of each byte first: an 80-bit header, then four sections in
a fixed order. A section champions decode while building the static map follows the one before it; a section read
lazily starts at an offset in the header (0 means absent). Each section takes what is left of the stream when the
draft writes it, and never assumes a size.

### Header (80 bits, `PlanHeader`)

| Field | Bits | Meaning |
|---|---:|---|
| `check` | 16 | `plan_check()`: a hash of `current_version` and the map (size, group count, first ally spawn tile), never 0. Unwritten memory reads 0, no plan; another version or map is rejected but for a 1 in 65535 chance |
| `field_layers` | 14 | The deepest field the draft computed, for champions' fuel estimates |
| `steps` | 1 | The steps section is in |
| `mirrored` | 1 | Every group has a mirror group, and enemy steps are coded from its ally steps |
| `spawn_offsets` | 1 | The steps hold each ally spawn tile's offsets |
| `tributes_walked` | 1 | Every tribute tile is off the camp tiles and walkable from our first spawn tile with every camp standing |
| `dash_spawn_steps` | 1 | A dash's static walls give every group the same steps from each ally spawn tile as the drafted spawn steps |
| `dash_altar_steps` | 1 | The same for the drafted altar steps |
| `dash_steps` | 1 | The dashers' steps follow the leads |
| `rice` | 3 x 3 | Rice parameter of the ally, enemy and altar steps |
| `attack_groups` | 8 | Leading groups whose members' attack tiles are in |
| `wards_at` | 13 | Bit offset of the ward section |
| `leads_at` | 13 | Bit offset of the leads |

### Sections

| # | Section | Read | Bytes |
|---|---|---|---|
| 1 | Steps | at static-map build (enemy steps on first ask) | with 2: 21-228 (median ~66) |
| 2 | Attack tiles | indexed on first use, up to the group asked for | (with 1) |
| 3 | Leads, then dash steps | round 1's farm | leads 4.5-10.5; dash steps 0 on 16 maps, 8-49 on the other 10 |
| 4 | Ward tiles | first ward decision at a site | 7-53 (median 20) |

**Free space:** 747-984 of the 1024 bytes on the bench maps. The tightest map known is gen-dense-camps-120105502 (98
groups, 3 dashers), whose dash steps take 235 bytes and leave 82 free.

**When space runs out**, in priority order:
- Steps that don't fit drop the whole plan.
- Attack tiles stop at the last group that fits (`attack_groups`).
- The leads and dash steps are written only if the whole ward section still fits after them. A ward site cut from the
  plan changes play; leads and dash steps change only fuel.
- Ward sites past the end of the stream read as no ward, and only sites that fit are searched.

In every case champions compute what is missing, which costs fuel, never correctness.

## The sections

### 1. Steps

- **Contents:** walking steps to each camp group's centre from our spawn, from theirs and from the tribute tiles of
  every altar. Per group, Rice-coded: 0 for unreachable, else steps + 1 less a Chebyshev lower bound (`steps_bound`:
  the spawn's box from either spawn, 0 from the altars).
- **Symmetry:** with `mirrored`, a group's enemy steps are the zigzag of their difference from its mirror group's ally
  steps.
- **Spawn tiles:** with `spawn_offsets` (up to 16 ally spawn tiles), per group reachable from our spawn: 1 bit if
  every spawn tile's extra steps match `spawn_offset`'s no-wall guess, else 2 bits a tile.
- **Champions:** `decode_steps` runs when the static map is built ([world.cpp](../../bots/astraeus/src/world.cpp));
  enemy steps are decoded on first ask (`decode_enemy_steps`). Read through `StaticMap::drafted_*`, `ally_steps` and
  `enemy_steps` in pathing.cpp (altar and spawn steps, attack slots, farm warm-up) and the farm. Decode costs 8.3k mean
  (20k max).

### 2. Attack tiles

- **Contents:** a bit per member of every group, by group: 1 if a bush tile within range 3 sees it. Then for each
  flagged member in the first `attack_groups` groups, a bit per open bush tile in its range-3 square, in
  `each_in_square`'s order.
- **Champions:** a range's attack tiles are `StaticMap::sight_off_bushes` (one shadow cast) plus those bush tiles
  within the range; range 1's are those within 1, which the draft checks. Indexed up to the group asked for (6.5k
  mean).

### 3. Leads and dash steps (at `leads_at`)

- **Leads:** for each of up to 6 bodies (our champions in id order, Cassi and Issac as two), 2 codes of
  `bit_width(groups)` bits: 0 for none, else 1 + a group the draft guesses the body's first farm choice to be,
  likeliest first.
  - The draft guesses the team from our picks so far plus its draft order for the rest (`expected_bodies`). It values
    each group per champion type from base stats (clear time and damage alone, or kiting for ranged spell casters;
    gems and gold), from that body's spawn tile. It skips groups an earlier body's first lead takes, and allows a clear
    too costly alone if shared with the strongest later body.
  - Rewritten at every draft write, since the expected team changes with each pick.
  - **Champions:** round 1's farm (`farm_turn<opening>`) visits the leads first. The loop's prunes are bounds that hold
    in any visiting order, and ties go by the usual group order, so the leads change only fuel: a good best early lets
    the rest be rejected cheaply. The first lead was the final choice for 74% of bodies.
- **Dash steps,** only with `dash_steps`: written when `dash_spawn_steps` is false on a map with crossable tiles.
  - Per body, 2 bits of dash kind (`ChampionFacts::dash_kind`, 0 for none). For a dasher: 4 bits of a spawn tile's
    index, 3 of a Rice parameter, 13 of the codes' length in bits, then per group 0 for unreachable, else 1 + the
    dash's steps from that tile less their Chebyshev distance.
  - **Champions:** a dasher decodes its own entry once instead of building a field from its spawn tile; on small maps
    (150 x groups >= the field's cost estimate) it builds the field instead.

### 4. Ward tiles (at `wards_at`)

- **Contents:** 4 bits of code width w, then w bits per ward site (each camp group, then each altar): 0 for none, else
  1 + the tile's row-major index in the site's `ward_box` (the group's camp tiles, or the altar's 3x3, widened by the
  ward range of 2 and clipped to the map). w is `bit_width` of the largest box area: 6 on most maps, 7 with a Monolith
  or big group.
- **The search:**
  - Candidates are the tiles within the ward range of a site's camp tiles or tribute tiles, minus walls, holes, altars
    and the enemy spawn.
  - Each is shadow-cast at radius 6; on a bush its own cluster is transparent (`vision.occlusion`).
  - A candidate scores the enemy-standable tiles a champion at the site's centre can't see itself: 3 each within 4 of
    the site, 1 each within 8. Ties go to the tile nearest the centre, and a site with no score gets no ward.
  - One tile per site, for the champion working there: vision is personal, so a team-wide coverage plan helps nobody
    (34 of 80 bush-ambush deaths were under a teammate's ward).
- **Champions:** `ward_planned` takes the planned tile for the current work (the claimed group, else the altar being
  waited at). It places it once within 2 with no visible allied ward there, and keeps the ward if it is already on it.
  Otherwise it falls back to `ward_bushes`. A lookup is one fixed-width read: ~250-350 fuel the first time at a site,
  ~7 after.
- **Effect:** wards 18.0 -> 28.2 a champion a game; champions never warding 18% -> 2% (27% of wards are now off
  bushes); surprise deaths 0.109 -> 0.082 a champion a game.

### Header facts that skip work

- `tributes_walked`: `altar_access`'s first build skips its flood. The walk is built later from spare fuel, or when a
  camp first changes.
- `dash_spawn_steps` and `dash_altar_steps`: dashers use the drafted steps instead of building a field from their
  spawn tile (`from_here`) and to the altars (`to_any_altar`). The draft checks them with a dash field per spawn tile
  and one from the tribute tiles; landing dashers' walls lie between dash and walking walls, so they are covered.
  Without them, dashers on maps with crossable tiles don't trust the walking steps, since a dash crosses holes and
  altars a walk cannot.

## The draft's work

`play_draft`: `analyse()`, then `write_plan`, then the pick. `analyse()` is resumable across draft turns; each part
checks `draft_reserve` (40000) plus its cost first, and a part not done is retried next draft turn. In order:

1. `StaticMap::build()` (~150k budgeted).
2. Walking fields from our spawn, theirs, every altar's tribute tiles and each ally spawn tile (up to 16); then
   `write_steps`, which checks that the stream decodes to what it computed, and the `tributes_walked` check.
3. Dash fields for the `dash_*_steps` checks.
4. Leads: per champion type, its group facts (`type_facts`), then each body's ranking.
5. Dash-step entries, when the flag check failed on a map with crossable tiles.
6. Attack tiles, per member, with the bush clusters near it (~20k a member budgeted).
7. The ward search, per site, with that site's bush clusters found under a fuel floor.

`write_plan` writes the ward section when more sites have been searched, the leads every round, then the header.

**Draft fuel:** round 0 uses 1.7M on average (3.2M max on the bench, 5.5M on the heaviest generated maps:
gen-dense-camps, gen-tiny-groups). Later draft turns use ~7k (9k max). No bench or stress run has missed a pick.

**Champion cost:** a champion's mandatory round-1 work averages ~174k at 100M fuel. At the real budget 18 of 241
round-1 turns still run out inside `decide`, mostly on heavy maps well over 200k. Play turns are unaffected.

## Not in the plan

Researched and left out; each write-up has the numbers.

| Idea | Why it's not in memory | Write-up |
|---|---|---|
| Walking distances between groups | For the farm loop's order they did no better than Chebyshev distance (49.2% of 356 head to head); the farm orders by Chebyshev from last turn's choice with no draft data | [distances.md](draft-compute/distances.md) |
| Chokepoints and dead-end pockets | Walkable pockets die at the base rate (x1.04). Off-foot islands do die x21.8, but champions already know them (`StaticMap::hops()`): hop and farm pricing, TODO 9 | [chokepoints.md](draft-compute/chokepoints.md) |
| Maze portals | Only 1 of 582 maps has a full field over ~40k; the routing stalls were the approach search's cap | [portals.md](draft-compute/portals.md) |
| Opening schedule | Strict plans lose (46.9%) and a bonus is level (51.9% of 1676): the search fits model noise, and after first contact (median round 56) the opening is fights the draft can't model. Code on branch `worktree-agent-a40911bd838aaa775` | [schedule.md](draft-compute/schedule.md) |
| Round 1's exact farm choice | Depends on `per_gold`, allies' posted claims and first moves, which the draft can't reproduce; the leads are the part that can be sent | [round1-farm.md](draft-compute/round1-farm.md) |
| A "no dash-crossable tile" flag | Only 4 of 111 dasher instances would use it | [first-turn.md](draft-compute/first-turn.md) |

## Open ideas

- **A map-aware pick:** draft choices are compiled in. Map features fed to a model fit offline (`tools/winrate`
  already values champions per map) would make them map-dependent, with no memory used: dash-crossable holes and
  altars, corridor share, bush density, camp mix.
- **More ward tiles:** a second tile per group for a second champion there, or weight towards the enemy's side.
- **Round 1 on heavy maps:** the farm loop (28k mean, 113k max; Ren keeps the plain bounds) and camp-group setup (22k)
  are the largest costs left ([first-turn.md](draft-compute/first-turn.md)).
- **Encoding rules that keep working:**
  - Use symmetry (enemy data as a difference from the mirror).
  - Send a cheap guess plus corrections.
  - Send what rebuilds data with host calls.
  - Index into sets both sides can list.
  - Rice-code sorted residuals, but keep fixed-width codes where a lookup must skip ahead.
  - Put pick-dependent data where a later 100k draft turn can rewrite it.
  - Whole-map bitmaps fit only on small maps: `import_linear_buffer` loads `(W*H+7)/8` bytes at ~1 fuel a byte.

## Background

### Rules ([cambc-rules.yaml](../../cambc-rules.yaml))

- `fuel.budget`: 100000 a turn; each bot's first turn gets 100x for the draft bot, 2x for a champion. Start-up is
  charged to the first turn; unused fuel is lost.
- `fuel.draft_exhaustion` and `draft.missed`: a draft bot that runs out after picking resumes in the next draft round.
  Running out before picking makes that pick and every later one random, and the draft bot never runs again.
- `memory.draft`: 1024 zero-initialised bytes, written in the draft, read-only in play. Each write starts at byte 0 and
  leaves bytes past its end unchanged.
- `memory.shared`: 8 bytes a team, read and written all match.
- `draft.information`: the draft bot sees terrain, spawns, altars and camp groups, no live units.
- `draft.picks`: 3-5 picks, one draft round per pick; a pick is hidden until both teams have picked that round.
- `map.symmetry_rule`: the symmetry maps team A's spawn, terrain, altars and camps onto team B's.
- `vision.occlusion` and `vision.personal`: walls and bushes block sight, holes do not; from inside a bush your own
  cluster is transparent. Each champion sees only from its own tile and its own ward.

### Fuel arithmetic

- A host search costs about 1.5k + (20 + layers) per 8x8 chunk (`search_cost_estimate` in
  [util.h](../../bots/astraeus/src/util.h)).
- Host prices (tools/README.md, 50x50): `is_set` or field get ~27, set ~16, whole-board op ~1 per chunk + 13,
  `reachable_tiles` r1-r4 70-95, `shadow_cast` r1/r4/r8 125/173/270, capped field r2/r8 ~900/1200, new bitboard ~260.
- WASM costs ~1 fuel an instruction, ~3x what the source suggests. Add ~1 per memset/memcpy byte, an allocation ~130
  plus ~290 to free, and a thrown and caught `cambc::error` ~3.9k.

### Changing the plan

- **New layout:** bump `current_version`, which the header's check covers.
- **New section:** a section decoded at static-map build goes after the steps with no offset; a lazy one gets a 13-bit
  offset in the header. It must take what is left and handle getting none. Its writer must check that what it wrote
  decodes to what it computed, as the existing writers do.
- **Fuel-only changes** (re-encoding a section): `tools/fuel/bench.py` replays must stay byte-identical. Compare round-1
  fuel too, since decoding lands there.
- **Play changes:** `py tools/ab.py` against a frozen astraeus copy (~1100 games) with matching drafts. A map-aware
  pick is invisible on test drafts, so judge it on own drafts (`--no-test-draft`). Confirm a gain on an unused suite,
  and record results in [EXPERIMENTS.md](../EXPERIMENTS.md).
