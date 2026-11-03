# Altars sealed inside a camp ring (02the-pack)

2026-11-03, branch `worktree-agent-a07cdc716d2b42e37` (astraeus from main f22811d1). On the ladder v68 went 0-10 on
02the-pack. Its only altar, (22,22), sits inside a closed ring of one 48-wolf group (64,800 health). We never buy a
crystal and hold our bags all game, while opponents teleport onto a tribute tile and score.

## The map

The pocket inside the ring is 12 tiles: the 8 tribute tiles plus (20,22), (24,22), (22,20) and (22,24). Every one of
them is a crystal landing, with 4-11 outside sources each (within 3, terrain ignored). Wolves have Strength 20 and
reach 3.

| Tile | Members in reach | Fire a camp phase, ring awake |
|---|---|---|
| edge tribute tiles (21,22), (22,21), (22,23), (23,22) | 32 | 640 |
| corner tribute tiles (21,21), (21,23), (23,21), (23,23) | 29 | 580 |
| the four outer pocket tiles | 26 | 520 |

- **Opponents** (ladder `2134ac16`, conqueror_of_openai): 25+ crystal trips, always onto (23,21), (23,23), (24,22) or
  (23,22). They tribute 4-175 gems at a time (channels of 1-18 turns), from round 74 to their 1001-gem win at round
  1464, and never wake the ring.
- **Deaths inside:** in 9 ladder the-pack games, 10 champions died to the ring inside it, with bags of 0-962. In
  `9a0fca24` at round 740, NEETCoders' Vesper woke the ring from (18,15) with both teams' champions inside, and both
  champions died within 6 rounds.

## Rules analysis

### 1. Inside when the ring wakes

- **Who wakes it:** only damage or a stun to a member wakes a group (`camps.wake`); proximity never does. That means:
  - an enemy's basic attack (reach 1 or 3) or unit spell on a member;
  - any ground spell whose 3x3 covers a member, i.e. a caster up to 5 from it, through walls and unseen
    (`abilities.ground_target`);
  - Varg's splash, or Heart of Ruin's dash landing;
  - an enemy inside hitting a wolf;
  - our own stray hits. The prototype never targets the ring while inside.
- **Time to die:** the ring deals 520-640 a phase (364-448 against a Jungle emblem). A champion dies in the phase
  where the summed fire reaches its health:
  - Cassi (600): 1 phase on an edge tile, 2 on the others.
  - 700-1200 health: 2 phases.
  - ~2000 health (shards): 4 phases.

  Members never move.
- **Tribute against death:** damage does not interrupt a tribute. A channel of b turn ends started in round t
  completes at the turn start of round t+b, after the camp phases of rounds t+1 to t+b. It scores only if b phases'
  fire stays below the champion's health:
  - at 1200 health on a corner tile: b = 2 (1160 < 1200), so bags up to 20;
  - on an edge tile: b = 1, so bags up to 10.

  Anything bigger dies with the bag, and a camp kill gives the gems to no one (`combat.camp_kill`). Locally
  (v5b against v4, 02the-pack, round 570): a champion on (20,22) took 360, 460 and 240 and died in the third phase.
- **Escapes:** none once the ring is awake.
  - A second crystal: a champion carries 1, buys it only on spawn or while dead, and spent it getting in.
  - Recall: 5 turn ends, cancelled by any damage, and the ring hits every phase.
  - Dash: 2 steps that may not cross visible camps (all are visible from inside), and the ring is 2 thick almost
    everywhere.
  - Killing a way out: one 1350-health wolf, under 520+ damage a phase.
  - Sleep: needs 2 phases with no champion in a member's reach, and we are in reach.

  So a woken ring with us inside is death, and the bag scores only if its channel ends first.
