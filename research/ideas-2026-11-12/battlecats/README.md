# BattleCats: behaviour model, classifier features, body sketch (2026-11-12)

Brief (user): "start work on reverse engineering battlecat behavior incl priority / classification." BattleCats
is a top UK ladder team and a likely final opponent. This note is analysis only: nothing was built, no games played.

**Summary**
- **Draft:** a fixed table per (map, side), with no counter-picking. Since 11-10 09:00 UTC, 99.4% of ranked games
  repeat their cell's modal team. C&I is in 99% of drafts and HoR in 89%. When Prism is picked it is always pick 0
  (485 of 485).
- **Priorities:** a type-ranked encoding. 99.6% of BattleCats' counted priority reads match three new tokens, which
  makes it easy to classify. Per champion instance, a 4-class model has BattleCats recall 0.78 at round 1 (draft only),
  0.91 at r50, 0.95 at r100 and 0.98 at r300, with precision 0.95 to 0.99.
- **Macro:** Prism is a bank. It keeps every capture share (476 gems collected a game) and pays in only when its bag
  covers the gems still needed to win: one channel of median 57 turns at median round 702, with about one ally
  within 3 tiles. Against us that channel completes only 19% of the time (603 channels).
- **Banking and denial:** the other champions pay in small bags (median 25) at middle altars. Its locks react to
  enemy tributes (median 3 rounds after the start). Enemy tributes of 150+ gems complete only 24% of the time
  against it.
- **Fighting:** basic attacks go to the lowest health (absolute) in reach; spells go mostly to the nearest. Retreat
  is a soft, health-graded flag. **Carrying gems never triggers a retreat.**
- **Against us:** BattleCats wins 29.5% of 2,100 current-version games (ranked 30.8% of 195). In those wins we die
  10.3 times a game against 3.2 in our wins. We lose 256 gems to kills (58 in our wins), and our Prism dies 1.74
  times a game (0.31). BattleCats' gem-fed Prism is the main killer of our Prism (215 of 717 Prism deaths).
- **Does it classify its opponent?** No evidence that it does. The draft cannot depend on the opponent and does
  not. In play, its encoding and flag use are the same against everyone. Map-matched differences against us have
  plain causes (fewer early contacts, more of our big tributes to lock). Its play is randomised from round 2, so a
  deterministic trajectory test cannot settle this; see section 6.

## Data and versions

- big-arm capture.db (read-only, one pull at 03:05 UTC):
  - every BattleCats match row since 11-05: 58,964 games, with picks and results;
  - the 3,269 replays captured since 11-08;
  - the 342 replays of today's live panel (v113/v115 against BattleCats) that the capture did not hold.
  - Decoded with `tools/replay/extract.mjs` into `~/tmp-offload/battlecats/ana`: 3,564 games, both sides.
- Replays exist only for ranked games and for our own scrims; BattleCats' 12k unranked games a day against other
  teams have picks and results only.
- **Versions**, dated from the draft (ranked games, share of cells matching the final table):
  - `old`: up to 11-09 06:00 UTC, without C&I; 931 decoded games.
  - `trans`: 11-09 06:00 to 11-10 09:00, a rollout: 30% → 68% → 78% → 87% → 96% of cells over 24 hours, so
    several submissions; 1,028 games.
  - `cur`: from 11-10 09:00, stable to 11-12 03:00 (100% of ranked cells since 11-11 06:00). 1,605 decoded games:
    956 against us (our scrims hit the same version: 99.1% of 1,855 draft cells match), 464 other teams, 110 Fish,
    75 Mite.
  - Everything below is `cur` unless marked.
- Current win rate of BattleCats (all kinds, 11-10 09:00 on): against us 29.5% of 2,100, Fish 48.2% of 1,625, Mite
  33.7% of 6,195, others 77.7% of 12,060.
  - It improved from the old version, ranked: against us 14.7% → 30.8%, Fish 29.3% → 47.0%, Mite 27.9% → 34.1%.

## 1. Draft (certain)

