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

## Pass 4 (2026-10-26)

Three more fuel-only cuts: Ren's farm bound, a group's summed health for the pre-facts bound, and camp groups built
without a zero fill. They were built and benched one at a time on 2a26b35f (52/52 identical at 100M after each, and
the play-turn `farm_turn<false>` compiled to the same code), then rebased onto 9be0f154 (CHANGES 165, first-turn
`home_ground`). The stack is **52/52 identical at 100M** against that, and play turns are unchanged in total
(-0.00%). Profiles: pass 2's profiler on main 9be0f154 and on the stack. The real budget was not rerun.

| | before (9be0f154) | after |
|---|---:|---:|
| Mandatory round-1 work at 100M (profiled): mean / p50 / p90 / max | 177.9k / 174.9k / 232.7k / 300.8k | 174.0k / 172.9k / 222.4k / 278.9k |
| Mandatory work over 200k, of 241 | 65 | 60 |
| Round 1 at 100M, mean (warm-up included) | 493.4k | 490.6k |

| phase (profiled means) | before | after |
|---|---:|---:|
| farm loop | 32.1k (97.6k max) | 28.9k (86.6k max) |
|   of which `fastest_clear` | 2.9k | 0.9k |
|   of which `min_camp_damage` | 4.1k | 3.2k |
| Ren's farm loop (35 instances) | 50.7k | 40.9k |
| camp groups | 21.9k | 21.2k |

One instance got dearer: gen-dense-camps-102108100 b, body 1, +5.5k. Nothing else rose by more than 1.7k, and that
one was not investigated.

### The cuts

1. **Ren's bound** (c5e25392, bot.cpp). Ren was left out of round 1's order-free prunes because its reflection
   (0.2x Focus to each attacker that hits it) clears faster than its output. `min_camp_damage`'s reflect path hits
   the target with our output and every living attacker with the reflection, each round. Monsters never gain
   health, so the clear takes at least the attackers' health over (output + reflection x living attackers), then the
   non-attackers' health over our output. The sort puts every striking member first, and non-attackers take only our
   hits. That is `reflected_clear`, shaved by 0.1% for the float steps.
   - **Damage.** Each attacker takes at most output + reflection a round, so it lives at least ceil(0.999 hp /
     (output + reflection)) rounds and strikes in all but the last. `beyond_spare` uses that for Ren.
   - **Shared and kiting clears.** A clear shared with the unclaimed partner runs `min_camp_damage` with no
     reflection, so `fastest x part` still bounds it, and `reflected_clear x part` is lower still. Ren is melee and
     never kites (`spell_clear_rounds` returns -1 with no spells).
   - **Ren's plain prunes stay.** They use the fastest clear, which the reflection can beat, so they are not bounds
     and they decide which groups Ren skips. Its result therefore depends on the visiting order: Ren gets the new
     prunes on top of the old ones, in the old order, and no leads. Every new prune is strict against the best so
     far, and without leads acceptance is strict too, so the best never changes.
   - **Result.** -1.9k on the mean (old base).
2. **A group's summed health** (a807bc8d, world.h/world.cpp/bot.cpp). `unweighed_beaten` ran `fastest_clear`'s pass
   over the members for every group it checked, which was 2.6k of round 1. `StaticMap::build` now sums each group's
   `max_health` (`CampGroup::health`). While a group's belief is at version 0 (every member alive at full health),
   the bound reads `health / strength`, the same number up to rounding, which the 1e-4 slack covers. The facts still
   keep `fastest_clear`, so the plain prunes see the same floats. Farm loop -2.2k, camp groups +0.5k (one float add
   a member costs ~8).
3. **Camp groups without a zero fill** (c2b73408, world.h). `emplace_back()` value-initialises. For a class with no
   user-provided constructor that zero-fills the whole object (an 80-byte `memory.fill`, ~1 fuel a byte) before the
   member initialisers run, even though every member but `handle` has one. An empty `CampGroup() {}` drops the fill
   and `build` writes `handle` at once. Camp groups -1.3k.

### What did not work, or was not done

