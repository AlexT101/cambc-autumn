# Maps we do badly on (badmaps, 2026-11-11)

Brief: the tail of the user's ladder table (wheel 0% of 14, the_pack, waves, orchard, ...). Root causes as game
mechanics and map features, which of them 506 (live v115) still has, and fixes that hold on fresh maps.
Results of the candidates: [EXPERIMENTS.md](../../EXPERIMENTS.md) "Bad maps (ocean = 506, 2026-11-11)".
Notes for the big-group agent: [for-biggroups.md](for-biggroups.md).

## Data

- Live: v115's 512 pinned scrims (256 each against Fish r2 and Mite r6, all 128 maps, both sides), decoded with
  extract.mjs into `~/tmp-offload/badmaps/ext/`. Wheel's 29 distinct v105-v114 scrims are in `extw/`.
- Map-level history: v105-v115 scrims per map and opponent (`an/scrim-bymap.json`; many versions repeat games, so
  counts overstate the sample).
- Ladder: big-arm's archive (g_*, s_team, matches for 11-05 to 11-11, `archive/`); it holds almost nothing after
  11-10, so the user's exact table could not be rebuilt. `cambc matches list` answered 503 twice and was left alone.
- Local: 506 against `spar-dvn1-Mt3q` and `spar-dvn1-Flp4` on the 128 ladder maps (`extl/`).
- Scripts: `~/tmp-offload/badmaps/an/` (`lib.py`, `lib2.py`, `allacct.py`, `classacct.py`, `bankpol.py`, `poltab.py`,
  `prismdeaths.py`, `shortcut.py`, `tele.py`, `paired.py`).

## Wheel

Feature: all 4 altars and all 9 gem clusters (63 gems per 50 rounds, the main gem source) are inside one walled ring
with two 1-tile doors on the symmetry axis; wolves, an Elk and the gold are outside. Both teams farm gems and bank in
the same small area all game.

- v105-v115 scrims: Mite 0 of 26, Fish 6 of 22. v115: Fish 2/2, Mite 0/2. Ranked 11-08 to 11-10: 6 of 15 (losses to
  Mite 3, Fish 3, Ad Astra 2, test4 1). Locally 506 loses 0/2 to the Mite body and wins 2/2 against Flp4.
- 10 losses to Fish: we captured 1,091 gems to 703 and lost. We died carrying 422 gems a game (Prism 243), they 86.
- 15 losses to Mite: captures 685 to 788; we died carrying 303 (Prism 181), they 73; we tribute 15 times a game, Mite
  58 times at a median bag of 8.
- v115 against Mite, side b: captures 826 to 797; 345 of our gems went to Mite through kills, 127 came back. At r616
  Prism walked a 152-gem bag into the dead-end pocket on Mite's side and Mite's Vesper (10,700 hp) killed it in two turns.
- Late in those games we still take gold: with Mite at 600+ gems, 10-16 of our 24-36 captures were outside the ring;
  Mite's were 3-13 of 36-45.
- Mite crosses the ring wall with teleport crystals (5 and 12 hops in the two games), mostly its Vesper carrying
  54-120 gems from its outside camps into the pocket on its own side, 8 steps from an altar. From spawn that is 19
  rounds to an altar against 33 on foot through a door. We never use a crystal there.
- Mite's Vesper also takes ~1.5x our Vesper's gold from the start (r200: 1,768 against 1,049). We split captures
  between Vesper and Prism. This is the known gold-concentration gap, on every map.

## Shared causes (v115's 176 losses, `an/lossclass.pkl`)

| class | Fish (78) | Mite (98) | signature | maps |
|---|---|---|---|---|
| gem bleed | 35 | 27 | captures level or ahead, 80+ more gems lost on death than taken | wheel, the_pond, honeycomb, harvest, great_wall, collision, interlock, courtyard, bowls, shrines, elkring, bullseye |
| overrun | 18 | 20 | 15+ deaths, twice theirs, captures under 60% | ribs, gold_rush, horseshoes, sunburst (Fish), swirl / hooks / oasis (Mite), elk_arena, stampede |
| big groups | 15 | 17 | 150+ gems behind on Golem / Monolith groups, level elsewhere | rows, geodes, famine, fields, waves (Mite), twisty, gap, quadrants |
| out-farmed, other | 10 | 34 | few deaths, fewer captures | rushbait, the_pack, yellow_brick_road, canyons, gem_rush, expanse, vault / the_line (Mite) |

### Gem bleed

- Prism never banks (`retaining_gems`): mean bag while alive 138, median largest bag 300. It died with 40+ gems 131
  times in 384 games, 160 gems a time, 101 of them in losses (Fish 85, Mite 46). 113 of the 131 had an enemy in
  sight two rounds before with health running down (median 15% the round before): lost fights, not ambushes. 18 of
  the 131 bags took the enemy to 1,000 on their own.