- **Fixed per (map, side), no counterpick.** We tested whether BattleCats' pick k depends on the opponent's earlier
  picks: leave-one-out modal accuracy, keyed on (map, side, own earlier picks) with and without the opponent's
  earlier picks (`draftdet.py`). On current ranked games pick 0 is 99.1% and picks 1-4 are 100%, the same with or
  without the opponent's picks.
  - Ranked 11-06 to 11-09 (old version): 98.5 / 96.3 / 99.3 / 98.8 / 100%, and the opponent's picks add nothing.
  - Unranked games are a mixture of BattleCats' test versions (12k a day), not one bot.
- **Composition** (current, one row per ranked map-side, 279 cells):
  - 5 picks (177 cells): C&I 100%, HoR 100%, Vendetta 70%, Marcella 68%, Prism 45%, Varg 41%, Vesper 31%,
    Ryth 24%, Willow 20%, Ren 2%. Top teams:
    - C&I + HoR + Marcella + Prism + Willow (26)
    - C&I + HoR + Varg + Vendetta + Vesper (25)
    - C&I + HoR + Marcella + Varg + Vendetta (23)
    - C&I + HoR + Marcella + Prism + Vendetta (20)
  - 4 picks (60 cells): C&I 100%, HoR 95%, Marcella 68%, Vendetta 45%, Prism 38%.
  - 3 picks (42 cells): C&I 95%, Marcella 64%, Vendetta 52%, HoR 40%.
- **Pick order:** Prism is always first when picked (485/485 ranked games). Otherwise slot 0 is mostly Vendetta, Ryth
  or Vesper, C&I comes at slot 1-2, HoR at slot 2-3, and the last slot is Vendetta, Willow or Varg.
- **Map features** (inferred; `draftmap.py`, 266 cells with decoded maps):
  - Prism on gem-cluster-rich, gold-poor maps: 42 gem clusters against 16 without it; gold 1,427 against 2,034.
  - Willow with Golems: 2.2 Golems against 0.5.
  - Marcella and Vesper split on gold total and cluster count.
  - Depth-2 trees beat the base rate by only 2-13 points, so a fresh-map draft model is approximate.
- **Change 11-09:** C&I entered (5% → 97% of games); Ryth (55% → 18%) and Varg (51% → 33%) went out.

## 2. Priorities (certain; the encoding was read off replays)

Each body's value is one of four kinds:

| kind | value | meaning (measured) |
|---|---|---|
| quiet, carrying | `L` = 13 − (teammates above it in the type order) | gems > 0 (median bag 23) |
| quiet, empty | `L + 7` | bag 0 (mean 0.1) |
| approach level | `L − 7m`, m = 1..24 | m grows as the nearest *seen* enemy closes: about m ≈ 25 − 2d (m 9-10 at d≈8, 13-14 at d≈5-6, 17-18 at d≈3-4, 23-24 at d=1) |
| flags | 40 / 35 / 38 | 40 = retreat (moves away 59% of contact rounds, hp 0.63); 35 = chase (moves toward 54%); 38 = strike (hits 61%) |

- **Type order** (highest acts first), from 1,500 games with no violations:
  HoR > Varg > Ryth > Marcella > Ren > Issac > Vendetta > {Willow, Vesper} > Prism > Cassi. Tavi and Stellar were
  never picked.
  - Examples: a five-body team runs L = 9..13 and 16..20; with C&I (six bodies) 8..13 and 15..20.
- **What the order does:** when quiet, the front line acts first and carriers act after the empty-handed. Bodies
  near an enemy act last, later the closer the enemy. Flagged bodies (retreat, chase, strike) act before everything.
