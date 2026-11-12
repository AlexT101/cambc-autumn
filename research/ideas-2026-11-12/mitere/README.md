# Mite: decision rules from replays (2026-11-12)

Brief (user, verbatim): "ok i think we should also try to reverse engineer high level rules / micro / macro of mite as
tuning doesn't change our micro/macro so we kind of have to find that out". This is analysis only: no builds and no
games played.

**Data**
- big-arm `capture.db`: every Mite match row since 11-09 12:00, 48,400 rows with picks.
- big-arm replays: the 495 ranked Mite replays since 11-10 12:00, against 10 teams, decoded.
- Our live scrims against the r7 pin (captured 11-12 03:11): 375 games, v115/v116/v117, decoded by mitefit.
- **Version groups:**
  - v0: 11-10 12:00 to 11-11 04:00.
  - v1: to 11-11 23:09.
  - v2: after 23:09. r7 is in v2.
  - Epoch boundaries are the scheduler's opp-check change times; `meta.CHANGES` lists them.
- "Certain" below means read directly off replays, with a sharp step and stable across versions. "Inferred" means a
  fit or an interpretation.

**Summary**
- **Map pool.** The platform pool grew from 128 to 170 maps. 42 new `05*` maps entered ranked play on 11-11 at 23:10
  UTC.
- **Draft** (certain).
  - The team is a deterministic function of the map. It ignores the opponent.
  - On the brand-new 05 maps Mite picked map-specific teams from its first ranked game there. So the draft is a
    feature model, not a lookup.
  - A depth-4 tree on simple map features fitted on the old maps predicts the new maps' exact team 61%. The 5-pick
    variable slot is predicted 76%.
  - The draft is very stable across versions: 9% of cells changed since 11-10.
- **The priority value is Mite's state machine** (certain).
  - The value is `base << 10 | k << 7 | mask`:
    - `base` is the state;
    - `k` is a fixed per-body index;
    - `mask` is the set of enemies the body sees.
  - States: channel 18965, retreat 2100 − d, kill 3100 − d, quiet 1000 + 20 × health (tanks 1025 + 24 × health),
    contact 100 − d, alert 0, dead 1050.
  - Higher priority acts first, so retreating and channelling bodies act first and bodies in contact act last.
- **Retreat rule** (certain; identical in v0, v1, v2 and r7). A body retreats when either holds:
  - health below 0.40;
  - bag ≥ about 11 gems with an enemy within about 4.
  - Numbers never enter. An empty body at 0.6+ health retreats 1-2% even when outnumbered by two.
  - Retreating bodies still shoot: 37-41% of their turns hit a champion.
- **Fighting** (measured):
  - Basic attacks take the lowest absolute health in reach.
  - Spells take the nearest target.
  - It has no carrier preference.
  - Far teammates do not converge on fights, the same as us.
- **Macro** (measured):
  - **Opening pack.** The whole team clears the nearest groups together for about 100-200 rounds, and big groups
    draw 3+ bodies all game.
  - **Vesper is the gold sink.** It takes 59% of capture gold by r100 and 50% overall, and buys about 125
    shard-equivalents a game, Greed-Strength first.
  - **Banking.** Small banks, 23-31 tributes a game, median bag 22-28, at middle altars 68-75%.
  - **Prism is a bank.** When drafted it hoards (median largest bag 203) and tributes as a finisher. Against us those
    channels complete 7 of 52 times.
  - **Crystals are wall shortcuts.** 87-93% cross terrain, saving a median 24 steps; with a bag, mostly toward an
    altar.
  - **Locks** come late (not carried before about r350), about 1.5 a game, mostly middle altars. It hits enemy locks
    only while carrying gems.
  - **Wards** are re-placed as soon as the cooldown allows, on bushes and camp tiles.
- **Against us** (r7): Mite wins 34% of 375. In its wins:
  - we die 9.65 times a game against 3.24 in our wins;
  - we lose 364 gems to kills against 52;
  - Mite's Vesper makes 3.86 kills a game;
  - its gold lead at r400 is +636.
  - The single biggest swing is Mite's Vesper dying: 1.09 times a game in our wins, 0.29 in its wins.

## 1. Draft

- **Fixed per (map, side) within a version** (`meta.py`, ranked rows):
  - in all 12 epochs since 11-11 04:00, every repeated cell repeats one team (modal share 1.000);
  - this holds across all opponents, so there is no counter-pick;
  - side-independent on 160 of 170 maps.
