# A champion's first turn: where its fuel goes (2026-10-26, astraeus)

A champion's first turn gets 200k fuel and pays for start-up. On the wide bench (26 maps, test drafts, both sides,
241 champion instances) 61 first turns ran out at the real budget. This is what that turn spends before the warm-up,
and the byte-identical cuts made to it. The draft plan's decode and attack-tile index were left alone (plan v4 is
rewriting them).

Baseline: f3f47ea (copied to `bots/variants/ft-base`). Bench: `tools/fuel/bench.py run <bot> --set wide --test-draft
--per-map --jobs 7`, at 100M and at the real budget (`--fuel 0`). Profiles: the same bench on a copy with
`debug_fuel` on and `FuelMeter`s around each phase (~170 fuel a meter; the loops inside farm use cheaper laps of
~15). Profiled numbers are therefore a few k high on both sides; the round-1 totals below are unmetered.

## Results

All six commits are fuel-only: **52/52 replays identical at 100M** against the baseline.

| | before | after |
|---|---:|---:|
| Round 1, real budget: mean / p50 / p90 / max | 194.1k / 193.5k / 200k / 200k | 193.5k / 193.4k / 200k / 200k |
| Round-1 turns at 200000 (ran out), of 241 | 61 | 53 |
| Round-1 turns that ran out in `decide` (`OOF 1`) | 59 | 50 |
| Round-1 turns whose `decide` finished (`D 1` line) | 183 | 191 |
| Round 1 at 100M, mean (warm-up included) | 539.2k | 520.6k (-3.5%) |
| Mandatory round-1 work at 100M (profiled): mean / p50 / p90 / max | 244.0k / 249.5k / 324.3k / 359.3k | 221.0k / 220.9k / 296.7k / 328.9k |
| Mandatory work over 200k, of 241 | 178 | 152 |
| Play turns after round 1 at 100M, mean | 48,501 | 48,408 (-0.2%; total fuel -0.22%) |

"Mandatory" is start-up + world update + Pathing + comms receive + `decide`, i.e. everything before the turn end and
warm-up. At the real budget the round-1 mean barely moves because the warm-up and the gated farm loop spend what is
freed; what changes is how many turns finish.

### What a round-1 out-of-fuel turn loses