- **Claimed groups (lead 2).**
  - **The bound.** A claimed group's value is `rate(worth x S x rounds / health, trip + rounds)` with
    `rounds <= health / (S + crew output)`. As a function of the rounds x it peaks at x = sqrt(trip (trip +
    horizon)), so `rate(W S xm / H, near + xm)` with `xm = min(H / (S + o), sqrt(t (t + h)))` bounds it before the
    facts. The prune is strict against `max(best_value, shared_value)`, guarded by `may_help` and `near > 0`.
  - **Byte-identical, but a net loss.** It saved 0.77k (claimed branch -0.53k, facts and steps -0.23k), but the
    check cost ~1k, mostly reading each ally's output: +0.28k. Out of line (`noinline`) it was the same, so the cost
    is the check, not codegen. It pruned only ~20%. The crew's head start (`delayed_damage`, `work_arrival`) cannot
    be bounded before the steps, and without it the bound is loose. Even free, it would save under 1k.
- **Deferring `too_late` (lead 4).** Empty-handed, once there is a best, a group that cannot take its place changes
  nothing: a risky one counts only with no best, and `from_altar_value` moves only when banking. The first turn can
  therefore compare the value first and read the deadline (`centre_to_altar`) only for a group that would be
  accepted. 52/52 identical, but only -0.39k: not kept.
- **`CampBelief() {}`**, as for camp groups: camp beliefs +35. `resize` already initialises them with a few
  stores, not a fill.
- **A struct-of-arrays layout for camp groups (lead 3).** Not built. Coarse laps (one per block, no per-group laps)
  put the group loop at ~250 a group plus ~200 a member, and camp beliefs at ~180 a group plus ~15 a member. The
  member loop's hot path is ~150 WASM instructions plus the host `set` (~16): four word loads, the design lookup,
  seven field stores, four running sums, the lookup-table store and the centre search. A struct of arrays keeps the
  same stores, each with its own address arithmetic. The only waste found was the zero fill (cut 3).
- **Ren, further.** After cut 1, Ren's remaining clears cost ~6k on its 35 instances (~0.9k on the mean). A tighter
  bound would pair the death order with the attackers' strengths (a rearrangement bound), and was not tried.

### Codegen traps found on the way

- **A local copy of a field in the play-turn loop costs fuel a group.** The first version of cut 1 kept
  `known.fastest` in a separate local, and the compiler could not merge it back with the field across the stores in
  between: +4 fuel a group checked, +0.08% on play turns. Use the template parameter (`opening ? quickest :
  known.fastest`), so the play-turn copy reads the field as before.
- **One more argument to an out-of-line function adds instructions.** `rated_beaten` is not inlined, and an extra
  parameter is a `local.tee` and a `local.get` per call. Ren's bound goes in through the `fastest` argument instead:
  the partner term then uses the reflected clear times `part`, which is looser but still valid.
- **Moving a function-local static into a helper changed codegen.** `rate`'s horizon moved into a helper with its
  own static changed `farm_turn<false>` (a select and a reordered load). A pure `rate_horizon` that the static calls
  left it identical.
- **Checking codegen.** Compile `bot.cpp` with the flags in `.cambc/build/compile_commands.json` plus `-S`, then diff
  each function's instructions with labels and comments normalised. That shows whether play-turn code changed
  without a bench: here only `farm_turn<true>` differed, and a few new out-of-line helpers appeared.
- **Laps on small helpers.** Laps of two `fuel()` reads cost ~15 each, so laps around per-group helpers
  (`unweighed_beaten`, `fastest_clear`) inflate them. Compare only runs with the same laps.

### The biggest round-1 costs left (means, profiled, after)

- **Farm loop 28.9k (86.6k max).** The pre-facts check is the largest part, ~8k with laps: `unweighed_beaten` ~2.7k
  beyond its fastest clear (two `rate` calls and the worth), `beyond_spare` 1.8k and `ally_engaged` 1.2k. Then
  clears ~4k, steps ~3k, claimed groups ~2.8k, `too_late` ~1.9k and facts ~1.5k.