- **Generalises to fresh maps** (`draftmap.py`). The 05 maps were first played at 23:10:01 UTC (against test4). Mite's
  first teams there were already map-specific:
  - 05runway: Vesper/Vendetta/HoR/C&I/Tavi;
  - 05cassette: Vesper/Willow/HoR/C&I/Tavi;
  - 05abacus: C&I/Prism/Marcella/Willow;
  - 05picnic: Vendetta/Marcella/C&I.
- **Tree fit:** a depth-4 tree on pick count, altar count, Elk count, area, gems, nearest altar and 5th-nearest group,
  fitted on the old maps. Measured on the 75 new-map cells:
  - exact team: train 77%, new maps 61% (majority 27%);
  - variable slot of 5-pick teams: train 87%, new maps 76%.
  - So Mite has a feature-based draft that these features approximate.
- **Shape** (333 cells, version 11 on):
  - 5 picks (213 cells):
    - Vesper/X/HoR/C&I/Tavi, with X = Willow 46%, Vendetta 40% or Prism 16%;
    - Varg replaces Tavi in 13 cells since 07:06.
  - 4 picks: Vesper/Tavi/HoR/C&I, Vesper/Vendetta/HoR/C&I, Vesper/Prism/HoR/C&I, or C&I/Prism/Marcella/Willow.
  - 3 picks: Vendetta/Marcella/C&I, Vesper/HoR/C&I, or Vesper/Vendetta/C&I.
  - Vesper is pick 0 in 83% of cells.
  - One-altar 5-pick maps take Prism or Willow; multi-altar maps with a near altar take Vendetta.
- **Across versions:** 22 of 254 ranked cells changed between 11-10 12:00 and now. The 04:21-07:06 version briefly put
  Prism in slot 1 on several maps, then reverted.
- **Unranked games:** Mite runs many test scrims against us, Fish and BattleCats on the same maps at once, varying
  slot 4. Unranked rows therefore mix versions.

## 2. Priority encoding = state machine (`mprio.py`, `states.py`, `rthr.py`, `alert.py`)

| state | base | when (r7, enemy within 6) | does |
|---|---|---|---|
| quiet | 1000 + ⌊20 health⌋ (HoR/Marcella 1025 + ⌊24 health⌋) | no enemy seen within 5 | farms |
| contact | 100 − d | enemy within 4, health ≥ 0.4, bag < 11 | hits 38%, moves away 27%, toward 29% |
| alert | 0 | enemy at 5-6 | moves away 55%, hits 7% |
| retreat | 2100 − d | health < 0.4, or bag ≥ 11 with enemy close | hits 37%, away 37%, toward 21% |
| kill / retreat-kill | 3100 − d / 5100 − d | rare (2-3%) | hits 44-47% |
| channel | 18965 | tribute or recall channel | |

- **The value:**
  - From 11-11 the value is `base << 10 | k << 7 | mask`. Plain bases persist alongside.
  - `k` (0-5) never changes within a body's life: a fixed body index.
  - `mask` holds the enemies the body sees: equal to its own sight in 86-95% of reads; the attacked target is inside
    it 99%. Bit 64 is set in contact and retreat.
  - In the alert state the low bits hold a single enemy bit.
- **The encoding is identical in v0, v1, v2 and r7.**
- **Turn order this gives** (high first): channel > retreat/kill > quiet (healthier first) > contact (closer first) >
  alert.
- **Retreat thresholds** (`rthr.py`; enemy within 4):

| condition | share in retreat |
|---|---|
| bag < 10, health < 0.40 | 0.66-0.77 |
| bag < 10, health 0.40-0.45 | 0.19-0.24 |
| bag < 10, health ≥ 0.6 | 0.01-0.03 |
| health ≥ 0.6, bag 0-8 | ≤ 0.06 |
| health ≥ 0.6, bag 9-10 | 0.14-0.39 |
| health ≥ 0.6, bag 11 | 0.37-0.42 |
| health ≥ 0.6, bag 12+ | 0.55-0.91 |

  - With a bag of 15+ the retreat share by enemy distance is: 0.91 at d = 1, 0.83 at 2, 0.71 at 3, 0.50 at 4, 0.25
    at 5, 0.15 at 6.
  - Numbers: an empty body at 0.6+ health is in retreat 1-2% at every numbers balance from −2 to +2.
- **The alert/contact/retreat split as a tree** (held-out accuracy 0.78): bag ≥ 11 and d ≤ 4 → retreat; health
  ≤ 0.41 → retreat; d ≤ 4 → contact; d 5-6 → alert.
