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

## Ship it?

Yes as a separate merge for next tournament:
- It wins the-pack family clearly (vs v68 50.6 -> 77.3 on fam2; 02the-pack 4/4 against v67 and v68), and it is the
  answer to ladder opponents who enter.
- It is level elsewhere at the real budget, with out-of-fuel turns unchanged.
- It is inert off sealed maps (identical replays at unlimited fuel).

Before shipping: an SPRT or a 20k-game A/B on held-out suites, and the fixes below.

## Next steps

- **topo-web** (12 differing games, 3 won against main's 5): there the seal is a lone Elk in a one-wide corridor
  (gen-topo-web-9891006307). Clearing it is cheap, gives gold and gems, and opens the walk both ways; a hop costs a
  crystal and a recall a bank. Price the hop trip against clearing the cut: its live health over our output, plus its
  fire, by the existing siege/breach model.
- **Locks inside:** both teams lock the altar, so a champion that teleports in can't tribute until it breaks the
  lock, and two teams' champions end up in the pocket together. pack-m4 (6 champions a side) ran out of fuel in
  'R' (retreat) turns about once every two turns there. Never lock an altar whose only access is a camp hop while we
  bank there ourselves, or count the 5 hits into the hop's price (`lock_turns` does).
- **Wake reach without sight:** a teleport seen at its start, or a rise in the enemy's tributed score, means an
  enemy is in the pocket. A ward there would let `wake_ring` act without direct sight.
- **Corners first:** prefer landings with fewer members in reach (29 on corners against 32 on edges) when the ring
  might wake.
- **Prepare on the ladder:** of the ladder teams, conqueror_of_openai enters, and NEETCoders wake rings; both should
  be in a gauntlet before shipping.