- Other champions hold bags under `min_bank` = 25 whatever the walk to an altar. Fish and Mite bank by the walk, not
  the bag. Chance of a tribute before the next capture, by bag and Chebyshev distance to the nearest altar at capture
  (non-Prism, `an/bankpol.pkl`):

| bag | team | 0-3 | 4-6 | 7-10 | 11-16 | 17+ |
|---|---|---|---|---|---|---|
| 1-24 | us | 68% | 34% | 27% | 17% | 9% |
| 1-24 | Mite | 95% | 66% | 46% | 38% | 31% |
| 1-24 | Fish | 83% | 49% | 40% | 32% | 22% |
| 25+ | us | 98% | 96% | 92% | 91% | 89% |
| 25+ | Mite | 92% | 73% | 57% | 45% | 34% |
| 25+ | Fish | 88% | 72% | 59% | 48% | 32% |

- We lose a bag under 25 before banking it 7.7% (Fish) and 6.9% (Mite) of the time, a bag of 25+ 4.4% and 3.9%.
- Earlier work: Prism banking and hoard caps lost 3-9 points locally (psm50b, retain cap 150, "doubles its Focus");
  CHANGES 461 raised the floor by map features and lost live. Neither tried a lower floor near an altar.

### Body fidelity for bag changes (user: don't trust the local mirrors too far)

- Flp4 banks like live Fish (0-3: 87-94%; 4-6: 47-72%; 17+: 20-25%). Mt3q does not bank like Mite: it keeps our
  25-gem step.
- The bodies kill our carriers less often than the real teams: a bag under 25 is lost 5.4% / 5.7% of the time
  locally against 7.7% / 6.9% live; 25+ 2.6% / 2.5% against 4.4% / 3.9%. Our Prism's 40+ gem deaths: 0.25-0.30 a game
  locally, 0.34 live.
- So a local read understates what earlier banking saves, and says nothing about Mite's own banking.

### Overrun

One-site maps where the first team fight decides. 00ribs (0 of 4): every gem source and both altars are in one room
~60 steps from both spawns; we lose 4-5 champions at first contact (r86-r142) and are behind 220-596 gold to
814-1,102 by r300. Locally 506 wins there (3 of 4), so it is the real teams' fighting, not the drafts.

### Draft matchups (for draftnudge)

Lost 0/2 locally to our own older body playing the opponent's picks, and lost live: wheel (Mite), famine (Mite),
gold_rush (Fish; ours Vesper, Vendetta, C&I against Vesper, HoR, C&I), harvest (Fish), terraces (Fish), expanse
(Fish). Per-map correlation of live and local results is weak (+0.29 Fish, +0.15 Mite).

## The user's questions