- **Where a retreating body goes** (r7):
  - low health: away from the enemy centroid 52%, toward its spawn 56%;
  - carriers: hold and shoot. Away 33%, toward an altar 19%, hit 41%. The carrier retreat is mostly a turn-order
    change, not a run to bank.

## 3. Fighting (`target.py`, `retreat.py`, `conv.py`)

- **Target choice**, with 2+ enemy champions in reach (v1 / v2 / r7):
  - Basic attacks: lowest absolute health 0.76 / 0.79 / 0.71.
    - When the nearest and the lowest differ, it takes the lowest 0.72 / 0.76 / 0.56.
    - Among equally near targets, the lowest health 0.74-0.80.
  - Spells: nearest 0.84 / 0.77 / 0.80. When they differ, nearest 0.59 / 0.50 / 0.56.
  - Most gems: 0.42-0.52, which is chance. No carrier preference.
  - Chosen over expected, against us: Stellar 1.21, Cassi 1.10, Ryth 1.08, ..., Vesper 0.83, Varg 0.77.
- **Focus:** 90-94% of the rounds where Mite damages champions hit one target, the same as its opponents.
- **No convergence** (`conv.py`). After a first contact (enemy within 3 after 8 quiet rounds):
  - mates 5-8 away are within 4 of the target 24% of the time six rounds later;
  - mates 9-14 away, 6%;
  - the mean distance grows by about 1. Ours are the same.
  - Real Mite does not bring the whole team to a fight.
- **Contact behaviour by health** is the same as ours. Within 3: moves away 0.43-0.48 under 0.5 health, 0.25 at 0.75
  and up.
- **Chase:** toward an enemy at 2-5 tiles:
  - 0.44-0.55 when the enemy is under 0.25 health, 0.20 when it is healthy (r7 / v1);
  - no extra pull toward carriers.
- **Ancestry:** the 11-09 notes ("+2000 turns 80% carry 10+ gems, 29% under 40% health") read the same rule from the
  older encoding. The rule has been stable since at least 11-09.

## 4. Macro (`econ.py`, `bank.py`, `macro2.py`, `tele.py`, `lockbuy.py`, `wards.py`, `build2.py`, `opening.py`, `clearers.py`, `cohesion.py`)

**Captures and opening.**
- Captures by r300: Mite 20-22, its opponents 17-18 (us 22.7).
- The first capture is the nearest group 58-76% (opponents about 50%). Wolf+ and Elk+ groups are 60% of first
  captures.
- 69-76% of captures by r300 are on its own side, 24-30% middle, 1-2% enemy side.
- **Opening pack.** Share of mates within 5, Mite vs us: r20 0.64 vs 0.52, r60 0.46 vs 0.35, r100 0.42 vs 0.37;
  equal from r300. Mites within 5 (C&I partner not counted):
  - quiet: 1.29 vs 0.98;
  - contact: 1.49 vs 1.47.
- **Clearing parties.** Distinct attackers per cleared group:
  - all groups: Mite 1.99, us 1.67;
  - before r200: 2.47, with 25% of clears by 4+ bodies (us 1.92 and 13%);
  - Elk+: 2.97;
  - Golem+: 3.35.
  - The most common early party is the whole team.
- One body takes the capture (1.06 shares a capture). Vesper takes 59% of capture gold by r100 (ours: Vesper 33%,
  Prism 27%). Over the game Vesper takes 50% of the gold and 34% of the gems; HoR takes 20% of the gems.

**Banking.**
- 23-31 tributes a game (r7: 22.8). Bag at the start, p25/p50/p75/p90: 12/24/50/100.
- First tribute about r93-111. Middle altars 68-75%.
- 80-84% complete; 11-15% are manual cancels (feints).
- Payers: Vesper 26-30%, HoR 20-23%, Issac 13%, Vendetta 10%.
- The median bag is flat over the game (22-34).
- **Prism bank.**
  - Median largest carried bag 203 (p75 420). Collects 440 a game, submits 118 against us (279 against v1 ranked
    opponents).
  - 1.4 tributes a game, median bag 525.
  - 52 of its 82 channels of 100+ against us are finishers (bag + banked ≥ 1000). Outcomes: stun 21, lock 17,
    completed 7, manual 6.
  - It dies 2.31 times a game against us, losing 257 gems a game.

**Locks.**
- Not carried before r200. Share of bodies carrying one: 2% at r200, 12% at r400, 19-29% from r600.
- First carried round: p10 346, median 550. 48% of bodies ever carry one.
- 1.5-1.9 placed a game. Middle altars 67-74%. First placement median r540-575.
- 6-15% go on a live enemy tribute. 27% are placed where the same body starts its own tribute within 3 rounds.
- About 0.4-0.9 a game on one-altar maps.
- Lock hits only with gems: 96% of hits have bag > 0. Stable since 11-09.

