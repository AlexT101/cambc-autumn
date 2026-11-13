# Scoreboard of lost games: charybdis self-play mirror (2026-11-13)

Data: `chy-mirror` vs `chy-ref` (identical charybdis), 5,120 games on 2,560 fresh maps (`maps/suites/mac13/ana`), 2x fuel.
The two sides of a map are byte-identical games (results.json: all 2,560 pairs agree), so there are **2,560 distinct games**,
each with one winner W and one loser L. Extracted to `replays/ana-mirror/`; per-game rows in
`data/scoreboard.jsonl.gz` (scripts: `scripts/scoreboard.py` rows, `scripts/findings.py` tables, `scripts/followups.py`).
Raw outputs: `data/findings_raw.md`, `data/followups_raw.md`. Every draft was a mirror (2,560/2,560). The gem identity
(collected = capture + kill bags - bags lost to champions - bags lost to camps) holds every round of every game.

Definitions. *Collected* = tributed + carried. D(r) = W collected - L collected at the end of round r.
**b0** = last round with D <= 0 (W leads for good after it); **b100** = last round with D <= 100.
Margin components (W minus L): *farm* = capture gems; *fight* = (kill bags taken - own bags lost to champions), which is
2x the kill-gem gap; *camp* = L's bags lost to camps minus W's. farm + fight + camp = change in D.
*Zone*: a group's `side` from extract.mjs (Chebyshev distance from the group's tile centroid to each spawn centre;
equal distance = mid, so "mid" is only the exact symmetry-axis groups). *Class*: monolith > golem > elk > wolf-only /
wolf+clusters > gem-only / gold-only / mixed clusters.

## Headline

- Games are level for a long time. The median break is **r403** (IQR 188-641) of a median 774-round game. L leads
  by 50+ gems at some point in 52% of games (100+ in 28%), with its largest lead at a median r209.
- Breaks come in three kinds. **72% are gradual**: the lead goes from 0 to 100 over a median 107 rounds, with no L
  death near b0 in 79% of them, and farm is the largest component in 77%. **20% jump** from <=0 to >100 in one step;
  69% of those are L's Prism dying at the break (median bag 229). **8% are "bank" wins**: L ended with more collected
  gems (486 carried on average) but W tributed to 1000 first.
- After the break the gap is mostly kill bags. Whole game, the W-L margin is +635 (median +456): fight +432 (median
  +142) and farm +200 (median +119). **78% of the kill-gem gap is Prism bags**: per game L's Prism loses 206 gems to
  champions, W's 17.
- W's Prism almost never dies: it never died in 91% of Prism games, L's in 42%. When a Prism died, the first to die
  was L's in 90%. L's first Prism death comes a median 19 rounds after b0. In 90% of games the break comes before any
  Prism death, so the duel mostly cashes in a lead that farming built.
- Before the break, W and L behave the same: labour mix, supply left unworked, cohesion, raids and steals all have
  |dz| < 0.1. The only early separators are small productivity edges (gold earned, capture gems per alive round, camp
  damage per alive round; dz 0.16-0.27), and those compound.
- Supply is wildly under-used by both teams. **82% of the group-rounds where a group is up go untouched**, on both
  halves and for both teams. Monoliths sit up 91% of the time, golems 68%. Clusters are cleared and then left unheld
  (gold clusters 9.8 rounds per capture).
- Side: team A wins 48.2% [46.2, 50.0]; on horizontal-symmetry maps 44.9% [40.9, 48.6]. Turn order matters a little.

## Outcome and time series

End types: 2,462 games ended on 1000 gems and 98 (3.8%) went to r2000. L's final tributed gems: median 334 (IQR 195-574).

| round | live | collected W/L | tributed W/L | capture W/L | kill gems W/L | lost to camps W/L | D (live) | W ahead |
|---|---|---|---|---|---|---|---|---|
| 100 | 2560 | 97 / 90 | 12 / 11 | 96 / 91 | 1 / 1 | 0 / 0 | +6 | 44% |
| 200 | 2560 | 225 / 199 | 50 / 47 | 221 / 204 | 8 / 3 | 0 / 1 | +27 | 58% |
| 300 | 2551 | 381 / 309 | 113 / 97 | 367 / 325 | 20 / 6 | 1 / 1 | +71 | 66% |
| 400 | 2496 | 555 / 415 | 204 / 157 | 522 / 450 | 42 / 9 | 1 / 2 | +134 | 71% |
| 600 | 1912 | 865 / 557 | 507 / 280 | 777 / 653 | 112 / 20 | 3 / 4 | +276 | 77% |
| 800 | 1187 | 1057 / 604 | 781 / 351 | 913 / 758 | 179 / 31 | 4 / 6 | +442 | 81% |
| 1000 | 718 | 1157 / 621 | 938 / 385 | 982 / 807 | 214 / 35 | 4 / 7 | +591 | 83% |