- **When going in pays:**
  - Exposure: the teleport channel (3 turn ends) plus the tribute (b turns) risks the bag. The recall out (5 turns)
    risks only the champion: it carries no bag, and a camp kill gives no kill gold.
  - Threat: an enemy reaching a wake tile within 3 + b turns. A ground-spell caster must be within 5 of a member
    (about 9 from us, since the ring's outer edge is about 4 from the tribute tiles); a ranged attacker within 3.
  - Bag size: small bags often keep 3 + b short (the ladder winner's channels were 1-6 turns). A 1000-gem bag
    (b = 100) is a gift to anyone who walks up.
  - Cost of a trip: 10 gold, plus a recall (5), the walk from spawn to a source (~6), the teleport (3) and b: about
    14 + b rounds on this map (spawn x 9-11, ring x 18-26).

### 2. The mirror: waking the ring on an enemy inside

- **Who takes the fire:** each awake member fires at the nearest champion in its own reach, and ties go to whoever
  acts first in that round's turn order. The enemy inside is within 3 of 26-32 members. On 02the-pack (computed from
  the map):
  - **Ground spell** (Stellar, Prism, Ryth: range 4, area 1): 136 tiles from which the 3x3 covers a member while no
    member reaches the caster. That is 0 fire on us and 520-640 on the enemy.
  - **Ranged basic attack** (reach 3, the same as the wolves'):
    - Enemy on a corner tribute tile or an outer pocket tile: some tiles take 0 fire, e.g. (28,17) and (27,16) for
      (23,21), or (18,15) for (22,20), the tile NEETCoders used.
    - Enemy on an edge tribute tile: the best tile takes one member's fire (20 a phase) for the phase or two the
      enemy lives. Then one step back leaves every member's reach, and the members near us fall asleep after 2
      phases.
  - **Melee:** adjacent to a member puts us nearest to it and its neighbours, so there is some fire, but little
    (a few wolves at 20 each).
- **The race:** the enemy dies in 2-4 phases, and its bag is lost unless its channel ends first (bags up to 10-20 at
  1200 health). Our hit does not cancel its tribute, since damage never does, and Marcella's stun immunity does not
  help.
- **Seeing them:**
  - Camps never block sight; only walls and bushes do. The pocket on 02the-pack has no bushes, so the enemy is
    visible from the wake tiles (5-6 away) unless a bush lies on the line.
  - Without sight: a teleport seen when it starts reserves its landing (World tracks it), and a ward (radius 6)
    placed within 2 of us sees the pocket from any wake tile.
- **Is it clean and cheap?** Yes. The fire on a tile is exact by the rule (nearest in reach, ties counted against
  us). It is computed only on maps with a camp hop, and only while an enemy carrying gems is seen in the pocket.
  Prototyped as `wake_ring` (below).

### 3. Trade-offs

- **Crystal:** 10 gold and carry 1, bought on spawn. On 02the-pack each bank costs one recall plus one crystal. Our
  income there is 2-4 gold a round (25 gold clusters), so a trip costs about 3-5 rounds of gold.
- **Score swing:** without crystals we tribute 0 and gold decides the game. With them, we usually win the race to
  1000 gems, by round ~800-1250 (below).
- **Waking risk:** an enemy needs to be within about 5 of a member during our 3 + b turns, and the mirror makes the
  wake free for them. Short channels bound the risk; the prototype also gates on it (below).

## The code before (main f22811d1)

- `StaticMap::foot()` (model/world.h:133): our walk from spawn, with every camp counted as cleared.
- `StaticMap::make_hops` (model/world.cc ~487): builds an altar hop only when the altar's tribute tiles are off
  `foot()`, i.e. cut off by terrain. A camp ring leaves them on foot, so there was no hop.
- `rebuild_altar_access` (economy/bank.cc ~185-290):
  - `open` holds the tribute tiles off live camps.
  - It drops the tiles that are on the static walk but off `altar_walk().ours`, the walk with live camps as walls.
  - With nothing left open, it lists the blocking groups (`blocks`). `altars_sealed` then holds, and siege/kite
    target the ring.
  - `siege_load` (siege.cc ~22) prices all 48 members, so the siege never passes `siege_ready`.
- `Pathing::to_any_altar` / `to_altar` (pathing.cc 186-193) price static walls only: 8 steps from outside the ring.
  `bank_gems`, `recall_to_bank`, `bankable_bag` and `closing` read these fields, so a hop (12) could never beat the
  walk (8), even with the altar open.
- `hop_route` / `take_hop` (bank.cc):
  - The price of a hop: walk to a source + 3 + walk from the landing + locks + recall.
  - It lands on the free tile nearest the altar, out of visible enemies' strike + 3.
  - Once `wants_crystal` is set, every spawn visit buys a crystal (shop.cc:76).
- Pockets: `continue_recall` keeps the turn-end recall while we are off `foot()`, and farm uses `beyond_walk`.

## The prototype (branch commits 08f73231 .. 6d630b47)

1. **Camp hops** (`StaticMap::make_hops`, `Hop::camps`):
   - Which altars: one whose tribute tiles (off camp tiles) are on foot but off the walk with every camp standing.
   - Its hop: pocket = its region with camps as walls; landings = pocket tiles within 3 of that walk; sources = that
     walk's tiles within 3 of a landing.
   - The draft flags such maps (`PlanHeader::camp_sealed`, plan version 9), so other maps make neither the flood nor
     the hops early.
2. **Access** (`rebuild_altar_access`):
   - A camp hop keeps its pocket's tribute tiles (off live camps) open, so `any_open` holds and the ring is no longer
     a siege target.
   - `access_fire` still prices awake members on those tiles, so `altar_usable` refuses a stirring ring.
3. **Walk or hop** (`altar_walked`, `altar_steps`):
   - A walk to an altar counts as none while no open tribute tile of it lies on `altar_walk().ours`. From inside a
     pocket, the pocket's own steps count.
   - Read by `bank_gems` (also per locked altar), `recall_to_bank` and `bankable_bag`.
   - Without a crystal, `bank_gems` heads home for one, by walking or by the turn-end recall when that is sooner.
   - `recall_to_bank` no longer recalls a champion that already carries one.
4. **Entry gate** (`ring_quiet` in `take_hop`):
   - No crystal goes in while an enemy seen this round or last is within its wake reach of a live ring member plus
     3 + b turns. Its wake reach is the larger of its basic-attack reach and its spells' reach.
   - A refused hop does not stand on the source, which is inside the ring's reach. The bag is held back
     (`bankable_bag`) for the 3 + b rounds the trip would have taken, and the champion farms meanwhile.
   - A first version waited on the source, and on mirror maps both teams' waiters blocked each other all game.
5. **Leaving** (`sealed_in`): in a camp pocket off our walk, `decide` ends the turn once the bag is in, so the
   turn-end recall goes out, and `continue_recall` keeps it, as it does for terrain pockets.
6. **A woken ring with us inside:** `continue_tribute` keeps the channel when we are damaged and sealed in. Neither
   fleeing nor fighting saves the bag; only the channel's end can.
7. **Waking the ring on an enemy** (`wake_ring`, after banking in `decide`). It acts only when all of these hold:
   - a visible enemy carrying gems is in a camp pocket, and the ring is asleep;
   - no ally of ours is in a live member's reach;
   - the ring kills the enemy (health / fire on its tile, in phases) before its tribute channel ends.

   It then hits a member, by basic attack or a ground spell, from a tile where the members that could pick us (as
   near us as the enemy) fire less than our health in a phase. Failing that, it walks to the nearest such tile.
   The tiles and their field are cached while the prey, the live members, our reach and our health stay the same.

Everything is inert on maps without a camp hop (`any_camp_hop()` reads the draft's flag first).

## Measurements

Fast runner, own drafts (`--no-test-draft`). Frozen main is `variants/astraeus-main-f22811d` (main f22811d1, which
had not moved when the runs started).

**Sealed-map families.**
- **fam2:** 77 maps. 15 are every gen, gen-s1 and ladder map where mapgen reports an altar enclosed by camps
  (01boss-battle, 02guardians, 02the-pack, 03the-front, gen-fortress, gen-topo-*, mut-the-pack, archipelago). The
  other 62 are `mapgen mutate 02the-pack --seed 1..80` mutants that kept the ring.
- **fam3:** the 33 maps of the A/B suites where every altar is enclosed by camps.

Both sides of each map, 154 + 66 games:

| Bot | vs v68 | vs v67 | vs main |
|---|---|---|---|
| main f22811d1 | 50.9 (fam2 50.6) | 49.5 (45.5, 59.1) | - |
| v1: camp hops (08f73231) | fam2 79.2 | fam2 60.4 | fam2 75.3 |
| + entry gate (52a682c2) | fam2 79.2 | fam2 63.0 | fam2 76.6 |
| + draft flag (fce4ef09) | 70.9 (77.9, 54.5) | 59.5 (60.4, 57.6) | 68.6 (76.0, 51.5) |
| **+ wake_ring, refusal fix (6d630b47)** | **70.9 (77.3, 56.1)** | **57.7 (57.1, 59.1)** | **68.2 (74.0, 54.5)** |

- **02the-pack itself:** 4/4 against v68 and 4/4 against v67, both sides. Main went 2/4 against each, in 2000-round
  gold games.
- **Waking, against a bot that enters** (6d630b47 vs the hop-only fce4ef09, 220 games): **59.5%** (fam2 63.6). Over
  fam2's 152 games, the hop-only bot lost 320 champions and 15,357 gems to camps, against 140 champions and 7,965 gems
  for ours. Tributed gems were 121,035 for ours against 99,622 for the hop-only bot.
- A siege-keeping variant (0c8cb017, reverted) kept the ring a siege target while the hop banked. It was slower on
  the-pack mutants (games 1100-1500 rounds against 800-950) and level elsewhere.

**A/B against frozen main:** 21 suites, `maps/fresh-98901` .. `98920` plus `fresh-ladder86`; 10,412 games; real
budget.

| Candidate | Win % | 95% CI | fresh-ladder86 | Out-of-fuel turns (cand / main) |
|---|---|---|---|---|
| 08f73231 (camp hops) | 50.8 | 49.8-51.7 | 50.0 | 56,122 / 53,803 (+4%) |
| 52a682c2 (+ gate) | 50.8 | 49.8-51.7 | 50.0 | 56,209 / 53,950 (+4%) |
| fce4ef09 (+ draft flag) | 50.1 | 49.1-51.0 | 51.2 | 55,406 / 55,320 |
| **6d630b47 (final)** | **50.3** | 49.3-51.3 | 50.6 (87-85) | 55,113 / 55,400 |

- **Out-of-fuel turns:** the +4% of the first two came from `any_camp_hop()` making `foot()` and the hops early on
  every map. The draft flag removed it.
- **Against v68 and v67** (final vs main, same suites): v68 50.3 against 49.9, and v67 65.7 against 65.7.
- **Maps that differ:**
  - At the real budget, 40% of games differ from main's against v68 (4,217 of 10,412, on 2,910 maps), but with
    flips even (559 to a win, 523 to a loss). Fuel noise: any code change shifts fuel-gated choices.
  - With fuel unlimited (`--fuel 100000000`), **101 games on 53 maps** differ, all sealed-altar families. The final
    bot won 50 of them and main 49. By family:
    - mut-the-pack: 14 of 17 games against main's 8;
    - topo-web: 3 of 12 against 5;
    - fortress, archipelago, topo-shortcut, topo-split: level.
- **Fresh suites, every altar enclosed** (33 maps, 66 games): 54.5% against main, 56.1% against v68 (main 51.5%).

## Second pass: audit and follow-ups (2026-11-03)

Branch `worktree-agent-a7b8af1f6caa6df5e`, on the prototype (713756ae): commits 6ec15309 (audit), 07835264 (seals
stay siege targets), eb1431f6 (siege stall). Fast runner, own drafts.

### Audit of the prototype

**Sound, kept as it was.** All of these hold against `cambc-rules.yaml`:
- **Rules analysis:**
  - `camps.wake`: only damage or a stun wakes a group.
  - `camps.attack`: the nearest champion in reach, ties by turn order.
  - `gems.tribute`: damage does not interrupt a tribute, and a channel started in round t ends at the turn start of
    t+b, after the camp phases of t+1..t+b.
  - `combat.camp_kill`, the teleport's 3 uncancellable turn ends, the recall cancelled by damage, and a dash that
    cannot cross visible camps.
- **`wake_ring`'s timing:** it skips a prey whose channel ends before the ring's fire kills it (`channel < phases`).
  That is exact, since a prey that dies in the camp phase of its end round never reaches the turn start that would
  score.
- **The camp hop itself:** `make_hops`, the access it opens, `altar_steps` and `altar_walked`.
- **The pocket's exits:** the `sealed_in` turn end, `continue_recall`'s pocket rule (off `foot()`, or sealed in on
  it), and `continue_tribute` keeping a damaged channel. All of these extend the terrain-pocket code rather than
  run beside it.
- **The draft flag:** the header layout changed and `plan_check` hashes `current_version`, so the bump to 9 is
  needed; `bits` counts the new flag.
- **The entry gate's hold:** `ring_refused_until` is a module global set in `bank_gems` and read in
  `bankable_bag`, but it does a job nothing else does. It is hysteresis after a refusal. Re-testing `ring_quiet`
  each turn in `bankable_bag` instead would oscillate: farming away, we stop seeing the enemy near the ring, walk
  back, see it, and leave again.

**Changed (6ec15309).** At unlimited fuel against the prototype on fam2 + fam3, the structural part reads exactly
50.0% (every map 1-1), so it is logic-neutral; the whole commit reads 51.4%.
- **Duplicated test:** the draft's `camp_sealed()` repeated `make_hops`' test. `PlanHeader::camp_sealed` now reads
  `any_camp_hop()` of the draft's undrafted map, which makes every hop. That is one definition, and the flag is now
  also clear when a sealed altar has no landing.
- **`ring_groups()`:** it rebuilt the ring with a dilate and a scan on every call and returned a static vector.
  The groups are now `StaticMap::Hop::ring`, made once in `make_hops`. `any_camp_hop()`, read every turn, looped
  the hops; `make_hops` now caches it.
- **`wake_ring`:**
  - `c.awake != Awake::asleep` also returned on `Awake::unknown`, a ring out of sight. A champion therefore never
    walked towards a ring it could not see. Now only a known-awake ring stops it.
  - The prey was any visible enemy in the pocket. It is now any enemy believed in the pocket:
    - seen there;
    - unseen there with its tile out of our vision, for fewer rounds than its recall takes (no walk leaves);
    - or seen teleporting there. That prey is walked towards and hit only once it lands: a ring woken early sleeps
      again 2 phases after no champion is in reach.
  - An enemy last seen tributing past its channel's end counts as banked.
- **`take_hop`:** of the landings nearest the goal, it takes the one the hop's ring reaches with the least Strength
  (corners 29 members, edges 32). On terrain hops every landing scores 0, so their choice is unchanged.
- **`bank_gems`:** with no walk to an altar and no crystal, the bag walks home for one, or the turn-end recall
  takes it. This was gated on `any_camp_hop()`; it now holds for every hop. A terrain pocket's altar field reads
  unreachable, so before this it took no step at all.

**Tried and dropped** (fam2 + fam3, 220 games against the prototype, fuel unlimited to separate logic from fuel
noise; together they read 42.3%, and 40.0% at the real budget):
- **The lock's 5 hits in the gate's window** (`ring_quiet` over 3 + lock + b turns): 47.7%. The gate already
  refuses broadly, and a longer window refuses more.
- **`home_trip` and `closing` through `altar_steps`**, so that `recall_to_bank` needs no camp-hop line: 46.4%.
  From spawn, the static walk (about 10 steps) is closer to the real hop trip than "unreachable", which made every
  home trip read useless. So `recall_to_bank` keeps its line ("on our walk with a crystal, the hop is the trip").
  The proper fix is a hop-aware home trip: from the landing, the walk or the hop, whichever is shorter.
- **No lock of our own on an altar only a camp hop reaches:** 50.0% at unlimited fuel and 47.3% at the real
  budget. There is no evidence for it, so it was not added.

### Clearing a seal or hopping it (07835264)

The prototype opened a camp hop's altar outright. The groups in its way therefore stopped being seals, and
`siege_ready` (whether the team clears a group within `siege_rounds` at a cost in health it can take) never judged
them again. A lone Elk in a corridor (topo-web) was hopped forever.

Now `AltarAccess::camp_hopped` marks an access whose only open tiles are a camp hop's. The blocks are listed as
for any seal, and `altars_sealed` holds. So the hop banks while the siege rule, the one main used for every seal,
decides whether clearing pays:
- **02the-pack:** the 48-wolf ring never passes.
- **A lone Elk:** it passes once the team is strong enough.

This is 0c8cb017 again (the prototype reverted it as slower on the-pack mutants). Here it is level: 49.1% against
the audit commit at the real budget and 52.0% at unlimited fuel, over fam2 + fam3 + fam4 (458 games).

It does re-expose a stall that main already had (eb1431f6, below). On fam4, its siege-branch turns rose from 7.5%
to 17.4% of ours, and games where our whole team ends in the siege branch for its last 300+ rounds rose from 4 to
9. Main had 8.

**The breach.** Killing one wolf, for example (25,21), opens a walk to a tribute tile. There are 8 such
single-member cuts, the ring's corner wolves. The best tile to shoot one from at range 3 is in reach of 3 other
members (60 a phase); adjacent, 14 (280). A siege priced on the cut (one member's 1350 health, and the fire on its
attack tiles rather than all 48 members' Strength) would pass mid-game.

It was not built:
- **It gives the edge away.** The gap opens a walk for the enemy too, since our side's corner is reachable from
  theirs. Against an opponent that does not hop (v68 and main, which never enter), that hands over the altar the
  crystal edge holds for us.
- **It is a different siege.** It needs a member target (`SiegeTarget`, `siege_load`, attack tiles, `attack_camp`'s
  choice) and a fire model per attack tile.

### Siege stall (eb1431f6)

On fam4's topo-backdoor maps, the stage tiles around a sealing pair of wolves lay beyond a row of gem and gold
clusters. Two things combined:
- `Pathing::route` stops at the depth the turn's fuel pays for.
- `step_towards_funded` reports only that no step was taken.

So `siege()` returned true every turn with the whole team on spawn, from round ~350 to 2000. Main does the same on
those maps.

The fix: a siege still gathering (not engaged) whose step towards the gathering tiles fails gives the turn to farm.
Farm's camps may be what holds the way.
- **Stalls on fam4:** from 9 to 2; siege-branch turns from 17.4% to 13.7%.
- **On the A/B suites:** stalls are rare (6 in 4,608 games, all shared-gems kites and one archipelago), and the
  same for both bots.

### Results

**Sealed families**, 458 games (fam2 and fam3 as above; fam4 is 119 new maps whose every altar mapgen reports
enclosed by camps, from `maps/fresh-73001..73080`, in `scratchpad/s2/fam4`). Real budget:

| Bot | vs main | vs v68 | vs v67 |
|---|---|---|---|
| main f22811d1 | - | 48.5 (fam2 50.6, fam3 51.5, fam4 46.2) | 55.7 (45.5, 59.1, 61.3) |
| prototype 6d630b47 | 58.7 (74.0, 54.5, 50.0) | 60.0 (77.3, 56.1, 50.0) | 56.8 (57.1, 59.1, 55.9) |
| **final eb1431f6** | **63.3** (76.0, 57.6, 56.7) | **59.8** (76.0, 53.0, 51.3) | **60.9** (57.1, 62.1, 63.0) |

- **Final against the prototype:** 48.0% at the real budget, 53.7% at unlimited fuel (fam4 53.8).
- **By family against v68:** the gain is the-pack's. On fam4's 18 held-out the-pack mutants (36 games), main won
  56%, the prototype 94% and the audit commit 87%. Other families are level within their small samples.
- **02the-pack**, both sides:
  - against v68: won 2/2, at rounds 1388 and 783;
  - against v67: won 2/2, at 2000 on score and at 929;
  - main split 1-1 with each, in 2000-round games.

**Broad A/B against frozen main** (`variants/astraeus-main-f22811d`), on `maps/fresh-99601` .. `99640` plus
`fresh-ladder86` (20,652 games, real budget):

| Candidate | Win % | 95% CI | fresh-ladder86 | Out-of-fuel turns (cand / main) |
|---|---|---|---|---|
| 07835264 (audit + seals) | 50.0 | 49.3-50.7 | 52.9 | 109,034 / 108,252 |
| **eb1431f6 (final)** | **50.1** | 49.4-50.7 | 52.9 (91-81) | 110,027 / 108,437 (+1.5%) |

- **Against the baselines, same suites:**

  | Bot | vs v68 | vs v67 |
  |---|---|---|
  | final | 50.1 (ladder86 50.6) | 65.9 (ladder86 69.8) |
  | main | 49.9 (ladder86 48.8) | 65.6 (ladder86 69.2) |
- **Fuel unlimited** (`--fuel 100000000`):
  - 50.0% against main.
  - Maps one bot won from both sides, where the logic must differ: 48 for ours and 51 for main's, out of 10,326.
    They are spread over the sealed and hop families: atoll 4-10, topo-backdoor 6-4, mut-the-pack 6-4,
    fortress 3-5.
  - atoll checked on 300 held-out atoll maps (`fresh-730xx`): 50.3%, with sweeps 7-5. The 4-10 was noise.

### Ship it?

It is level on the broad suites and +4.6 over the prototype against main on the sealed families. It keeps the
prototype's the-pack gain, and fixes a stall main also has.

Before shipping:
- a 20k A/B on other held-out suites;
- a gauntlet against ladder-style opponents. The ones used here are the prototype (it enters and wakes) and main
  and v67/v68 (neither); conqueror_of_openai and NEETCoders themselves were not available.

### Still open

- **A hop-aware home trip:** `home_trip`'s walk from spawn, `closing` and farm's bank pricing read the static
  field, which ignores the ring. Pricing the hop from the landing would remove `recall_to_bank`'s camp-hop line.
- **The breach** (above): a member-targeted siege. It is worth it only where the gap does not open the altar to the
  enemy as well, or against opponents that hop anyway.
- **Out-of-fuel turns:** +1.5% on the broad suites; pack-m4's crowded retreat turns are not looked at.
- **The siege's reach:** a seal whose stage tiles are beyond the route search's fuel-paid depth is now left to
  farm, but no siege yet routes there in steps over several turns.