- **Share of counted reads matched** (the classifier's rule: one read per value change per observer):
  - BattleCats: approach levels 70.9%, flags 14.6%, quiet 14.1%; unmatched 0.4%.
  - Other teams produce these tokens rarely: bc_quiet 3.0%, bc_level 1.4%, bc_flag 3.4% of their reads.
  - Mite never produces them.
  - Fish does, through chance residues of its small negative values: bc_level 9.8%, bc_quiet 0.7%. Its own tokens
    still take 89% of its reads; the BattleCats test runs first in `cls4.py`.
- **Team Kungarna** writes the same quiet empty tier (15-20) and the 35/40 flags, but no carrying tier and no
  negative levels: probably shared code. Our classifier confuses the two unless it sees levels (section 7).

## 3. Economy and target priorities

**Captures (measured; not distinctive).**
- The first capture is the nearest group to its spawn in 54% of games, the second-nearest in 21%, the same as its
  opponents (54% / 18%).
- Capture #1: Wolf+cluster group on its own side 26%, gold cluster 25%, Elk+cluster group 24%, gem cluster 10%.
  Median round 26 (opponents 24).
- Captures to r300: 20.2 a game (opponents 18.8); 75% on its own side, 16% middle, 9% on the enemy side.
- Enemy-side captures: 5.8 a game (opponents 5.6).
- Golem and Monolith groups: 0.3% of its captures to r300.
- **Who takes the gems:** Vendetta 18%, Prism 18%, Marcella 15%, HoR 13%, Varg 10%, C&I 15%. Gold goes mostly to
  Vendetta (23%) and Vesper (18%), consistent with Vesper's +33% gold.

**Income against each opponent** (BattleCats minus opponent, mean):

| opponent | r200 gems / gold | r400 gems / gold | r600 gems / gold |
|---|---|---|---|
| us (956) | −24 / −52 | −49 / −210 | −70 / −392 |
| Fish (110) | −15 / −117 | −55 / −144 | −87 / −195 |
| Mite (75) | −19 / −93 | −66 / −93 | −103 / +144 |
| others (464) | +4 / +127 | +23 / +351 | +41 / +729 |

**Tributes (measured).**
- Small and often: 19.3 a game. Bag at start, p25/p50/p75/p90: 15/25/45/88. First tribute at median round 103.
- 93.5% complete. Altars: middle 58%, own side 35%, enemy side 7%.
- Payers: Vendetta 20%, HoR 16%, Marcella 16%, Issac 14%, Cassi 10%, Varg 8%, Vesper 8%. Prism is excluded; see
  the bank below.

**The Prism bank (measured; the intent is inferred).**
- Prism is in 605 current games.
- Per game it collects 476 gems, tributes 246, and loses 79 to deaths (0.84 deaths a game). It makes 1.6 tributes a
  game, with a median bag of **694**.
- Its bag at r100/200/300/400/500/600: median 35/84/136/184/245/264 (p75 56/137/223/326/428/500).
- 42% of Prism games end with no Prism tribute at all.
- 979 of its 990 tributes start with 100+ gems.
  - Bags of 600+ (n=640): start at median round 702, channel 57 turns, and the bag covers the gems still needed to
    win in 94%. It has a median 1 ally within 3 and the nearest enemy at 9.
  - Outcomes of those 640: completed 103, stunned 261, manual cancel 146, locked 103.
- **By opponent:** we cancel the big Prism channel most: 19% complete against us (stun 253, lock 104, manual 97 of
  603), 50% against others, 28% against Fish, 38% against Mite.
- **Inferred:** Prism banks for one tribute that ends the game, and the bag doubles as damage.
  - +1.5 Focus a gem: a 250-gem Prism has about +375 Focus, so its 1.5×Focus stun-spell hits for ~700.
  - BattleCats' Prism is the top killer of our Prism (215 of 717), then Marcella 121, HoR 94, Vendetta 93.
- The bank exists in every version (old: collects 444, submits 249, 1.26 big tributes a game).

**Locks (measured).**
- 2.34 a game, placed in 74% of games. First lock at median round 337. Altars: middle 83%, own 10%, enemy 7%.
- **35% are placed on a live enemy tribute** (others 6%); the old version did 19%. The median latency from our
  tribute start is 3 rounds (p25 1, p75 6), on a median bag of 93.
- Enemy tributes against it, by bag:

  | bag | completed | locked | stunned | own cancel |
  |---|---|---|---|---|
  | under 50 | 95.7% | 1.5% | | |
  | 50-149 | 82.8% | 7.6% | | |
  | 150+ | **24.3%** | 16.1% | 30.0% | 27.7% |

- It destroys enemy locks: 2.83 a game (old 1.64; opponents 1.73).

**Other macro (measured).**
- Teleport crystals: 7.5 a game (opponents 1.8). 91% have no enemy within 6, median bag 4, median round 510. They
  are short-range travel (range 3, terrain ignored), not escapes.
- Wards: 177 a game (opponents 126). Completed recalls: 48 a game (median bag 4).
- **Builds** (emblems a game):
  - Marcella: Bruiser-Focus 1.8, Bruiser-Health 1.2, then Prospector/Treasure/Jungle.
  - HoR: Bruiser-Focus 1.0, Bruiser-Health 0.7, Prospector-Focus 0.7.
  - Vesper: **Bruiser-Strength 6.9**, Power-Health 3.4 (78 Strength shards).
  - Prism: Health only (30 shards: Bruiser/Prospector/Power/Treasure/Tribute-Health).
  - Vendetta and Varg: one emblem each of many families (Treasure, Prospector, Jungle, Durability, Collectors), Varg
    with Bruiser-Strength 3.0.
  - Cassi/Issac: little (Power-Focus 0.6 / Prospector-Health 0.7).
  - Each body buys about 2 crystals and 1 lock a game.

## 4. Fighting and retreat (measured)

**Target choice** (basic attacks and unit spells with 2+ enemy champions in reach; reach = attack range or spell
range 4; random choice would be 0.47):
- Overall: lowest health 72%, nearest 87%, most gems 52% when a carrier is in reach. Opponents: 76% / 80% / 60%.
- **Basic attacks: lowest absolute health.**
  - When the nearest and the lowest-health enemy differ (1,489), it takes the lowest 63%.
  - Among equally near enemies (15,770), it takes the lowest health 81% (by fraction 76%).
- **Spells: mostly the nearest.**
  - When nearest and lowest differ (3,103): nearest 49%, lowest 43%. Opponents take the lowest 60%.
- No carrier preference beyond health: most gems 51-56% among equally near targets.
- Chosen over expected, by type: Prism 1.17, Cassi 1.15, Issac 1.14, ... Marcella 0.78, Vesper 0.78.
- **Spell use** (casts a game): HoR dash 62 and shield 37, Issac dash 58, Vendetta dash 45. Cassi damage spell on
  camps 27 (on champions 6), CC on camps 14 (on champions 8). Prism CC on camps 6 (on champions 2.5). Marcella damage
  spell on camps 12 (on champions 8). Spells farm camps more than they hit champions.

**Retreat flag 40**, share of rounds with a seen enemy within 6:

| health | <0.1 | 0.1-0.2 | 0.2-0.3 | 0.3-0.4 | 0.4-0.5 | ≥0.5 |
|---|---|---|---|---|---|---|
| share flagged 40 | 0.64 | 0.40 | 0.24 | 0.15 | 0.10 | 0.02-0.05 |

- A graded hazard, not a fixed threshold.
- Outnumbered by 2+ within 5: 0.59 under half health, 0.11 above. Level numbers: 0.23 / 0.02.
- **Bag size does not raise it.** At half health or more: carrying 50+ gems 1.7%, 1-49 gems 2.6%, empty 3.2%.
- Cassi is flagged most (11.7% of contact rounds), the rest 4.4-6.2%.

**With an enemy within 3** (round-start positions; BattleCats, then its opponents for comparison):

| health | moves away | hits a champion | dies this round |
|---|---|---|---|
| <0.25 | 0.61 (opp 0.56) | 0.24 (0.31) | 0.22 (0.22) |
| 0.25-0.5 | 0.49 (0.51) | 0.39 (0.41) | 0.025 |
| 0.5-0.75 | 0.34 (0.38) | 0.45 (0.47) | 0.006 |
| ≥0.75 | 0.26 (0.29) | 0.41 (0.46) | 0.004 |

- Outnumbered by 2 within 5: moves away 0.48, hits 0.36, dies 0.072.

**Kills and deaths a game** (C&I counted once):

| opponent | BC kills | gems taken | BC deaths | BC gems lost | BC's dead |
|---|---|---|---|---|---|
| us | 5.1 | 115 | 7.1 | 134 | C&I 2.60, HoR 1.35, Vendetta 0.84, Marcella 0.84 |
| Fish | 6.8 | 64 | 8.1 | 146 | C&I 3.15, HoR 1.58 |
| Mite | 6.4 | 113 | 6.5 | 115 | |
| others | 8.0 | 107 | 6.0 | 106 | |

- Its kills against us come from Prism 1.09, Marcella 0.95, Vendetta 0.85, HoR 0.63.
- Deaths to camps: 0.19-0.25 a game.

## 5. Against us: what it exploits, and its habits

**Our weaknesses it exploits** (293 BattleCats wins against 663 of ours, current version, live and scrim):

| per game | BattleCats wins | our wins |
|---|---|---|
| our deaths | 10.3 | 3.2 |
| gems we lose to kills | 256 | 58 |
| our Prism deaths | 1.74 | 0.31 |
| our C&I deaths | 3.16 | 1.25 |
| our 100+ tributes completed | 0.29 | 1.34 |
| our 100+ tributes cancelled | 0.92 | 3.25 |
| BattleCats' 100+ tributes completed | 1.87 | 0.49 |
| gold at r400 (BattleCats − us) | +593 | −561 |

- **Gem bleed through our Prism.** This is the same "Prism hoard deaths" class as badmaps' v115 losses. Our Prism dies
  0.75 a game against it, with a mean bag of 76, and BattleCats' Prism is the main killer.
- **Our C&I dies** 1.83 a game, the most of any of our champions.
- **Early fights decide it:** the gold gap at r400 already separates its wins from ours.
- **Maps where BattleCats beats us most** (all current games, n ≥ 14): 03twisty 17/17; 02the_pack 13/14;
  adgato_gemcombat5, 04wheel, 04orchard and 03ultrastarvation all ≥ 0.81; 00dunes 0.75.
  - Mostly one- and two-altar maps. By altar count: 1 → 0.34, 2 → 0.26, 3 → 0.38, 4 → 0.29, 5-6 → 0.10-0.18.

**Its exploitable habits** (each measured; whether exploiting it gains is untested):
1. **The bank is one target.** At r500 the Prism carries a median 245 gems (p75 428), it dies 0.84 a game, and its
   big channel has about one escort.
   - When it completes, BattleCats usually wins: in 94% of the 600+ channels the bag covered what was still needed.
   - We already cancel 81% of those channels, but restarts make the bank a repeated threat.
   - Killing the Prism with its bag is the swing: up to the whole bag goes to the killer.
2. **Carriers do not run.** A bag never raises its retreat flag. Its hp ≥ 0.5 carriers stay in contact as often as
   empty ones.
3. **C&I is its weak pick.** 99% of drafts, 600-health Cassi, 2.6 deaths a game against us and 3.15 against Fish.
4. **Its spells take the nearest target, not the weakest.** A healthy front body draws its stuns and nukes off a
   hurt one behind it.
5. **Its draft is known on ladder maps** (fixed table), though not on fresh maps.
6. **It denies big tributes hard.** Its locks follow our tribute starts within ~3 rounds and 150+ bags complete
   24%. Our big tributes near its bodies are the risk, not its pressure in general.

## 6. Does BattleCats classify its opponent? (measured; no evidence)

- **Draft:** cannot and does not (section 1).
- **Priority encoding:** the same against every opponent. With map and side matched (222 cells against us,
  80 Fish, 52 Mite), the share of unmatched values differs by −0.002 and of flags by −0.010 against us.
- **Behaviour, map-matched,** against us minus against other teams (`oppdep.py`), same map and side:

  | measure | difference ±95% | vs others' mean |
  |---|---|---|
  | locks a game | −0.13 ±0.24 | 2.38 |
  | locks on a live enemy tribute | +0.39 ±0.20 | 0.55 |
  | teleports | −0.62 ±0.43 | 8.86 |
  | tributes by r400 | −0.75 ±0.42 | 7.67 |
  | captures by r300 | −0.28 ±0.65 | 21.0 |
  | contact rounds by r400 | −23 ±7 | 117 |
  | hits by r400 | −17 ±4 | 63 |

  - Each difference follows from our play: we avoid early contact, and we start more big tributes for it to lock.
  - Fish and Mite: every difference is inside its interval except locks on tributes against Fish (+0.47 ±0.38).
- **Trajectory test (`diverge.py`):** inconclusive. Same map and side, pairs of games: BattleCats' moves diverge
  before any of its bodies has seen an enemy in 639 of 833 pairs even against the *same* enemy team, often at
  round 2. Its play is randomised, so this test cannot show a dependence on the opponent. It does mean a body cannot
  be a deterministic copy.

## 7. Classifier features and accuracy (`cls4.py`)

Three tokens, added before the 11-09 model's tokens (`research/ideas-2026-11-09/oppmodel/tokens.py`), with
L = 13 − (teammates above it in BattleCats' type order):
- `bc_quiet`: v = L or L + 7;
- `bc_level`: v < 0, v ≥ −300, (L − v) mod 7 = 0;
- `bc_flag`: v ∈ {35, 38, 40}.

**The model:** the oppmodel's naive Bayes (pick slot given champion, plus tempered token log-likelihoods) with a
fourth class.
- Train: before 11-11 00:00. Test: from 11-11 00:00 (1,132 BattleCats sides, 270 others, 70 Fish, 35 Mite).
- Data:
  - both sides of the decoded BattleCats games (11-08 to 11-12);
  - the oppmodel's 11-07 to 11-09 Fish, Mite and others datasets;
  - our own sides excluded.

**Per champion instance, test set:**

| round | accuracy | BC recall | BC precision | BC p>0.8 | others confidently misread (>0.9) |
|---|---|---|---|---|---|
| 1 (draft only) | 0.779 | 0.777 | 0.954 | 0.46 | 1.1% |
| 25 | 0.842 | 0.850 | 0.961 | 0.56 | 1.1% |
| 50 | 0.896 | 0.911 | 0.971 | 0.67 | 0.6% |
| 100 | 0.936 | 0.954 | 0.980 | 0.79 | 0.2% |
| 300 | 0.969 | 0.983 | 0.994 | 0.90 | 0.1% |
| 1000 | 0.986 | 0.997 | 1.000 | 1.00 | 0.0% |

- **Without the BattleCats tokens** (the current tokens, four classes), BattleCats is still found by its draft, but
  everything else collapses into one "other" token. Precision falls to 0.92 at r100 and 0.81 at r1000, and other
  teams' recall to 0.67 at r100 and 0.23 at r1000. The new tokens are what separate it.
- **Robustness:** if BattleCats dropped its quiet tiers, recall would still be 0.93 at r100 and 0.96 at r300. The
  approach levels carry the class.
- **Leave-one-team-out** (each other team scored by a model fitted without it): share read as BattleCats at
  r100 / r300, confidently (p > 0.9) in brackets:

  | team | r100 | r300 |
  |---|---|---|
  | Team Kungarna | 0.70 (0.50) | 0.89 (0.79) |
  | Trzy Kwaterki | 0.32 (0.06) | 0.14 (0.03) |
  | Vvvvv | 0.11 (0.01) | 0.05 (0.01) |
  | NEETCoders (uses 35/40) | 0.07 (0.06) | 0.02 (0.02) |
  | every other team | ≤ 0.03 (0) | |

  - Kungarna shares the quiet empty tier and flags, but never writes `bc_level` or the carrying tier. If it matters,
    split `bc_quiet` into its two tiers and fit Kungarna into "other".
- **Mite's newest version escapes the 11-09 classifier.** From 11-11 ~04:00 UTC (35 test sides), Mite writes new
  values, which read as `other`:
  - 1,044,480-1,074,560 (multiples of 128 near 255×4096);
  - 129-392 (128 + small, 256 + 8, 384 + 1/8);
  - 2097-2098.

  Mite recall is 0.87 at round 1 (draft), 0.64 at r100 and 0.42 at r1000, with 31-58% confidently wrong. Whoever
  owns `model/opp_class` should refit before trusting `opp::mite` in a gate or live.

## 8. A local BattleCats body: what it would need (sketch, not built)

The Fish body's lesson applies: a body that fights softly misleads fight changes. Fidelity targets to check against
it, the same way as `fidcmp.py`:
- against us: BattleCats kills 5.1 and deaths 7.1 a game, our deaths 5.4;
- in its wins: our deaths 10.3, our Prism deaths 1.74;
- its gold lead at r400 in its wins;
- big Prism channels 1.6 a game, completing 19% against us;
- locks 2.34 a game, 35% on live tributes.

1. **Draft.**
   - Ladder maps: the exact per-(map, side) table (`meta.py` rows; 279 cells).
   - Fresh maps: C&I and HoR always. Prism as pick 0 on gem-cluster-rich maps. Willow when Golems are present.
     Marcella or Vesper by gold. Vendetta or Varg to fill.
2. **Priorities:** the exact encoding of section 2, so our classifier reads the body as BattleCats (bodies that
   write ocean's priorities read "other", as Flp did).
3. **Macro.**
   - Nearest-first captures, as now.
   - Every non-Prism carrier pays in at about 25 gems at the nearest middle or own altar.
   - **Prism takes every share it can** and channels only once its bag ≥ 1000 − banked (from r~600). It restarts
     after a cancel.
   - Locks: one a body. Placed on any enemy tribute within reach (latency ~3), else on middle altars from r~330.
     Break enemy locks.
   - Teleports as short travel.
4. **Fight.**
   - Basic attacks: lowest absolute health in reach. Spells: nearest.
   - Retreat as the graded table above, raised when outnumbered by 2, never for the bag.
   - Contact bodies act after the others (the priority encoding does this by itself).
5. **Builds:** section 3's emblem lists, the most fidelity-relevant first: Vesper's Bruiser-Strength stack, Marcella
   and HoR Bruiser-Focus, Prism Health only. They set the kill rate, as Mite's build did for its body.
6. **Randomness:** BattleCats is randomised. A body should take a per-game seed like the Fish and Mite bodies, or it
   will under-sample its variance.

Starting point: a copy of the Fish body (`bots/variants/rt-Flp4`) with the draft table, the priority writer and the
Prism-bank rule. Those three are what make it BattleCats; the fight rules above are second.

## Files

- Python tools, all in this folder:
  - `meta.py`: capture rows.
  - `bl.py`: decoded games.
  - `feat.py`: one pass to `~/tmp-offload/battlecats/feats.jsonl.gz`.
  - `fl.py`: loader.
  - `draftdet.py`, `draftmap.py`: draft.
  - `prio_states.py`: priority classes.
  - `econ.py`, `bank.py`, `prism.py`: economy and banking.
  - `combat.py`, `target2.py`, `retreat.py`: fighting.
  - `oppdep.py`, `diverge.py`: opponent dependence.
  - `ourloss.py`: our losses.
  - `cls4.py`, `cls4_dbg.py`: classifier.
- Outputs: `out/`.
- Data under `~/tmp-offload/battlecats/`:
  - `raw/all.tsv.gz` (match rows), `raw/repl`, `raw/panel`;
  - `ana/` (decoded), `ds_bc.pkl` (classifier dataset), `manifest.tsv`;
  - `tools/*_remote.sh` (the big-arm queries).