(A game that has ended contributes its final value to the W/L columns. "D" and "W ahead" use live games only.)
Tributing lags collecting badly: at r400, W has tributed only 37% of what it has collected.

## A. The break

| | median | IQR | p10-p90 |
|---|---|---|---|
| b0 (lead > 0 for good) | 403 | 188-641 | 83-893 |
| strict b0 (lead >= 0 for good) | 388 | | W never behind: 8.0% |
| b100 (lead > 100 for good) | 542 | 346-748 | |
| b0 / game length | 0.52 | | |

| class | n | b0 median | b0 IQR | b100 median | end median |
|---|---|---|---|---|---|
| size S (<1600 tiles) | 705 | 293 | 133-574 | 442 | 826 |
| size M (1600-3000) | 797 | 383 | 180-612 | 519 | 751 |
| size L (3000+) | 1058 | 464 | 258-684 | 591 | 753 |
| 3 picks | 414 | 342 | 157-606 | 518 | 858 |
| 4 picks | 471 | 371 | 156-643 | 511 | 789 |
| 5 picks | 1675 | 423 | 216-645 | 547 | 751 |
| generated | 1920 | 422 | 202-654 | 560 | 780 |
| mutation | 640 | 326 | 152-589 | 484 | 746 |

Kinds of break:

| type | games | what happens at b0 |
|---|---|---|
| gradual (b100 > b0) | 1840 (72%) | surge of median 107 rounds; no L death within 2 rounds of b0 in 79%; L Prism death at b0 in 5% |
| jump (D from <=0 to >100 in one step) | 516 (20%) | L Prism died at the break in 69% (median bag lost 229); another L death in 13%; no L death in 18% (a single large capture, e.g. a Monolith) |
| bank (L ends with more collected gems) | 204 (8%) | L carried 486 gems at the end (mostly its Prism); median end r693 |