**Does our gem worth in gold read the enemy's state?** Yes, but only how far the enemy is from 1,000, not how fast it
is going. Farm values a group at gems + `per_gold` x gold. `per_gold` (shop.cc `prices`) is `gold_price_scale` x
(the best next emblem's rounds saved per gold) x `gems_share`, times a hump of 1.25 while the higher score is in
100-500. `gems_share` (camps.cc) is min(our gems to 1,000, the enemy's gems to 1,000, our rate x rounds left) over
our living champions. The enemy's remaining gems are counted as gems we will still farm, which overstates them when
the enemy tributes faster than we do. Separately `comeback::cooked` (enemy past a score and a lead) turns on the
mirror pull, denial and snipes. Variant `bm-pace` scales the enemy's remaining gems by our rate over theirs.

**Teleport crystals.** Fish and Mite use them all game; we almost never do. Teleports a game in v115's scrims: Mite
3.52, Fish 2.34, us 0.35. On the 32 ladder maps where one hop shortens the spawn-to-altar walk by 8+ steps: Mite
10.9, Fish 5.8, us 0.09. 18% of fresh ladder-v2 maps have `tele_gain` of 1.5 or more (22% 1.3+). Our code makes hops
only for altars and groups no walk reaches (`StaticMap::make_hops`). Our win rate on the 32 maps is not lower
(73% / 64% against 68% / 61% elsewhere), so the size of the gain is unknown. Built as `bm-tp` (shortcut hops for banking only, not for farm): it hops 4 times a game on those maps and
does not win; see Candidates.

**min_bank from the draft or from play?** Play. What separates the real teams' banking from ours is the carrier's
walk to an altar at that moment, which varies within a map: the same map has camps beside an altar and far from
one. A per-map floor from the draft can only use the map's average, which is what CHANGES 461 did.

## Candidates and results

All are copies of `variants/oc-dfuel-506`, built `--release`, frozen in `bots/variants/` (untracked; diffs in
[patches/](patches/)). Batches: `replays/ab/bm11-f200a-*` (seeds 1212000-019) and `bm11-f200b-*` (1212020-039),
5,120 fresh ladder-v2 maps each, both sides, `--fuel 200000`, against the fixed bodies `spar-dvn1-Flp4` and
`spar-dvn1-Mt3q`. Tables come from `tools/paired.py TAG CAND oc-dfuel-506 [SUBSETFILE LABEL]`; the result table
is in [EXPERIMENTS.md](../../EXPERIMENTS.md) under "Bad maps".

| candidate | change | all fresh, both bodies | verdict |
|---|---|---|---|
| `bm-nb-d` | a non-Prism bag under 25 banks when bag >= 2.75 x altar walk (break-even from 8% death a cycle and 0.22 gems a champion-round) | +0.05 ±0.42 of 40,960 | level |
| `bm-nb-f` | the same with Fish's measured rule, bag >= 8 x (walk - 2) | -0.04 ±0.57 of 20,480 | level |
| `bm-pace` | `gems_share` scales the enemy's remaining gems by our tribute rate over theirs | -0.31 ±0.58 | level, leaning negative |
| `bm-lb` | Prism stops retaining once enemy score + its bag reaches 1,000 | -2.01 ±0.31 | loses |
| `bm-tp` | `make_hops` adds shortcut hops to walkable altars (a wall crossing that saves 8+ steps after the channel) | -0.42 ±0.36; +0.33 ±1.15 on hop-gain maps | loses |

- wheel against Mt3q (2 games): base 0/2, nb-f 0/2, nb-d 1/2, pace 0/2, tp 0/2. No candidate fixes wheel.
- `bm-nb-d` does what it should (fewer gems lost on death, more small tributes) and pays for it in captures.
  The bodies kill carriers less often than Fish and Mite, so the live value may be higher than the local one.
- `bm-tp` hops 4 times a game where base hops 0.14, and loses on the maps without a long spawn-to-altar detour:
  there the hop costs 10 gold and a 3-turn channel that cannot be cancelled for a short saving. It also raises
  out-of-fuel turns at stock fuel by half. A stricter version (hops only where the saving outweighs the crystal's
  price) was not built; even a +1 point gain on the 22% of maps with a detour is +0.2 overall.
- Seeds 1212000-1212039 are used (`~/tmp-offload/badmaps/maps11`).

## Not done

- The user's ladder table (wheel 0 of 14) could not be rebuilt exactly: `cambc matches list` returned 503 and
  the archive is thin after 11-10. The wheel record here is from scrims and the archive to 11-10.
- Keeping a hoarding Prism alive: tried below ("Prism's hoard"), eight arms, none passes. An escort for the hoard
  was not built.
- One-site overruns (38 of 176 losses, e.g. ribs 0/4) and the out-farmed tail (rushbait, the_pack,
  yellow_brick_road, vault, the_line) were classified but not decoded.
- No 100k arms (no 200k gain to confirm), no live tests, and the runtime-configured bodies were not used.

## Prism's hoard (second job, 2026-11-11)

Diagnosis of the 131 live deaths with 40+ gems (`tools/prism2.py`, output `~/tmp-offload/badmaps/an/prism2.pkl`),
the eight arms and their results are in [EXPERIMENTS.md](../../EXPERIMENTS.md) under "Keeping a hoarding Prism alive".
In short: Prism dies fighting on after a second enemy joins an even fight; an earlier retreat line (45% health
under threat) cuts the deaths 13-18% with a level win rate; refusing fights it falls in does nothing because the
fight model does not foresee the fall; leaving sooner for packs loses 0.7 points.

- Arms: `tools/mkarms.py NAME MODE FIGHTS LINE [STAKE]` copies `oc-dfuel-506`, applies the code in
  `patches/bm-dear-fall.patch` (that file is `bm-psr`: mode 3, fights off, line on, stake on) and builds.
  bm-pf-a 1/on/off, bm-pf-b 2/on/off, bm-pr 1/off/on, bm-pfr 1/on/on, bm-pfr-p 3/on/on, bm-pr-p 3/off/on,
  bm-ps 0/off/off/on, bm-psr 3/off/on/on.
- Runs: `tools/run12.sh`, `tools/run13.sh` (mechanism batch `replays/ab/bm12-mech-*` with replays extracted to
  `~/tmp-offload/badmaps/extm/`, then fresh half A `replays/ab/bm11-f200a-*`); `tools/prism3.py` makes the death table.
- The mechanism batch reused seeds 1212020-023 (already played by bm-nb-d); the paired read is on 1212000-019.
