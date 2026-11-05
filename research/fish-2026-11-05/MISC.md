# Fish: shopping, altar locks, teleports, wards and the opening (low-hanging rules)

Five behaviours, each with the exact rule (or the best partial one), its accuracy with
denominators per cohort, and kept counterexamples. Data: all five decoded cohorts (403 games,
engine `v3_0_0`): `model` 124, `confirm` 96, `third` 43, `fourth` 46, `fifth` 94. Item purchases
come from `drafts-emblems-games.json.gz` (four oldest cohorts only); everything else from the
actors' own cached perspectives, except the lock table in section 2c (observer, see there).

**Independence.** The rules in sections 1, 2b, 2c, 3 and 4 were found by looking at all five
cohorts, so the per-cohort counts show that they hold everywhere, not that they were confirmed
on held-out data. The lock-map threshold (2a) was read off the four oldest cohorts' maps and
then checked on the maps seen only in the fifth cohort. Counts are turns or events, which are
correlated within a game. They are not independent trials.

Scripts (new, `tools/fish/misc_*`): `misc_rows.py` (compact per-turn rows →
`replays/fish-misc/rows-v1.jsonl.gz`), `misc_common.py`, `misc_shop.py`, `misc_consumables.py`,
`misc_locks.mjs` (raw-replay lock table → `replays/fish-misc/locks-v1.json.gz`),
`misc_lockplace.py`, `misc_wards.py`, `misc_opening.py`. Results: `misc-shop.json`,
`misc-consumables.json`, `misc-lockplace.json`, `misc-wards.json`, `misc-opening.json` in this
folder, each with its counterexamples. The scripts refuse to overwrite their output.

## 1. Shopping: where, when and how much (exact)

**Rule.**

```text
at the very start of its turn (before any walk, attack or cast; 13,389/13,389 shop turns):
  if dead, or alive on a tile of Fish's spawn box:
      buy a teleport crystal (on crystal maps, condition unknown: section 3)
      buy an altar lock if lock map (2a), not carrying one, and (gold - 10*crystals) mod 30 >= 10
      buy floor((gold - 10*consumables) / 30) shards in the known build order (DRAFTS-EMBLEMS.md)
Fish's spawn box = the spawn itself (see the correction below).
```

**Correction (coordinating session): the "box" is simply the spawn.** The cached `spawnA`
bounds are half-open: `maxX - minX` is 3 on 3x3 spawns, 4 on 4x4 (`breadth.spawn` uses
`range(minX, maxX)`). `misc_rows.spawn_tiles` read them as inclusive, so its "real spawn" adds a
row and column of ordinary tiles outside the spawn. On the sixth cohort, injured Fish champions
ending a turn on those "edge" tiles are not healed by the next turn (196/199; the 3 are likely
Willow heals). On box tiles they are healed or are being hit (spawn camping). So there is no
engine or Fish off-by-one: **Fish shops at the start of every turn it begins on its own spawn
or dead, with gold >= 30.** Sixth cohort, checked independently: 1,666/1,666 on spawn shop,
0/216 on the adjacent edge. The "always shops on spawn" baseline row below is therefore not a
baseline: its misses are the off-spawn edge tiles. Other uses of `on-own-spawn` flags from
`misc_rows.py` (lock-map distances, opening) inherit the same widened spawn; the lock-map gap
uses walking distance and is likely barely affected, but it was not re-run.

| Test (all cohorts) | model | confirm | third | fourth | fifth | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Alive, turn starts on real spawn, gold >= 30: shops iff in box | 3923/3927 | 3382/3382 | 1301/1301 | 1452/1452 | 3170/3170 | **13,228/13,232 (99.97%)** |
| Baseline: always shops on spawn | 3634/3927 | 3057/3382 | 1222/1301 | 1354/1452 | 2781/3170 | 12,048/13,232 (91.05%) |
| Dead with gold >= 30: shops | 232/232 | 249/249 | 85/85 | 114/114 | 154/154 | **834/834** |
| Alive, whole turn off spawn: never shops | | | | | | 1,715,297/1,715,297 |
| Gold after a shop turn < 30 | 4061/4062 | 3420/3420 | 1342/1342 | 1516/1516 | 3049/3049 | 13,388/13,389 |
| Shards = floor((gold - 10 x consumables)/30) (item logs) | 4062/4062 | 3420/3420 | 1342/1342 | 1516/1516 | n/a | **10,340/10,340** |
| Lock bought iff rule above (lock maps, not carrying) | 1161/1162 | 940/941 | 334/334 | 390/390 | n/a | **2,825/2,827 (99.93%)** |
| ... of which crystal turns | 69/69 | 42/42 | 14/14 | 1/1 | n/a | 126/126 |

So the purchase order is crystal first, then the lock, then shards with whatever is left.
Nothing is ever kept back to complete an emblem.

Counterexamples: `191044e1322b831b` r411-414 actor 1 (Vendetta, 125 gold, inside the box at
(22,16), four turns without shopping; the only box failures). Lock rule: `d243b4879a26f105` and
`29fc06002174c15c`, both r36 actor 0 or 5 (Vesper Vale, 239 gold, 29 left over, no lock). Lock buying had
not started yet in those games (section 2a: 8 games start late). `8543fa95ef512a4d` r792 actor 0
(Marcella) ends a shop turn with 122 gold, presumably gold earned later in the same turn.

