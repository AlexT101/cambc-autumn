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

## Pass 2 (2026-10-26)

Five more fuel-only cuts, three of them plan facts (3 header bits, 76 -> 79; plan v6 on merge, CHANGES 160). Baseline: main at df3b03e (plan v5 with
the ward plan), frozen as `bots/variants/astraeus-df3b03e-p2`. The cuts were built and checked one at a time on
3b2677b (52/52 identical at 100M after each), then rebased onto df3b03e: the stack is **52/52 identical at 100M**
against it, and play turns after round 1 are 0.04% cheaper in total.

Profiles: a copy with laps (two `fuel()` reads, ~12 fuel) around each phase and a `MAND` line printing the fuel spent
from the turn's start, start-up included, to the end of `decide`; per-call laps (camp damage, fastest clear) add a
few k. A `FACTS` line in the same copy checked, per instance, which plan facts would hold before any was built.

| | before (df3b03e) | after |
|---|---:|---:|
| Round 1, real budget: mean / p50 / p90 | 193.8k / 193.4k / 200k | 193.0k / 192.7k / 200k |
| Round-1 turns at 200000 (ran out), of 241 | 48 | 28 |
| Round-1 turns that ran out in `decide` (`OOF 1 decide`) | 47 | 26 |
| Round-1 turns whose `decide` finished (`D 1` line) | 194 | 215 |
| Out-of-fuel play turns, whole bench (games diverge at this budget) | 763 | 697 |
| Mandatory round-1 work at 100M (profiled): mean / p50 / p90 / max | 212.0k / 213.4k / 286.0k / 318.9k | 193.4k / 191.8k / 255.9k / 308.1k |
| Mandatory work over 200k, of 241 | 141 | 107 |
| Round 1 at 100M, mean (warm-up included) | 523.6k | 516.8k |

Phases that changed (means over 241, profiled):

| phase | before | after |
|---|---:|---:|
| draft decode | 11.8k | 8.3k |
| drafted attack tiles (index included) | 8.6k | 6.5k |
| `altar_access` (siege) | 18.2k | 8.5k |
|   of which live camps' first build | 5.6k | 2.4k |
| farm loop | 49.8k | 46.7k |
|   field from here (dashers) | 3.7k | 1.7k |
|   `to_any_altar` inside `centre_to_altar` (dashers) | 2.6k | 0.6k |
| `decide` (`act`) | 112.2k | 97.1k |

### The cuts

1. **`tributes_walked`, 1 bit** (117dd2aa). Every tribute tile is off the camp tiles and walkable from our first
   spawn tile with every camp standing. Live camps are a subset of the camp tiles, so every tribute tile is then on
   `altar_access`'s live walk however many camps have died, and its first build finds them all open without the
   flood (5.9k mean, 23k on 100x100) or the reads after it. The walk (`AltarWalk::ours`) is left unknown until a
   camp change needs it or `prepare_next_turn` has spare fuel. True on 222 of 241 instances (false on hooks and
   boss-battle). `altar_access` 18.2k -> 11.7k at the time; with cut 5, 8.5k. Inlined, the new code made play turns
   ~11 fuel dearer each; the early return now stays inline and the rebuild is out of line.