Every round-1 run-out is inside `decide` (`OOF 1 decide`). The champion's `D 1` line never prints: whatever `decide` had not yet done that
turn (on most of these maps the farm's walk comes last) is lost, and its turn end (comms send, ward, recall start)
is skipped. The next round resumes the stale turn, abandons it at the next check and plays round 2 on what is
left; on many-group maps (gen-classic, gen-hourglass-102205812) that round-2 turn often runs out too (`D 2` missing).
Even finished round-1 decides are cut short: before, 136 of 183 logged `farm-partial-evaluation`, 106
`ward-no-bushes-fuel`, 44 `farm-no-route` and 45 `crow-flies-farm`; after, 119 / 74 / 49 / 46 of 191.

## Per-phase breakdown, round 1 at 100M (means over 241 instances; max in brackets)

| phase | before | after | change |
|---|---:|---:|---:|
| start-up before `main` + `Instance` | 11.8k | 11.8k | 0 (an empty SDK bot pays 11.3k) |
| `StaticMap::build` | 60.9k (100k) | 49.4k (95k) | -11.5k |
|   new + boards | 6.3k | 6.3k | |
|   altars + camp groups | 26.5k (55k) | 22.1k (44k) | -4.4k |
|   crossings | 12.6k (23k) | 5.8k (23k) | -6.8k (dashers only now) |
|   draft decode | 12.7k (34k) | 12.8k (34k) | untouched |
| `World::init_beliefs` | 21.6k (35k) | 18.5k (29k) | -3.1k |
| `World::update` | 14.1k | 13.9k | |
| Pathing, comms receive | 3.4k | 3.2k | |
| **before `decide`** | **112.6k** | **97.8k** | **-14.8k** |
| `decide` | 131.3k (224k) | 123.2k (208k) | -8.1k |
|   ward (first) | 2.1k | 2.2k | |
|   siege (`altar_access` and its floods) | 29.5k (63k) | 21.8k (40k) | -7.6k |
|   farm evaluation loop | 50.9k (132k) | 50.4k (131k) | |
|   farm attack tiles (index 6.6k) | 13.5k | 13.3k | |
|   farm after the loop (tiles, approach, route) | 24.4k | 24.2k | |
|   ward (end), turn order | 8.1k | 8.1k | |
| **mandatory** | **244.0k** | **221.0k** | **-23.0k** |

Per map (mean over the map's champions, before -> after): ambush 298.5k -> 252.2k, lanes 327.0k -> 299.1k,
boss-battle 331.4k -> 301.9k, gen-classic 313.8k -> 280.3k, gen-hourglass-102205812 328.7k -> 303.5k, pilgrimage
259.9k -> 229.8k, huge-shared 267.3k -> 242.2k, monolith-heavy 270.9k -> 242.9k, caves 207.7k -> 191.5k; small maps
-7k to -15k (fragment 124.3k -> 117.7k). Maps that still run out are the many-group (lanes 42 groups, hourglass 68,
classic 40, dense-camps 35, boss-battle 31 with 158 members) and 100x100 ones.

## The cuts

Commits on main (CHANGES 156), each byte-identical at 100M:

1. **Crossings only for dashers** (9fe986f1, world.cpp/world.h). `find_crossings` (~45 whole-board ops, 12.6k mean,
   23k on 100x100) feeds only `dash_walls`, `landing_dash_walls`, `near_crossable` and `crossable`, and every reader
   checks `has_dash()` first. A champion without a dash leaves them unbuilt (the draft bot still builds them):
   -12.6k for a non-dasher, -6.8k on the mean.
2. **Live camps' first build from the camp tiles** (c5014abe, 0b087ca4, pathing.cpp/.h). `Pathing::live_camps` set
   every live member one by one (~60 each). It now copies `camp_tiles` and starts each group's mask full, so only
   dead members flip. `live_flips_` then counts from another start, but it is only compared with its own snapshots.
   -1.8k on round 1. The first version branched inside the steady-state loop and cost ~5 fuel a play turn; out of
   line (0b087ca4) play turns came out ~19 cheaper than the baseline.
3. **Leaner camp-group loop** (3bf0333d, world.cpp, one hunk in `StaticMap::build`). Group sums in locals, camp
   designs in a fixed array, the centre found in place without `central_tile`'s vectorised loops (a 5-member centre
   was ~430 fuel). With cut 5, camp groups went 26.5k -> 22.1k on the mean (boss-battle 54.7k -> 44.1k).
4. **Altar access reads the static walk only off the live one** (c3fcbc78, bot.cpp). `altar_access`'s first build
   flooded our static walk (`Pathing::foot`, 6k mean, 23k on 100x100) to find tribute tiles off it. Live camps only
   add walls, so every tile on the live walk (`ours`, flooded anyway) is on the static walk: the flood now runs first
   and the static walk is read only for tribute tiles off it. Usually none are, and the warm-up builds the static
   walk later. Siege -7.6k on the mean, -24k on ambush (100x100).
5. **Camp members and healths in fixed static arrays** (a730ff65, world.h/world.cpp). `CampGroup::members`,
   `CampBelief::health` and `health_round` were `std::vector`s over the static bump allocator; their reserve/assign
   cost ~150 each, three per group (~25k on gen-hourglass-102205812's 68 groups). `StaticArray<T>` takes its elements
   from `static_alloc` in one call (no growth; copies share elements, and nothing copies these). Round 1 -2k to
   -6k; play turns ~70 fuel cheaper on the mean, as every read loses the vector indirection.

## What did not work

- `[[clang::minsize]]` on `StaticMap::build` and `World::init_beliefs`: dearer (boss-battle camp beliefs 11.6k ->
  21.6k, camp groups +8k).
- Building camp members with `resize` and direct writes instead of `reserve` + `push_back`: dearer (+6k on
  gen-hourglass-102205812); `resize` + a raw loop for the camp healths: no change. The cost is libc++'s per-vector
  machinery, not the per-element loop, hence the fixed arrays.
- Per-element loops do cost what they look like: a scalar sum is ~8 fuel an element, an unrolled 5-element centre
  ~300. Small loops are cheaper with `#pragma clang loop vectorize(disable)` but the gain is small.
- `fuel()` reads cost 6, so laps of raw reads (`AccMeter`, ~15) profile inner loops far better than `FuelMeter`
  (~170, which on a 40-group farm loop added ~30k).

## The biggest round-1 costs left, with ideas

- **Farm evaluation loop, 50k (132k max).** First readings per group: `min_camp_damage` + `spell_clear_rounds`
  13k (Ren's reflect path is O(n^2) per group; 69k max), group facts 10k (`fastest_clear` 3k), `from_here` 7.7k on
  the 118 turns that need it (a dasher on a map with crossings: the draft's spawn steps are walking steps). Ideas:
  a plan section with dash-graph spawn steps or a flag that they equal the walking ones (v4); evaluate groups whose
  Chebyshev bound already loses after the others, so `fastest_clear` and the camp damage run for fewer groups.
- **Camp groups and beliefs, ~22k + ~9k.** Still ~300 a group for `CampGroup`/`CampBelief` construction and the
  per-member `set_tile`; a struct-of-arrays layout would remove most of it.
- **Draft decode 12.8k (34k on 68 groups) and attack-tile index 6.6k (17k).** ~100 fuel a decoded value. Decode the
  enemy and altar steps on first ask, and index only up to the group asked, rather than all groups up front (v4's
  call).
- **Floods.** The live walk from spawn in `altar_access` (5.9k, 23k on 100x100) and, for dashers, the static walk
  from our tile. One plan bit, "every tribute tile is on the live walk from this spawn", would let round 1 skip the
  live flood when no camp state has changed.
- **Crossings for dashers, 12.6k (23k).** ~45 whole-board ops; a plan bit for "no crossable tile" would skip them on
  maps without hole or altar lines.
- **`init_beliefs` per champion, ~600 each.** Every `ChampionBelief` allocates `possible` and `undashed`, which
  allies never use.
- **`World::update` 14k, start-up 11.8k.** The update costs the same every turn; start-up is the SDK's (an empty bot
  pays 11.3k).