**Teleport crystals.**
- 3.1-4.9 a game (we use 0.47).
- Hop 3 tiles. Walking the same hop would take a median 24 more steps (p25 15); 25% of hops are unreachable on foot
  within 60.
- 78% end nearer an altar. With a bag of 30-99, 61% are followed by a tribute within 20 rounds; with an empty bag, 3%.
- No enemy within 6 in 95%+.
- Users: Vesper 1.2, HoR 1.0, Issac 0.65 a game.
- Bodies carrying a crystal: 16% at r200, 26% at r600, 55% after r1400.
- Top maps: great_wall 23 a game, one_gem 20, twisty 20, starvation 18.

**Wards.**
- 3.6 per body per 100 rounds (us 2.4).
- Gap between one body's wards: median 14 (ours 19); 31% exactly 10, i.e. as soon as the cooldown allows.
- 59% on bushes, 60% within 3 of a camp group.

**Builds** (shard-equivalents a game, r7):

| body | total | main families |
|---|---|---|
| Vesper | 125 | Greed-Strength 39, Bruiser-Health 23, Greed-Health 7, Bruiser-Strength 6 |
| Marcella | 84 | Bruiser-Health 18, Greed-Focus 15 |
| Vendetta | 50 | one emblem each of Prospector, Monster, Durability, Jungle, Capture |
| Prism | 47 | Bruiser-Health 9, Prospector-Focus 5 |
| HoR | 35 | Prospector-Focus, Durability-Health, Jungle-Focus, Bruiser-Health |
| Tavi | 24 | |
| Issac | 17 | Prospector-Health first |
| Cassi | 10 | Prospector-Focus first |
| Willow | 4 | |

- The non-carries buy one emblem each of several families, Prospector first.

**Recalls.** About 42 completed a game. Every body also starts a recall almost every turn and cancels it the next;
our bot does the same.

## 5. Stable and changed rules by version

- **Stable from v0 (11-10) to r7:**
  - the priority encoding and every state threshold;
  - targeting;
  - capture, bank and lock patterns;
  - teleport use;
  - Vesper as the gold sink;
  - the opening pack.
- **Changed:**
  - draft cells: 9% since 11-10. Prism briefly in slot 1 in the 04:21-07:06 version; Varg replacing Tavi on a few
    maps since 07:06.
  - the share of shifted against plain priority values.
  - Lock count is roughly flat (1.5-1.9).
- Against us the r7 basic attacks lean more to the nearest (0.37 when nearest ≠ lowest, against 0.21-0.23 in ranked).
  This probably follows our compositions, not a rule change.

## 6. Exploits (mechanism and frequency; none tested)

1. **Kill Mite's Vesper.**
   - Mechanism: it is the gold sink (50-59% of Mite's capture gold) and the main killer (3.86 kills a game in Mite's
     wins).
   - Evidence: it dies 1.09 times a game in our wins and 0.29 in its wins. Mite's targeting does not protect it.
   - Frequency: Vesper is in 86% of r7 drafts.
2. **Numbers don't make it retreat.**
   - Mechanism: an empty body above 0.4 health stays in contact when outnumbered, retreat 1-2%.
   - Frequency: of its turns at 0.6+ health with a bag under 10 and an enemy within 4, 8% are outnumbered by one
     and 3% by two.
   - Exploit: a 2-on-1 on an empty Mite body is not answered by disengaging.
3. **Carriers (bag ≥ 11) flip to retreat once an enemy is within about 4.**
   - Mechanism: in that state they act first but rarely bank (toward an altar 19%).
   - Frequency: about a quarter of its turns at 0.6+ health with an enemy within 4.
   - Exploit: zoning carriers with one body slows its banking without a fight.
4. **Its Prism dies with big bags against us** (2.31 deaths and 257 gems a game).
   - Mechanism: its finisher channel completes 7 of 52 times, and stun and lock already work.
   - Frequency: Prism is in 22% of r7 drafts.
5. **No locks before about r350, and few on live tributes** (6-15%). Our early and mid-game tributes are almost never
   locked.
6. **It never tributes at a locked altar, and hits locks only with gems.** A lock on its preferred middle altar stalls
   its small-bag banking. The 11-09 test of a relock errand on the older Mite lost captures; the base already exploits
   this.