Win rate by collected-gem lead (either side's view):

| lead at | <=-100 | -99..-25 | -24..24 | 25..99 | 100..199 | 200+ |
|---|---|---|---|---|---|---|
| r200 | 22% | 39% | 50% | 61% | 76% | 84% |
| r300 | 14% | 36% | 50% | 64% | 80% | 92% |
| r400 | 11% | 37% | 50% | 63% | 79% | 95% |

## B. What builds W's margin (W minus L, gems; mean [95% CI]; median)

| component | pre (1..b0) | surge (b0..b100) | b0..b0+100 | post (b100..end) | r1-300 | r1-600 | whole game |
|---|---|---|---|---|---|---|---|
| D change | -48 [-54,-43]; -12 | +86 [83,89]; +86 | +319 [301,338]; +134 | +622 [597,649]; +411 | +71 [64,78]; +27 | +308 [291,324]; +137 | +635 [612,662]; +456 |
| farm | -20 [-24,-16]; -10 | +60 [58,63]; +63 | +76 [72,80]; +62 | +177 [165,188]; +67 | +42 [37,47]; +17 | +124 [115,133]; +67 | +200 [187,213]; +119 |
| fight | -27 [-34,-21]; 0 | +25 [22,28]; 0 | +240 [222,260]; 0 | +442 [413,474]; +100 | +28 [24,33]; 0 | +183 [169,197]; +16 | +432 [405,464]; +142 |
| camp | -1 | +1 | +3 | +3 | +1 | +1 | +2 |
| bank (carried, W-L at end of window) | -65 | -54 | +150 | -54 | +55 | +81 | -54 |
| capture: own / mid / enemy zone | -12 / -5 / -3 | +29 / +18 / +13 | +36 / +23 / +17 | +56 / +73 / +48 | +18 / +14 / +10 | +45 / +47 / +32 | +65 / +81 / +54 |
| capture: elk / wolf+cl / gem-cl / golem / monolith | -3 / -5 / -7 / -1 / -5 | +21 / +14 / +14 / +7 / +3 | +23 / +14 / +18 / +9 / +12 | +53 / +34 / +36 / +20 / +32 | +15 / +10 / +11 / +4 / +0 | +43 / +27 / +26 / +18 / +7 | +65 / +39 / +40 / +24 / +30 |
| n | 2560 | 1840 | 2560 | 2560 | 2560 | 2560 | 2560 |

Wolf-only groups and mixed clusters add at most 2 gems; gold clusters add none.

- The lead that forms at the break is **farming**: farm is the largest component in 77% of surge windows. The fight
  mean is a heavy tail: its median is 0 in every window up to b0+100, while its mean there is +240, carried by the
  20% of jump breaks and by Prism kills soon after.
- Before the break, L's small lead comes from both components (farm -20, fight -27). After it, W out-captures L on
  every class and zone (mid and enemy zones grow most after b100: raids, see D), and wins the Prism duel.
- Kill-gem gap: Prism bags are 0.78 of it. The Prism carries 57% (W) and 47-49% (L) of its team's collected gems
  at r300-400, so a Prism kill swings D by about 2 x 133.

## C. Isolating farming from the Prism duel

| subset | n | b0 med | pre: farm / fight | b0..+100: farm / fight | whole: farm / fight / bank |
|---|---|---|---|---|---|
| all | 2560 | 403 | -20 / -27 | +76 / +240 | +200 / +432 / -54 |
| Prism drafted, no Prism death before b0 | 2011 | 359 | -25 / -8 | +76 / +253 | +180 / +506 / -65 |
| Prism drafted, a Prism died before b0 | 216 | 692 | +22 / -238 | +67 / +434 | +242 / +324 / +12 |
| no Prism drafted (13%) | 333 | 531 | -19 / -4 | +81 / +36 | +299 / +60 / -29 |
| no kill before r300 (44%) | 1134 | 508 | -22 / -25 | +65 / +251 | +87 / +415 / -106 |

- **Prism drafted, no Prism death before b0 (90% of Prism games).** W is ahead at r300 in 68% (median lead +35).
  The r1-300 lead (+85) is farm +50 / fight +35 (kills of non-Prism bodies); by class elk +18, gem-cl +14, wolf+cl
  +12, golem +5; by zone own +21, mid +17, enemy +12. In the pre-break window W captures *less* per alive round
  (dz -0.36, by construction of b0) and nothing else separates the teams (|dz| <= 0.16).
- **No kill before r300.** The r300 lead is only +20 (median +8, IQR -15..+46), all of it farm, and W leads in 58%.
  Over r1-300 the separators are productivity, not time allocation: capture gems per 100 alive rounds 23.8 vs 22.5
  (dz +0.27, W higher in 61%), gold earned +63 (dz +0.20), camp damage per alive round 25.1 vs 24.6 (dz +0.20).
  Labour mix, cohesion, idle supply, raids and steals: |dz| <= 0.11. These games are still decided by fights later
  (whole game: fight +415 vs farm +87).
- **No Prism drafted.** Games are farm-decided (farm +299 vs fight +60) and break later (b0 median 531).

## D. Do W and L behave differently? (paired dz = mean(W-L) / sd(W-L))

Rounds 1-150, all 2,560 games, ordered by |dz|: gold earned +41 (dz +0.20); capture gems per 100 alive rounds
19.6 vs 18.4 (+0.16); gold spent +33 (+0.16); kills 0.31 vs 0.19 (+0.16); deaths 0.23 vs 0.35 (-0.15); dead share
1.8% vs 2.7% (-0.12); raids 0.70 vs 0.60 (+0.11); camp damage per alive round 20.0 vs 19.7 (+0.11); steals (+0.10);
work share 32.6% vs 32.1% (+0.09). Then walk 54.1% vs 53.9% (+0.04), idle own-half supply 76.0% vs 76.1% (-0.03),
largest-cluster share 76.5% vs 76.6% (-0.02), nearest ally 4.49 vs 4.50 (-0.01). **Nothing reaches |dz| 0.25.**
Pre-break (b0 >= 100, n=2037): only W's lower capture rate (-0.29, by construction) and |dz| <= 0.13 for the rest.
In the 100 rounds after b0 everything separates (L dead share 18% vs 4%, dz -0.80; work +7pt, dz +0.71; raids
+0.6, dz +0.51), but that is the result of the break, not its cause.

Which early lead predicts the winner (share of games where the eventual winner led on it, ties excluded):

| lead in | r100 | r200 | r300 | r400 |
|---|---|---|---|---|
| collected gems | 57% | 62% | 68% | 72% |
| capture gems | 56% | 61% | 66% | 68% |
| tributed gems | 53% | 54% | 57% | 61% |
| gold earned | 56% | 60% | 65% | 68% |
| camp damage dealt | 54% | 56% | 63% | 65% |
| kills (games with unequal kills) | 63% (n=435) | 64% | 69% | 74% (n=1370) |
| Prism bag | - | 63% | 66% | 69% |
| Prism Focus | - | 62% | 66% | 68% |

Labour by phase (% of champion-rounds, W / L; macro.py classes):

| phase | walk | walk_bag | camp | hold | tribute | recall | fight | wait_camp | spawn+idle | dead | camp dmg / alive rd |
|---|---|---|---|---|---|---|---|---|---|---|---|
| r1-150 | 35.1 / 35.2 | 19.0 / 18.7 | 27.8 / 27.5 | 4.5 / 4.4 | 0.3 / 0.3 | 4.5 / 4.4 | 2.6 / 2.6 | 1.7 / 1.7 | 2.6 / 2.6 | 1.8 / 2.7 | 20.0 / 19.7 |
| r151-400 | 25.0 / 25.5 | 31.4 / 30.2 | 21.1 / 19.9 | 4.6 / 4.2 | 1.4 / 0.9 | 5.2 / 4.9 | 2.6 / 2.6 | 2.6 / 2.4 | 2.3 / 2.3 | 3.8 / 7.1 | 25.3 / 23.5 |
| r401-800 | 26.3 / 26.6 | 29.5 / 29.1 | 15.5 / 13.7 | 4.0 / 3.4 | 5.3 / 1.6 | 3.7 / 3.4 | 2.8 / 2.7 | 3.6 / 2.4 | 2.4 / 2.5 | 5.1 / 14.1 | 25.3 / 24.3 |

Walking is 54-56% of champion-rounds in every phase, for both teams. Camp work falls from 28% to 15% after r400.

Supply left up and unworked (% of up group-rounds with no camp hit and no capture hold, W / L, by zone relative to
the team): r1-150 own 82/82, mid 89/89, enemy 82/82; r151-400 81/81, 85/85, 81/81; r401-800 86/86, 86/86, 86/86.
Raids (captures on the enemy half) per game: r1-150 0.7/0.6, r151-400 2.0/1.4, r401-800 2.8/1.7, whole game
6.8/4.4 (126 vs 72 gems). Steals (capturing a group the other team cleared): whole game 1.6/1.0.

Cohesion (W / L): nearest living ally of field bodies 4.49/4.50 (r1-150), 5.62/5.59 (r151-400), 5.65/5.81
(r401-800); share of bodies in the largest cluster (linked within 8) 76.5/76.6, 69.9/70.7 (W-L -0.8pt [-1.1, -0.6]),
70.4/71.7 (-1.3pt). W is marginally *less* clustered after r150.

Gold (team, W / L): earned r150 707/666, r300 1707/1535, r600 3996/3375, end 5952/4566; spent at the end 5059/4269;
unspent r300 186/149, r600 457/266, end 893/297. Shard-equivalents (emblem = 5) at r300 / r600, W / L: Prism
20.6/17.9 and 48.5/40.0; Vesper 25.0/22.8 and 57.8/51.8; Vendetta 13.3/12.4 and 31.6/28.2; Cassi, Issac and Willow
stay at 0.3-5.8 by r600 (they buy almost nothing).

## Deaths (per game, W / L)

| victim | games | deaths W / L | median round W / L | mean bag W / L | by camp W / L | outnumbered* W / L | by Prism W / L |
|---|---|---|---|---|---|---|---|
| Prism | 2227 | 0.15 / 1.59 | 553 / 728 | 136 / 133 | 13% / 3% | 48% / 57% | 46% / 76% |
| Cassi | 2500 | 0.63 / 1.58 | 588 / 681 | 13 / 15 | 9% / 3% | 25% / 31% | 49% / 64% |
| Issac | 2500 | 0.47 / 0.91 | 470 / 595 | 7 / 8 | 12% / 6% | 35% / 42% | 40% / 53% |
| Vesper Vale | 1607 | 0.29 / 0.99 | 569 / 704 | 21 / 25 | 7% / 3% | 37% / 55% | 52% / 59% |
| Willow | 1592 | 0.61 / 1.33 | 640 / 664 | 2 / 3 | 9% / 5% | 25% / 39% | 47% / 54% |
| Ryth | 725 | 0.58 / 1.89 | 463 / 687 | 13 / 13 | 10% / 4% | 40% / 60% | 43% / 61% |
| Marcella | 379 | 0.55 / 2.05 | 505 / 720 | 12 / 15 | 8% / 3% | 41% / 61% | 53% / 73% |

*Outnumbered = more enemies than allies + self within 8 at the start of the death round (champion kills only).
Bags lost at own deaths per game, W / L: r1-150 2/4, r151-400 7/38, r401-800 23/138, r801+ 9/77.

## Prism (2,227 games with a Prism)

Focus at r200 / r300 / r400 / r600, W vs L: 323/284, 496/403, 676/507, 950/600. Carried gems (median): 122/100,
210/158, 310/211, 440/209. Prism never died: W 91%, L 42%; first death (when it died) median r457 (W) and r467 (L).
W's Prism scores 52% of W's tributed gems, L's 18%. W's Prism per game (games ending on 1000 gems): 1.07 completed
tributes (median 547 gems, IQR 355-734), plus 1.94 cancelled by stun, 1.41 cancelled by itself, 0.95 by lock.
L's Prism completes 0.2 tributes a game: its gems mostly die with it. The game-ending tribute is W's Prism's in 56%.

## E. Map classes (whole-game W-L components; mutations pooled, 640 games over 126 bases)

| preset | n | b0 med | end med | farm | fight | b0..+100 farm / fight | games with abs(fight) > abs(farm) | team A wins | to r2000 |
|---|---|---|---|---|---|---|---|---|---|
| ladder | 1120 | 418 | 767 | +151 | +458 | +67 / +253 | 49% | 47% | 3% |
| mutation | 640 | 326 | 746 | +256 | +381 | +87 / +211 | 45% | 50% | 4% |
| classic | 300 | 415 | 752 | +162 | +512 | +74 / +292 | 54% | 48% | 3% |
| tiny | 60 | 248 | 816 | +394 | +465 | +82 / +157 | 37% | 32% | 3% |
| monolith | 50 | 505 | 820 | +159 | +595 | +75 / +308 | 42% | 56% | 10% |
| huge | 40 | 476 | 642 | +90 | +236 | +73 / +141 | 52% | 55% | 0% |
| lakes | 40 | 433 | 826 | +207 | +468 | +66 / +330 | 48% | 50% | 8% |
| contested-centre | 40 | 235 | 788 | +324 | +368 | +77 / +193 | 45% | 35% | 0% |
| small-brawl | 40 | 426 | 1032 | +306 | +756 | +87 / +305 | 60% | 52% | 8% |
| monolith-only | 30 | 886 | 1215 | +555 | +50 | +206 / +86 | 13% | 50% | 3% |
| shared-gems | 30 | 402 | 1387 | +724 | +73 | +127 / +43 | 3% | 43% | 20% |
| maze | 30 | 440 | 884 | +190 | +425 | +47 / +365 | 60% | 60% | 3% |
| vaults | 30 | 570 | 822 | +121 | +369 | +82 / +275 | 47% | 60% | 0% |
| altar-poor | 20 | 438 | 766 | +38 | +500 | +38 / +371 | 65% | 45% | 0% |
| lanes | 20 | 558 | 804 | +141 | +269 | +80 / +145 | 50% | 45% | 5% |

The camp component is between -10 and +20 on every class. Farm-decided: shared-gems, monolith-only (and no-Prism
games). Fight-decided: altar-poor, maze, small-brawl, classic. Earliest breaks: contested-centre (235), tiny (248),
mutations (326). Latest: monolith-only (886), vaults (570), lanes (558). Classes under 30 games are noise.

## F. Side asymmetry

Team A (moves first in odd rounds) wins 48.2% [46.2, 50.0] of 2,560 games. By symmetry: horizontal 44.9% [40.9,
48.6] (n=597), rotational 48.8% (n=1483), vertical 50.2% (n=480). By size 47.7-48.5% and by picks 47.8-48.8%: flat.
r2000 games: 44.9% (n=98). The effect is small (about 2 points overall, maybe 5 on horizontal maps).

## G. Other large or surprising things

- **Unworked supply.** Group classes over the whole game (both teams):

| class | groups | up share | up and untouched (monsters alive) | cleared, unheld | captures per 1000 group-rounds | share of capture gems |
|---|---|---|---|---|---|---|
| wolf-only | 1478 | 82% | 89% | 1% | 4.7 | 1% |
| wolf+clusters | 19849 | 68% | 81% | 2% | 6.5 | 28% |
| elk | 9514 | 59% | 76% | 2% | 7.0 | 34% |
| golem | 1909 | 68% | 85% | 1% | 4.3 | 8% |
| gem clusters | 9045 | 48% | 71% | 11% | 10.6 | 23% |
| gold clusters | 8488 | 66% | 82% | 10% | 6.8 | 0% |
| monolith | 1427 | 91% | 96% | 0% | 0.7 | 4% |

  Monoliths are almost never taken (1,245 untouched-up rounds per capture), and golems and wolf-only groups rarely.
  Cleared gold clusters wait 9.8 rounds per capture to be held (gem clusters 4.8, everything else about 2).
- **Champions who don't farm.** Capture gems per 1000 alive rounds: Prism 637, Vesper 270, Vendetta 235, Marcella
  234, Stellar 203, Varg 185, Ryth 175, Tavi 154, Ren 141, Heart of Ruin 128, Issac 122, Cassi 106, **Willow 19**.
  Willow walks 67% of its alive time and deals 7.8 camp damage a round, against the Prism's 42 and Vesper's 38.
  Cassi and Issac (picked in 98% of games) are poor farmers, at 12% dead time each.
- **Hoarding.** At the end, 394 gems on average are still carried (both teams); 40% of games end with 300+. In the
  98 r2000 games, W carries 1,200 gems at the end against 613 tributed: its Prism attempts and has cancelled 27
  tributes a game (locks, stuns). Hold a bag of 1,000+ and the channel runs 100+ turns, so it never completes.
- **Gold piles up.** W ends with 893 unspent gold (L 297); W has 457 unspent at r600.
- **Tribute lag.** At r400, W has tributed 204 of its 555 collected gems, L 157 of 415.

## Caveats

- In a mirror, W vs L comparisons partly measure winning: everything after b0 is mostly consequence. Read causes
  only from the pre-break and r1-150 windows.
- The bootstrap resamples games. Each distinct game is one map, and both sides' copies are deduplicated.
- Zones use extract.mjs's `side`: Chebyshev distance from the tile centroid to each spawn centre, not walking
  distance, so "mid" is only exactly equidistant groups. The idle-supply zones for W and L mirror each other.
- "Unworked" means a round with no damage to the group's monsters and no capture hold. A group being walked to
  counts as unworked.
- The labour classes are macro.py's (first match wins). Cohesion counts Cassi and Issac as two bodies. Ren's
  reflected camp damage is left out of camp damage.
- Shard-equivalents count an emblem as 5 shards (Greed 25). They come from the per-round item arrays.
- For 256 of the 2,560 maps the suite's `index.json` has no entry; their presets come from the file names.

## Follow-up: champion roles (r1-400) and walking (`scripts/roles.py`, raw output `data/roles_raw.md`)

Pooled over both teams and all 2,560 games. Labour is given as % of alive rounds (macro.py classes); dead is % of all rounds.

| champion | bodies | walk | walk_bag | camp | hold | tribute | recall | fight | wait_camp | idle+spawn | dead |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Prism | 4454 | 7.2 | 52.6 | 18.9 | 7.3 | 0.7 | 5.8 | 2.8 | 2.4 | 2.2 | 2.3 |
| Vesper Vale | 3214 | 18.6 | 29.2 | 31.1 | 4.7 | 1.4 | 7.6 | 2.7 | 2.0 | 2.5 | 1.7 |
| Vendetta | 1264 | 20.3 | 30.9 | 28.7 | 5.4 | 1.3 | 7.6 | 1.0 | 1.8 | 2.8 | 1.9 |
| Marcella | 758 | 30.4 | 31.3 | 14.1 | 7.3 | 2.1 | 4.9 | 5.5 | 2.3 | 1.9 | 4.1 |
| Willow | 3184 | 64.8 | 6.2 | 18.0 | 0.6 | 0.1 | 2.3 | 1.0 | 2.8 | 4.2 | 2.8 |
| Cassi | 5000 | 39.4 | 21.7 | 24.5 | 3.2 | 0.6 | 3.6 | 2.2 | 2.7 | 2.1 | 6.6 |
| Issac | 5000 | 32.6 | 23.3 | 26.3 | 4.4 | 0.8 | 5.0 | 2.6 | 2.1 | 2.7 | 6.6 |
| Ryth | 1450 | 27.9 | 26.7 | 23.9 | 5.5 | 1.2 | 5.5 | 5.4 | 1.8 | 1.6 | 4.1 |
| Heart of Ruin | 1550 | 29.8 | 25.2 | 26.3 | 4.8 | 0.9 | 4.4 | 4.6 | 1.7 | 2.1 | 3.7 |
| Varg | 786 | 29.8 | 28.0 | 27.5 | 3.8 | 1.0 | 5.4 | 1.3 | 1.5 | 1.6 | 1.6 |
| Stellar | 164 | 23.6 | 31.6 | 25.6 | 5.2 | 1.2 | 5.3 | 1.6 | 3.3 | 2.5 | 2.5 |
| Ren | 658 | 23.7 | 28.0 | 28.8 | 5.0 | 0.9 | 5.6 | 3.0 | 2.1 | 2.6 | 3.0 |
| Tavi | 520 | 33.6 | 22.0 | 24.3 | 6.8 | 1.3 | 3.1 | 4.9 | 2.0 | 1.7 | 5.5 |

| champion | camp dmg / alive rd | real recalls / 100 alive (completed) | hp share at recall start mean / median | deaths / 1000 alive | gold earned r300 / r600 | gold spent r300 / r600 | dist to own Prism |
|---|---|---|---|---|---|---|---|
| Prism | 42.5 | 1.62 (1.30) | 0.84 / 1.00 | 0.44 | 685 / 1588 | 588 / 1341 | - |
| Vesper Vale | 31.0 | 2.23 (1.84) | 0.81 / 0.94 | 0.32 | 774 / 1771 | 729 / 1663 | 14.0 |
| Vendetta | 31.8 | 2.04 (1.80) | 0.65 / 0.69 | 0.36 | 419 / 972 | 396 / 912 | 16.7 |
| Marcella | 10.5 | 1.38 (1.09) | 0.78 / 0.92 | 0.83 | 272 / 556 | 236 / 506 | 11.3 |
| Willow | 10.4 | 0.63 (0.53) | 0.69 / 0.74 | 0.55 | 16 / 35 | 12 / 29 | 8.4 |
| Cassi | 16.1 | 0.95 (0.84) | 0.76 / 0.92 | 0.69 | 72 / 168 | 59 / 152 | 11.8 |
| Issac | 13.4 | 1.34 (1.17) | 0.64 / 0.64 | 0.64 | 80 / 191 | 70 / 177 | 13.4 |
| Ryth | 23.9 | 1.51 (1.26) | 0.71 / 0.80 | 0.82 | 303 / 606 | 278 / 572 | 12.1 |
| Heart of Ruin | 15.3 | 1.17 (1.05) | 0.72 / 0.84 | 0.71 | 157 / 341 | 140 / 314 | 18.9 |
| Varg | 31.5 | 1.48 (1.28) | 0.69 / 0.76 | 0.30 | 261 / 611 | 240 / 565 | 15.4 |
| Stellar | 33.4 | 1.46 (1.30) | 0.77 / 0.91 | 0.54 | 206 / 506 | 190 / 473 | 10.1 |
| Ren | 18.1 | 1.49 (1.33) | 0.66 / 0.68 | 0.59 | 229 / 487 | 211 / 461 | 17.4 |
| Tavi | 23.6 | 0.85 (0.73) | 0.72 / 0.80 | 1.14 | 278 / 651 | 270 / 641 | 10.5 |

A real recall is one that completes or lasts 2+ rounds, so recall feints are left out. The hp share is read at the
end of the round before the start. Gold is per champion (Cassi and Issac each have their own). The Prism distance
is Chebyshev, over rounds when both bodies are alive.

- The Prism walks carrying gems 53% of its alive time (it is the team's bag). It recalls at full health (median 1.00),
  so it recalls to shop or reposition, not to heal.
- Willow walks 65% of its alive time, earns 35 gold by r600 and stays closest to the Prism (8.4). Cassi and Issac
  earn under 200 gold by r600 and are dead 6.6% of r1-400.
- Vendetta, Issac and Ren recall at about 0.65 health, the others at 0.7-0.95.

Walk legs (runs of walk / walk_bag rounds), by the class of the round that ends them. Each cell is the share of walk
rounds / mean leg length (rounds).

| phase | walk rounds | camp hit | hold | tribute/altar | spawn/recall | fight | wait by camp | died | regroup | other |
|---|---|---|---|---|---|---|---|---|---|---|
| r1-150 | 2.45M | 58% / 8.7 | 5% / 3.2 | 2% / 10.2 | 6% / 4.8 | 12% / 6.5 | 13% / 13.0 | 0% / 7.1 | 1% / 16.0 | 3% / 8.3 |
| r151-400 | 3.95M | 45% / 8.9 | 5% / 3.2 | 6% / 13.4 | 7% / 4.6 | 13% / 7.0 | 19% / 13.0 | 0% / 8.4 | 1% / 18.0 | 4% / 10.1 |
| r401-800 | 4.61M | 35% / 9.5 | 5% / 3.1 | 9% / 12.7 | 7% / 5.6 | 16% / 8.4 | 20% / 13.6 | 1% / 10.9 | 2% / 22.5 | 6% / 11.5 |

"Regroup" means the leg ends within 3 of an ally who was more than 8 away when it began (checked only when no other
class applies). "Wait by camp" legs end standing next to a live or respawning group without hitting it. They take
13-20% of walk rounds and are the longest legs after regroups (13 rounds).

Legs ending at a camp hit or a hold: walking steps from the leg's start to the chosen group, against the nearest
*other* group that was up (alive or cleared, not respawning) and unworked (no hit, no hold) at the leg's start.

| phase | legs | chosen median / mean | nearest idle-up median | a nearer idle-up group existed | one within half the chosen distance | same, excluding Monoliths |
|---|---|---|---|---|---|---|
| r1-150 | 201k | 5 / 9.4 | 9 | 31% | 14% | 14% |
| r151-400 | 263k | 4 / 8.7 | 10 | 25% | 12% | 11% |
| r401-800 | 237k | 4 / 8.6 | 10 | 25% | 12% | 12% |

By chosen distance, the share of legs with a non-Monolith idle-up group within half that distance: 0-5 steps 3%,
6-10 steps 13%, 11-20 steps 23%, 21-40 steps 34%, 41+ steps 52% (n = 385k, 126k, 116k, 58k, 16k). Most legs to a camp are short
repositioning steps. The long walks are the ones that pass up nearer free groups. Those groups may be gold-only,
on the enemy half, or about to be taken by an ally: the metric does not judge value or safety.

From a capture payout to the recipient's next camp hit: median 17 rounds (IQR 8-32, mean 26.4), over 287k payouts.
Another 14k payouts are never followed by a hit.

Not computed: leg purpose by intent (it is read from the round that ends the leg, so a walk interrupted by a fight
counts as "fight"); value- or safety-weighted alternative groups; walking distance from mid-leg positions.

## Follow-up: where the Prism's walking goes (`scripts/prismwalk.py`, raw output `data/prismwalk_raw.md`)

Both teams pooled. Each cell gives the share of that champion's walk rounds / mean leg length. A leg's purpose is the
class of the round that ends it, as in roles.py.

| champion | phase | walk % of alive | camp hit | hold | tribute/altar | spawn/recall | fight | wait by camp | regroup | other |
|---|---|---|---|---|---|---|---|---|---|---|
| Prism | r1-400 | 61% | 51% / 7.4 | 14% / 3.9 | 1% / 15.2 | 6% / 3.2 | 13% / 5.5 | 14% / 14.1 | 0% / 15.6 | 1% / 13.3 |
| Prism | r401-800 | 59% | 35% / 8.0 | 11% / 3.4 | 6% / 12.2 | 5% / 3.8 | 19% / 7.3 | 19% / 13.9 | 1% / 25.1 | 3% / 10.1 |
| Vesper | r1-400 | 49% | 50% / 7.0 | 7% / 1.8 | 8% / 11.4 | 8% / 3.1 | 10% / 5.6 | 14% / 10.2 | 1% / 13.9 | 3% / 9.6 |
| Vesper | r401-800 | 56% | 34% / 6.7 | 6% / 1.9 | 13% / 9.8 | 7% / 3.6 | 16% / 7.4 | 17% / 10.1 | 2% / 21.4 | 5% / 10.5 |

Captures the Prism shared, split by who dealt most of the group's monster damage that cycle:

| phase | Prism dealt most | an ally dealt most ("collection") | an enemy dealt most |
|---|---|---|---|
| r1-400 | 34,280 captures (69%); 27.4 gems each to the Prism; Prism did 75% of the damage | 14,303 (29%); 21.4 gems; Prism did 16% | 1,437 (3%) |
| r401-800 | 21,854 (79%); 27.7 gems; Prism did 86% | 4,773 (17%); 21.3 gems | 1,097 (4%) |

Collections are short trips:

| phase | Prism walk leg into the tiles, median / mean | Prism's distance at the clear (median) | clear to Prism arrival, median / mean | clear to payout (median) | clearing ally waiting on or within 2 of the tiles until the Prism arrives, median / mean | ally waited 3+ rounds |
|---|---|---|---|---|---|---|
| r1-400 | 4 / 6.5 | 2 | 3 / 4.3 | 7 | 2 / 2.2 | 36% |
| r401-800 | 4 / 7.3 | 3 | 3 / 5.9 | 7 | 2 /2.4 | 40% |

Completed recalls. A shop trip is a completed recall that started at 90% health or more:

| champion | phase | completed recalls per champion-game | started at >= 90% hp | of those, bought on spawn | gold per buying trip, median / mean | recall start to next camp hit, median / mean |
|---|---|---|---|---|---|---|
| Prism | r1-400 | 5.06 | 64% | 90% | 150 / 172 | 19 / 24.1 |
| Prism | r401-800 | 2.18 | 61% | 89% | 180 / 253 | 19 / 27.3 |
| Vesper | r1-400 | 7.24 | 55% | 91% | 150 / 158 | 16 / 21.3 |
| Vesper | r401-800 | 4.87 | 63% | 88% | 150 / 195 | 17 / 23.1 |

Prism alive rounds within 2 of an altar while not channelling a tribute:
- r1-400: 3.3% of alive rounds (12.8 a game), carrying a mean bag of 149. Of these rounds, 53% are walk_bag, 16% camp and 12% fight.
- r401-800: 5.9% (15.6 a game), carrying 456. Only 9% of these rounds are wait_altar (standing still); 49% are walk_bag and 16% fight.

Reading:
- Collections and altar waiting are small costs.
- The Prism's walking goes mostly to camp-hit legs (7-8 rounds each).
- Long walks to a camp that is still up or respawning end in waiting: 14-19% of walk rounds, legs of about 14 rounds.
- In r1-400 the Prism makes about 3.2 healthy shop trips (about 2.9 that buy), each spending a median 150 gold (5 shards, one emblem). Each trip costs a median 19 rounds from recall start to the next camp hit, about 60-75 of its 400 rounds.

Not computed:
- Whether a trip's purchase could have waited, or been bundled with another trip.
- How long the walk back from spawn is, separately from the 19 rounds (they include the 5-turn channel).
- Damage shares count champion damage to monsters only (no Ren reflection).
- "Arrival" is the first round of the Prism's unbroken stay on the tiles up to the payout.