**Trigger for going home: not recovered.** The shop itself is a pure "on spawn or dead"
reflex. The decision to walk or recall home is still only the ROUTES.md forecast.

**vs astraeus** (`economy/shop.cc`): both shop on any spawn tile (the earlier "box" claim was a
decoder misreading; see the correction). Our bot also carries a lock and crystal by its own logic (section 2).

## 2. Altar locks

### 2a. Which maps: decided by map geometry, consistent per map

Lock purchases are all-or-nothing per map: 116/116 maps in the four item-log cohorts have
either every game with a lock bought or none. Bought-vs-placed agrees in 307/309 games, the
other two bought one and never placed it. In 202 of the 210 lock games the first lock is bought
at the first shop turn whose leftover is >= 10. In 8 games it starts later (r187-727) after
missed opportunities, e.g. `d411d0f6bd41627c` (01starvation, first r191), `56facc0d6a9c844a`
(04gem_caverns, r727). That later trigger is unknown.

**Feature.** Walking distance in king steps, with walls, holes and altars blocking and camps
not, from each spawn region to a tile beside each altar. Take the altar nearest our spawn and
set gap = enemy distance minus own distance. **Locks iff gap <= 4.**

| Threshold sweep (115 old maps) | 0 | 1 | 2 | 3 | **4** | 5 | 6 | 8 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Maps right | 91 | 105 | 107 | 111 | **112** | 112 | 109 | 106 |

- Old maps: **112/115** (baseline "always lock" 76/116).
- Held-out maps seen only in the fifth cohort: **7/7** (baseline 5/7). This is a small check.
- Errors: `04yin_yang` (gap 5, locks), `02the_pond` (gap 5, locks) and `02the_pack` (one
  altar, gap 0, never locks: 2 games). Gap 5 is ambiguous: 01elk_arena (mixed: the fifth cohort's
  game placed none), 00interlock and 01concentrated_wealth (none).
- Reading: Fish locks only when the enemy can reach our banking altar about as fast as we can.
  Every one-altar map locks except 02the_pack. Maps with an altar much closer to us never do.

### 2b. Where it is placed

Of 1,506 placements: **82% from distance 2** (the maximum), **66% at our nearest altar**
(rank 0 by our walking distance) and 27% at the second nearest. 722 (48%) are followed by the
placer's own tribute at that altar within 3 turns. 500 are made with no gems carried. Only 93
happen while an enemy is visibly tributing there. Locks are a pre-banking and
territorial move, not a reaction to enemy tributes.

### 2c. When a carried lock is placed (`misc_locks.mjs` + `misc_lockplace.py`)

Opportunities: completed turns of an alive Fish champion that carries a lock (or places one)
and ends within 2 of an altar without Fish's lock. Turns that start channelling a tribute or
teleport, or stunned, are excluded (15,211). So are turns where every altar within 2 already
has Fish's lock (35,873), since a second lock there is illegal. The lock table is the
observer's: a lock within 2 tiles is almost always in the actor's sight, but this is still a
labelling proxy.

**Rule: place iff some altar within 2 has no lock of either team.** With only an enemy lock
on it, Fish nearly never adds its own (58 of 2,152), although the rules allow one lock per team.

| | model | confirm | third | fourth | fifth | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Rule | 902/1053 | 1029/1174 | 301/351 | 603/655 | 675/802 | **3,510/4,035 (86.99%)** |
| Baseline: never place | 597/1053 | 774/1174 | 229/351 | 482/655 | 479/802 | 2,561/4,035 (63.47%) |

Errors: 467 lockless-altar turns without a placement. Examples: `a01c1f9f1c54417d` r582
actor 0 (Marcella, 108 gems, then tributes unlocked at (40,7)), `f983f4e8efc50a51` r434 actor 1,
r491 actor 5. There are also 58 placements beside an enemy lock (`f983f4e8efc50a51` r364
actor 0). Fish's lock memory (a lock it believes is still there) is the likely missing input.

**vs astraeus** (`economy/bank.cc` `place_lock`): we skip only altars with our own lock. Fish
also skips any altar that holds an enemy lock, and buys locks only on gap <= 4 maps.

## 3. Teleport crystals: fixed wall-crossing hops (descriptive, near-exact geometry)

- Crystals are bought on 17 of 116 maps (item logs), never on the other 99. On 8 of the 17,
  one is bought at every shop turn without one (00pilgrimage 214/214, 02tangle 161/161). On the
  other 9 they are sporadic (04braided_river 21/141, 01islands 2/222).
- Of 883 teleports, **881 are to a tile exactly 3 away** (Chebyshev), the maximum. For **744
  (84%)** the walk between the two tiles is >= 40 steps or impossible, and for 75 it is 12-39.
  64 are 3-step walks, probably blocked by camps or units, e.g. `6c26dc26b28e0957` r265 actor 2.