2. **`dash_spawn_steps` and `dash_altar_steps`, 2 bits** (fc25f87b). A dash's static walls give every group the same
   steps from each ally spawn tile, and from the tribute tiles, as the walking steps the plan holds. The draft
   checks with one dash field per spawn tile and one from the tribute tiles (layers left out of the header's
   `field_layers`, so the plan's estimates are unchanged). Landing-dash walls lie between dash and walking walls,
   so they agree too. Dashers then read the drafted spawn and altar steps where they had to build a field from
   their tile and `to_any_altar`. Of the 107 dasher instances on maps with crossings, the spawn steps agree on 63
   and the altar steps on 87: -4.0k on the mean.
3. **Attack tiles indexed only up to the group asked** (284ca6c5). The index counts each flagged member's bush bits
   to find the next member's; it now stops at the group asked for and resumes from there. -2.1k.
4. **Enemy steps decoded on first ask** (2ca3720a). Round 1's `decide` reads the ally steps, and the farm loop the
   altar steps and spawn offsets, but the enemy steps only the warm-up (centre caps) and `home_ground` (once the
   centres are warm). The build skips their codes: with Rice parameter 0, which the mirrored zigzags almost always
   take, each code ends at a zero bit, found by popcounts a 57-bit window at a time (~5 fuel a code against ~50 to
   decode one; the mirror lookup made the enemy steps ~150 a group). `get_rice` is now inlined into the decode
   loops (~-1.2k of the -3.5k). A plan written for the map always has every mirror group, so the deferred decode
   no longer rejects the plan for a missing one (it would read unreachable).
5. **Live camps' first build skips beliefs at version 0** (c5d1f936). A `CampBelief`'s version changes with every
   health or state change, so one still at 0 is the first belief, every member alive, which the first build
   already drew by copying the camp tiles. Only groups seen changed are scanned: 5.6k -> 2.4k.

### What did not work, or was not done

- **"No dash-crossable tile" bit:** only 4 of 111 dasher instances (boss-battle) have none: altars have standable
  tiles on two sides on nearly every map. About -0.2k on the mean; not built.
- **Camp tiles set in the board's words** instead of a host set per member in the camp-group loop: +1.2k (the
  shifts, masks and 64-bit ops cost more than the ~16-fuel host call). Reverted.
- **The farm order (`nearest_groups`) at turn end:** nothing in round 1's `decide` reads it (there is no farm choice
  yet, so the loop's order is null). `prepare_next_turn` builds it after `decide` from spare fuel, so it is not in
  the mandatory work; building it on first need would move it into round 2's 100k `decide`. Left as is.
- **Allies' `possible`/`undashed` boards:** two allocations, ~260 fuel, per ally, ~1.1k on the mean. The boards are
  read on ~60 paths that would all need auditing for a null board, as a copy of a null bitboard faults. Not done.
- **Faster decode code:** ~90-150 fuel a value is the WASM op count itself (`get_rice`'s fast path is ~50 ops, the
  `local.get`/`local.set` included), so only decoding less helps. The altar steps and spawn offsets are read in
  round 1, so they stay at build.
- **Camp groups and beliefs (22k + 7k):** per group, the member loop ~480 (about 100 a member), `emplace_back` ~120,
  the members' `StaticArray` ~70, the belief ~300. No single part is large; a struct-of-arrays layout was not tried.
- **Farm loop exact cuts:** `min_camp_damage` (10.6k, 48k max) and `spell_clear_rounds` (3.9k, 39.5k max) are one
  call per group in round 1. Ren's reflect path updates every attacker's health each step, and a faster
  formulation would round the floats differently; `std::sort`'s order of ties feeds the damage too. Left alone.

### The biggest round-1 costs left (means, profiled)

- **Farm evaluation loop, 46.7k (131k max):** ~2k a group spread over its facts, steps, clears and tail; camp
  damage and spell clears 14.4k, fastest clear 3.2k.