7. **The draft is known in advance** on ladder maps (fixed table) and 61-76% predictable on fresh maps.
8. **Far teammates don't come to fights.** An isolated pack of 2-3 Mite bodies fights alone.

## 7. Where our bot loses to it (r7 live, 129 losses against 246 wins)

| per game | Mite wins | our wins |
|---|---|---|
| our deaths | 9.65 | 3.24 |
| gems we lose to kills | 364 | 52 |
| our Prism deaths (gems lost) | 1.34 (195) | 0.20 (15) |
| our Cassi deaths | 3.23 | 1.19 |
| our Willow deaths | 1.55 | 0.34 |
| our deaths by r300 | 1.53 | 0.94 |
| earned gold at r400, Mite − us | +636 | −371 |
| banked at r600, Mite − us | +223 | 0 |
| our 100+ tributes completed | 0.54 | 1.59 |
| Mite's 100+ tributes completed | 1.96 | 0.63 |

- **Who kills us** in its wins: Vesper 3.86, Prism 1.16, HoR 1.16, Marcella 0.97 a game.
- **Numbers at our deaths:** at the round start we had the numbers advantage 43% of the time and even numbers 25%. We
  lose even fights to a fed Vesper, not ambushes.
- **Maps:** Mite does best on 2-altar maps (43%) and 3-pick maps (50%). It wins 03ultrastarvation 5/5 and
  04two_kingdoms, 02the_pond, 03twisty and 02harvest 5/6 each.
- **Small maps, live:** ocean v115 57% against charybdis v116 57% and v117 55% on maps under 1,000 tiles. 00stampede is
  lost by both, so the local body's small-map gap between the two drafts is not seen against real Mite (05 maps not
  yet played live).

## 8. What a faithful body needs beyond constants

In order of likely impact:
1. **Retreat as section 2:** health < 0.40, or (bag ≥ 11 and an enemy within about 4). Ignore numbers. Keep shooting
   while retreating. Low-health retreat heads home.
2. **Vesper as the capturer and gold sink:**
   - the pack clears and Vesper stands on the tile;
   - Vesper builds Greed-Strength, then Bruiser-Health;
   - the others buy one emblem each of several families, Prospector first.
3. **Opening pack:** the whole team clears the nearest groups together for about 100-200 rounds. Elk+ and Golem+ groups
   draw 3+ bodies all game.
4. **Targeting:** basic attacks on the lowest absolute health in reach; spells on the nearest.
5. **Banking:**
   - small bags (median about 25) at middle altars;
   - Prism hoards and channels as a finisher (bag + banked ≥ 1000), else at bag + banked of about 800.
6. **Crystals:** buy on spawn visits. Hop 3 tiles when terrain makes the walk about 12+ steps longer, mostly toward an
   altar with a bag.
7. **Locks:** none bought before about r350; then about half the bodies carry one and place it at a middle altar they
   bank at. Hit enemy locks only with gems; never tribute at a locked altar.
8. **Wards:** re-place on cooldown (about every 10-14 rounds), on bushes and camp tiles.
9. **Priority writer:** the section 2 encoding, so our classifier reads the body as Mite and so the turn order (retreat
   first, contact last) matches.
10. **Draft on fresh maps:** use `draftmap.py`'s tree, or better, Mite's own table where the map is a ladder map.

## Files

- **Python tools** (this folder):
  - `meta.py`: rows and epochs.
  - `ml.py`: decoded-game loader, both sources.
  - `feat.py`: per-game features → `~/tmp-offload/mitere/feats.jsonl.gz`.
  - `pass2.py` / `p2l.py`: per body-round rows with positions → `p2.jsonl.gz`.
  - `fl.py`: feature loader.
  - `mprio.py`: priority decoder.
  - Analyses: `states.py`, `rthr.py`, `alert.py`, `target.py`, `retreat.py`, `conv.py`, `econ.py`, `bank.py`,
    `banktrig.py`, `macro2.py`, `tele.py`, `lockbuy.py`, `wards.py`, `build.py`, `build2.py`, `opening.py`,
    `clearers.py`, `cohesion.py`, `ourloss.py`, `draftmap.py`.
  - `tools/*_remote.sh`: the big-arm queries.
- **Data** under `~/tmp-offload/mitere/`:
  - `raw/` (rows, replays, the 05 maps' replays, platform map list);
  - `ana/` (decoded ranked games), `ana05/` (05 map geometry);
  - `feats.jsonl.gz`, `p2.jsonl.gz`.
- The r7 live games are mitefit's `~/tmp-offload/mitefit/live/`.