- **Camp groups 21.2k (43k).**
- **Start-up 11.8k** (the SDK's).
- **`farm_attack_tiles` 10.8k, siege 10.6k** (`altar_access` 8.5k), **`update_champions` 8.8k, draft decode 8.4k**
  (steps 7.7k), **champion beliefs 6.8k, camp beliefs 6.5k, attack tiles 6.6k + 4.6k index, ward 6.0k,
  crossings 5.8k** (dashers), **`home_ground` 4.2k** (new with CHANGES 165), **turn order 4.4k**.

## Pass 5 (2026-10-26)

Seven fuel-only cuts from three parallel branches (from f9d2e26b), reviewed and stacked on main 2fc174c5, which
now bounds round 1 with the turn-end queue (fa26fd0e). Branch `fuel/round1-pass5`. Each commit was benched on top
of the one before it and against main (`bots/variants/p5-base3`, `replays/fuel/p5/base3.json`): **52/52 identical at
100M after every step**. Play turns -0.2% (total fuel -0.21%). Profiles: pass 3's profiler with agent C's `p5` laps
(anchors fixed for main, `unweighed_beaten`'s lap dropped on both sides), so they run ~10k above pass 4's.

| | before (2fc174c5) | after |
|---|---:|---:|
| Mandatory round-1 work at 100M (profiled): mean / p50 / p90 / max | 184.8k / 181.6k / 240.5k / 304.2k | 160.7k / 157.5k / 209.0k / 268.8k |
| Mandatory work over 200k, of 241 | 82 | 40 |
| Turn before the queue (below): round 1 over 200k / round 2 over 100k | 42 / 90 | 11 / 84 |

Phases (profiled means): start-up 11.9k -> 10.7k, build 45.0k -> 41.6k, `init_beliefs` 13.8k -> 12.2k, siege
11.2k -> 9.9k, `farm_attack_tiles` 11.3k -> 8.9k (index 4.7k -> 3.4k), farm loop 34.2k -> 29.0k, `home_ground`
4.2k -> 2.1k, `place_ward` 6.0k -> 4.2k, turn order 4.5k -> 1.3k.

**Round 1 is bounded now, so its total measures nothing.** At 100M the queue stops where the real budget would, so
the bench's round-1 mean sits near 200k. What matters is each turn's work before the queue, and whether a cut moves
work into the queue that a later turn then makes on demand. A copy printing `QS round spent` before the queue and
`QE` after it, with the warm-up flags, measures that (`qs.py`, `qsr.py` in the pass's scratchpad). Full stack
against main, means before the queue:

| | round 1 | 2 | 3 | 5 | 10 | 20 |
|---|---:|---:|---:|---:|---:|---:|
| 2fc174c5 | 163.5k | 91.2k | 69.0k | 65.6k | 55.9k | 44.6k |
| stack | 140.7k | 89.9k | 67.3k | 64.5k | 55.1k | 44.1k |

The map warm-up finishes by round 6.0 instead of 6.8 (earlier on 129 instances, later on none), the whole warm-up by
27.9 instead of 28.3. Round 2's p90 rose 135.5k -> 140.1k: an instance whose round-1 queue never runs now decodes
the enemy steps on round 2 (cut 3).

### The cuts

1. **`ally_engaged` behind an ally box** (39d9da51, agent A). On the first turn, `engaged(g)` builds on first need
   the bounding box of the allies `ally_engaged` reads (`!is_self && alive && visible`), and returns false without
   calling it when the Chebyshev distance from the group's centre to the box is at least `members.size() + reach`.
   Members are cardinally connected (rules `camps.groups`) and the centre is a member tile, so every member is within
   `members.size() - 1` of it and `threat_radius() = max(dist(m, centre) + m.reach) <= members.size() - 1 + reach`
   (`reach` is the members' longest). The box distance is at most every boxed ally's, so `ally_engaged` would find
   none in the radius. Allies change only in `World::update`; both call sites keep their short-circuit order. Play
   turns pay ~0.4 a turn: a later turn computes the `threat_radius` round 1 used to cache.
2. **The pre-facts bound with its turn constants hoisted** (53019ce6, A). `unweighed_beaten` becomes a lambda in
   `farm_turn` with the capture rounds, `rate`'s horizon and the partner part hoisted (`opening ? ... : 0`). Each
   float has the same operands in the same order. `max(b1, b2) * 1.0001f < best` became `b1 * 1.0001f < best && b2 *
   1.0001f < best`: rounding is monotone, so `fl(max(b1, b2) c) = max(fl(b1 c), fl(b2 c))`, and there is no NaN
   (worth >= 0, rounds >= 1, horizon > 0). `from_altar` was -1. Main's new `group_hop(g) < 0` guard merged cleanly.
3. **`home_ground` reads one group's enemy steps on the first turn** (f36c69a7, agent B, changed). With mirrored
   steps at Rice parameter 0, `enemy_steps_of(g)` skips to group g's code (`skip_rice`, popcounts over 57-bit
   windows), from the last group asked when past it, else from the section start, and returns `decode_mirrored`'s
   `ally[mirror] + unzigzag(code)`. The reader reads zero bits past the end, as the decode does. A group with no
   mirror while `mirrored` is set would differ (the decode marks every group unreachable), but the draft sets
   `mirrored` only when every group's mirror is a group, from the same `StaticMap` code on the same map.
   - **As written it lost on this main.** Round 1 -2.1k before the queue (over 200k 39 -> 36), round 2 +3.6k (p90
     +15k, over 100k 87 -> 96): a play turn's farm weighs nearly every group, and with no table each `home_ground`
     read was lazy. Making `enemy_steps` itself lazy for every reader was worse (round 2 +4.8k).
   - **Kept form:** `home_ground(map, g, opening)` reads lazily only on the first turn (`farm_turn<false>` keeps its
     instructions), and the turn-end queue decodes every group's steps first thing on round 1, under a fuel check
     (`warm_enemy_steps`, ~150 a group). An instance whose round-1 queue never runs decodes on its round-2 farm.
4. **`operator new` from a bump arena** (736e991a, agent C, fixed). Every replaceable new/new[] (plain, aligned,
   nothrow) takes 16-aligned blocks from a 2 MiB static arena that is never freed, then malloc (alignment <= 16) or
   aligned_alloc, throwing `bad_alloc` on failure; every delete form ignores arena pointers (one unsigned compare) and
   frees the rest. Round 1 made ~300 allocations (every bitboard is `operator new(size, align_val_t{16})`) at ~130
   each, plus frees. Nothing orders or hashes by address (no pointer-keyed containers; the one `uintptr_t` checks the
   draft buffer's alignment), and the replay harness hashes no pointers. Arena memory starts zeroed where recycled
   heap memory may not, so a read of uninitialised memory could differ; none showed in any bench.
   - **Fixed in review:** `arena_take` rounded `n | 1` up before comparing, so a request near `SIZE_MAX` (what `new[]`
     passes on a size overflow) wrapped to a small size and got an arena block instead of `bad_alloc`. It now rejects
     `n >= left` first. `left` is a multiple of 16, so the rounded size fits exactly when `n < left`: the arena/heap
     split is unchanged for every other request. The aligned_alloc path also guards its rounding.
   - **Memory:** `probe-memory` shows the local engine caps linear memory at 4096 pages (256 MiB); a bot with the
     2 MiB array starts at 34 pages. A full 00ambush (100x100) game peaked at 52 pages (3.3 MiB) on main and 73
     (4.6 MiB) with the arena. The arena is full by rounds 100-500 (round 1 uses ~200 KB), then allocations go to
     malloc as before. The server's cap is unverified.
   - The biggest cut: round 1 -12.8k before the queue (over 200k 36 -> 17), round 2 -3.3k (over 100k 96 -> 86).
5. **`ward_bushes` tests a square until `near_bushes` exists** (34d1ac12, C, moved). On main the bush ward goes down
   only at the turn end (9a0148e3), and its early-out built `near_bushes` (every bush dilated by 2, ~1.9k, 3.8k on
   100x100) to test one tile. `near_bushes = square_dilate(bushes, ward_range())`, so testing `here` on it is exactly
   "a bush within `ward_range` of `here`", which `any_within(bushes, here, ward_range())` answers. Nothing holds
   `within`'s scratch board across the call.
   - **Placement:** C built the board in `StaticMap::warm_up`, which the bounded queue reaches late, and every
     turn-end ward check until then pays `any_within`: rounds 2-5 +90-170 a turn, round 2 over 100k 86 -> 89. At the
     queue's end, or never built, it was +130-250 a turn through round 20. Built first in round 1's queue only:
     round 2 +46, later rounds +30-55 (instances whose round-1 queue never ran). Kept: the queue builds it first
     whenever it is missing.
6. **The attack-tile index counts with fixed masks** (ee85c19d, C). `count_in_small_square<R>` (R <= 4: at most 9
   wide, so at most two 8x8 chunks each way) makes the row and column masks once and reads up to four words: the
   masks `each_word_in_square` makes per chunk. C checked it natively against the old count on 3.67M cases.
7. **The turn order skips escape threats when no enemy can be in strike reach** (3a87b275, C). `out_of_reach`:
   Safety unbuilt, no enemy in sight, not a healer, and no tracked unseen enemy's `possible` within 6 of us.
   `compute_strike` caps every reach at `Strike::max_reach` (6) and `threat_strike` caps its widening, so for an
   unseen enemy `threats_at` searches `top = min(radius, reach) <= 6`, finds nothing, takes `d = radius + 1` and
   misses: `offer_escape` offers nothing. `refresh()` never sets `built_`, and the enemy lists and `possible` boards
   are fixed for the turn, so the first-turn check in `may_escape`, before the refresh, is the same test. Only caches
   are skipped: per-`Safety` ones, and `strike_memo`/`most_damage`, keyed by everything they read. The only reader
   of this `Safety` after the turn order is a healer's `see_again` + `exposure_here`, hence no healers.
   - **Kept the first-turn hoist** over C's variant without it (-2.05k): -1.07k more on round 1 for ~5 fuel on
     off-spawn play turns (+0.01% in total), turns that average 50k of 100k.

Codegen: `farm_turn<false>` kept its instructions after every step. Play-turn functions that changed: `bank_gems`
(the same instructions, two `try_table`s on its StaleTurn throw path nested differently), `place_ward` (+21, cut 5),
`set_turn_order` (+12) and `offer_escape` (+4, cut 7); cut 3 only adds out-of-line helpers.

### What did not work, or was not done

- **Agent A:** Ren's `reflected_clear` from the summed health plus `beyond_spare` early exits, 52/52 but -99
  (`p5a/c3-dropped.patch`); an eager ally box, -761 against the lazy one's -888; a batch pre-pass over every group's
  bound, a per-type memo of `beyond_spare`'s `ceil` terms and a distance threshold, each estimated under 0.5k.
- **Agent B:** a fast path for an all-zero enemy-steps section, +0.08k (2 of 26 maps qualify); a tighter Ren clear
  bound (healthiest attacker first, with the reflection; fuzzed on 200k groups), 52/52 but +0.02k, because Ren's
  plain prunes after the steps already skip more than any sound bound can; a pairing bound on Ren's damage, not
  built.
- **Pass 4's dearer instance** (gen-dense-camps-102108100 b, body 1, +5.5k) is Ren, and not a cache interaction.
  Pass 4 gave Ren the pre-facts check, which there costs ~480 a group (`reflected_clear`, two `rate`s with an
  unclaimed partner) and skips 18 of 35 groups. Ren's plain prunes would have skipped each of them after the facts,
  so it saves facts and steps (~400 a group) but never a clear. Over Ren's 35 instances it still wins (-1.9k).
- **Agent C:** `ChampionBelief() {}` to skip a 196-byte fill per enemy, 52/52 but -0.77k (`p5c/cbfill-dropped.patch`);
  `find_crossings`' two exact savings, -0.45k (`p5c/crossings-dropped.patch`); skipping `farm_attack_tiles`' fuel
  floor with drafted tiles, not exact (`approach_cost` primes `Pathing::ready_check_`, keyed only on slot, round and
  position); allies' `undashed` boards, ~15 a board left after the arena; `track`, `altar_access`, draft decode and
  camp groups re-read with no exact cut over 0.5k.
- **Not run on this main** (wrapped up early): the gen-s1 maps and the real budget on the final stack, per-cut
  profiles, reverse-order stress copies. On f9d2e26b agents B and C ran the 12 gen-s1 maps 24/24 identical.

### Codegen traps found on the way

- **A function's static local is named after its signature.** A new parameter on `home_ground` renamed its cache, so
  an assembly diff flags `farm_turn<false>` though its instructions are the same. Normalise static names first.
- **A member function hides the free function it calls unqualified.** A `StaticMap::decode_enemy_steps(floor)` would
  hide the free `decode_enemy_steps(plan, ...)` that `enemy_steps` calls.
- **Stopping a bench chain's shell leaves its python and cambc children running**, still writing bundles into the
  next run's game directories. Kill the children too.

### The biggest round-1 costs left (means, profiled, after)

Farm loop 29.0k (85k max), camp groups 24.0k (47k), `init_beliefs` 12.2k, start-up 10.7k (the SDK's), siege 9.9k
(`altar_access` 7.8k), `farm_attack_tiles` 8.9k, draft decode 7.9k. Round 2 is now the turn most often over budget:
84 of 241 before its queue, against round 1's 11.

## Many-group maps: the first decision finishes late (2026-10-29, fuel round W31)

On ~100-group maps round 1's mandatory work is ~265-320k against 200k (gen-close-spawns-8280304800, 12 instances,
profiled at 100M: `build_static` 84k, 103k for dashers with crossings 19k, of which the camp loop 61k;
`init_beliefs` 23k; `update` 20k; `decide` 130-185k). Round 2 at 100M, a normal second turn, is 157-175k. No exact
cut closes a 100k gap, so the change is in what the real budget does with the overflow.

What happened (m7, real budget, many-group set: farmland-8280102700, labyrinth-8280203805, pillars-8280204000,
close-spawns-8280304800, dense-camps-8280305500, three-lane-8280302522; own drafts, both sides, 72 instances):
60 round-1 turns ran out in `decide`. Round 2 resumed the stale tail, which ran on to the next stale check: 3-6k for
dashers but 67-77k for the others on close-spawns (the tail after the farm loop has no check), and was thrown
away. Round 2 then replayed the decision from scratch on a single budget, and 53 of the 60 replays ran out too (6
of them twice). So 7 champions first acted in round 2, 47 in round 3 and 6 in round 4.

The change (main.cc): `late` starts true, so a first decision that runs out finishes in round 2 as that round's
turn (CHANGES 217's late finish) instead of being replayed. Identical at 100M (52/52 wide, 32/32 OOF set, 12/12
many-group; +15 fuel on round 1 only). Real budget, many-group set: 25 of the 60 act in round 2, 35 in round 3,
none later; out-of-fuel turns in rounds 1-10 113 -> 73 (round 2's 53 gone; 13 round-3 turns now run out: the first
play-turn farm loop, which used to be the replay); all rounds 222 -> 177. OOF set (16 maps): 1977 -> 1954, rounds
1-10 49 -> 54 (01yellow-brick-road, which runs out in most early rounds either way; games diverge). The decision
acts on beliefs a round old; in rounds 1-2 little has moved, and a refused action spends nothing.

### What would make round 1 fit (designs, not built)

- **The 35 that still finish in round 3** have a remainder above round 2's 100k: mandatory work above ~295k. Every
  ~10k cut from round 1 moves a few of them to round 2; round 1 needs about -110k to fit in 200k.
- **Lazy camp layout.** The opening farm loop's prunes read per group only centre, gems, gold, `has_monolith`,
  strength, health, reach and the member count (`unweighed_beaten` at belief version 0, `beyond_spare`, `engaged`);
  members only for groups that pass them. But `camp_tiles` and `group_lookup` are needed whole by Pathing and the
  update, and the per-group sums need each member's type, so a lazy layout saves only the member copy and the
  healths: ~20k of the camp loop's 61k plus `init_beliefs`' 23k. The rest is the per-member walk (~145 WASM
  instructions a member).
- **Draft certificate.** The plan already carries the first choice's leads; the round-1 loop costs ~600 fuel a group
  beyond them. A per-group "pruned in round 1" bit is not sound: the prunes read allies' claims, our spawn tile and
  both drafts, which the draft bot only partly knows. A stop index needs the groups in nearest-first order from our
  spawn and a lower bound on the lead's value the runtime checks; the play turns' `stop_from` does this, the
  opening does not, and ordering changes which of two equal-valued groups wins unless ties keep index order.
- **Stale tails of later turns.** Later turns' first run-outs still replay (CHANGES 217); their tails run on with no
  stale check after the farm loop (`farm_attack_tiles`, the walk search), up to ~75k of the next round wasted. A
  check there changes nothing at 100M.