- **Camp groups 22.1k (44k) and camp beliefs 7.1k (17k).**
- **Champion beliefs 10.3k:** ~540 a `ChampionBelief` (its two boards and zeroing), turn ranks 2.0k.
- **Start-up 11.8k** (the SDK's), **`update_champions` 8.8k**, **draft decode 8.3k (20k)**, **attack tiles 6.5k**,
  **crossings 5.8k (dashers only, 23k on 100x100)**, **ward 5.9k**, **turn order 4.4k**.

## Pass 3 (2026-10-26)

Four more fuel-only cuts, none in the plan. Baseline: main at 12c2e69f (CHANGES 160, plan v6), frozen as
`bots/variants/astraeus-12c2e69-p3`. Each commit was benched 52/52 identical at 100M on top of the ones before it,
and play turns after round 1 are 0.04% cheaper in total. Same profiler as pass 2, plus a finer copy with laps
around the farm loop's parts (they add ~10k to the loop, so only differences between them count).

| | before (12c2e69f) | after |
|---|---:|---:|
| Round 1, real budget: mean / p50 / p90 | 193.0k / 192.7k / 200k | 193.0k / 192.9k / 199.7k |
| Round-1 turns at 200000 (ran out), of 241 | 28 | 21 |
| Round-1 turns that ran out in `decide` | 26 | 21 |
| Round-1 turns whose `decide` finished (`D 1` line) | 215 | 222 |
| Out-of-fuel play turns, whole bench (games diverge at this budget) | 697 | 597 |
| Mandatory round-1 work at 100M (profiled): mean / p50 / p90 / max | 193.4k / 191.8k / 255.9k / 308.1k | 188.5k / 186.7k / 249.1k / 300.8k |
| Mandatory work over 200k, of 241 | 107 | 93 |
| Round 1 at 100M, mean (warm-up included) | 516.8k | 513.8k |

| phase (profiled means) | before | after |
|---|---:|---:|
| champion beliefs (`init_beliefs`' champion part) | 10.3k | 6.8k |
| camp beliefs | 7.1k | 6.5k |
| camp groups | 22.1k | 21.9k |
| farm loop | 46.7k | 46.2k |

### The cuts

1. **Camp members and healths from one allocation each** (23b4817a). `StaticMap::build` sizes one
   `StaticArray<CampMember>` from the camp layout and gives each group a slice; `init_beliefs` does the same for
   the healths and their rounds. -0.75k, later turns unchanged. A `static_alloc` costs ~50, less than expected.
2. **Allies' beliefs get no `possible`/`undashed` storage** (4dbd8bc9). Every read of these boards is of an enemy:
   loops over `World::enemies`, Safety's foes and World's tracking, all behind an enemy check or `tracked`, which
   only enemies set. Allies take storage-less boards moved out of one board allocated once (`no_board()`).
   A copy of such a board would fault, so `ChampionBelief`'s copy operations are deleted (at merge; nothing
   copied one). Champion beliefs -1.6k.
3. **`ally_engaged` builds the threat board only with an ally near** (af83bf24). `CampGroup::threat_radius()`
   (member distance from the centre plus reach, made on first ask) bounds every threat tile, so an ally beyond it
   cannot be on the board (~400 fuel the first time). The farm loop asks it for every group too costly alone.
   Round 1 -0.4k; play turns -0.03% in total.
4. **The first ranks without `rank_turns`** (7ddcde7b). With every priority 0 and each order by index,
   `rank_turns` leaves each rank and next rank at the champion's index; `init_beliefs` writes those. -1.9k.

### What did not work, or was not done

- **`ally_engaged` as a member-by-ally distance loop** instead of the threat board: +1.3k on round 1 and +0.44%
  on play turns. The board is cached per group, so it wins over turns; boss-battle's large groups pay most.
  Cut 3 keeps the board and only skips it for far groups.
- **Fastest clear on first need** (claimed groups and a loop with no best yet never read it): fastest clear
  -0.8k on round 1, but play turns +0.05% (~24 fuel a turn), so not kept.
- **`safe_targets` testing each harmless member by a word scan** (`count_in_square`) instead of `any_within`'s 4
  host ops: +0.65k (+17k on boss-battle). As with pass 2's camp tiles, a WASM bit loop costs more than host ops
  for a few tiles. Dilating the open tiles once and testing each member would need the board's padding masked.
- **Farm loop, the rest:** about 2k fuel a group, spread over its facts (~265 a group), steps (~350, mostly the
  drafted spawn step and the centre field lookup), camp damage and spell clears (~600), the altar steps (~120)
  and the value tail. Each part is a few dozen lines of arithmetic at ~3 fuel a C++ operation; none repeats work
  another does. Pruning more groups earlier would change the visiting order, and with it which of two
  equal-valued groups wins, so it isn't exact. A cheaper bound before the steps (the Chebyshev bound, as the
  field-from-here prune already uses) would save only the ~300 a pruned group's step lookup costs, and a hop or a
  recall out of a pocket can beat it.
- **Camp damage:** the sort's tie order and Ren's per-step float updates feed the result, so nothing there was
  changed.
- **Camp groups as a struct of arrays:** not tried. Per group, the 80-byte zero fill and the vector's bookkeeping
  are ~120 fuel and the member loop ~100 a member: a different layout would save little of that.

### The biggest round-1 costs left (means, profiled)

- Farm loop 46.2k (131k max); camp groups 21.9k (44k); start-up 11.8k (the SDK's); `update_champions` 8.8k; draft
  decode 8.3k; champion beliefs 6.8k; camp beliefs 6.5k; attack tiles 6.5k; ward 5.9k; crossings 5.8k (dashers);
  turn order 4.4k.