- The hops repeat: 255 distinct (map, from, to) hops cover the 883 uses. Examples:
  02tangle (12,26)->(9,29) 50 times and (87,53)->(90,50) 47 times, 00pilgrimage (9,47)->(12,45)
  48 times. These are precomputed per-map shortcuts across walls, not combat escapes: 113 of 738
  (15%, four item-log cohorts) are taken with an enemy visible.

Open: which maps get crystals, and when a carried crystal is used. Our bot's `buy_crystal` uses
a similar "hop only a crystal reaches" idea.

## 4. Wards: partial (cadence and tile choice approximate; one exact quirk)

- **Teammates' wards: exact quirk.** 32,417 failed inputs target a tile 2 away. **32,015
  (98.76%)** of them are a teammate's current ward tile. Fish does not track allied wards and
  keeps choosing a tile a teammate already holds (placing onto an unseen allied ward fails
  silently). After such a failure it places elsewhere on 2,489 turns and gives up on 27,187.
  This also makes the opening diverge (section 5). astraeus has the same collision and retries
  up to 3 tiles (`bot.cc` `ward_bushes`).
- **Geometry.** Of 42,469 placements without an earlier cast or teleport in the turn:
  distance 2 in **88.73%**, a bush tile in **78.80%**.
- **Tile score.** Score each legal tile within 2 by its new bush tiles: bush tiles in the
  ward's 13x13 shadowcast that the actor's own 17x17 sight and its current ward do not see
  (`tools/replay/narrative/vision.py`). On turns with a positive best score:

  | | model (40 games) | fifth (40 games) |
  | --- | ---: | ---: |
  | Chosen tile in the argmax | 1949/2428 (80.3%) | 2433/2831 (85.9%) |
  | Unique argmax hit | 755/2428 | 832/2831 |
  | Random legal tile in the argmax | 10.6% | 12.2% |
  | First, blocked attempt in the argmax | 1585/1719 (92.2%) | 2266/2467 (91.9%) |

  The tie-break among argmax tiles is not recovered: first or last in x-y or y-x lexicographic order gets 32-41%. The
  scored tiles win when farther away (dist 2: 1,321 of 1,674 tied cases).
- **Cadence: weak.** Gaps between an actor's wards: exactly 10 (placed on recharge) **21.5%**,
  10-12 33.8%, >= 60 13.9% of 48,197. With the ward ready and a positive score, Fish attempts
  a ward in 3,238 of 7,821 model turns (41%). With score 0 it attempts in 1.3% of 120,517, but
  those are still a third of its wards, many with an enemy in sight. A trigger is not recovered.

## 5. Opening: deterministic given the map, side and roster

Games are grouped by (map, Fish side, Fish roster): 99 groups, 259 pairs. Each actor's inputs
are compared round by round through round 300.

| Pairs with every actor's inputs identical through round | 1 | 5 | 10 | 20 | 50 | 100 | 200 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| of 259 | 236 | 223 | 220 | 179 | 142 | 66 | 25 |

- The median first divergence is round 53. 16 pairs never diverge through r300.
- **168 of 243 divergences come at or after the first enemy sighting.** The other 75 come
  before it: camp state changed by opponents, units unseen until a blocked input, or the
  round-1 cases below.
- The first camp group attacked, and the round of that attack, match for every actor in
  186/259 pairs (72%).
- **Round-1 divergences** look like a dropped priority write and the ward attempt with it,
  with the move and recall-start unchanged. In 04bridges, actor 5 (Willow) plays [Move,
  Set priority -6, ward attempt blocked, Recall] in `5e2578c38cc2fe3b` but [Move, Recall] in
  `5821412e3de0c8c4`. In 02fields and 02gift_wrapping only the priority write differs. Its
  priority then stays 0 for round 2, so it acts first among its team. The likely cause is
  exhausting the first-turn fuel, or opponent-dependent work, but this is not verified (fuel is
  not in the replay).
- Consequence: for a given map and side, Fish's first ~20 rounds (moves, ward tiles, first
  camps) can be read off one replay. This holds across opponents: only 3 of the 259
  pairs had the same known opponent draft.

## Not done

Tribute gem thresholds and altar choice, priority penalty-5 and the positive modes, Willow
following, and path tie-breaks were not examined. The home-trip trigger (as opposed to the
shop) is still open.

## Reproduce

```sh
python3 tools/fish/misc_rows.py replays/fish-misc/rows-v1.jsonl.gz --jobs 7
R=research/fish-2026-11-05
node tools/fish/misc_locks.mjs replays/fish-misc/locks-v1.json.gz --jobs 6 $R/manifest.json \
  $R/confirmation-manifest.json $R/third-manifest.json $R/fourth-manifest.json $R/fifth-manifest.json
python3 tools/fish/misc_shop.py $R/misc-shop.json
python3 tools/fish/misc_consumables.py $R/misc-consumables.json
python3 tools/fish/misc_lockplace.py $R/misc-lockplace.json
python3 tools/fish/misc_wards.py $R/misc-wards.json          # vision: 40 games each, model and fifth
python3 tools/fish/misc_opening.py $R/misc-opening.json
```
